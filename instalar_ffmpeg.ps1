Write-Host "Descargando FFmpeg (esto puede tardar unos minutos dependiendo de tu internet)..." -ForegroundColor Cyan
$url = "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip"
$zipFile = "ffmpeg.zip"
$extractFolder = "ffmpeg_temp"

Invoke-WebRequest -Uri $url -OutFile $zipFile

Write-Host "Extrayendo archivos..." -ForegroundColor Cyan
Expand-Archive -Path $zipFile -DestinationPath $extractFolder -Force

Write-Host "Copiando binarios a la carpeta 'bin'..." -ForegroundColor Cyan
$binDir = "bin"
if (-Not (Test-Path $binDir)) {
    New-Item -ItemType Directory -Force -Path $binDir | Out-Null
}

$ffmpegPath = "$extractFolder\ffmpeg-master-latest-win64-gpl\bin\ffmpeg.exe"
$ffprobePath = "$extractFolder\ffmpeg-master-latest-win64-gpl\bin\ffprobe.exe"

Copy-Item $ffmpegPath -Destination "$binDir\ffmpeg.exe" -Force
Copy-Item $ffprobePath -Destination "$binDir\ffprobe.exe" -Force

Write-Host "Limpiando archivos temporales..." -ForegroundColor Cyan
Remove-Item $zipFile -Force
Remove-Item $extractFolder -Recurse -Force

Write-Host "=============================================" -ForegroundColor Green
Write-Host "¡FFmpeg se ha instalado correctamente de forma local!" -ForegroundColor Green
Write-Host "Ya puedes ejecutar build.ps1 para generar tu ejecutable." -ForegroundColor Green
Write-Host "=============================================" -ForegroundColor Green
Pause
