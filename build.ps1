# Script de compilacion para DowVideo
Write-Host "Iniciando compilacion de DowVideo..." -ForegroundColor Cyan

# Verifica si el usuario puso un logo.ico en la misma carpeta
if (Test-Path "logo.ico") {
    Write-Host "¡Se encontró logo.ico! Se agregará al .exe" -ForegroundColor Green
    pyinstaller --noconfirm --noconsole --onedir --name "DowVideo" --icon "logo.ico" --collect-all customtkinter --collect-all plyer main.py
} else {
    Write-Host "No se encontró logo.ico. Se compilará con el ícono por defecto." -ForegroundColor Yellow
    Write-Host "(Nota: Si quieres tu propio ícono, pon una imagen llamada 'logo.ico' aquí y vuelve a correr este script)" -ForegroundColor Gray
    pyinstaller --noconfirm --noconsole --onedir --name "DowVideo" --collect-all customtkinter --collect-all plyer main.py
}

Write-Host "=============================================" -ForegroundColor Green
Write-Host "¡Compilación Terminada!" -ForegroundColor Green
Write-Host "Tu programa listo para usar está dentro de la carpeta: 'dist\DowVideo'" -ForegroundColor Cyan
Write-Host "=============================================" -ForegroundColor Green
Pause
