import tkinter as tk
from tkinter import messagebox, filedialog, ttk
import yt_dlp
import threading
import os
import json
import re
import requests
from io import BytesIO
from PIL import Image, ImageTk

CONFIG_FILE = "config.json"

def cargar_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                data = json.load(f)
                if 'carpeta_destino' in data:
                    del data['carpeta_destino']
                    with open(CONFIG_FILE, 'w') as out_f:
                        json.dump(data, out_f, indent=4)
                return data
        except Exception:
            return {}
    return {}

def guardar_config(tipo, ruta):
    config = cargar_config()
    config[f'carpeta_{tipo}'] = ruta
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=4)

def inicializar_configuracion():
    config = cargar_config()
    modificado = False
    
    if 'carpeta_video' not in config:
        config['carpeta_video'] = obtener_ruta_defecto("video")
        modificado = True
        
    if 'carpeta_audio' not in config:
        config['carpeta_audio'] = obtener_ruta_defecto("audio")
        modificado = True
        
    if modificado:
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=4)

formatos_disponibles = {'video': [], 'audio': []}

cancelar_descarga_flag = False
archivos_sesion = set()

def obtener_ruta_defecto(tipo):
    perfil = os.environ.get('USERPROFILE', os.path.expanduser('~'))
    if tipo == "video":
        ruta = os.path.join(perfil, 'Videos', 'DowV')
    else:
        ruta = os.path.join(perfil, 'Music', 'DowV')
    
    os.makedirs(ruta, exist_ok=True)
    return ruta

def actualizar_carpeta_ui(*args):
    tipo = opcion_var.get()
    config = cargar_config()
    key = f'carpeta_{tipo}'
    
    if key in config:
        nueva_ruta = config[key]
    else:
        nueva_ruta = obtener_ruta_defecto(tipo)
        guardar_config(tipo, nueva_ruta)
        
    carpeta_destino.set(nueva_ruta)
    etiqueta_carpeta.config(text=f"Carpeta: {nueva_ruta}")

def seleccionar_carpeta():
    carpeta = filedialog.askdirectory()
    if carpeta:
        tipo = opcion_var.get()
        carpeta_destino.set(carpeta)
        etiqueta_carpeta.config(text=f"Carpeta: {carpeta}")
        guardar_config(tipo, carpeta)

def obtener_urls():
    texto = entrada_url.get("1.0", tk.END).strip()
    return [linea.strip() for linea in texto.split('\n') if linea.strip().startswith('http')]

def buscar_calidades_hilo():
    urls = obtener_urls()
    if not urls:
        return
    
    url = urls[0]
    
    etiqueta_estado.config(text="Buscando calidades automáticamente...", fg="blue")
    
    ydl_opts = {
        'extractor_args': {'youtube': {'player_client': ['android', 'web']}},
        'playlist_items': '1',
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
            thumb_url = info.get('thumbnail')
            
            if 'entries' in info:
                entradas = list(info['entries'])
                formatos = entradas[0].get('formats', []) if entradas and entradas[0] else []
                if not thumb_url and entradas and entradas[0]:
                    thumb_url = entradas[0].get('thumbnail')
            else:
                formatos = info.get('formats', [])
                
            if thumb_url:
                try:
                    res = requests.get(thumb_url, timeout=5)
                    img_data = res.content
                    ventana.after(0, lambda d=img_data: mostrar_miniatura(d))
                except Exception as e:
                    print("Error descargando miniatura:", e)
            
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
def on_url_change(event=None):
    global id_after_busqueda
    if id_after_busqueda:
        ventana.after_cancel(id_after_busqueda)
    etiqueta_imagen.config(image='')
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

def cancelar_descarga():
    global cancelar_descarga_flag
    cancelar_descarga_flag = True
    etiqueta_estado.config(text="Cancelando... por favor espere.", fg="red")
    boton_cancelar.config(state=tk.DISABLED)

def limpiar_temporales(directorio):
    if not directorio or not os.path.exists(directorio):
        return
    for archivo in os.listdir(directorio):
        if archivo.endswith('.part') or archivo.endswith('.ytdl'):
            try:
                os.remove(os.path.join(directorio, archivo))
            except:
                pass

def mostrar_miniatura(img_data):
    try:
        img = Image.open(BytesIO(img_data))
        img = img.resize((160, 90), Image.Resampling.LANCZOS)
        foto = ImageTk.PhotoImage(img)
        etiqueta_imagen.config(image=foto)
        etiqueta_imagen.image = foto
    except Exception as e:
        print("Error procesando miniatura:", e)

def actualizar_progreso_ui(percent_float, percent_str, speed, eta):
    barra_progreso['value'] = percent_float
    if percent_float < 100:
        etiqueta_stats.config(text=f"Progreso: {percent_str} | Vel: {speed} | Faltan: {eta}")
    else:
        etiqueta_stats.config(text="Procesando archivo (Uniendo audio/video)...")

def progress_hook(d):
    global cancelar_descarga_flag
    if cancelar_descarga_flag:
        raise Exception("Descarga_Cancelada")
    
    if d['status'] == 'downloading':
        if 'filename' in d:
            archivos_sesion.add(d['filename'])
            
        total_bytes = d.get('total_bytes') or d.get('total_bytes_estimate', 0)
        downloaded = d.get('downloaded_bytes', 0)
        percent_float = (downloaded / total_bytes * 100) if total_bytes > 0 else 0.0
        
        speed = d.get('_speed_str', 'N/A').strip()
        eta = d.get('_eta_str', 'N/A').strip()
        percent_str = d.get('_percent_str', f'{percent_float:.1f}%').strip()
        
        ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
        speed = ansi_escape.sub('', speed)
        eta = ansi_escape.sub('', eta)
        percent_str = ansi_escape.sub('', percent_str)
        
        ventana.after(0, lambda p=percent_float, ps=percent_str, s=speed, e=eta: actualizar_progreso_ui(p, ps, s, e))
        
    elif d['status'] == 'finished':
        if 'filename' in d:
            archivos_sesion.add(d['filename'])
        ventana.after(0, lambda: actualizar_progreso_ui(100.0, "100%", "N/A", "00:00"))

def postprocessor_hook(d):
    if d['status'] == 'finished':
        filepath = d.get('info_dict', {}).get('filepath')
        if filepath:
            archivos_sesion.add(filepath)

def iniciar_descarga():
    # Usamos un hilo para que la ventana no diga "No responde" mientras descarga
    hilo = threading.Thread(target=descargar, daemon=True)
    hilo.start()

def descargar():
    global cancelar_descarga_flag, archivos_sesion
    cancelar_descarga_flag = False
    archivos_sesion.clear()
    
    urls = obtener_urls()
    if not urls:
        messagebox.showwarning("Falta el enlace", "¡Mae, ponga al menos un enlace de YouTube primero!")
        return

    boton_descargar.config(state=tk.DISABLED)
    boton_cancelar.config(state=tk.NORMAL)
    etiqueta_estado.config(text="Descargando... ¡dele un toque!", fg="blue")
    
    ventana.after(0, lambda: barra_progreso.config(value=0))
    ventana.after(0, lambda: etiqueta_stats.config(text="Iniciando descarga..."))
    
    formato = opcion_var.get()
    
    # Opciones base
    ydl_opts = {
        'extractor_args': {'youtube': {'player_client': ['android', 'web']}},
        'progress_hooks': [progress_hook],
        'postprocessor_hooks': [postprocessor_hook],
        'nooverwrites': True,
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
            'outtmpl': f'%(title)s_{calidad_mp3}kbps.%(ext)s',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': calidad_mp3,
            }],
        })
    else:
        formato_yt = 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best'
        res_str = "Mejor_Video"
        if "p" in calidad_seleccionada and calidad_seleccionada != "Mejor Video":
            res = calidad_seleccionada.replace("p", "")
            res_str = f"{res}p"
            formato_yt = f'bestvideo[height<={res}][ext=mp4]+bestaudio[ext=m4a]/best[height<={res}][ext=mp4]/best'
            
        ydl_opts.update({
            'format': formato_yt,
            'outtmpl': f'%(title)s_{res_str}.%(ext)s',
        })

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download(urls)
        etiqueta_estado.config(text="¡Descarga completada con éxito!", fg="green")
        ventana.after(0, lambda: etiqueta_stats.config(text="¡Listo!"))
    except Exception as e:
        if str(e) == "Descarga_Cancelada":
            etiqueta_estado.config(text="Descarga cancelada por el usuario.", fg="red")
            ventana.after(0, lambda: etiqueta_stats.config(text="Cancelado."))
            ventana.after(0, lambda: barra_progreso.config(value=0))
            for archivo in archivos_sesion:
                try:
                    if os.path.exists(archivo):
                        os.remove(archivo)
                    if os.path.exists(archivo + '.part'):
                        os.remove(archivo + '.part')
                    if os.path.exists(archivo + '.ytdl'):
                        os.remove(archivo + '.ytdl')
                except:
                    pass
        else:
            etiqueta_estado.config(text="Hubo un error al descargar.", fg="red")
            print(e)
    finally:
        limpiar_temporales(destino)
        boton_descargar.config(state=tk.NORMAL)
        boton_cancelar.config(state=tk.DISABLED)

# --- Diseño de la Ventanita ---
inicializar_configuracion()

ventana = tk.Tk()
ventana.title("Descargador de YouTube")
ventana.geometry("450x580")

tk.Label(ventana, text="Enlaces de YouTube (uno por línea):", font=("Arial", 10)).pack(pady=5)

entrada_url = tk.Text(ventana, width=50, height=5)
entrada_url.pack(pady=5)
entrada_url.bind("<KeyRelease>", on_url_change)
entrada_url.bind("<<Paste>>", lambda e: ventana.after(10, on_url_change))

etiqueta_imagen = tk.Label(ventana)
etiqueta_imagen.pack(pady=5)

carpeta_destino = tk.StringVar()

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

marco_botones = tk.Frame(ventana)
marco_botones.pack(pady=15)

boton_descargar = tk.Button(marco_botones, text="¡Descargar!", command=iniciar_descarga, bg="#d90429", fg="white", font=("Arial", 10, "bold"))
boton_descargar.pack(side=tk.LEFT, padx=5)

boton_cancelar = tk.Button(marco_botones, text="Cancelar", command=cancelar_descarga, bg="#8d99ae", fg="white", font=("Arial", 10, "bold"), state=tk.DISABLED)
boton_cancelar.pack(side=tk.LEFT, padx=5)

etiqueta_estado = tk.Label(ventana, text="", font=("Arial", 9, "bold"))
etiqueta_estado.pack(pady=5)

barra_progreso = ttk.Progressbar(ventana, orient="horizontal", length=400, mode="determinate")
barra_progreso.pack(pady=5)

etiqueta_stats = tk.Label(ventana, text="", font=("Arial", 8), fg="gray")
etiqueta_stats.pack(pady=2)

ventana.mainloop()