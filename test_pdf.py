import requests

respuesta = requests.post("http://localhost:5000/export/pdf", json={
    "filename": "ventas.xlsx",
    "resultado": {
        "filas": 100,
        "columnas": 3,
        "nombres_columnas": ["Mes", "Ventas", "Meta"],
        "estadisticas": {
            "Ventas": {"promedio": 5000, "maximo": 9000, "minimo": 1000, "total": 500000}
        },
        "muestra": [
            {"Mes": "Enero", "Ventas": 5000, "Meta": 4500}
        ]
    },
    "insights": "Las ventas superaron la meta en Q1."
})

with open("test_reporte.pdf", "wb") as f:
    f.write(respuesta.content)

print("PDF generado OK, revisa test_reporte.pdf")