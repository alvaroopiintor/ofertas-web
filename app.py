from flask import Flask, request, jsonify, render_template, abort
from flask_cors import CORS
from psycopg2 import pool
from contextlib import contextmanager
import os
import logging
from urllib.parse import urlparse
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

# ==================== BASE DE DATOS (CONNECTION POOL) ====================
db_pool = None

def init_db_pool():
    global db_pool
    DATABASE_URL = os.environ.get("DATABASE_URL")
    if not DATABASE_URL:
        logger.warning("DATABASE_URL no configurada. (Ignorar si no se requiere DB inmediatamente)")
        return
    
    result = urlparse(DATABASE_URL)
    try:
        # Inicializamos el ThreadedConnectionPool
        db_pool = pool.ThreadedConnectionPool(
            minconn=1,
            maxconn=20,
            database=result.path[1:],
            user=result.username,
            password=result.password,
            host=result.hostname,
            port=result.port,
            sslmode='require'
        )
        logger.info("✅ Connection Pool de PostgreSQL inicializado correctamente")
    except Exception as e:
        logger.error(f"❌ Error inicializando el Connection Pool: {e}")

# Ejecutamos la inicialización del pool al arrancar
init_db_pool()

@contextmanager
def get_db_connection():
    """Context manager para obtener y liberar conexiones del pool de forma segura."""
    if not db_pool:
        raise Exception("El Connection Pool no está inicializado.")
    conn = None
    try:
        conn = db_pool.getconn()
        yield conn
    finally:
        if conn:
            db_pool.putconn(conn)

def init_db():
    try:
        with get_db_connection() as conn:
            c = conn.cursor()
            c.execute("""
                CREATE TABLE IF NOT EXISTS ofertas (
                    id SERIAL PRIMARY KEY,
                    nombre TEXT,
                    precio TEXT,
                    precio_antes TEXT,
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
            if 'precio_antes' not in cols:
                c.execute("ALTER TABLE ofertas ADD COLUMN precio_antes TEXT")
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
        logger.info("✅ DB Lista")
    except Exception as e:
        logger.error(f"❌ Error DB: {e}")

# Solo ejecutamos init_db si hay URL configurada
if os.environ.get("DATABASE_URL"):
    init_db()

# ==================== RUTAS SEO ====================
@app.route("/")
def home():
    return render_template("index.html", meta=None)

@app.route("/ping")
def ping():
    """Ruta ligera para mantener el servidor despierto desde Google Apps Script"""
    return jsonify({"status": "ok", "mensaje": "Servidor despierto"})

@app.route("/producto/<int:producto_id>")
def seo_producto(producto_id):
    try:
        with get_db_connection() as conn:
            c = conn.cursor()
            c.execute("SELECT nombre, descripcion, imagen, precio FROM ofertas WHERE id = %s", (producto_id,))
            row = c.fetchone()
            
        if not row: return render_template("index.html", meta=None), 404
        meta = {
            "title": f"{row[0]} - SPAIN LINKS",
            "description": row[1][:150] if row[1] else f"¡Chollo por {row[3]}!",
            "image": row[2],
            "url": f"https://spainlinks.com/producto/{producto_id}"
        }
        return render_template("index.html", meta=meta)
    except Exception as e: 
        logger.error(f"Error SEO producto: {e}")
        return render_template("index.html", meta=None)

# ==================== API OFERTAS ====================
@app.route("/api/ofertas", methods=["POST"])
@requiere_api_key
def add_oferta():
    data = request.json
    try:
        with get_db_connection() as conn:
            c = conn.cursor()
            # CAMBIA EL c.execute POR ESTE:
            c.execute("""
                INSERT INTO ofertas (nombre, precio, precio_antes, link, imagen, categoria, descripcion, activo)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (data.get("nombre"), data.get("precio"), data.get("precio_antes"), data.get("link"),
                  data.get("imagen"), data.get("categoria"), data.get("descripcion", ""), data.get("activo", True)))
        return jsonify({"status": "ok"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/api/ofertas", methods=["GET"])
def get_ofertas():
    categoria = request.args.get("categoria")
    activos = request.args.get("activos", "true")
    sort = request.args.get("sort", "default")
    search = request.args.get("search", "").strip()
    
    page = max(1, int(request.args.get("page", 1)))
    limit = min(100, max(1, int(request.args.get("limit", 20))))
    offset = (page - 1) * limit
    
    conditions = ["activo=TRUE"] if activos.lower() == "true" else []
    params = []
    
    # 1. Filtro de categoría
    if categoria and categoria != 'all':
        conditions.append("categoria=%s")
        params.append(categoria)
        
    # 2. Filtro de búsqueda (Buscador del header)
    if search:
        conditions.append("(LOWER(nombre) LIKE LOWER(%s) OR LOWER(categoria) LIKE LOWER(%s))")
        params.extend([f"%{search}%", f"%{search}%"])
        
    where = "WHERE " + " AND ".join(conditions) if conditions else ""
    
    # 3. Lógica de Ordenación en BD
    order_by = "ORDER BY fecha_creacion DESC"
    if sort == "votes":
        order_by = "ORDER BY (votos_calientes - votos_frios) DESC"
    elif sort == "price-asc":
        # Extrae números del texto "12,99€" y reemplaza coma por punto para ordenar
        order_by = "ORDER BY NULLIF(regexp_replace(replace(precio, ',', '.'), '[^0-9.]', '', 'g'), '')::NUMERIC ASC"
    elif sort == "price-desc":
        order_by = "ORDER BY NULLIF(regexp_replace(replace(precio, ',', '.'), '[^0-9.]', '', 'g'), '')::NUMERIC DESC"
    
    try:
        with get_db_connection() as conn:
            c = conn.cursor()
            # Contar total de resultados para la paginación del frontend
            c.execute(f"SELECT COUNT(*) FROM ofertas {where}", tuple(params))
            total = c.fetchone()[0]
            
            # Obtener solo los productos de la página solicitada
            c.execute(f"""
                SELECT id, nombre, precio, precio_antes, link, imagen, categoria, descripcion, 
                       activo, fecha_creacion, votos_calientes, votos_frios 
                FROM ofertas {where} {order_by} LIMIT %s OFFSET %s
            """, tuple(params) + (limit, offset))

            rows = c.fetchall()
            
       res = [{"id": r[0], "nombre": r[1], "precio": r[2], "precio_antes": r[3], "link": r[4], 
               "imagen": r[5], "categoria": r[6], "descripcion": r[7], "activo": r[8], 
               "fecha_creacion": str(r[9]), "votos_calientes": r[10], "votos_frios": r[11]} for r in rows]
                
        return jsonify({"ofertas": res, "total": total})
    except Exception as e:
        logger.error(f"Error cargando ofertas: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/stats", methods=["GET"])
def get_stats():
    """Devuelve el conteo total y por categorías para el frontend"""
    try:
        with get_db_connection() as conn:
            c = conn.cursor()
            # Contar totales
            c.execute("SELECT COUNT(*) FROM ofertas")
            total = c.fetchone()[0]
            
            # Contar activos
            c.execute("SELECT COUNT(*) FROM ofertas WHERE activo=TRUE")
            activos = c.fetchone()[0]
            
            # Contar por categorías (solo activos)
            c.execute("SELECT categoria, COUNT(*) FROM ofertas WHERE activo=TRUE GROUP BY categoria")
            categorias_db = c.fetchall()
            # Convertimos la respuesta en un diccionario {'tecnologia': 15, 'hogar': 8, ...}
            categorias_dict = {row[0]: row[1] for row in categorias_db}
            
        return jsonify({
            "total": total, 
            "activos": activos,
            "categorias": categorias_dict
        })
    except Exception as e:
        logger.error(f"Error obteniendo stats: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500



@app.route("/api/ofertas/<int:id>/activo", methods=["PATCH"])
@requiere_api_key
def update_activo(id):
    data = request.json
    try:
        with get_db_connection() as conn:
            c = conn.cursor()
            c.execute("UPDATE ofertas SET activo=%s WHERE id=%s", (data.get("activo"), id))
            conn.commit()
        return jsonify({"status": "ok"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/api/ofertas/<int:id>/voto", methods=["POST"])
def votar(id):
    tipo = request.json.get("tipo")
    col = "votos_calientes" if tipo == "caliente" else "votos_frios"
    try:
        with get_db_connection() as conn:
            c = conn.cursor()
            c.execute(f"UPDATE ofertas SET {col} = {col} + 1 WHERE id=%s", (id,))
            conn.commit()
            c.execute("SELECT votos_calientes, votos_frios FROM ofertas WHERE id=%s", (id,))
            r = c.fetchone()
        return jsonify({"calientes": r[0], "frios": r[1]})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/ofertas/<int:id>/comentarios", methods=["GET"])
def get_comentarios(id):
    # Paginación segura: por defecto página 1, 10 comentarios por página (máximo 50)
    page = max(1, int(request.args.get("page", 1)))
    limit = min(50, max(1, int(request.args.get("limit", 10))))
    offset = (page - 1) * limit

    try:
        with get_db_connection() as conn:
            c = conn.cursor()
            
            # 1. Obtener el total de comentarios activos para este producto
            c.execute("SELECT COUNT(*) FROM comentarios WHERE oferta_id=%s AND activo=TRUE", (id,))
            total = c.fetchone()[0]
            
            # 2. Obtener solo los comentarios de esta página
            c.execute("""
                SELECT id, usuario, texto, fecha 
                FROM comentarios 
                WHERE oferta_id=%s AND activo=TRUE 
                ORDER BY fecha DESC 
                LIMIT %s OFFSET %s
            """, (id, limit, offset))
            rows = c.fetchall()
            
        comentarios_lista = [{"id":r[0], "usuario":r[1], "texto":r[2], "fecha":str(r[3])} for r in rows]
        
        # Devolvemos un diccionario con los datos y la metadata de paginación
        return jsonify({
            "comentarios": comentarios_lista,
            "total": total,
            "page": page,
            "limit": limit
        })
    except Exception as e:
        logger.error(f"Error cargando comentarios paginados: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/ofertas/<int:id>/comentarios", methods=["POST"])
def add_comentario(id):
    data = request.json
    try:
        with get_db_connection() as conn:
            c = conn.cursor()
            c.execute("INSERT INTO comentarios (oferta_id, usuario, texto) VALUES (%s, %s, %s)", (id, data.get("usuario", "Anónimo"), data.get("texto")))
            conn.commit()
        return jsonify({"status": "ok"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
