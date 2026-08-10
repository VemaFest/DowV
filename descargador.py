import tkinter as tk
from tkinter import messagebox, filedialog, ttk
import yt_dlp
import threading
import os
import json

CONFIG_FILE = "config.json"

def cargar_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    return {}

def guardar_config(ruta):
    with open(CONFIG_FILE, 'w') as f:
        json.dump({'carpeta_destino': ruta}, f)

formatos_disponibles = {'video': [], 'audio': []}

def obtener_ruta_defecto(tipo):
    perfil = os.environ.get('USERPROFILE', os.path.expanduser('~'))
    if tipo == "video":
        return os.path.join(perfil, 'Videos')
    else:
        return os.path.join(perfil, 'Music')

def actualizar_carpeta_ui(*args):
    tipo = opcion_var.get()
    ruta_actual = carpeta_destino.get()
    
    ruta_video = obtener_ruta_defecto("video")
    ruta_audio = obtener_ruta_defecto("audio")
    
    if not ruta_actual or ruta_actual == ruta_video or ruta_actual == ruta_audio:
        nueva_ruta = obtener_ruta_defecto(tipo)
        carpeta_destino.set(nueva_ruta)
        etiqueta_carpeta.config(text=f"Carpeta: {nueva_ruta}")
        guardar_config(nueva_ruta)
    else:
        etiqueta_carpeta.config(text=f"Carpeta: {ruta_actual}")

def seleccionar_carpeta():
    carpeta = filedialog.askdirectory()
    if carpeta:
        carpeta_destino.set(carpeta)
        etiqueta_carpeta.config(text=f"Carpeta: {carpeta}")
        guardar_config(carpeta)

def buscar_calidades_hilo():
    url = var_url.get().strip()
    if not url.startswith("http"):
        return
    
    etiqueta_estado.config(text="Buscando calidades automáticamente...", fg="blue")
    
    ydl_opts = {
        'extractor_args': {'youtube': {'player_client': ['android', 'web']}},
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            formatos = info.get('formats', [])
            
            formatos_disponibles['video'] = []
            formatos_disponibles['audio'] = []
            
            resoluciones = []
            for f in formatos:
                if f.get('vcodec') != 'none':
                    res = f.get('height', 0)
                    if res and res not in resoluciones:
                        resoluciones.append(res)
                        
                if f.get('acodec') != 'none' and f.get('vcodec') == 'none':
                    abr = f.get('abr', 0)
                    if abr and abr not in [a['abr'] for a in formatos_disponibles['audio']]:
                        formatos_disponibles['audio'].append({'abr': abr, 'format_id': f['format_id']})
            
            resoluciones.sort(reverse=True)
            for r in resoluciones:
                formatos_disponibles['video'].append(f"{r}p")
                
            formatos_disponibles['audio'].sort(key=lambda x: x['abr'], reverse=True)
            
            ventana.after(0, actualizar_combobox)
            ventana.after(0, lambda: etiqueta_estado.config(text="¡Calidades encontradas!", fg="green"))
    except Exception as e:
        ventana.after(0, lambda: etiqueta_estado.config(text="Error al buscar calidades.", fg="red"))
        print(e)

def iniciar_busqueda():
    threading.Thread(target=buscar_calidades_hilo, daemon=True).start()

id_after_busqueda = None
def on_url_change(*args):
    global id_after_busqueda
    if id_after_busqueda:
        ventana.after_cancel(id_after_busqueda)
    id_after_busqueda = ventana.after(800, iniciar_busqueda)

def actualizar_combobox(*args):
    tipo = opcion_var.get()
    opciones = []
    if tipo == "video":
        opciones = ["Mejor Video"] + formatos_disponibles['video']
    else:
        opciones = ["Mejor Audio"] + [f"{int(a['abr'])} kbps" for a in formatos_disponibles['audio']]
    
    combo_calidad['values'] = opciones
    if opciones:
        combo_calidad.current(0)

def iniciar_descarga():
    # Usamos un hilo para que la ventana no diga "No responde" mientras descarga
    hilo = threading.Thread(target=descargar, daemon=True)
    hilo.start()

def descargar():
    url = var_url.get().strip()
    if not url:
        messagebox.showwarning("Falta el enlace", "¡Mae, ponga un enlace de YouTube primero!")
        return

    boton_descargar.config(state=tk.DISABLED)
    etiqueta_estado.config(text="Descargando... ¡dele un toque!", fg="blue")
    
    formato = opcion_var.get()
    
    # Opciones base (guarda el archivo en la misma carpeta del programa)
    ydl_opts = {
        'outtmpl': '%(title)s.%(ext)s', 
        'extractor_args': {'youtube': {'player_client': ['android', 'web']}},
    }

    destino = carpeta_destino.get()
    if destino:
        ydl_opts['paths'] = {'home': destino}

    calidad_seleccionada = combo_calidad.get()
    
    # Configuramos si queremos Audio o Video
    if formato == "audio":
        formato_yt = 'bestaudio/best'
        calidad_mp3 = '192'
        if "kbps" in calidad_seleccionada:
            abr_str = calidad_seleccionada.split(" ")[0]
            calidad_mp3 = abr_str
            for a in formatos_disponibles['audio']:
                if int(a['abr']) == int(abr_str):
                    formato_yt = a['format_id']
                    break
                    
        ydl_opts.update({
            'format': formato_yt,
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': calidad_mp3,
            }],
        })
    else:
        formato_yt = 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best'
        if "p" in calidad_seleccionada and calidad_seleccionada != "Mejor Video":
            res = calidad_seleccionada.replace("p", "")
            formato_yt = f'bestvideo[height<={res}][ext=mp4]+bestaudio[ext=m4a]/best[height<={res}][ext=mp4]/best'
            
        ydl_opts.update({
            'format': formato_yt,
        })

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        etiqueta_estado.config(text="¡Descarga completada con éxito!", fg="green")
    except Exception as e:
        etiqueta_estado.config(text="Hubo un error al descargar.", fg="red")
        print(e)
    finally:
        boton_descargar.config(state=tk.NORMAL)

# --- Diseño de la Ventanita ---
ventana = tk.Tk()
ventana.title("Descargador de YouTube")
ventana.geometry("450x420")

tk.Label(ventana, text="Enlace de YouTube:", font=("Arial", 10)).pack(pady=5)

var_url = tk.StringVar()
var_url.trace_add('write', on_url_change)
entrada_url = tk.Entry(ventana, width=50, textvariable=var_url)
entrada_url.pack(pady=5)

carpeta_destino = tk.StringVar()
config_data = cargar_config()
ruta_guardada = config_data.get('carpeta_destino', '')
if ruta_guardada:
    carpeta_destino.set(ruta_guardada)

boton_carpeta = tk.Button(ventana, text="Elegir dónde guardar", command=seleccionar_carpeta)
boton_carpeta.pack(pady=5)

etiqueta_carpeta = tk.Label(ventana, text="", font=("Arial", 8), fg="gray")
etiqueta_carpeta.pack(pady=2)

opcion_var = tk.StringVar(value="video")
opcion_var.trace_add('write', actualizar_combobox)
opcion_var.trace_add('write', actualizar_carpeta_ui)
actualizar_carpeta_ui()

marco_opciones = tk.Frame(ventana)
marco_opciones.pack(pady=5)

tk.Radiobutton(marco_opciones, text="Video (MP4)", variable=opcion_var, value="video").pack(side=tk.LEFT, padx=10)
tk.Radiobutton(marco_opciones, text="Audio (MP3)", variable=opcion_var, value="audio").pack(side=tk.LEFT, padx=10)

tk.Label(ventana, text="Calidad:", font=("Arial", 10)).pack(pady=2)
combo_calidad = ttk.Combobox(ventana, state="readonly", width=30)
combo_calidad.pack(pady=5)
combo_calidad.set("Busca un video primero")

boton_descargar = tk.Button(ventana, text="¡Descargar!", command=iniciar_descarga, bg="#d90429", fg="white", font=("Arial", 10, "bold"))
boton_descargar.pack(pady=15)

etiqueta_estado = tk.Label(ventana, text="", font=("Arial", 9, "bold"))
etiqueta_estado.pack(pady=5)

ventana.mainloop()