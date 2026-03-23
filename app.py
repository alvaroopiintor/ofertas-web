from flask import Flask, request, jsonify
from flask_cors import CORS
import sqlite3

app = Flask(__name__)
CORS(app)

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

init_db()

# 🔥 AÑADIR OFERTA
@app.route("/api/ofertas", methods=["POST"])
def add_oferta():
    data = request.json
    
    conn = conectar()
    c = conn.cursor()

    c.execute("""
    INSERT INTO ofertas (nombre, precio, link, imagen, categoria)
    VALUES (?, ?, ?, ?, ?)
    """, (
        data["nombre"],
        data["precio"],
        data["link"],
        data["imagen"],
        data["categoria"]
    ))

    conn.commit()
    conn.close()

    return {"status": "ok"}

# 🔥 OBTENER OFERTAS
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

# 🔥 BORRAR (admin)
@app.route("/api/ofertas/<int:id>", methods=["DELETE"])
def delete_oferta(id):
    conn = conectar()
    c = conn.cursor()

    c.execute("DELETE FROM ofertas WHERE id=?", (id,))
    
    conn.commit()
    conn.close()

    return {"status": "deleted"}

app.run(debug=True)