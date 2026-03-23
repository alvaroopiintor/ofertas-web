from flask import Flask, request, jsonify
from flask_cors import CORS
import sqlite3
import os

app = Flask(__name__)
CORS(app)

# -----------------------------
# Conexión a la base de datos
# -----------------------------
def conectar():
    return sqlite3.connect("database.db")

def init_db():
    conn = conectar()
    c = conn.cursor()

    c.execute("""
    CREATE TABLE IF NOT EXISTS ofertas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT,
        precio TEXT,
        link TEXT,
        imagen TEXT,
        categoria TEXT
    )
    """)

    conn.commit()
    conn.close()

# Inicializa la base de datos
init_db()

# -----------------------------
# RUTAS API
# -----------------------------

# 🔥 Añadir oferta (usado por tu bot)
@app.route("/api/ofertas", methods=["POST"])
def add_oferta():
    data = request.json
    
    conn = conectar()
    c = conn.cursor()

    c.execute("""
    INSERT INTO ofertas (nombre, precio, link, imagen, categoria)
    VALUES (?, ?, ?, ?, ?)
    """, (
        data.get("nombre"),
        data.get("precio"),
        data.get("link"),
        data.get("imagen"),
        data.get("categoria")
    ))

    conn.commit()
    conn.close()

    return {"status": "ok"}

# 🔥 Obtener ofertas (para la web)
@app.route("/api/ofertas", methods=["GET"])
def get_ofertas():
    categoria = request.args.get("categoria")

    conn = conectar()
    c = conn.cursor()

    if categoria:
        c.execute("SELECT * FROM ofertas WHERE categoria=?", (categoria,))
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

# 🔥 Borrar oferta (solo admin)
@app.route("/api/ofertas/<int:id>", methods=["DELETE"])
def delete_oferta(id):
    conn = conectar()
    c = conn.cursor()

    c.execute("DELETE FROM ofertas WHERE id=?", (id,))
    
    conn.commit()
    conn.close()

    return {"status": "deleted"}

# -----------------------------
# RUN APP (Render listo)
# -----------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)