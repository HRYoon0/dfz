param([string]$Path)
$m = @($env:DFZ_DATA, "C:\Program Files\Digital Fit Zone\DigitalFitZone_Data", (Join-Path $PSScriptRoot "../../reference/DigitalFitZone_Data")) |
  Where-Object { $_ -and (Test-Path (Join-Path $_ "Managed/DFZ.Rules.dll")) } | Select-Object -First 1
if (-not $m) { throw "DigitalFitZone_Data를 찾지 못했다. DFZ_DATA 환경 변수로 알려 주세요." }
$m = Join-Path $m "Managed"
$null = [Reflection.Assembly]::LoadFrom("$m/DFZ.Core.dll")
$null = [Reflection.Assembly]::LoadFrom("$m/DFZ.Rules.dll")
$asm = [Reflection.Assembly]::LoadFrom("$m/DFZ.WebHost.dll")
$html = [IO.File]::ReadAllText($Path, [Text.Encoding]::UTF8)
Write-Output ("size = {0} KB" -f [math]::Round([Text.Encoding]::UTF8.GetByteCount($html) / 1024, 1))
$r = $asm.GetType("DigitalFitZone.WebHost.WebGameLint").GetMethod("Check").Invoke($null, @($html))
foreach ($p in $r.GetType().GetProperties()) {
  $val = $p.GetValue($r)
  if ($val -is [System.Collections.IEnumerable] -and -not ($val -is [string])) {
    $i = 0; foreach ($e in $val) { $i++; Write-Output ("  {0}[{1}] {2}" -f $p.Name, $i, $e) }
    if ($i -eq 0) { Write-Output ("  {0} = (none)" -f $p.Name) }
  } else { Write-Output ("  {0} = {1}" -f $p.Name, $val) }
}
Write-Output ("title = " + $asm.GetType("DigitalFitZone.WebHost.WebGameTitle").GetMethod("From").Invoke($null, @($html)))
Write-Output ("hint  = " + $asm.GetType("DigitalFitZone.WebHost.WebGameHint").GetMethod("From").Invoke($null, @($html)))
