param([Parameter(Mandatory=$true)][string]$JobsPath,[Parameter(Mandatory=$true)][string]$ResultPath)
$ErrorActionPreference='Stop'
if([Environment]::Version.Major -lt 10){throw 'This tool requires PowerShell 7.6 with .NET 10.'}
foreach($name in @('K4os.Compression.LZ4','ValveKeyValue','ZstdSharp','System.IO.Hashing','ValvePak','ValveResourceFormat')){Add-Type -Path (Join-Path "$PSScriptRoot/lib" ($name+'.dll'))}
Add-Type -Path "$PSScriptRoot/NativeCamera.cs" -ReferencedAssemblies @((Get-ChildItem "$PSHOME/ref/*.dll").FullName;"$PSScriptRoot/lib/ValveResourceFormat.dll","$PSScriptRoot/lib/ValveKeyValue.dll")
$jobs=Get-Content -LiteralPath $JobsPath -Raw | ConvertFrom-Json
$results=@()
foreach($job in $jobs){
 try{
  $changes=[PatchModels]::Run($job.mod,$job.original,$job.blocks)
  $results+=@{id=$job.id;status=if($changes){'changed'}else{'native'};changes=$changes}
 }catch{
  $message=$_.Exception.GetBaseException().Message
  $results+=@{id=$job.id;status='unsupported';reason=$message}
 }
}
ConvertTo-Json -InputObject @($results) -Depth 8 | Set-Content -LiteralPath $ResultPath -Encoding utf8
