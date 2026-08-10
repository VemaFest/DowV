# Script de compilacion para DowVideo
Write-Host "Iniciando compilacion de DowVideo..." -ForegroundColor Cyan

# Verifica si el usuario puso un logo.ico en la misma carpeta
$binArgs = ""
if (Test-Path "bin\ffmpeg.exe") {
    Write-Host "Binarios de FFmpeg encontrados. Se integrarán a la app para mayor portabilidad." -ForegroundColor Green
    $binArgs = "--add-binary ""bin/ffmpeg.exe;bin"" --add-binary ""bin/ffprobe.exe;bin"""
} else {
    Write-Host "AVISO: No se detectó FFmpeg local. La app requerirá que esté instalado en la PC de destino." -ForegroundColor Yellow
}

$dataArgs = ""
if (Test-Path "logo.png") {
    $dataArgs += " --add-data `"logo.png;.`""
}
if (Test-Path "logo_icono.png") {
    $dataArgs += " --add-data `"logo_icono.png;.`""
}
if (Test-Path "logo.ico") {
    $dataArgs += " --add-data `"logo.ico;.`""
}

if (Test-Path "logo.ico") {
    Write-Host "¡Se encontró logo.ico! Se agregará al .exe y a la ventana" -ForegroundColor Green
    Invoke-Expression "pyinstaller --noconfirm --noconsole --onedir --name `"DowVideo`" --icon `"logo.ico`" $dataArgs --collect-all customtkinter --collect-all plyer $binArgs main.py"
} else {
    Write-Host "No se encontró logo.ico. Se compilará con el ícono por defecto." -ForegroundColor Yellow
    Write-Host "(Nota: Si quieres tu propio ícono, pon una imagen llamada 'logo.ico' aquí y vuelve a correr este script)" -ForegroundColor Gray
    Invoke-Expression "pyinstaller --noconfirm --noconsole --onedir --name `"DowVideo`" $dataArgs --collect-all customtkinter --collect-all plyer $binArgs main.py"
}

Write-Host "=============================================" -ForegroundColor Green
Write-Host "¡Compilación Terminada!" -ForegroundColor Green
Write-Host "Tu programa listo para usar está dentro de la carpeta: 'dist\DowVideo'" -ForegroundColor Cyan
Write-Host "=============================================" -ForegroundColor Green
Pause
