# -*- coding: utf-8 -*-
import sqlite3
import os
from datetime import datetime
from flask_login import UserMixin

DB_PATH = os.path.join("reports", "usuarios.db")

class Usuario(UserMixin):
    """
    Representa a un usuario de la aplicacion.
    UserMixin le da a Flask-Login los metodos que necesita:
    is_authenticated, is_active, get_id, etc.
    """
    def __init__(self, id, username, password_hash, rol, creado_en):
        self.id = id
        self.username = username
        self.password_hash = password_hash
        self.rol = rol  # "admin" o "usuario"
        self.creado_en = creado_en

    def es_admin(self):
        return self.rol == "admin"


def get_connection():
    """Abre una conexion a la base de datos SQLite."""
    os.makedirs("reports", exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # Permite acceder a columnas por nombre
    return conn


def inicializar_db():
    """
    Crea las tablas si no existen.
    Se llama una vez al iniciar la app.
    """
    conn = get_connection()
    cursor = conn.cursor()

    # Tabla de usuarios
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            rol TEXT NOT NULL DEFAULT 'usuario',
            creado_en TEXT NOT NULL
        )
    """)

    # Tabla de actividad - registra cada analisis hecho
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS actividad (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id INTEGER NOT NULL,
            username TEXT NOT NULL,
            filename TEXT NOT NULL,
            filas INTEGER,
            columnas INTEGER,
            fecha TEXT NOT NULL,
            FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
        )
    """)

    conn.commit()
    conn.close()


def crear_usuario(username, password_hash, rol="usuario"):
    """Inserta un nuevo usuario en la base de datos."""
    conn = get_connection()
    try:
        conn.execute(
            "INSERT INTO usuarios (username, password_hash, rol, creado_en) VALUES (?, ?, ?, ?)",
            (username, password_hash, rol, datetime.now().strftime("%d/%m/%Y %H:%M"))
        )
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        # El username ya existe
        return False
    finally:
        conn.close()


def buscar_usuario_por_username(username):
    """Busca un usuario por su nombre. Devuelve objeto Usuario o None."""
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM usuarios WHERE username = ?", (username,)
    ).fetchone()
    conn.close()
    if row:
        return Usuario(row["id"], row["username"], row["password_hash"], row["rol"], row["creado_en"])
    return None


def buscar_usuario_por_id(user_id):
    """Busca un usuario por su ID. Flask-Login lo necesita."""
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM usuarios WHERE id = ?", (user_id,)
    ).fetchone()
    conn.close()
    if row:
        return Usuario(row["id"], row["username"], row["password_hash"], row["rol"], row["creado_en"])
    return None


def registrar_actividad(usuario_id, username, filename, filas, columnas):
    """Guarda un registro cada vez que un usuario analiza un archivo."""
    conn = get_connection()
    conn.execute(
        "INSERT INTO actividad (usuario_id, username, filename, filas, columnas, fecha) VALUES (?, ?, ?, ?, ?, ?)",
        (usuario_id, username, filename, filas, columnas, datetime.now().strftime("%d/%m/%Y %H:%M"))
    )
    conn.commit()
    conn.close()


def obtener_todos_usuarios():
    """Devuelve lista de todos los usuarios. Solo para el admin."""
    conn = get_connection()
    rows = conn.execute("SELECT * FROM usuarios ORDER BY creado_en DESC").fetchall()
    conn.close()
    return [Usuario(r["id"], r["username"], r["password_hash"], r["rol"], r["creado_en"]) for r in rows]


def obtener_metricas():
    """Devuelve metricas globales para el panel de administrador."""
    conn = get_connection()

    total_usuarios = conn.execute("SELECT COUNT(*) FROM usuarios WHERE rol = 'usuario'").fetchone()[0]
    total_analisis = conn.execute("SELECT COUNT(*) FROM actividad").fetchone()[0]

    # Analisis por usuario
    por_usuario = conn.execute("""
        SELECT username, COUNT(*) as total, MAX(fecha) as ultimo
        FROM actividad
        GROUP BY username
        ORDER BY total DESC
    """).fetchall()

    # Ultimos 5 analisis globales
    recientes = conn.execute("""
        SELECT username, filename, filas, fecha
        FROM actividad
        ORDER BY id DESC
        LIMIT 5
    """).fetchall()

    conn.close()

    return {
        "total_usuarios": total_usuarios,
        "total_analisis": total_analisis,
        "por_usuario": [dict(r) for r in por_usuario],
        "recientes": [dict(r) for r in recientes]
    }


def eliminar_usuario(user_id):
    """Elimina un usuario por su ID. Solo el admin puede hacer esto."""
    conn = get_connection()
    conn.execute("DELETE FROM usuarios WHERE id = ?", (user_id,))
    conn.execute("DELETE FROM actividad WHERE usuario_id = ?", (user_id,))
    conn.commit()
    conn.close()