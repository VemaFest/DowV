import tkinter as tk
from tkinter import messagebox, filedialog, ttk
import customtkinter as ctk
import yt_dlp
import threading
import os
import requests
from io import BytesIO
from PIL import Image, ImageTk
import subprocess
from plyer import notification
import logging

from core.logger import YTDLLogger
from core.history import cargar_historial, agregar_a_historial, limpiar_todo_historial
from core.config import cargar_config, guardar_config, inicializar_configuracion, obtener_ruta_defecto
from core.downloader import extraer_info_robusto

class DowVideoApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        # Setup window
        self.title("DowV - Descargador de YouTube")
        self.geometry("550x650")
        
        # NOTE: Descomenta esto cuando agregues logo.ico a la carpeta de tu proyecto (o assets/)
        # self.iconbitmap("logo.ico")

        # Configurar y inicializar dependencias
        inicializar_configuracion()
        
        # Variables de estado
        self.formatos_disponibles = {'video': [], 'audio': []}
        self.cancelar_descarga_flag = False
        self.archivos_sesion = set()
        self.id_after_busqueda = None
        
        self.setup_ui()
        
    def setup_ui(self):
        # Estilizar el ttk.Treeview
        style = ttk.Style()
        style.theme_use("default")
        style.configure("Treeview", 
            background="#2b2b2b",
            foreground="white",
            rowheight=25,
            fieldbackground="#2b2b2b",
            bordercolor="#343638",
            borderwidth=0)
        style.map('Treeview', background=[('selected', '#1f538d')])
        style.configure("Treeview.Heading",
            background="#565b5e",
            foreground="white",
            relief="flat")
        style.map("Treeview.Heading", background=[('active', '#343638')])

        self.notebook = ctk.CTkTabview(self)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.tab_descargas = self.notebook.add("Descargas")
        self.tab_historial = self.notebook.add("Historial")

        self._build_tab_descargas()
        self._build_tab_historial()

    def _build_tab_descargas(self):
        ctk.CTkLabel(self.tab_descargas, text="Enlaces de YouTube (uno por línea):", font=("Arial", 12)).pack(pady=5)

        self.entrada_url = ctk.CTkTextbox(self.tab_descargas, width=450, height=80)
        self.entrada_url.pack(pady=5)
        self.entrada_url.bind("<KeyRelease>", self.on_url_change)
        self.entrada_url.bind("<<Paste>>", lambda e: self.after(10, self.on_url_change))

        self.etiqueta_imagen = ctk.CTkLabel(self.tab_descargas, text="")
        self.etiqueta_imagen.pack(pady=5)

        self.carpeta_destino = ctk.StringVar()

        self.boton_carpeta = ctk.CTkButton(self.tab_descargas, text="Elegir dónde guardar", command=self.seleccionar_carpeta)
        self.boton_carpeta.pack(pady=5)

        self.etiqueta_carpeta = ctk.CTkLabel(self.tab_descargas, text="", font=("Arial", 10), text_color="gray")
        self.etiqueta_carpeta.pack(pady=2)

        self.opcion_var = ctk.StringVar(value="video")
        self.opcion_var.trace_add('write', self.actualizar_combobox)
        self.opcion_var.trace_add('write', self.actualizar_carpeta_ui)
        self.actualizar_carpeta_ui()

        marco_opciones = ctk.CTkFrame(self.tab_descargas, fg_color="transparent")
        marco_opciones.pack(pady=5)

        ctk.CTkRadioButton(marco_opciones, text="Video (MP4)", variable=self.opcion_var, value="video").pack(side=tk.LEFT, padx=10)
        ctk.CTkRadioButton(marco_opciones, text="Audio (MP3)", variable=self.opcion_var, value="audio").pack(side=tk.LEFT, padx=10)

        ctk.CTkLabel(self.tab_descargas, text="Calidad:", font=("Arial", 12)).pack(pady=2)
        self.combo_calidad = ctk.CTkComboBox(self.tab_descargas, state="readonly", width=300)
        self.combo_calidad.pack(pady=5)
        self.combo_calidad.set("Busca un video primero")

        marco_botones = ctk.CTkFrame(self.tab_descargas, fg_color="transparent")
        marco_botones.pack(pady=10)

        self.boton_descargar = ctk.CTkButton(marco_botones, text="¡Descargar!", command=self.iniciar_descarga, fg_color="#d90429", hover_color="#ef233c", font=("Arial", 12, "bold"))
        self.boton_descargar.pack(side=tk.LEFT, padx=5)

        self.boton_cancelar = ctk.CTkButton(marco_botones, text="Cancelar", command=self.cancelar_descarga, fg_color="#8d99ae", hover_color="#9ca8ba", font=("Arial", 12, "bold"), state="disabled")
        self.boton_cancelar.pack(side=tk.LEFT, padx=5)

        self.etiqueta_estado = ctk.CTkLabel(self.tab_descargas, text="", font=("Arial", 12, "bold"))
        self.etiqueta_estado.pack(pady=2)

        self.barra_progreso = ctk.CTkProgressBar(self.tab_descargas, orientation="horizontal", width=400, mode="determinate")
        self.barra_progreso.pack(pady=5)
        self.barra_progreso.set(0)

        self.etiqueta_stats = ctk.CTkLabel(self.tab_descargas, text="", font=("Arial", 10), text_color="gray")
        self.etiqueta_stats.pack(pady=2)

    def _build_tab_historial(self):
        marco_herramientas = ctk.CTkFrame(self.tab_historial, fg_color="transparent")
        marco_herramientas.pack(fill=tk.X, padx=5, pady=5)

        ctk.CTkLabel(marco_herramientas, text="Buscar:").pack(side=tk.LEFT, padx=(0,5))
        self.entrada_busqueda_historial = ctk.CTkEntry(marco_herramientas, width=250)
        self.entrada_busqueda_historial.pack(side=tk.LEFT, padx=5)

        self.boton_limpiar = ctk.CTkButton(marco_herramientas, text="Limpiar Historial", command=self.limpiar_todo_historial_wrapper, fg_color="#ff4d4d", hover_color="#ff6b6b", width=120)
        self.boton_limpiar.pack(side=tk.RIGHT, padx=5)

        columnas = ('titulo', 'calidad', 'fecha', 'ruta')
        self.arbol_historial = ttk.Treeview(self.tab_historial, columns=columnas, show='headings')
        self.arbol_historial.heading('titulo', text='Título')
        self.arbol_historial.heading('calidad', text='Calidad')
        self.arbol_historial.heading('fecha', text='Fecha')
        self.arbol_historial.heading('ruta', text='Ruta')

        self.arbol_historial.column('titulo', width=220)
        self.arbol_historial.column('calidad', width=100)
        self.arbol_historial.column('fecha', width=120)
        self.arbol_historial.column('ruta', width=0, stretch=tk.NO) 

        scrollbar = ttk.Scrollbar(self.tab_historial, orient=tk.VERTICAL, command=self.arbol_historial.yview)
        self.arbol_historial.configure(yscroll=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.arbol_historial.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        ctk.CTkLabel(self.tab_historial, text="Doble clic en un elemento para abrir su ubicación.", font=("Arial", 10), text_color="gray").pack(pady=2)

        self.entrada_busqueda_historial.bind('<KeyRelease>', self.refrescar_historial_ui)
        self.arbol_historial.bind('<Double-1>', self.abrir_ruta_historial)
        
        self.refrescar_historial_ui()

    def limpiar_todo_historial_wrapper(self):
        if messagebox.askyesno("Confirmar", "¿Seguro que deseas borrar todo el historial?"):
            limpiar_todo_historial()
            self.refrescar_historial_ui()

    def refrescar_historial_ui(self, event=None):
        busqueda = self.entrada_busqueda_historial.get().lower()
        for item in self.arbol_historial.get_children():
            self.arbol_historial.delete(item)
        for item in cargar_historial():
            if busqueda in item['titulo'].lower() or busqueda in item['calidad'].lower():
                self.arbol_historial.insert('', tk.END, values=(item['titulo'], item['calidad'], item['fecha'], item['ruta']))

    def abrir_ruta_historial(self, event):
        seleccion = self.arbol_historial.selection()
        if seleccion:
            item = self.arbol_historial.item(seleccion[0])
            ruta = item['values'][3]
            if ruta and os.path.exists(ruta):
                subprocess.Popen(f'explorer /select,"{ruta}"')
            elif ruta:
                carpeta = os.path.dirname(ruta)
                if os.path.exists(carpeta):
                    os.startfile(carpeta)
                else:
                    messagebox.showinfo("Error", "El archivo y su carpeta ya no existen.")

    def actualizar_carpeta_ui(self, *args):
        tipo = self.opcion_var.get()
        config = cargar_config()
        key = f'carpeta_{tipo}'
        
        if key in config:
            nueva_ruta = config[key]
        else:
            nueva_ruta = obtener_ruta_defecto(tipo)
            guardar_config(tipo, nueva_ruta)
            
        self.carpeta_destino.set(nueva_ruta)
        self.etiqueta_carpeta.configure(text=f"Carpeta: {nueva_ruta}")

    def seleccionar_carpeta(self):
        carpeta = filedialog.askdirectory()
        if carpeta:
            tipo = self.opcion_var.get()
            self.carpeta_destino.set(carpeta)
            self.etiqueta_carpeta.configure(text=f"Carpeta: {carpeta}")
            guardar_config(tipo, carpeta)

    def obtener_urls(self):
        texto = self.entrada_url.get("1.0", tk.END).strip()
        return [linea.strip() for linea in texto.split('\n') if linea.strip().startswith('http')]

    def actualizar_combobox(self, *args):
        tipo = self.opcion_var.get()
        opciones = []
        if tipo == "video":
            opciones = ["Mejor Video"] + self.formatos_disponibles['video']
        else:
            opciones = ["Mejor Audio"] + [f"{int(a['abr'])} kbps" for a in self.formatos_disponibles['audio']]
        
        self.combo_calidad.configure(values=opciones)
        if opciones:
            self.combo_calidad.set(opciones[0])

    def on_url_change(self, event=None):
        if self.id_after_busqueda:
            self.after_cancel(self.id_after_busqueda)
        self.etiqueta_imagen.configure(image='')
        self.id_after_busqueda = self.after(800, self.iniciar_busqueda)

    def iniciar_busqueda(self):
        t = threading.Thread(target=self.buscar_calidades_hilo)
        t.daemon = True
        t.start()

    def mostrar_miniatura(self, img_data):
        try:
            img = Image.open(BytesIO(img_data))
            img = img.resize((160, 90), Image.Resampling.LANCZOS)
            foto = ImageTk.PhotoImage(img)
            self.etiqueta_imagen.configure(image=foto)
            self.etiqueta_imagen.image = foto
        except Exception as e:
            print("Error procesando miniatura:", e)

    def buscar_calidades_hilo(self):
        urls = self.obtener_urls()
        if not urls:
            return
        
        url = urls[0]
        self.etiqueta_estado.configure(text="Buscando calidades automáticamente...", text_color="#3a86ff")
        
        ydl_opts = {
            'extractor_args': {'youtube': {'player_client': ['android', 'web']}},
            'playlist_items': '1',
            'logger': YTDLLogger(),
        }
            
        try:
            info = extraer_info_robusto(ydl_opts, url, download=False)
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
                    self.after(0, lambda d=img_data: self.mostrar_miniatura(d))
                except Exception as e:
                    print("Error descargando miniatura:", e)
            
            self.formatos_disponibles['video'] = []
            self.formatos_disponibles['audio'] = []
            
            resoluciones = []
            for f in formatos:
                if f.get('vcodec') != 'none':
                    res = f.get('height', 0)
                    if res and res not in resoluciones:
                        resoluciones.append(res)
                        
                if f.get('acodec') != 'none' and f.get('vcodec') == 'none':
                    abr = f.get('abr', 0)
                    if abr and abr not in [a['abr'] for a in self.formatos_disponibles['audio']]:
                        self.formatos_disponibles['audio'].append({'abr': abr, 'format_id': f.get('format_id')})
            
            resoluciones.sort(reverse=True)
            self.formatos_disponibles['video'] = [f"{r}p" for r in resoluciones]
            self.formatos_disponibles['audio'].sort(key=lambda x: x['abr'], reverse=True)
            
            self.after(0, self.actualizar_combobox)
            self.after(0, lambda: self.etiqueta_estado.configure(text="¡Calidades encontradas!", text_color="#00b4d8"))
        except Exception as e:
            self.after(0, lambda: self.etiqueta_estado.configure(text="Error al buscar calidades.", text_color="#ff4d4d"))
            print(e)

    def iniciar_descarga(self):
        urls = self.obtener_urls()
        if not urls:
            return
        t = threading.Thread(target=self.descargar, args=(urls,))
        t.daemon = True
        t.start()

    def cancelar_descarga(self):
        self.cancelar_descarga_flag = True
        self.etiqueta_estado.configure(text="Cancelando... por favor espere.", text_color="#ff4d4d")
        self.boton_cancelar.configure(state="disabled")

    def limpiar_temporales(self, directorio):
        if not directorio or not os.path.exists(directorio):
            return
        for a in self.archivos_sesion:
            try:
                base = os.path.splitext(a)[0]
                if os.path.exists(base + '.ytdl'):
                    os.remove(base + '.ytdl')
                if os.path.exists(base + '.part'):
                    os.remove(base + '.part')
            except:
                pass

    def actualizar_progreso_ui(self, percent_float, percent_str, speed, eta):
        self.barra_progreso.set(percent_float / 100.0)
        if percent_float < 100:
            self.etiqueta_stats.configure(text=f"Progreso: {percent_str} | Vel: {speed} | Faltan: {eta}")
        else:
            self.etiqueta_stats.configure(text="Procesando archivo (Uniendo audio/video)...")

    def progress_hook(self, d):
        if self.cancelar_descarga_flag:
            raise Exception("Descarga_Cancelada")
            
        if d['status'] == 'downloading':
            try:
                percent = d.get('_percent_str', '0.0%').strip()
                percent_float = float(percent.replace('%', ''))
                speed = d.get('_speed_str', 'N/A').strip()
                eta = d.get('_eta_str', 'N/A').strip()
                
                self.after(0, lambda pf=percent_float, ps=percent, sp=speed, e=eta: self.actualizar_progreso_ui(pf, ps, sp, e))
            except Exception:
                pass

    def postprocessor_hook(self, d):
        if self.cancelar_descarga_flag:
            raise Exception("Descarga_Cancelada")
        if d['status'] == 'finished':
            self.archivos_sesion.add(d['info_dict'].get('filepath', ''))

    def descargar(self, urls):
        self.cancelar_descarga_flag = False
        self.archivos_sesion.clear()
        
        if not urls:
            self.after(0, lambda: messagebox.showwarning("Falta el enlace", "¡Mae, ponga al menos un enlace de YouTube primero!"))
            return

        self.boton_descargar.configure(state="disabled")
        self.boton_cancelar.configure(state="normal")
        
        playlist_items_str = ""
        if len(urls) == 1:
            self.etiqueta_estado.configure(text="Revisando si es una playlist...", text_color="#3a86ff")
            ydl_opts_flat = {
                'extractor_args': {'youtube': {'player_client': ['android', 'web']}},
                'extract_flat': True,
                'logger': YTDLLogger(),
            }
            videos_lista = []
            try:
                info = extraer_info_robusto(ydl_opts_flat, urls[0], download=False)
                if 'entries' in info:
                    for i, entry in enumerate(info['entries']):
                        if entry:
                            videos_lista.append({'index': i+1, 'title': entry.get('title', f'Video {i+1}')})
            except Exception:
                pass
                
            if len(videos_lista) > 1:
                seleccion_terminada = threading.Event()
                items_seleccionados = []
                
                def mostrar_popup():
                    popup = ctk.CTkToplevel(self)
                    popup.title("Seleccionar Videos de la Playlist")
                    popup.geometry("400x500")
                    popup.transient(self)
                    popup.grab_set()
                    
                    ctk.CTkLabel(popup, text=f"Se detectó una lista de {len(videos_lista)} videos.\nSelecciona cuáles deseas descargar:", font=("Arial", 12, "bold")).pack(pady=10)
                    
                    marco_busqueda_popup = ctk.CTkFrame(popup, fg_color="transparent")
                    marco_busqueda_popup.pack(fill=tk.X, padx=10, pady=5)
                    ctk.CTkLabel(marco_busqueda_popup, text="Buscar:").pack(side=tk.LEFT, padx=(0,5))
                    entrada_busqueda_popup = ctk.CTkEntry(marco_busqueda_popup)
                    entrada_busqueda_popup.pack(side=tk.LEFT, fill=tk.X, expand=True)
                    
                    scrollable_frame = ctk.CTkScrollableFrame(popup)
                    scrollable_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
                    
                    vars_check = {}
                    checkbuttons_refs = {}
                    for v in videos_lista:
                        var = ctk.StringVar(value="on")
                        vars_check[v['index']] = var
                        cb = ctk.CTkCheckBox(scrollable_frame, text=v['title'], variable=var, onvalue="on", offvalue="off")
                        cb.pack(anchor="w", pady=5, padx=5)
                        checkbuttons_refs[v['index']] = {'cb': cb, 'title': v['title'].lower()}
                        
                    def filtrar_popup(event):
                        busqueda = entrada_busqueda_popup.get().lower()
                        for v in videos_lista:
                            idx = v['index']
                            ref = checkbuttons_refs[idx]
                            if busqueda in ref['title']:
                                ref['cb'].pack(anchor="w", pady=5, padx=5)
                            else:
                                ref['cb'].pack_forget()
                                
                    entrada_busqueda_popup.bind('<KeyRelease>', filtrar_popup)
                        
                    def confirmar():
                        for idx, var in vars_check.items():
                            if var.get() == "on":
                                items_seleccionados.append(idx)
                        popup.destroy()
                        seleccion_terminada.set()
                        
                    btn = ctk.CTkButton(popup, text="Confirmar Selección", command=confirmar, fg_color="#d90429", hover_color="#ef233c")
                    btn.pack(pady=15)
                    
                    def on_closing():
                        popup.destroy()
                        seleccion_terminada.set()
                        
                    popup.protocol("WM_DELETE_WINDOW", on_closing)
                    
                self.after(0, mostrar_popup)
                seleccion_terminada.wait()
                
                if not items_seleccionados:
                    self.after(0, lambda: self.etiqueta_estado.configure(text="Descarga cancelada (sin selección).", text_color="#ff4d4d"))
                    self.after(0, lambda: self.boton_descargar.configure(state="normal"))
                    self.after(0, lambda: self.boton_cancelar.configure(state="disabled"))
                    return
                    
                playlist_items_str = ",".join(map(str, items_seleccionados))
                
        self.etiqueta_estado.configure(text="Descargando... ¡dele un toque!", text_color="#3a86ff")
        
        self.after(0, lambda: self.barra_progreso.set(0))
        self.after(0, lambda: self.etiqueta_stats.configure(text="Iniciando descarga..."))
        
        formato = self.opcion_var.get()
        
        ydl_opts = {
            'extractor_args': {'youtube': {'player_client': ['android', 'web']}},
            'progress_hooks': [self.progress_hook],
            'postprocessor_hooks': [self.postprocessor_hook],
            'nooverwrites': True,
            'logger': YTDLLogger(),
        }
        
        logging.info("--- INICIO DE NUEVA SESIÓN DE DESCARGA ---")
        logging.info(f"URLs solicitadas: {urls}")
        
        if playlist_items_str:
            ydl_opts['playlist_items'] = playlist_items_str

        destino = self.carpeta_destino.get()
        if destino:
            ydl_opts['paths'] = {'home': destino}

        calidad_seleccionada = self.combo_calidad.get()
        
        if formato == "audio":
            formato_yt = 'bestaudio/best'
            calidad_mp3 = '192'
            if "kbps" in calidad_seleccionada:
                abr_str = calidad_seleccionada.split(" ")[0]
                calidad_mp3 = abr_str
                for a in self.formatos_disponibles['audio']:
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
            for url in urls:
                info = extraer_info_robusto(ydl_opts, url, download=True)
                
                entradas = info.get('entries') if 'entries' in info else [info]
                for entry in entradas:
                    if not entry: continue
                    titulo = entry.get('title', 'Video Desconocido')
                    calidad_str = f"{self.opcion_var.get().upper()} - {self.combo_calidad.get()}"
                    
                    logging.info(f"Atributos del Video Procesado:")
                    logging.info(f" - Título: {titulo}")
                    logging.info(f" - ID: {entry.get('id', 'N/A')}")
                    logging.info(f" - Duración: {entry.get('duration', 'N/A')} seg")
                    logging.info(f" - Calidad seleccionada: {calidad_str}")
                    
                    ruta_final = ""
                    req_dl = entry.get('requested_downloads', [])
                    if req_dl:
                        ruta_final = req_dl[0].get('filepath', '')
                    else:
                        with yt_dlp.YoutubeDL(ydl_opts) as ydl_dummy:
                            ruta_final = ydl_dummy.prepare_filename(entry)
                        
                    self.after(0, lambda t=titulo, c=calidad_str, r=ruta_final: agregar_a_historial(t, c, r))
                    self.after(0, self.refrescar_historial_ui)
                        
            self.etiqueta_estado.configure(text="¡Descarga completada con éxito!", text_color="#00b4d8")
            self.after(0, lambda: self.etiqueta_stats.configure(text="¡Listo!"))
            logging.info("--- SESIÓN DE DESCARGA COMPLETADA CON ÉXITO ---")
            try:
                notification.notify(
                    title="DowV - Éxito",
                    message="¡La descarga se ha completado con éxito!",
                    app_name="DowVideo",
                    timeout=5
                )
            except Exception:
                pass
        except Exception as e:
            if str(e) == "Descarga_Cancelada":
                self.etiqueta_estado.configure(text="Descarga cancelada por el usuario.", text_color="#ff4d4d")
                self.after(0, lambda: self.etiqueta_stats.configure(text="Cancelado."))
                self.after(0, lambda: self.barra_progreso.set(0))
                for archivo in self.archivos_sesion:
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
                self.etiqueta_estado.configure(text="Hubo un error al descargar.", text_color="#ff4d4d")
                logging.error(f"!!! ERROR FATAL DURANTE LA DESCARGA !!!\nDetalles: {str(e)}")
                self.after(0, lambda err=str(e): messagebox.showerror("Error de Descarga", f"Se produjo un error durante la descarga:\n\n{err}\n\nRevisa el archivo dowv_auditoria.log para más detalles."))
                print(e)
                try:
                    notification.notify(
                        title="DowV - Error",
                        message="Ocurrió un problema al descargar el medio.",
                        app_name="DowVideo",
                        timeout=5
                    )
                except Exception:
                    pass
        finally:
            self.limpiar_temporales(destino)
            self.after(0, lambda: self.boton_descargar.configure(state="normal"))
            self.after(0, lambda: self.boton_cancelar.configure(state="disabled"))
