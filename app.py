from flask import Flask, request, jsonify
from flask_cors import CORS
import psycopg2
import os
from urllib.parse import urlparse

app = Flask(__name__)  # ✅ Corregido
CORS(app)

# -----------------------------
# Conexión a PostgreSQL (Neon)
# -----------------------------
def conectar():
    DATABASE_URL = os.environ.get("DATABASE_URL")
    if not DATABASE_URL:
        raise Exception("DATABASE_URL no configurada en Render")
    
    # Parsear URL para psycopg2
    result = urlparse(DATABASE_URL)
    conn = psycopg2.connect(
        database=result.path[1:],
        user=result.username,
        password=result.password,
        host=result.hostname,
        port=result.port,
        sslmode='require'  # ✅ Requerido para Neon
    )
    return conn

def init_db():
    try:
        conn = conectar()
        c = conn.cursor()
        c.execute("""
        CREATE TABLE IF NOT EXISTS ofertas (
            id SERIAL PRIMARY KEY,
            nombre TEXT,
            precio TEXT,
            link TEXT,
            imagen TEXT,
            categoria TEXT
        )
        """)
        conn.commit()
        conn.close()
        print("✅ Base de datos inicializada correctamente")
    except Exception as e:
        print(f"❌ Error inicializando DB: {e}")

# Inicializar DB al iniciar
init_db()

# -----------------------------
# RUTAS API
# -----------------------------
@app.route("/api/ofertas", methods=["POST"])
def add_oferta():
    try:
        data = request.json
        conn = conectar()
        c = conn.cursor()
        c.execute("""
        INSERT INTO ofertas (nombre, precio, link, imagen, categoria)
        VALUES (%s, %s, %s, %s, %s)
        """, (
            data.get("nombre"),
            data.get("precio"),
            data.get("link"),
            data.get("imagen"),
            data.get("categoria")
        ))
        conn.commit()
        conn.close()
        return jsonify({"status": "ok"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/api/ofertas", methods=["GET"])
def get_ofertas():
    try:
        categoria = request.args.get("categoria")
        conn = conectar()
        c = conn.cursor()
        
        if categoria:
            c.execute("SELECT * FROM ofertas WHERE categoria=%s ORDER BY id DESC", (categoria,))
        else:
            c.execute("SELECT * FROM ofertas ORDER BY id DESC")
        
        rows = c.fetchall()
        conn.close()
        
        ofertas = []
        for r in rows:
            ofertas.append({
                "id": r[0],
                "nombre": r[1],
                "precio": r[2],
                "link": r[3],
                "imagen": r[4],
                "categoria": r[5]
            })
        
        return jsonify(ofertas)
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/api/ofertas/<int:id>", methods=["DELETE"])  # ✅ Corregido sintaxis
def delete_oferta(id):
    try:
        conn = conectar()
        c = conn.cursor()
        c.execute("DELETE FROM ofertas WHERE id=%s", (id,))
        conn.commit()
        conn.close()
        return jsonify({"status": "deleted"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# -----------------------------
# RUN APP
# -----------------------------
if __name__ == "__main__":  # ✅ Corregido
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
