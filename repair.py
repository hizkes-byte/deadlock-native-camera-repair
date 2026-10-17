"""Restore each supported mod hero's cameras from the currently installed base game."""
import argparse, datetime, hashlib, json, os, pathlib, re, shutil, struct, subprocess, sys, uuid, zlib

ROOT = pathlib.Path(__file__).resolve().parent

def digest(path):
    h = hashlib.sha256()
    with pathlib.Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(4 * 1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()

def current_digest(path):
    return digest(path) if pathlib.Path(path).exists() else None

def native_startup(citadel, output_dir):
    target = citadel / 'cfg/autoexec.cfg'
    if not target.parent.is_dir():
        raise ValueError('Game cfg folder not found')
    old = target.read_bytes() if target.exists() else b''
    if old.startswith((b'\xff\xfe', b'\xfe\xff')):
        raise ValueError('UTF-16 autoexec is not supported; convert it to UTF-8 first')
    text = old.decode('latin1')
    begin = '// BEGIN CODEX NATIVE CAMERA MODE'
    end = '// END CODEX NATIVE CAMERA MODE'
    pattern = r'(?ms)^' + re.escape(begin) + r'\r?\n.*?^' + re.escape(end) + r'(?:\r?\n|$)'
    if (begin in text or end in text) and not re.search(pattern, text):
        raise ValueError('Incomplete native camera startup block')
    clean = re.sub(pattern, '', text)
    separator = '\r\n' if clean and not clean.endswith('\n') else ''
    new = (clean + separator + begin + '\r\ncitadel_camera_overrides_enabled "false"\r\n' + end + '\r\n').encode('latin1')
    if new == old:
        return None
    output = output_dir / 'autoexec.cfg'
    output.write_bytes(new)
    return dict(kind='configuration', source=str(target), output=str(output), before=current_digest(target), after=digest(output))

def write_json(path, value):
    pathlib.Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')

class VPK:
    def __init__(self, path):
        self.path = pathlib.Path(path)
        self.entries = {}
        with self.path.open('rb') as stream:
            magic, self.version, self.tree_size = struct.unpack('<III', stream.read(12))
            if magic != 0x55AA1234 or self.version not in (1, 2):
                raise ValueError('Not a supported VPK v1/v2')
            self.header_size = 28 if self.version == 2 else 12
            self.sections = struct.unpack('<4I', stream.read(16)) if self.version == 2 else None
            self.start = self.header_size + self.tree_size
            self.data_size = self.sections[0] if self.sections else self.path.stat().st_size - self.start
            tree = stream.read(self.tree_size)
        pos = 0
        def string():
            nonlocal pos
            end = tree.index(b'\0', pos)
            value = tree[pos:end].decode('utf-8')
            pos = end + 1
            return value
        while (ext := string()):
            while (folder := string()):
                while (name := string()):
                    entry_pos = pos
                    crc, preload, archive, offset, length, terminator = struct.unpack_from('<IHHIIH', tree, pos)
                    pos += 18
                    if terminator != 65535:
                        raise ValueError('Invalid VPK entry')
                    pre = tree[pos:pos + preload]
                    pos += preload
                    key = ('' if folder == ' ' else folder + '/') + name + ('.' + ext if ext != ' ' else '')
                    self.entries[key] = dict(crc=crc, preload=pre, archive=archive, offset=offset, length=length,
                                             entry_pos=self.header_size + entry_pos)
    def read(self, key):
        e = self.entries[key]
        if e['archive'] == 32767:
            source = self.path
            offset = self.start + e['offset']
        else:
            if not self.path.name.endswith('_dir.vpk'):
                raise ValueError('External VPK chunks require a _dir.vpk index')
            source = self.path.with_name(self.path.name[:-8] + f"_{e['archive']:03}.vpk")
            offset = e['offset']
        with source.open('rb') as stream:
            stream.seek(offset)
            value = e['preload'] + stream.read(e['length'])
        if len(value) != len(e['preload']) + e['length'] or zlib.crc32(value) != e['crc']:
            raise ValueError('Resource CRC mismatch: ' + key)
        return value

def rebuild_model(source, blocks):
    raw = pathlib.Path(source).read_bytes()
    size, header, version, relative, count = struct.unpack_from('<IHHII', raw)
    if size != len(raw) or header != 12:
        raise ValueError('Unsupported model header or trailing payload')
    table = 8 + relative
    result = bytearray(raw[:table + 12 * count])
    audit = []
    ends = []
    for i in range(count):
        position = table + i * 12
        tag, rel, length = struct.unpack_from('<4sII', raw, position)
        start = position + 4 + rel
        old = raw[start:start + length]
        ends.append(start + length)
        replacement = pathlib.Path(blocks) / f'{tag.decode()}-{i}.bin'
        data = replacement.read_bytes() if replacement.exists() else old
        if data != old and tag not in (b'MDAT', b'DATA'):
            raise ValueError('Unexpected non-camera resource block edit')
        while len(result) % 16:
            result.append(0)
        struct.pack_into('<II', result, position + 4, len(result) - position - 4, len(data))
        result.extend(data)
        audit.append(dict(index=i, block=tag.decode(), unchanged=(data == old)))
    if max(ends) != len(raw):
        raise ValueError('Unsupported trailing model data')
    struct.pack_into('<I', result, 0, len(result))
    return bytes(result), audit

def rebuild_vpk(source, replacements, output):
    vpk = VPK(source)
    with pathlib.Path(source).open('rb') as stream:
        prefix = bytearray(stream.read(vpk.start + vpk.data_size))
    tail = bytearray()
    for key, data in replacements.items():
        e = vpk.entries[key]
        if e['preload']:
            raise ValueError('Preloaded model entries are not supported')
        struct.pack_into('<IHHIIH', prefix, e['entry_pos'], zlib.crc32(data), 0, 32767,
                         vpk.data_size + len(tail), len(data), 65535)
        tail.extend(data)
    if vpk.version == 2:
        struct.pack_into('<4I', prefix, 12, vpk.data_size + len(tail), 0, 48, 0)
        partial = prefix + tail
        checksums = hashlib.md5(partial[28:vpk.start]).digest() + hashlib.md5(b'').digest()
        tail.extend(checksums + hashlib.md5(partial + checksums).digest())
    with pathlib.Path(output).open('wb') as stream:
        stream.write(prefix)
        stream.write(tail)
    checked = VPK(output)
    # Unchanged entries retain their bytes, offsets and CRCs; validate each payload.
    for key in vpk.entries:
        actual = checked.read(key)
        if key in replacements:
            if actual != replacements[key]:
                raise ValueError('Changed resource verification failed')
        elif actual != vpk.read(key):
            raise ValueError('Unrelated resource changed: ' + key)

def locate_citadel():
    import winreg
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r'Software\Valve\Steam') as key:
        steam = pathlib.Path(winreg.QueryValueEx(key, 'SteamPath')[0])
    roots = [steam]
    folders = steam / 'steamapps/libraryfolders.vdf'
    if folders.exists():
        roots += [pathlib.Path(p.replace('\\\\', '\\')) for p in re.findall(r'"path"\s+"([^"]+)"', folders.read_text(encoding='utf-8'))]
    for root in roots:
        manifest = root / 'steamapps/appmanifest_1422450.acf'
        if manifest.exists():
            match = re.search(r'"installdir"\s+"([^"]+)"', manifest.read_text(encoding='utf-8'))
            if match:
                candidate = root / 'steamapps/common' / match[1] / 'game/citadel'
                if (candidate / 'pak01_dir.vpk').exists():
                    return candidate.resolve()
    raise ValueError('Deadlock not found; pass --citadel with its game/citadel folder')

def locate_pwsh():
    bundled = pathlib.Path.home() / '.cache/codex-runtimes/codex-primary-runtime/dependencies/native/powershell/pwsh.exe'
    path = bundled if bundled.exists() else shutil.which('pwsh')
    if not path:
        raise ValueError('PowerShell 7.6 (.NET 10) is required')
    return str(path)

def ensure_game_closed(pwsh):
    result = subprocess.run([pwsh, '-NoProfile', '-Command',
                             'if(Get-Process -Name deadlock,citadel -ErrorAction SilentlyContinue){exit 2}'], check=False)
    if result.returncode:
        raise ValueError('Close Deadlock before repairing MOD files')

def run_ps(pwsh, script, *arguments):
    subprocess.run([pwsh, '-NoProfile', '-File', str(ROOT / script), *map(str, arguments)], check=True)

def apply_files(changes, run, pwsh):
    ensure_game_closed(pwsh)
    for item in changes:
        if current_digest(item['source']) != item['before'] or digest(item['output']) != item['after']:
            raise ValueError('MOD or staged file changed; run the tool again')
    backup_dir = run / 'backups'
    backup_dir.mkdir()
    stages = []
    committed = []
    try:
        for item in changes:
            source = pathlib.Path(item['source'])
            item['backup'] = str(backup_dir / source.name) if item['before'] is not None else None
            if item['backup']:
                shutil.copyfile(source, item['backup'])
                if digest(item['backup']) != item['before']:
                    raise ValueError('Backup verification failed')
            stage = source.with_name(source.name + '.native-camera-' + uuid.uuid4().hex + '.tmp')
            stages.append((item, stage))
            shutil.copyfile(item['output'], stage)
            if digest(stage) != item['after']:
                raise ValueError('Staged replacement verification failed')
        ensure_game_closed(pwsh)
        for item, stage in stages:
            if current_digest(item['source']) != item['before']:
                raise ValueError('MOD Manager changed a file during repair')
            os.replace(stage, item['source'])
            committed.append(item)
        for item in committed:
            if digest(item['source']) != item['after']:
                raise ValueError('Installed archive verification failed')
    except Exception:
        for item in committed:
            if item['backup']:
                shutil.copyfile(item['backup'], item['source'])
            else:
                pathlib.Path(item['source']).unlink()
        raise
    finally:
        for _, stage in stages:
            if stage.exists():
                stage.unlink()

def restore(report_path, pwsh):
    ensure_game_closed(pwsh)
    report = json.loads(pathlib.Path(report_path).read_text(encoding='utf-8'))
    if not report.get('applied'):
        raise ValueError('This report does not describe an installed repair')
    changes = report['archives']
    for item in changes:
        if digest(item['source']) != item['after']:
            raise ValueError('MOD changed after repair; restore will not overwrite it: ' + item['source'])
        if item['backup'] and digest(item['backup']) != item['before']:
            raise ValueError('Backup hash mismatch')
    stages = []
    committed = []
    try:
        for item in changes:
            target = pathlib.Path(item['source'])
            if item['backup'] is None:
                stages.append((item, None))
                continue
            stage = target.with_name(target.name + '.native-restore-' + uuid.uuid4().hex + '.tmp')
            stages.append((item, stage))
            shutil.copyfile(item['backup'], stage)
            if digest(stage) != item['before']:
                raise ValueError('Restore stage hash mismatch')
        for item, stage in stages:
            if digest(item['source']) != item['after']:
                raise ValueError('MOD changed during restore')
            if stage is None:
                pathlib.Path(item['source']).unlink()
            else:
                os.replace(stage, item['source'])
            committed.append(item)
        for item in committed:
            if current_digest(item['source']) != item['before']:
                raise ValueError('Restored file hash mismatch')
    except Exception:
        for item in committed:
            shutil.copyfile(item['output'], item['source'])
        raise
    finally:
        for _, stage in stages:
            if stage is not None and stage.exists():
                stage.unlink()
    report['restored'] = True
    write_json(report_path, report)
    print('Restore completed and verified.', flush=True)

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--citadel', type=pathlib.Path)
    parser.add_argument('--addons', type=pathlib.Path)
    parser.add_argument('--runs', type=pathlib.Path, default=ROOT / 'runs')
    parser.add_argument('--include-disabled', action='store_true')
    parser.add_argument('--no-startup', action='store_true', help='Do not add the native-camera startup setting')
    parser.add_argument('--apply', action='store_true')
    parser.add_argument('--restore', type=pathlib.Path)
    parser.add_argument('--restore-latest', action='store_true')
    args = parser.parse_args()
    pwsh = locate_pwsh()
    if args.restore or args.restore_latest:
        report_path = args.restore
        if args.restore_latest:
            reports = sorted(args.runs.glob('*/report.json'), reverse=True)
            report_path = next((p for p in reports if (r := json.loads(p.read_text(encoding='utf-8'))).get('applied') and not r.get('restored')), None)
            if report_path is None:
                raise ValueError('No installed repair to restore')
        restore(report_path, pwsh)
        return
    citadel = (args.citadel or locate_citadel()).resolve()
    addons = (args.addons or citadel / 'addons').resolve()
    if args.apply:
        ensure_game_closed(pwsh)
    original_path = citadel / 'pak01_dir.vpk'
    if addons == citadel or not addons.is_dir():
        raise ValueError('The MOD directory must be a separate existing folder')
    original = VPK(original_path)
    original_stamp = (original_path.stat().st_size, original_path.stat().st_mtime_ns)
    run = args.runs.resolve() / (datetime.datetime.now().strftime('%Y%m%d-%H%M%S') + '-' + uuid.uuid4().hex[:6])
    run.mkdir(parents=True)
    model_dir = run / 'models'
    model_dir.mkdir()
    jobs, records, archives = [], [], {}
    files = sorted(addons.glob('*.vpk'))
    if not args.include_disabled:
        files = [p for p in files if re.fullmatch(r'pak\d+_dir\.vpk', p.name, re.I)]
    files = [p for p in files if not re.search(r'_\d{3}\.vpk$', p.name, re.I)]
    if not files:
        raise ValueError('No MOD VPK indexes found')
    for path in files:
        print('Scanning ' + path.name, flush=True)
        try:
            archive = VPK(path)
            if any(e['archive'] != 32767 for e in archive.entries.values()):
                records.append(dict(id=len(records), archive=path.name, status='unsupported', reason='Multi-chunk MOD VPKs require repacking before repair'))
                continue
            archives[path.name] = dict(path=path, index=archive, before=digest(path))
            for key in archive.entries:
                if not key.endswith('.vmdl_c') or not key.startswith('models/heroes'):
                    continue
                record = dict(id=len(records), archive=path.name, model=key)
                records.append(record)
                if key not in original.entries:
                    record.update(status='unsupported', reason='No exact native model path match')
                    continue
                if archive.entries[key]['preload']:
                    record.update(status='unsupported', reason='Preloaded model entry unsupported')
                    continue
                folder = model_dir / str(record['id'])
                folder.mkdir()
                try:
                    mod = folder / 'mod.vmdl_c'
                    native = folder / 'native.vmdl_c'
                    mod.write_bytes(archive.read(key))
                    native.write_bytes(original.read(key))
                    jobs.append(dict(id=record['id'], mod=str(mod), original=str(native), blocks=str(folder / 'blocks')))
                except Exception as exc:
                    record.update(status='unsupported', reason=str(exc))
        except Exception as exc:
            print('Skipped archive: ' + str(exc), flush=True)
            records.append(dict(id=len(records), archive=path.name, status='unsupported', reason=str(exc)))
    jobs_path = run / 'jobs.json'
    result_path = run / 'results.json'
    write_json(jobs_path, jobs)
    if jobs:
        run_ps(pwsh, 'Worker.ps1', '-JobsPath', jobs_path, '-ResultPath', result_path)
        for result in json.loads(result_path.read_text(encoding='utf-8-sig')):
            records[result['id']].update(result)
    replacements, verify_jobs = {}, []
    for job in jobs:
        record = records[job['id']]
        if record.get('status') != 'changed':
            continue
        data, audit = rebuild_model(job['mod'], job['blocks'])
        patched = pathlib.Path(job['mod']).with_name('patched.vmdl_c')
        patched.write_bytes(data)
        record['blockValidation'] = audit
        replacements.setdefault(record['archive'], {})[record['model']] = data
        verify_jobs.append(dict(job, patched=str(patched)))
    if verify_jobs:
        verification_path = run / 'verify.json'
        write_json(verification_path, verify_jobs)
        run_ps(pwsh, 'Verify.ps1', '-JobsPath', verification_path)
    output_dir = run / 'patched'
    output_dir.mkdir()
    changes = []
    for name, models in replacements.items():
        source = archives[name]['path']
        output = output_dir / name
        rebuild_vpk(source, models, output)
        changes.append(dict(kind='archive', source=str(source), output=str(output), before=archives[name]['before'], after=digest(output), models=list(models)))
    startup_change = None if args.no_startup else native_startup(citadel, output_dir)
    if startup_change:
        changes.append(startup_change)
    if (original_path.stat().st_size, original_path.stat().st_mtime_ns) != original_stamp:
        raise ValueError('The base game updated during the repair; run again')
    for archive in archives.values():
        if digest(archive['path']) != archive['before']:
            raise ValueError('MOD files changed during the repair; close the manager and run again')
    report = dict(nativeArchive=str(original_path), nativeStamp=original_stamp, addons=str(addons), applied=False, models=records, archives=changes)
    report_path = run / 'report.json'
    write_json(report_path, report)
    if args.apply and changes:
        apply_files(changes, run, pwsh)
        report['applied'] = True
        write_json(report_path, report)
    summary = {status: sum(r.get('status') == status for r in records) for status in ('changed', 'native', 'unsupported')}
    print('RESULT: ' + json.dumps(summary) + '; archives=' + str(sum(c.get('kind') == 'archive' for c in changes)) + '; startupChanged=' + str(bool(startup_change)) + '; applied=' + str(report['applied']), flush=True)
    print('Report: ' + str(report_path), flush=True)
    for record in records:
        if record.get('status') == 'unsupported':
            print('UNSUPPORTED: ' + record['archive'] + ' ' + record.get('model', '') + ': ' + record['reason'], flush=True)

if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        print('ERROR: ' + str(error), file=sys.stderr, flush=True)
        sys.exit(1)
