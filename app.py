from flask import Flask, request, jsonify, render_template, abort
from flask_cors import CORS
import psycopg2
import os
import logging
from urllib.parse import urlparse
from datetime import datetime
from functools import wraps

# ==================== CONFIGURACIÓN LOGGING ====================
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ==================== INICIALIZAR FLASK ====================
app = Flask(__name__)

# ==================== CONFIGURAR CORS ====================
DOMINIOS_PERMITIDOS = [
    "https://www.spainlinks.com",
    "https://spainlinks.com",
    "https://ofertas-web.onrender.com",
    "http://localhost:5500",
    "http://127.0.0.1:5500"
]

CORS(app, resources={r"/*": {
    "origins": DOMINIOS_PERMITIDOS,
    "methods": ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    "allow_headers": ["Content-Type", "X-API-KEY"],
}})

# ==================== SEGURIDAD API ====================
API_SECRET_KEY = os.environ.get("API_SECRET_KEY", "clave_desarrollo_local_123")

def requiere_api_key(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        api_key = request.headers.get('X-API-KEY')
        if not api_key or api_key != API_SECRET_KEY:
            return jsonify({"status": "error", "message": "No autorizado"}), 401
        return f(*args, **kwargs)
    return decorated

# ==================== BASE DE DATOS ====================
def conectar():
    DATABASE_URL = os.environ.get("DATABASE_URL")
    if not DATABASE_URL:
        raise Exception("DATABASE_URL no configurada en Render")
    result = urlparse(DATABASE_URL)
    return psycopg2.connect(
        database=result.path[1:],
        user=result.username,
        password=result.password,
        host=result.hostname,
        port=result.port,
        sslmode='require'
    )

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
                categoria TEXT,
                descripcion TEXT,
                activo BOOLEAN DEFAULT TRUE,
                fecha_creacion TIMESTAMP DEFAULT NOW(),
                ultima_verificacion TIMESTAMP DEFAULT NOW(),
                votos_calientes INT DEFAULT 0,
                votos_frios INT DEFAULT 0
            )
        """)
        
        # Verificar columnas para actualizaciones
        c.execute("SELECT column_name FROM information_schema.columns WHERE table_name='ofertas'")
        cols = [row[0] for row in c.fetchall()]
        if 'votos_calientes' not in cols:
            c.execute("ALTER TABLE ofertas ADD COLUMN votos_calientes INT DEFAULT 0")
        if 'votos_frios' not in cols:
            c.execute("ALTER TABLE ofertas ADD COLUMN votos_frios INT DEFAULT 0")

        c.execute("""
            CREATE TABLE IF NOT EXISTS comentarios (
                id SERIAL PRIMARY KEY,
                oferta_id INT REFERENCES ofertas(id) ON DELETE CASCADE,
                usuario TEXT NOT NULL,
                texto TEXT NOT NULL,
                fecha TIMESTAMP DEFAULT NOW(),
                activo BOOLEAN DEFAULT TRUE
            )
        """)
        conn.commit()
        conn.close()
        logger.info("✅ DB Lista")
    except Exception as e:
        logger.error(f"❌ Error DB: {e}")

init_db()

# ==================== RUTAS SEO ====================
@app.route("/")
def home():
    return render_template("index.html", meta=None)

@app.route("/producto/<int:producto_id>")
def seo_producto(producto_id):
    try:
        conn = conectar()
        c = conn.cursor()
        c.execute("SELECT nombre, descripcion, imagen, precio FROM ofertas WHERE id = %s", (producto_id,))
        row = c.fetchone()
        conn.close()
        if not row: return render_template("index.html", meta=None), 404
        meta = {
            "title": f"{row[0]} - SPAIN LINKS",
            "description": row[1][:150] if row[1] else f"¡Chollo por {row[3]}!",
            "image": row[2],
            "url": f"https://spainlinks.com/producto/{producto_id}"
        }
        return render_template("index.html", meta=meta)
    except: return render_template("index.html", meta=None)

# ==================== API OFERTAS ====================
@app.route("/api/ofertas", methods=["POST"])
@requiere_api_key
def add_oferta():
    data = request.json
    conn = conectar()
    c = conn.cursor()
    c.execute("""
        INSERT INTO ofertas (nombre, precio, link, imagen, categoria, descripcion, activo)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    """, (data.get("nombre"), data.get("precio"), data.get("link"), data.get("imagen"),
          data.get("categoria"), data.get("descripcion", ""), data.get("activo", True)))
    conn.commit()
    conn.close()
    return jsonify({"status": "ok"})

@app.route("/api/ofertas", methods=["GET"])
def get_ofertas():
    categoria = request.args.get("categoria")
    activos = request.args.get("activos", "true")
    page = max(1, int(request.args.get("page", 1)))
    limit = min(100, max(1, int(request.args.get("limit", 20))))
    offset = (page - 1) * limit
    
    conn = conectar()
    c = conn.cursor()
    conditions = ["activo=TRUE"] if activos.lower() == "true" else []
    params = []
    if categoria:
        conditions.append("categoria=%s")
        params.append(categoria)
    where = "WHERE " + " AND ".join(conditions) if conditions else ""
    
    c.execute(f"SELECT COUNT(*) FROM ofertas {where}", tuple(params))
    total = c.fetchone()[0]
    c.execute(f"SELECT id, nombre, precio, link, imagen, categoria, descripcion, activo, fecha_creacion, votos_calientes, votos_frios FROM ofertas {where} ORDER BY fecha_creacion DESC LIMIT %s OFFSET %s", tuple(params) + (limit, offset))
    rows = c.fetchall()
    conn.close()
    
    res = []
    for r in rows:
        res.append({"id": r[0], "nombre": r[1], "precio": r[2], "link": r[3], "imagen": r[4], "categoria": r[5], "descripcion": r[6], "activo": r[7], "fecha_creacion": str(r[8]), "votos_calientes": r[9], "votos_frios": r[10]})
    return jsonify({"ofertas": res, "total": total})

@app.route("/api/ofertas/<int:id>/activo", methods=["PATCH"])
@requiere_api_key
def update_activo(id):
    data = request.json
    conn = conectar()
    c = conn.cursor()
    c.execute("UPDATE ofertas SET activo=%s WHERE id=%s", (data.get("activo"), id))
    conn.commit()
    conn.close()
    return jsonify({"status": "ok"})

@app.route("/api/ofertas/<int:id>/voto", methods=["POST"])
def votar(id):
    tipo = request.json.get("tipo")
    conn = conectar()
    c = conn.cursor()
    col = "votos_calientes" if tipo == "caliente" else "votos_frios"
    c.execute(f"UPDATE ofertas SET {col} = {col} + 1 WHERE id=%s", (id,))
    conn.commit()
    c.execute("SELECT votos_calientes, votos_frios FROM ofertas WHERE id=%s", (id,))
    r = c.fetchone()
    conn.close()
    return jsonify({"calientes": r[0], "frios": r[1]})

@app.route("/api/ofertas/<int:id>/comentarios", methods=["GET"])
def get_comentarios(id):
    conn = conectar()
    c = conn.cursor()
    c.execute("SELECT id, usuario, texto, fecha FROM comentarios WHERE oferta_id=%s AND activo=TRUE ORDER BY fecha DESC", (id,))
    rows = c.fetchall()
    conn.close()
    return jsonify([{"id":r[0], "usuario":r[1], "texto":r[2], "fecha":str(r[3])} for r in rows])

@app.route("/api/ofertas/<int:id>/comentarios", methods=["POST"])
def add_comentario(id):
    data = request.json
    conn = conectar()
    c = conn.cursor()
    c.execute("INSERT INTO comentarios (oferta_id, usuario, texto) VALUES (%s, %s, %s)", (id, data.get("usuario", "Anónimo"), data.get("texto")))
    conn.commit()
    conn.close()
    return jsonify({"status": "ok"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
