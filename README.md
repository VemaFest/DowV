<h1 align="center">
  DowVideo 🎥
</h1>

<p align="center">
  <strong>Un descargador de YouTube potente, moderno y modular construido en Python.</strong>
</p>

---

## 🌟 Características Principales

- **Diseño Moderno (UI/UX):** Interfaz gráfica súper profesional construida con `customtkinter` (Estilo Google Material / Dark Mode).
- **Descargas Rápidas y Seguras:** Motor basado en el robusto `yt-dlp`, que garantiza descargas a la máxima velocidad posible.
- **Anti-Bot Integrado:** Capacidad nativa para esquivar los bloqueos de YouTube (HTTP Error 429) usando simulación de clientes `android`/`web`.
- **Selector de Calidad:** Obtén tu contenido en 4K (si está disponible) o extrae el audio a MP3 (hasta 320 kbps).
- **Soporte para Playlists:** Si introduces el enlace de una lista de reproducción, te abrirá un popup interactivo para seleccionar exactamente qué videos deseas descargar.
- **Historial Interactivo:** Tabla con el registro completo de tus descargas y atajos para abrir el archivo en el explorador de Windows.
- **Notificaciones Nativas:** Al finalizar tu descarga, Windows te enviará una notificación (Push).
- **Carga de Miniaturas:** Previsualización inteligente del video antes de descargarlo.

## 🏗️ Arquitectura del Proyecto (MVC)

El proyecto está diseñado bajo un modelo modular para facilitar futuras integraciones y mantener el código ordenado:

```text
DowVideo/
├── core/                  # Lógica interna y funcionalidades crudas
│   ├── config.py          # Gestión de rutas y configuraciones JSON
│   ├── downloader.py      # Lógica y envolturas para usar yt-dlp
│   ├── history.py         # Persistencia del historial de descargas
│   └── logger.py          # Sistema de auditoría centralizado
├── ui/                    # Capa visual (Interfaz Gráfica)
│   └── app.py             # Renderizado y flujos de CustomTkinter
├── main.py                # Punto de entrada de la aplicación
├── build.ps1              # Script de compilación (.exe)
└── .gitignore             # Archivos excluidos del repositorio
```

## 🚀 Instalación y Requisitos (Modo Desarrollador)

Para poder ejecutar el código fuente necesitas **Python 3.10 o superior** y el sistema **FFmpeg** instalado en tus variables de entorno (fundamental para unir el audio y video en alta calidad).

1. Clona este repositorio:
   ```bash
   git clone https://github.com/VemaFest/DowV.git
   cd DowV
   ```
2. Instala las dependencias de Python necesarias:
   ```bash
   pip install yt-dlp customtkinter plyer requests Pillow
   ```
3. Inicia la aplicación:
   ```bash
   python main.py
   ```

## 📦 Compilar a `.exe` (Para Windows)

Si deseas compartir el programa con tus amigos sin necesidad de que instalen Python, puedes crear un archivo ejecutable portable. 

Asegúrate de tener instalado **PyInstaller**:
```bash
pip install pyinstaller
```

Luego, simplemente corre nuestro script automático en PowerShell:
```powershell
.\build.ps1
```

¡Y listo! Tu aplicación quedará perfectamente empaquetada dentro de la carpeta `dist/DowVideo/DowVideo.exe`. Si quieres que tenga un icono personalizado, pon una imagen llamada `logo.ico` en la raíz antes de ejecutar el script.

## 📝 Auditoría e Historial (Logs)
- Todos los errores, avisos de dependencias y advertencias son atrapados y procesados de manera segura en el archivo invisible `dowv_auditoria.log`.
- El historial personal se guarda en `historial.json` de manera estrictamente local.

---

> Hecho con 💙 y Python.
