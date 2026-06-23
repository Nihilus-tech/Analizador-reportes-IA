# -*- coding: utf-8 -*-
"""
Fase 4 — Generador de PDF
Recibe los mismos datos que ya produce tu app y genera un PDF descargable.

Conceptos clave:
- BytesIO: archivo en memoria RAM (sin tocar el disco)
- SimpleDocTemplate: el "lienzo" de ReportLab donde vas agregando bloques
- story: lista de bloques (Paragraph, Table, Spacer) que ReportLab ensambla en orden
- seek(0): "rebobina" el buffer al inicio para que Flask pueda enviarlo
"""

from io import BytesIO
from datetime import datetime

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer,
    Table, TableStyle, HRFlowable
)
import base64
from reportlab.platypus import Image as RLImage
import io

# ── Paleta de colores ──────────────────────────────────────────────────────────
AZUL_OSCURO = colors.HexColor("#1e3a5f")
AZUL_MEDIO  = colors.HexColor("#2563eb")
AZUL_CLARO  = colors.HexColor("#eff6ff")
GRIS_TEXTO  = colors.HexColor("#6b7280")
BLANCO      = colors.white


def generar_pdf(filename: str, resultado: dict, insights: str) -> BytesIO:
    """
    Parámetros:
      filename  → nombre del archivo que subió el usuario (ej: "ventas.xlsx")
      resultado → diccionario que devuelve analyzer.analyze_file()
      insights  → string que devuelve ai_engine.generate_insights()

    Devuelve:
      BytesIO con el PDF listo para que Flask lo envíe con send_file()
    """
    buffer = BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=2 * cm,
        leftMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
    )

    styles = getSampleStyleSheet()

    # ── Estilos personalizados ─────────────────────────────────────────────────
    estilo_titulo = ParagraphStyle(
        "Titulo",
        parent=styles["Title"],
        fontSize=20,
        textColor=AZUL_OSCURO,
        fontName="Helvetica-Bold",
        spaceAfter=4,
    )
    estilo_meta = ParagraphStyle(
        "Meta",
        parent=styles["Normal"],
        fontSize=9,
        textColor=GRIS_TEXTO,
        spaceAfter=10,
    )
    estilo_seccion = ParagraphStyle(
        "Seccion",
        parent=styles["Heading2"],
        fontSize=12,
        textColor=AZUL_MEDIO,
        fontName="Helvetica-Bold",
        spaceBefore=14,
        spaceAfter=6,
    )
    estilo_cuerpo = ParagraphStyle(
        "Cuerpo",
        parent=styles["Normal"],
        fontSize=9,
        leading=14,
        textColor=colors.HexColor("#1f2937"),
        spaceAfter=6,
    )
    estilo_pie = ParagraphStyle(
        "Pie",
        parent=styles["Normal"],
        fontSize=7,
        textColor=GRIS_TEXTO,
    )

    story = []

    # ── ENCABEZADO ─────────────────────────────────────────────────────────────
    story.append(Paragraph("Reporte Ejecutivo de Analisis", estilo_titulo))
    story.append(Paragraph(
        f"Archivo: <b>{filename}</b> &nbsp;|&nbsp; "
        f"Generado: {datetime.now().strftime('%d/%m/%Y %H:%M')}",
        estilo_meta,
    ))
    story.append(HRFlowable(width="100%", thickness=2, color=AZUL_MEDIO, spaceAfter=12))

    # ── RESUMEN DEL ARCHIVO ────────────────────────────────────────────────────
    story.append(Paragraph("Resumen del Archivo", estilo_seccion))

    columnas_texto = ", ".join(resultado["nombres_columnas"])
    story.append(Paragraph(
        f"<b>Registros:</b> {resultado['filas']} filas &nbsp;|&nbsp; "
        f"<b>Columnas:</b> {resultado['columnas']}",
        estilo_cuerpo,
    ))
    story.append(Paragraph(
        f"<b>Columnas disponibles:</b> {columnas_texto}",
        estilo_cuerpo,
    ))

    # ── TABLA DE ESTADÍSTICAS ──────────────────────────────────────────────────
    if resultado.get("estadisticas"):
        story.append(Paragraph("Estadisticas por Columna Numerica", estilo_seccion))
        story.append(Spacer(1, 0.2 * cm))

        # Encabezados + filas
        encabezados = ["Columna", "Promedio", "Maximo", "Minimo", "Total"]
        filas = [encabezados]
        for col, vals in resultado["estadisticas"].items():
            filas.append([
                col,
                f"{vals['promedio']:,.2f}",
                f"{vals['maximo']:,.2f}",
                f"{vals['minimo']:,.2f}",
                f"{vals['total']:,.2f}",
            ])

        tbl = Table(filas, repeatRows=1)
        tbl.setStyle(TableStyle([
            # Encabezado
            ("BACKGROUND",    (0, 0), (-1, 0), AZUL_OSCURO),
            ("TEXTCOLOR",     (0, 0), (-1, 0), BLANCO),
            ("FONTNAME",      (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE",      (0, 0), (-1, 0), 9),
            ("ALIGN",         (0, 0), (-1, 0), "CENTER"),
            ("BOTTOMPADDING", (0, 0), (-1, 0), 7),
            ("TOPPADDING",    (0, 0), (-1, 0), 7),
            # Filas alternas
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [BLANCO, AZUL_CLARO]),
            # Datos
            ("FONTSIZE",      (0, 1), (-1, -1), 8),
            ("ALIGN",         (1, 1), (-1, -1), "RIGHT"),   # números a la derecha
            ("ALIGN",         (0, 1), (0, -1),  "LEFT"),    # nombres a la izquierda
            ("TOPPADDING",    (0, 1), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 1), (-1, -1), 5),
            # Bordes
            ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#d1d5db")),
            ("BOX",  (0, 0), (-1, -1), 1,   AZUL_OSCURO),
        ]))
        story.append(tbl)

    # ── MUESTRA DE DATOS (primeras 3 filas) ───────────────────────────────────
    if resultado.get("muestra"):
        story.append(Paragraph("Muestra de Datos (primeras 3 filas)", estilo_seccion))
        story.append(Spacer(1, 0.2 * cm))

        keys = list(resultado["muestra"][0].keys())
        muestra_filas = [keys]
        for registro in resultado["muestra"]:
            muestra_filas.append([str(registro.get(k, "")) for k in keys])

        tbl_muestra = Table(muestra_filas, repeatRows=1)
        tbl_muestra.setStyle(TableStyle([
            ("BACKGROUND",    (0, 0), (-1, 0), AZUL_MEDIO),
            ("TEXTCOLOR",     (0, 0), (-1, 0), BLANCO),
            ("FONTNAME",      (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE",      (0, 0), (-1, -1), 7),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [BLANCO, AZUL_CLARO]),
            ("GRID",  (0, 0), (-1, -1), 0.4, colors.HexColor("#d1d5db")),
            ("BOX",   (0, 0), (-1, -1), 1,   AZUL_MEDIO),
            ("TOPPADDING",    (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        story.append(tbl_muestra)

    # ── INSIGHTS DE IA ────────────────────────────────────────────────────────
    story.append(Paragraph("Analisis e Insights (IA)", estilo_seccion))
    story.append(HRFlowable(width="100%", thickness=1, color=AZUL_CLARO, spaceAfter=8))

    # Escapamos caracteres especiales para que ReportLab no se confunda
    insights_safe = (
        insights
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace("\n", "<br/>")   # saltos de línea → saltos en el PDF
    )
    story.append(Paragraph(insights_safe, estilo_cuerpo))

    # GRAFICA
    if resultado.get("grafica"):
        story.append(Paragraph("Visualizacion de Datos", estilo_seccion))
        story.append(Spacer(1, 0.2 * cm))
    
        img_data = resultado["grafica"].split(",")[1]
        img_bytes = base64.b64decode(img_data)
        img_buffer = io.BytesIO(img_bytes)
    
        img = RLImage(img_buffer, width=16*cm, height=8*cm)
        story.append(img)

    # ── PIE DE PÁGINA ─────────────────────────────────────────────────────────
    story.append(Spacer(1, 1 * cm))
    story.append(HRFlowable(width="100%", thickness=1, color=GRIS_TEXTO, spaceAfter=5))
    story.append(Paragraph(
        "Generado automaticamente por Analizador de Reportes IA. "
        "Este reporte es informativo y no constituye asesoria profesional.",
        estilo_pie,
    ))

    doc.build(story)
    buffer.seek(0)   # rebobinar al inicio para que Flask pueda leerlo
    return buffer