# -*- coding: utf-8 -*-
from datetime import datetime
from flask import Flask, render_template, request, jsonify, send_file, redirect, url_for, flash
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from flask_bcrypt import Bcrypt
from dotenv import load_dotenv
import os
import re
import json
from modules.analyzer import analyze_file, get_sheets, analyze_all_sheets
from modules.ai_engine import generate_insights
from modules.pdf_generator import generar_pdf
from modules.historial import guardar_analisis, cargar_historial
from modules.database import (
    inicializar_db, crear_usuario, buscar_usuario_por_username,
    buscar_usuario_por_id, registrar_actividad, obtener_todos_usuarios,
    obtener_metricas, eliminar_usuario
)

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "clave_secreta_larga_1234")

bcrypt = Bcrypt(app)

# Configurar Flask-Login
login_manager = LoginManager(app)
login_manager.login_view = "login"  # Si no estas autenticado, te manda aqui
login_manager.login_message = "Inicia sesion para acceder."

UPLOAD_FOLDER = os.getenv("UPLOAD_FOLDER", "uploads")
REPORTS_FOLDER = os.getenv("REPORTS_FOLDER", "reports")

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(REPORTS_FOLDER, exist_ok=True)

ALLOWED_EXTENSIONS = {"csv", "xlsx", "xls"}


@login_manager.user_loader
def load_user(user_id):
    """Flask-Login llama esto para saber quien es el usuario activo."""
    return buscar_usuario_por_id(int(user_id))


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def crear_admin_inicial():
    """
    Crea el usuario admin la primera vez que arranca la app.
    Si ya existe, no hace nada.
    """
    admin = buscar_usuario_por_username("admin")
    if not admin:
        password_hash = bcrypt.generate_password_hash("admin1234").decode("utf-8")
        crear_usuario("admin", password_hash, rol="admin")
        print(">>> Admin creado: usuario=admin, contrasena=admin1234")
        print(">>> Cambia la contrasena desde el panel de admin.")


# ── INICIALIZACION ─────────────────────────────────────────────────────────────
inicializar_db()
crear_admin_inicial()


# ── RUTAS DE AUTENTICACION ────────────────────────────────────────────────────

@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("index"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        usuario = buscar_usuario_por_username(username)

        if usuario and bcrypt.check_password_hash(usuario.password_hash, password):
            login_user(usuario)
            return redirect(url_for("index"))
        else:
            flash("Usuario o contrasena incorrectos.")

    return render_template("login.html")


@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))


# ── PANEL DE ADMINISTRADOR ────────────────────────────────────────────────────

@app.route("/admin")
@login_required
def admin():
    if not current_user.es_admin():
        return redirect(url_for("index"))

    usuarios = obtener_todos_usuarios()
    metricas = obtener_metricas()
    return render_template("admin.html", usuarios=usuarios, metricas=metricas)


@app.route("/admin/crear-usuario", methods=["POST"])
@login_required
def crear_usuario_route():
    if not current_user.es_admin():
        return redirect(url_for("index"))

    username = request.form.get("username", "").strip()
    password = request.form.get("password", "")
    rol = request.form.get("rol", "usuario")

    if not username or not password:
        flash("Usuario y contrasena son obligatorios.")
        return redirect(url_for("admin"))

    password_hash = bcrypt.generate_password_hash(password).decode("utf-8")
    exito = crear_usuario(username, password_hash, rol)

    if exito:
        flash(f"Usuario '{username}' creado correctamente.")
    else:
        flash(f"El usuario '{username}' ya existe.")

    return redirect(url_for("admin"))


@app.route("/admin/eliminar-usuario/<int:user_id>", methods=["POST"])
@login_required
def eliminar_usuario_route(user_id):
    if not current_user.es_admin():
        return redirect(url_for("index"))

    if user_id == current_user.id:
        flash("No puedes eliminar tu propia cuenta.")
        return redirect(url_for("admin"))

    eliminar_usuario(user_id)
    flash("Usuario eliminado.")
    return redirect(url_for("admin"))


# ── RUTAS PRINCIPALES ─────────────────────────────────────────────────────────

@app.route("/")
@login_required
def index():
    return render_template("index.html")


@app.route("/analyze", methods=["POST"])
@login_required
def analyze():
    if "file" not in request.files:
        return jsonify({"error": "No se recibio ningun archivo"}), 400

    file = request.files["file"]

    if file.filename == "" or not allowed_file(file.filename):
        return jsonify({"error": "Formato no valido. Usa CSV o Excel"}), 400

    filename_clean = re.sub(r'[^a-zA-Z0-9._-]', '_', file.filename)
    filepath = os.path.join(UPLOAD_FOLDER, filename_clean)
    file.save(filepath)

    try:
        sheets = get_sheets(filepath)

        if sheets and len(sheets) > 1:
            sheet_name = request.form.get("sheet_name", sheets[0])
        else:
            sheet_name = 0

        resultado = analyze_file(filepath, sheet_name=sheet_name)
        insights = generate_insights(resultado)

        # Guardar historial y actividad con el usuario actual
        guardar_analisis(
            filename_clean, resultado, insights,
            usuario=current_user.username
        )
        registrar_actividad(
            current_user.id, current_user.username,
            filename_clean, resultado["filas"], resultado["columnas"]
        )

        return jsonify({
            "message": f"Archivo analizado: {resultado['filas']} filas, {resultado['columnas']} columnas.",
            "filename": filename_clean,
            "datos": resultado,
            "insights": insights,
            "sheets": sheets,
            "sheet_actual": sheet_name if sheets else None
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route("/analyze/all", methods=["POST"])
@login_required
def analyze_all():
    if "file" not in request.files:
        return jsonify({"error": "No se recibio ningun archivo"}), 400

    file = request.files["file"]

    if file.filename == "" or not allowed_file(file.filename):
        return jsonify({"error": "Formato no valido. Usa CSV o Excel"}), 400

    filename_clean = re.sub(r'[^a-zA-Z0-9._-]', '_', file.filename)
    filepath = os.path.join(UPLOAD_FOLDER, filename_clean)
    file.save(filepath)

    try:
        resultado = analyze_all_sheets(filepath)
        hojas = resultado.get("hojas_incluidas", [])
        insights = generate_insights(resultado)

        guardar_analisis(
            filename_clean, resultado, insights,
            usuario=current_user.username
        )
        registrar_actividad(
            current_user.id, current_user.username,
            filename_clean, resultado["filas"], resultado["columnas"]
        )

        return jsonify({
            "message": f"Analisis de {len(hojas)} hojas: {resultado['filas']} filas totales.",
            "filename": filename_clean,
            "datos": resultado,
            "insights": insights,
            "sheets": hojas,
            "sheet_actual": "todas"
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route("/export/pdf", methods=["POST"])
@login_required
def export_pdf():
    data = request.get_json()
    if not data:
        return jsonify({"error": "No se recibieron datos"}), 400

    resultado = data.get("datos", {})
    resultado["grafica"] = data.get("grafica")

    buffer = generar_pdf(
        filename=data.get("filename", "archivo"),
        resultado=resultado,
        insights=data.get("insights", "")
    )

    return send_file(
        buffer,
        mimetype="application/pdf",
        as_attachment=True,
        download_name=f"reporte_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    )


@app.route("/historial", methods=["GET"])
@login_required
def get_historial():
    # Cada usuario ve solo su historial
    return jsonify(cargar_historial(usuario=current_user.username))


@app.route("/historial/<registro_id>", methods=["GET"])
@login_required
def get_analisis(registro_id):
    detalle_path = os.path.join(REPORTS_FOLDER, f"analisis_{registro_id}.json")
    if not os.path.exists(detalle_path):
        return jsonify({"error": "Analisis no encontrado"}), 404
    with open(detalle_path, "r", encoding="utf-8") as f:
        return jsonify(json.load(f))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)