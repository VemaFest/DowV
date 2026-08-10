import os
import json
from datetime import datetime

HISTORIAL_FILE = "historial.json"

def cargar_historial():
    if os.path.exists(HISTORIAL_FILE):
        try:
            with open(HISTORIAL_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return []
    return []

def guardar_historial(datos):
    with open(HISTORIAL_FILE, 'w', encoding='utf-8') as f:
        json.dump(datos, f, indent=4)

def agregar_a_historial(titulo, calidad, ruta):
    historial = cargar_historial()
    fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    historial.insert(0, {"titulo": titulo, "calidad": calidad, "fecha": fecha, "ruta": ruta})
    historial = historial[:50]
    guardar_historial(historial)

def limpiar_todo_historial():
    guardar_historial([])
