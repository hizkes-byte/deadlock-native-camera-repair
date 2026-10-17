param([Parameter(Mandatory=$true)][string]$JobsPath)
$ErrorActionPreference='Stop'
foreach($name in @('K4os.Compression.LZ4','ValveKeyValue','ZstdSharp','System.IO.Hashing','ValvePak','ValveResourceFormat')){Add-Type -Path (Join-Path "$PSScriptRoot/lib" ($name+'.dll'))}
Add-Type -Path "$PSScriptRoot/NativeCamera.cs" -ReferencedAssemblies @((Get-ChildItem "$PSHOME/ref/*.dll").FullName;"$PSScriptRoot/lib/ValveResourceFormat.dll","$PSScriptRoot/lib/ValveKeyValue.dll")
$jobs=Get-Content -LiteralPath $JobsPath -Raw | ConvertFrom-Json
foreach($job in $jobs){[PatchModels]::Verify($job.mod,$job.patched,$job.original);Write-Host "Verified native cameras and preserved model data: $($job.id)"}
