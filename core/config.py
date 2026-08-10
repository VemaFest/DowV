import os
import json

CONFIG_FILE = "config.json"

def obtener_ruta_defecto(tipo):
    perfil = os.environ.get('USERPROFILE', os.path.expanduser('~'))
    if tipo == "video":
        ruta = os.path.join(perfil, 'Videos', 'DowV')
    else:
        ruta = os.path.join(perfil, 'Music', 'DowV')
    
    os.makedirs(ruta, exist_ok=True)
    return ruta

def cargar_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if 'carpeta_destino' in data:
                    del data['carpeta_destino']
                    with open(CONFIG_FILE, 'w', encoding='utf-8') as out_f:
                        json.dump(data, out_f, indent=4)
                return data
        except Exception:
            return {}
    return {}

def guardar_config(tipo, ruta):
    config = cargar_config()
    config[f'carpeta_{tipo}'] = ruta
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
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
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=4)
