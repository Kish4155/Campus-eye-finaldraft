$env:Path = "C:\src\flutter\bin;C:\src\mingit\cmd;" + $env:Path
Write-Host "========================================================" -ForegroundColor Cyan
Write-Host "  Launching CAMPUS-EYE Cross-Platform Flutter App" -ForegroundColor Cyan
Write-Host "========================================================" -ForegroundColor Cyan
if ($args.Count -eq 0) {
    flutter run -d edge
} else {
    flutter run $args
}
