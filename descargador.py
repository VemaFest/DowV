import tkinter as tk
from tkinter import messagebox, filedialog
import yt_dlp
import threading
import os

def seleccionar_carpeta():
    carpeta = filedialog.askdirectory()
    if carpeta:
        carpeta_destino.set(carpeta)
        etiqueta_carpeta.config(text=f"Carpeta: {carpeta}")

def iniciar_descarga():
    # Usamos un hilo para que la ventana no diga "No responde" mientras descarga
    hilo = threading.Thread(target=descargar)
    hilo.start()

def descargar():
    url = entrada_url.get()
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

    # Configuramos si queremos Audio o Video
    if formato == "audio":
        ydl_opts.update({
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
        })
    else:
        ydl_opts.update({
            'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
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
ventana.geometry("400x320")

tk.Label(ventana, text="Enlace de YouTube:", font=("Arial", 10)).pack(pady=10)

entrada_url = tk.Entry(ventana, width=45)
entrada_url.pack(pady=5)

carpeta_destino = tk.StringVar()
boton_carpeta = tk.Button(ventana, text="Elegir dónde guardar", command=seleccionar_carpeta)
boton_carpeta.pack(pady=5)

etiqueta_carpeta = tk.Label(ventana, text="Carpeta: (misma carpeta del programa)", font=("Arial", 8), fg="gray")
etiqueta_carpeta.pack(pady=2)

opcion_var = tk.StringVar(value="video")
tk.Radiobutton(ventana, text="Video de alta calidad (MP4)", variable=opcion_var, value="video").pack()
tk.Radiobutton(ventana, text="Solo Audio (MP3)", variable=opcion_var, value="audio").pack()

boton_descargar = tk.Button(ventana, text="¡Descargar!", command=iniciar_descarga, bg="#d90429", fg="white", font=("Arial", 10, "bold"))
boton_descargar.pack(pady=15)

etiqueta_estado = tk.Label(ventana, text="", font=("Arial", 9, "bold"))
etiqueta_estado.pack(pady=5)

ventana.mainloop()