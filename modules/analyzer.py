import pandas as pd
import math

def get_sheets(filepath):
    if filepath.endswith(".csv"):
        return None
    xl = pd.ExcelFile(filepath)
    return xl.sheet_names

def limpiar_valor(valor):
    if valor is None:
        return 0
    try:
        if math.isnan(valor) or math.isinf(valor):
            return 0
    except:
        pass
    return valor

def analyze_file(filepath, sheet_name=0):
    if filepath.endswith(".csv"):
        df = pd.read_csv(filepath)
    else:
        df = pd.read_excel(filepath, sheet_name=sheet_name)

    df = df.fillna(0)
    rows, cols = df.shape
    numeric_cols = df.select_dtypes(include='number')

    stats = {}
    for col in numeric_cols.columns:
        stats[col] = {
            "promedio": limpiar_valor(round(float(numeric_cols[col].mean()), 2)),
            "maximo": limpiar_valor(round(float(numeric_cols[col].max()), 2)),
            "minimo": limpiar_valor(round(float(numeric_cols[col].min()), 2)),
            "total": limpiar_valor(round(float(numeric_cols[col].sum()), 2))
        }

    return {
        "filas": rows,
        "columnas": cols,
        "nombres_columnas": list(df.columns),
        "estadisticas": stats,
        "muestra": df.head(3).fillna(0).to_dict(orient="records")
    }

def analyze_all_sheets(filepath):
    """Lee todas las hojas y las combina en un solo analisis."""
    xl = pd.ExcelFile(filepath)
    sheets = xl.sheet_names

    # Leer cada hoja y agregarle una columna que diga de qué hoja viene
    dfs = []
    for sheet in sheets:
        df = pd.read_excel(filepath, sheet_name=sheet)
        df["_hoja"] = sheet
        dfs.append(df)

    # Combinar todo en un solo DataFrame
    df_total = pd.concat(dfs, ignore_index=True)
    df_total = df_total.fillna(0)

    rows, cols = df_total.shape
    numeric_cols = df_total.select_dtypes(include='number')

    stats = {}
    for col in numeric_cols.columns:
        if col == "_hoja":
            continue
        stats[col] = {
            "promedio": limpiar_valor(round(float(numeric_cols[col].mean()), 2)),
            "maximo": limpiar_valor(round(float(numeric_cols[col].max()), 2)),
            "minimo": limpiar_valor(round(float(numeric_cols[col].min()), 2)),
            "total": limpiar_valor(round(float(numeric_cols[col].sum()), 2))
        }

    return {
        "filas": rows,
        "columnas": cols,
        "nombres_columnas": [c for c in df_total.columns if c != "_hoja"],
        "estadisticas": stats,
        "muestra": df_total.head(3).fillna(0).to_dict(orient="records"),
        "hojas_incluidas": sheets
    }