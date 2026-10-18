param([Parameter(ValueFromRemainingArguments = $true)][string[]]$Paths)
$m = @($env:DFZ_DATA, "C:\Program Files\Digital Fit Zone\DigitalFitZone_Data", (Join-Path $PSScriptRoot "../../reference/DigitalFitZone_Data")) |
  Where-Object { $_ -and (Test-Path (Join-Path $_ "Managed/DFZ.Rules.dll")) } | Select-Object -First 1
if (-not $m) { throw "DigitalFitZone_Data를 찾지 못했다. DFZ_DATA 환경 변수로 알려 주세요." }
$m = Join-Path $m "Managed"
$null = [Reflection.Assembly]::LoadFrom("$m/DFZ.Core.dll")
$asm = [Reflection.Assembly]::LoadFrom("$m/DFZ.Rules.dll")
$limitsType = $asm.GetType("DigitalFitZone.Rules.Json.JsonReaderLimits")
$limits = $limitsType.GetProperty("Default").GetValue($null)
$loader = [Activator]::CreateInstance($asm.GetType("DigitalFitZone.Rules.Loader.GameRuleSetLoader"), @($limits))
foreach ($path in $Paths) {
  $json = [IO.File]::ReadAllText($path, [Text.Encoding]::UTF8)
  $r = $loader.Load($json)
  Write-Output ("{0} -> IsSuccess={1}" -f $path, $r.IsSuccess)
  if ($r.IsSuccess) {
    $w = $r.RuleSet.Flow.Web
    Write-Output ("   title={0} flowType={1}" -f $r.RuleSet.Title, $r.RuleSet.Flow.Type)
    if ($w) { Write-Output ("   entry={0} bridge={1} people={2} usesPlayerBridge={3}" -f $w.Entry, $w.Bridge, $w.People, $w.UsesPlayerBridge) }
  }
  $v = $r.Validation
  foreach ($p in $v.GetType().GetProperties()) {
    $val = $p.GetValue($v)
    if ($val -is [System.Collections.IEnumerable] -and -not ($val -is [string])) {
      foreach ($e in $val) {
        $parts = foreach ($ep in $e.GetType().GetProperties()) { "{0}={1}" -f $ep.Name, $ep.GetValue($e) }
        Write-Output ("   " + $p.Name + ": " + ($parts -join " | "))
      }
    } else { Write-Output ("   " + $p.Name + " = " + $val) }
  }
}
