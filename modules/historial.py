# -*- coding: utf-8 -*-
import json
import os
from datetime import datetime

HISTORIAL_PATH = os.path.join("reports", "historial_{usuario}.json")
MAX_REGISTROS = 10

def guardar_analisis(filename, resultado, insights, usuario="general"):
    historial = cargar_historial(usuario)

    registro_id = datetime.now().strftime("%Y%m%d%H%M%S")

    registro = {
        "id": registro_id,
        "fecha": datetime.now().strftime("%d/%m/%Y %H:%M"),
        "filename": filename,
        "filas": resultado.get("filas", 0),
        "columnas": resultado.get("columnas", 0),
        "resumen": insights[:300] + "..." if len(insights) > 300 else insights,
        "usuario": usuario
    }

    os.makedirs("reports", exist_ok=True)

    detalle_path = os.path.join("reports", f"analisis_{registro_id}.json")
    with open(detalle_path, "w", encoding="utf-8") as f:
        json.dump({
            "filename": filename,
            "resultado": resultado,
            "insights": insights,
            "usuario": usuario
        }, f, ensure_ascii=False, indent=2)

    historial.insert(0, registro)
    historial = historial[:MAX_REGISTROS]

    ruta = HISTORIAL_PATH.format(usuario=usuario)
    with open(ruta, "w", encoding="utf-8") as f:
        json.dump(historial, f, ensure_ascii=False, indent=2)


def cargar_historial(usuario="general"):
    ruta = HISTORIAL_PATH.format(usuario=usuario)
    if not os.path.exists(ruta):
        return []
    try:
        with open(ruta, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return []