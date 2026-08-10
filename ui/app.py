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
        self.geometry("750x650") # Un poco mas ancho para el Sidebar + Grid
        self.minsize(700, 600)
        
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
        # Configuracion de color global estricta basada en paletas ColorHunt
        ctk.set_appearance_mode("dark")
        
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        # ====== SIDEBAR ======
        self.sidebar_frame = ctk.CTkFrame(self, width=150, corner_radius=0, fg_color="#222831")
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(4, weight=1)
        
        self.logo_label = ctk.CTkLabel(self.sidebar_frame, text="DowVideo", font=ctk.CTkFont(size=22, weight="bold"), text_color="#ff5722")
        self.logo_label.grid(row=0, column=0, padx=20, pady=(20, 30))

        self.btn_descargas = ctk.CTkButton(self.sidebar_frame, text="Descargas", fg_color="transparent", text_color="#eeeeee", hover_color="#2d4059", anchor="w", font=ctk.CTkFont(size=14), command=self.show_descargas)
        self.btn_descargas.grid(row=1, column=0, padx=10, pady=5, sticky="ew")

        self.btn_historial = ctk.CTkButton(self.sidebar_frame, text="Historial", fg_color="transparent", text_color="#eeeeee", hover_color="#2d4059", anchor="w", font=ctk.CTkFont(size=14), command=self.show_historial)
        self.btn_historial.grid(row=2, column=0, padx=10, pady=5, sticky="ew")

        # ====== MAIN CONTAINER ======
        self.main_container = ctk.CTkFrame(self, fg_color="#2d4059", corner_radius=0)
        self.main_container.grid(row=0, column=1, sticky="nsew")
        self.main_container.grid_rowconfigure(0, weight=1)
        self.main_container.grid_columnconfigure(0, weight=1)

        # ====== FRAMES ======
        self.frame_descargas = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self.frame_historial = ctk.CTkFrame(self.main_container, fg_color="transparent")
        
        self._build_tab_descargas()
        self._build_tab_historial()

        # Iniciar en Descargas
        self.show_descargas()

    def show_descargas(self):
        self.frame_historial.grid_forget()
        self.frame_descargas.grid(row=0, column=0, sticky="nsew", padx=30, pady=30)
        self.btn_descargas.configure(fg_color="#393e46")
        self.btn_historial.configure(fg_color="transparent")

    def show_historial(self):
        self.frame_descargas.grid_forget()
        self.frame_historial.grid(row=0, column=0, sticky="nsew", padx=30, pady=30)
        self.btn_historial.configure(fg_color="#393e46")
        self.btn_descargas.configure(fg_color="transparent")
        self.refrescar_historial_ui()

    def _build_tab_descargas(self):
        self.frame_descargas.grid_columnconfigure(0, weight=1)
        self.frame_descargas.grid_columnconfigure(1, weight=1)
        self.frame_descargas.grid_rowconfigure(2, weight=1)
        
        # TITLE
        ctk.CTkLabel(self.frame_descargas, text="Ingresa el Enlace de YouTube:", font=ctk.CTkFont(size=14, weight="bold"), text_color="#eeeeee").grid(row=0, column=0, columnspan=2, pady=(0, 5), sticky="w")
        
        # URL BOX
        self.entrada_url = ctk.CTkTextbox(self.frame_descargas, height=60, fg_color="#eeeeee", text_color="#222831")
        self.entrada_url.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(0, 15))
        self.entrada_url.bind("<KeyRelease>", self.on_url_change)
        self.entrada_url.bind("<<Paste>>", lambda e: self.after(10, self.on_url_change))

        # --- GRID STRUCTURE ---
        # LEFT COLUMN (SETTINGS)
        settings_frame = ctk.CTkFrame(self.frame_descargas, fg_color="#393e46", corner_radius=10)
        settings_frame.grid(row=2, column=0, sticky="nsew", padx=(0, 10))
        
        ctk.CTkLabel(settings_frame, text="Configuración", font=ctk.CTkFont(size=14, weight="bold"), text_color="#ff5722").pack(pady=(15, 5))
        
        self.opcion_var = ctk.StringVar(value="video")
        self.opcion_var.trace_add('write', self.actualizar_combobox)
        self.opcion_var.trace_add('write', self.actualizar_carpeta_ui)
        
        radio_frame = ctk.CTkFrame(settings_frame, fg_color="transparent")
        radio_frame.pack(pady=5)
        ctk.CTkRadioButton(radio_frame, text="Video", variable=self.opcion_var, value="video", fg_color="#ff5722", hover_color="#ec5b38").pack(side="left", padx=10)
        ctk.CTkRadioButton(radio_frame, text="Audio", variable=self.opcion_var, value="audio", fg_color="#ff5722", hover_color="#ec5b38").pack(side="left", padx=10)

        ctk.CTkLabel(settings_frame, text="Calidad:", font=ctk.CTkFont(size=12)).pack(pady=(10, 0))
        self.combo_calidad = ctk.CTkComboBox(settings_frame, state="readonly", fg_color="#eeeeee", text_color="#222831", button_color="#a8a492")
        self.combo_calidad.pack(pady=5, padx=20, fill="x")
        self.combo_calidad.set("Busca un video primero")
        
        ctk.CTkLabel(settings_frame, text="Guardar en:", font=ctk.CTkFont(size=12)).pack(pady=(10, 0))
        self.carpeta_destino = ctk.StringVar()
        self.etiqueta_carpeta = ctk.CTkLabel(settings_frame, text="", font=ctk.CTkFont(size=10), text_color="#a8a492")
        self.etiqueta_carpeta.pack(pady=0, padx=10)
        
        btn_folder = ctk.CTkButton(settings_frame, text="Cambiar Carpeta", command=self.seleccionar_carpeta, fg_color="#524646", hover_color="#a8a492")
        btn_folder.pack(pady=10)

        self.actualizar_carpeta_ui()

        # RIGHT COLUMN (THUMBNAIL & PREVIEW)
        preview_frame = ctk.CTkFrame(self.frame_descargas, fg_color="#393e46", corner_radius=10)
        preview_frame.grid(row=2, column=1, sticky="nsew", padx=(10, 0))
        
        ctk.CTkLabel(preview_frame, text="Vista Previa", font=ctk.CTkFont(size=14, weight="bold"), text_color="#ff5722").pack(pady=(15, 5))
        
        self.etiqueta_imagen = ctk.CTkLabel(preview_frame, text="Sin miniatura", fg_color="#222831", width=240, height=135, corner_radius=8)
        self.etiqueta_imagen.pack(pady=10, padx=20, expand=True)

        # BOTTOM (ACTIONS & PROGRESS)
        action_frame = ctk.CTkFrame(self.frame_descargas, fg_color="transparent")
        action_frame.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(20, 0))
        
        self.boton_descargar = ctk.CTkButton(action_frame, text="DESCARGAR", font=ctk.CTkFont(size=16, weight="bold"), command=self.iniciar_descarga, fg_color="#ff5722", hover_color="#ec5b38", height=45)
        self.boton_descargar.pack(side="left", padx=(0, 10), expand=True, fill="x")
        
        self.boton_cancelar = ctk.CTkButton(action_frame, text="Cancelar", font=ctk.CTkFont(size=14, weight="bold"), command=self.cancelar_descarga, fg_color="#524646", hover_color="#a8a492", state="disabled", height=45)
        self.boton_cancelar.pack(side="left", padx=(10, 0))
        
        self.etiqueta_estado = ctk.CTkLabel(self.frame_descargas, text="", font=ctk.CTkFont(size=12, weight="bold"))
        self.etiqueta_estado.grid(row=4, column=0, columnspan=2, pady=(10, 0))
        
        self.barra_progreso = ctk.CTkProgressBar(self.frame_descargas, orientation="horizontal", mode="determinate", progress_color="#ff5722")
        self.barra_progreso.grid(row=5, column=0, columnspan=2, sticky="ew", pady=5)
        self.barra_progreso.set(0)
        
        self.etiqueta_stats = ctk.CTkLabel(self.frame_descargas, text="", font=ctk.CTkFont(size=11), text_color="#a8a492")
        self.etiqueta_stats.grid(row=6, column=0, columnspan=2)

    def _build_tab_historial(self):
        self.frame_historial.grid_rowconfigure(1, weight=1)
        self.frame_historial.grid_columnconfigure(0, weight=1)
        
        ctk.CTkLabel(self.frame_historial, text="Historial de Descargas", font=ctk.CTkFont(size=18, weight="bold"), text_color="#eeeeee").grid(row=0, column=0, sticky="w", pady=(0, 15))
        
        marco_herramientas = ctk.CTkFrame(self.frame_historial, fg_color="transparent")
        marco_herramientas.grid(row=1, column=0, sticky="ew", pady=(0, 10))

        ctk.CTkLabel(marco_herramientas, text="Buscar:", text_color="#eeeeee").pack(side=tk.LEFT, padx=(0,5))
        self.entrada_busqueda_historial = ctk.CTkEntry(marco_herramientas, width=250, fg_color="#eeeeee", text_color="#222831")
        self.entrada_busqueda_historial.pack(side=tk.LEFT, padx=5)

        self.boton_limpiar = ctk.CTkButton(marco_herramientas, text="Limpiar Historial", command=self.limpiar_todo_historial_wrapper, fg_color="#ec5b38", hover_color="#ff5722")
        self.boton_limpiar.pack(side=tk.RIGHT, padx=5)

        # Theme
        style = ttk.Style()
        style.theme_use("default")
        style.configure("Treeview", 
            background="#393e46",
            foreground="#eeeeee",
            rowheight=30,
            fieldbackground="#393e46",
            bordercolor="#222831",
            borderwidth=0)
        style.map('Treeview', background=[('selected', '#ff5722')])
        style.configure("Treeview.Heading",
            background="#222831",
            foreground="#ff5722",
            relief="flat",
            font=("Arial", 10, "bold"))
        style.map("Treeview.Heading", background=[('active', '#524646')])

        columnas = ('titulo', 'calidad', 'fecha', 'ruta')
        self.arbol_historial = ttk.Treeview(self.frame_historial, columns=columnas, show='headings')
        self.arbol_historial.heading('titulo', text='Título')
        self.arbol_historial.heading('calidad', text='Calidad')
        self.arbol_historial.heading('fecha', text='Fecha')
        self.arbol_historial.heading('ruta', text='Ruta')

        self.arbol_historial.column('titulo', width=220)
        self.arbol_historial.column('calidad', width=100)
        self.arbol_historial.column('fecha', width=120)
        self.arbol_historial.column('ruta', width=0, stretch=tk.NO) 

        scrollbar = ttk.Scrollbar(self.frame_historial, orient=tk.VERTICAL, command=self.arbol_historial.yview)
        self.arbol_historial.configure(yscroll=scrollbar.set)
        
        self.arbol_historial.grid(row=2, column=0, sticky="nsew")
        scrollbar.grid(row=2, column=1, sticky="ns")

        ctk.CTkLabel(self.frame_historial, text="Doble clic en un elemento para abrir su ubicación.", font=ctk.CTkFont(size=11), text_color="#a8a492").grid(row=3, column=0, pady=5)

        self.entrada_busqueda_historial.bind('<KeyRelease>', self.refrescar_historial_ui)
        self.arbol_historial.bind('<Double-1>', self.abrir_ruta_historial)

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
        self.etiqueta_imagen.configure(image='', text="Buscando...")
        self.id_after_busqueda = self.after(800, self.iniciar_busqueda)

    def iniciar_busqueda(self):
        t = threading.Thread(target=self.buscar_calidades_hilo)
        t.daemon = True
        t.start()

    def mostrar_miniatura(self, img_data):
        try:
            img = Image.open(BytesIO(img_data))
            # Ajustado para que el Thumbnail sea más grande (16:9 approx)
            img = img.resize((240, 135), Image.Resampling.LANCZOS)
            foto = ImageTk.PhotoImage(img)
            self.etiqueta_imagen.configure(image=foto, text="")
            self.etiqueta_imagen.image = foto
        except Exception as e:
            print("Error procesando miniatura:", e)

    def buscar_calidades_hilo(self):
        urls = self.obtener_urls()
        if not urls:
            return
        
        url = urls[0]
        self.after(0, lambda: self.etiqueta_estado.configure(text="Buscando calidades automáticamente...", text_color="#ec5b38"))
        
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
            self.after(0, lambda: self.etiqueta_estado.configure(text="¡Calidades encontradas!", text_color="#eeeeee"))
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
                import re
                # yt-dlp a veces incluye códigos ANSI de color en estos strings, hay que limpiarlos
                percent_raw = d.get('_percent_str', '0.0%')
                percent_clean = re.sub(r'\x1b[^m]*m', '', percent_raw).strip()
                percent_float = float(percent_clean.replace('%', ''))
                
                speed = re.sub(r'\x1b[^m]*m', '', d.get('_speed_str', 'N/A')).strip()
                eta = re.sub(r'\x1b[^m]*m', '', d.get('_eta_str', 'N/A')).strip()
                
                self.after(0, lambda pf=percent_float, ps=percent_clean, sp=speed, e=eta: self.actualizar_progreso_ui(pf, ps, sp, e))
            except Exception as ex:
                print("Error en progreso:", ex)

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
            self.after(0, lambda: self.etiqueta_estado.configure(text="Revisando si es una playlist...", text_color="#ec5b38"))
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
                        
                    btn = ctk.CTkButton(popup, text="Confirmar Selección", command=confirmar, fg_color="#ff5722", hover_color="#ec5b38")
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
                
        self.after(0, lambda: self.etiqueta_estado.configure(text="Descargando... ¡dele un toque!", text_color="#eeeeee"))
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
                        
            self.after(0, lambda: self.etiqueta_estado.configure(text="¡Descarga completada con éxito!", text_color="#eeeeee"))
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
                self.after(0, lambda: self.etiqueta_estado.configure(text="Descarga cancelada por el usuario.", text_color="#ff4d4d"))
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
                self.after(0, lambda: self.etiqueta_estado.configure(text="Hubo un error al descargar.", text_color="#ff4d4d"))
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
