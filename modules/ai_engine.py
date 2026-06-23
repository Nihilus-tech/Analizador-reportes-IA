# -*- coding: utf-8 -*-
import os
from groq import Groq

def generate_insights(analysis_data):
    client = Groq(api_key=os.getenv("GROQ_API_KEY"))

    stats_text = ""
    for col, values in analysis_data["estadisticas"].items():
        stats_text += f"\n- {col}: promedio={values['promedio']}, maximo={values['maximo']}, minimo={values['minimo']}, total={values['total']}"

    columnas = ", ".join(analysis_data["nombres_columnas"])

    prompt = f"""Eres un analista de negocios experto.
Analiza estos datos empresariales y genera un reporte ejecutivo en español.

DATOS DEL ARCHIVO:
- Total de registros: {analysis_data['filas']} filas
- Columnas disponibles: {columnas}

ESTADISTICAS NUMERICAS:{stats_text}

Genera un reporte con:
1. RESUMEN EJECUTIVO (2-3 oraciones sobre que representan estos datos)
2. HALLAZGOS CLAVE (3-4 insights importantes)
3. TENDENCIAS (que patrones se observan)
4. RECOMENDACIONES (2-3 acciones concretas basadas en los datos)

Se especifico con los numeros. Escribe como un consultor profesional."""

    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=1000,
        temperature=0.7
    )

    return response.choices[0].message.content