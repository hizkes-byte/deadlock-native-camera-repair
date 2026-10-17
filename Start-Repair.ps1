param([ValidateSet('repair','scan','all','restore')][string]$Mode='repair',[string]$Citadel,[string]$Addons)
$ErrorActionPreference='Stop'
$python=Join-Path $env:USERPROFILE '.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
if(!(Test-Path -LiteralPath $python)){
 $command=Get-Command python.exe -ErrorAction SilentlyContinue
 if(!$command -or $command.Source -like '*WindowsApps*'){throw 'Python 3.10+ is required. This computer can use the bundled Codex Python runtime.'}
 $python=$command.Source
}
$arguments=@((Join-Path $PSScriptRoot 'repair.py'))
if($Mode -eq 'repair'){$arguments+='--apply'}
if($Mode -eq 'all'){$arguments+=@('--apply','--include-disabled')}
if($Mode -eq 'restore'){$arguments+='--restore-latest'}
if($Citadel){$arguments+=@('--citadel',$Citadel)}
if($Addons){$arguments+=@('--addons',$Addons)}
& $python @arguments
if($LASTEXITCODE -ne 0){throw "Repair tool failed with exit code $LASTEXITCODE. See the message above."}
