# Deadlock Native Camera Repair Tool

**Restore each hero's own original camera data instead of imposing one camera position on every hero.**

Custom scripts and documentation were primarily generated and revised by **OpenAI GPT through Codex** at the publisher's request, using third-party Source 2 parsing libraries. This is unofficial software, **not guaranteed to be ban-safe**. Read the [disclaimer and GPT disclosure](DISCLAIMER.en.md) before use.

[中文使用说明](README.zh-CN.md) · Updated: October 17, 2026

## 1. Requirements

- Windows, Steam, an installed copy of Deadlock, and the hero mods to repair.
- **Python 3.10+ and PowerShell 7.6, based on .NET 10.** Windows PowerShell 5.1 alone, or installing .NET 10 without a compatible PowerShell, is insufficient.
- The launcher prefers an existing supported Codex runtime bundle. Otherwise, `python.exe` and `pwsh.exe` must be accessible from the command line. Runtimes are not included or installed automatically.
- Sufficient disk space: scans create extracted models and repaired copies, and installation saves complete VPK backups. Usage can exceed the original mod size.

**Extract the entire ZIP** into a writable folder you can keep. Do not run inside the ZIP or copy just one `.cmd` file. Keep `lib/`, `licenses/` and the other included files.

## 2. Recommended workflow

1. **Exit Deadlock and close your mod manager.** Pause updates and keep an independent backup of important mods.
2. Run `Scan.cmd`. It locates the game and generates a report and repaired copies. **It does not replace game files or change startup configuration.**
3. Read the summary and the `Report:` path, especially `UNSUPPORTED` messages. Completion does not mean every model is supported.
4. Run `Repair.cmd`. It rechecks current files, verifies repaired copies, backs up originals, installs repairs, and disables global camera overrides.
5. After successful completion, launch the game and test movement, standing, crouching, aiming, wall proximity and transformations in the sandbox. Sandbox testing does not establish that online use is free of account penalties.

Stop using the earlier uniform global-camera workaround to avoid competing startup settings.

## 3. Launchers

| File | Purpose |
| --- | --- |
| `Scan.cmd` | Scan the default scope and generate a report and repaired copies without installing. |
| `Repair.cmd` | Back up and repair the default scope, and disable global camera overrides. |
| `Repair-Including-Disabled.cmd` | Expand to other single-file VPKs in addons, potentially modifying disabled mods. Usually unnecessary for the first attempt. |
| `Restore.cmd` | Undo the latest successfully installed, not-yet-restored run in this tool folder, including startup configuration changed by that run. |

The default scope uses the filename pattern `pak<number>_dir.vpk`, not every mod manager's enabled-state database. Other naming conventions may require the expanded scope.

## 4. What changes

The tool reads original references from the installed `game/citadel/pak01_dir.vpk` and official archive chunks. **It does not modify official resource archives.** For models with exact original paths and compatible rigs, it synchronizes standing, crouching, near, far and aiming attachments, related FOV metadata and `CitadelCameraSettings_t`. It checks other model data and unrelated VPK resources for consistency.

An installed repair also maintains a marked block at the end of `game/citadel/cfg/autoexec.cfg`:

```text
citadel_camera_overrides_enabled "false"
```

This lets heroes use their own camera data. Existing startup content is preserved and backed up; the tool does not assign one height or distance to every hero.

## 5. Results and backups

| Message | Meaning |
| --- | --- |
| `changed` | A camera difference was found and a checked model repair was generated. |
| `native` | No modification was needed; this can include accessory models requiring no gameplay camera repair. |
| `unsupported` / `UNSUPPORTED` | The model or archive could not be processed automatically; read the reason. |
| `archives` | Number of VPKs requiring changes. |
| `startupChanged` | Whether the native-camera startup block requires changes. |
| `applied=True` | This run actually installed changes; scans or runs needing no changes may show `False`. |

Reports are saved as `runs/<timestamp-id>/report.json`. The `models` list records model statuses; `archives` records file changes and can include startup configuration. Previous files are saved in that run's `backups/` folder.

For automatic restoration, **keep the complete tool folder in place, including reports, backups and generated repaired copies**. Reports contain absolute paths.

## 6. Undoing a repair

Exit the game and manager, then run `Restore.cmd` from the original tool folder. It checks current files and backup SHA256 hashes before restoring the state preceding that run. Updates, reordering, mod reinstallation or manual configuration edits afterward may cause restoration to refuse overwriting files. Keep reports and backups, investigate the differences, and do not bypass verification.

**Restoration returns mods to their pre-run state. It does not uninstall mods or restore a completely unmodified game.** Disabling all mods requires separate action through your manager and mod-loading configuration.

## 7. Compatibility and rerunning

The current implementation supports single-file VPK v1/v2 mods and cameras in embedded MDAT meshes. Missing exact original paths, incompatible rigs, multi-chunk mod archives, preloaded model entries and external-mesh cameras are skipped. Other supported models in the same VPK may still be repaired.

This is a batch repair tool, not a permanent runtime camera lock. Check and rerun it after replacing skins, enabling, disabling or reordering mods, reinstalling mods, or updating the game. Future format changes may break compatibility. Problems caused by abilities, model poses or geometry occlusion may remain.

## 8. Custom paths and troubleshooting

If discovery fails, open PowerShell in the extracted folder and specify **`game/citadel`, not addons or the game's top-level folder**:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\Start-Repair.ps1 -Mode scan -Citadel "D:\SteamLibrary\steamapps\common\Deadlock\game\citadel"
```

After checking the scan, change `-Mode scan` to `-Mode repair`. Use `-Addons "full mod-directory path"` to specify another mod folder.

- **Missing runtimes:** install the required versions, add them to PATH and open a new terminal. Check `python --version` and `pwsh -NoProfile -Command "[Environment]::Version"`; the latter should report major version 10 or newer.
- **Changed files or hash mismatch:** close the manager, wait for updates to finish, and scan again.
- **Unsupported model:** read the report and wait for a tool or mod update.
- **No restorable run:** check that the original tool folder, `runs/`, reports and backups remain intact and in place.
- **Execution blocked by system policy:** verify the source and follow your device's administration rules. Do not disable security software.

## 9. Testing and distribution

Development referenced build `25999968`. Repair, repeat-run and rollback tests used copies of six VPKs containing eight hero models, with resource-consistency checks and selected failure cases. The publisher subsequently reported effective results in their own environment. This is not a guarantee for all mods, game versions or account safety.

The package contains source, parsing libraries and licenses, not game assets. Retain `ThirdPartyNotices.txt` and `licenses/` when sharing. Do not include `runs/`, backups, repaired VPKs or private paths. See the [disclaimer](DISCLAIMER.en.md) for further limitations.
