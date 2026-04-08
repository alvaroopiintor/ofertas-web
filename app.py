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


# ==================== CONFIGURAR CORS (RESTRINGIDO) ====================
DOMINIOS_PERMITIDOS = [
    "https://www.spainlinks.com",
    "https://spainlinks.com",  # SUSTITUYE ESTO POR TU URL REAL DE NETLIFY
    "http://localhost:5500",              # Para Live Server de VSCode
    "http://127.0.0.1:5500",              # Alternativa de Live Server
    "http://localhost:3000"               # Por si usas otros servidores locales
]

CORS(app, resources={r"/*": {
    "origins": DOMINIOS_PERMITIDOS,
    "methods": ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    "allow_headers": ["Content-Type", "X-API-KEY"],
    "expose_headers": ["Content-Type"],
    "supports_credentials": False
}})



# ==================== RUTAS PARA SEO Y NAVEGACIÓN ====================

@app.route("/")
def home():
    # Renderiza la home normal
    return render_template("index.html", meta=None)

@app.route("/producto/<int:producto_id>")
def seo_producto(producto_id):
    try:
        conn = conectar()
        c = conn.cursor()
        # Buscamos los datos básicos para las Meta Tags
        c.execute("""
            SELECT nombre, descripcion, imagen, precio 
            FROM ofertas WHERE id = %s
        """, (producto_id,))
        row = c.fetchone()
        conn.close()

        if not row:
            return render_template("index.html", meta=None), 404

        # Preparamos los datos para el SEO
        meta_data = {
            "title": f"{row[0]} - Oferta en SPAIN LINKS",
            "description": (row[1][:150] + "...") if row[1] else f"¡Consigue este producto por solo {row[3]}!",
            "image": row[2],
            "url": f"https://tudominio.com/producto/{producto_id}" # Cambia por tu dominio real
        }

        return render_template("index.html", meta=meta_data)
    except Exception as e:
        logger.error(f"Error en SEO: {e}")
        return render_template("index.html", meta=None)



# ==================== CLAVE SECRETA API ====================
API_SECRET_KEY = os.environ.get("API_SECRET_KEY", "clave_desarrollo_local_123")

def requiere_api_key(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        api_key = request.headers.get('X-API-KEY')
        if not api_key or api_key != API_SECRET_KEY:
            return jsonify({"status": "error", "message": "No autorizado"}), 401
        return f(*args, **kwargs)
    return decorated



# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)



# ==================== CONEXIÓN A BASE DE DATOS ====================
def conectar():
    DATABASE_URL = os.environ.get("DATABASE_URL")
    if not DATABASE_URL:
        raise Exception("DATABASE_URL no configurada en Render")


    

    result = urlparse(DATABASE_URL)
    conn = psycopg2.connect(
        database=result.path[1:],
        user=result.username,
        password=result.password,
        host=result.hostname,
        port=result.port,
        sslmode='require'
    )
    return conn

# ==================== INICIALIZAR BASE DE DATOS ====================
def init_db():
    try:
        conn = conectar()
        c = conn.cursor()
        

        # ✅ TABLA PRINCIPAL DE OFERTAS

        # ✅ TABLA COMPLETA CON TODOS LOS CAMPOS NECESARIOS
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
            ultima_verificacion TIMESTAMP DEFAULT NOW()
        )
        """)
        

        # ✅ Verificar columnas existentes
        c.execute("SELECT column_name FROM information_schema.columns WHERE table_name='ofertas'")
        columnas_existentes = [row[0] for row in c.fetchall()]
        
        # ✅ Añadir columnas faltantes
        columnas_a_anadir = [
            ('descripcion', "ALTER TABLE ofertas ADD COLUMN descripcion TEXT"),
            ('activo', "ALTER TABLE ofertas ADD COLUMN activo BOOLEAN DEFAULT TRUE"),
            ('fecha_creacion', "ALTER TABLE ofertas ADD COLUMN fecha_creacion TIMESTAMP DEFAULT NOW()"),
            ('ultima_verificacion', "ALTER TABLE ofertas ADD COLUMN ultima_verificacion TIMESTAMP DEFAULT NOW()"),
            ('votos_calientes', "ALTER TABLE ofertas ADD COLUMN votos_calientes INT DEFAULT 0"),
            ('votos_frios', "ALTER TABLE ofertas ADD COLUMN votos_frios INT DEFAULT 0")
        ]
        
        for nombre_col, sql in columnas_a_anadir:
            if nombre_col not in columnas_existentes:
                logger.info(f"⚠️ Añadiendo columna '{nombre_col}'...")
                c.execute(sql)

        # ✅ CREAR TABLA DE COMENTARIOS
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
        

        # ✅ Verificar y añadir columnas si no existen
        c.execute("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name='ofertas'
        """)
        
        columnas_existentes = [row[0] for row in c.fetchall()]
        
        if 'descripcion' not in columnas_existentes:
            logger.info("⚠️ Añadiendo columna 'descripcion'...")
            c.execute("ALTER TABLE ofertas ADD COLUMN descripcion TEXT")
        
        if 'activo' not in columnas_existentes:
            logger.info("⚠️ Añadiendo columna 'activo'...")
            c.execute("ALTER TABLE ofertas ADD COLUMN activo BOOLEAN DEFAULT TRUE")
        
        if 'fecha_creacion' not in columnas_existentes:
            logger.info("⚠️ Añadiendo columna 'fecha_creacion'...")
            c.execute("ALTER TABLE ofertas ADD COLUMN fecha_creacion TIMESTAMP DEFAULT NOW()")
        
        if 'ultima_verificacion' not in columnas_existentes:
            logger.info("⚠️ Añadiendo columna 'ultima_verificacion'...")
            c.execute("ALTER TABLE ofertas ADD COLUMN ultima_verificacion TIMESTAMP DEFAULT NOW()")
        


        conn.commit()
        conn.close()
        logger.info("✅ Base de datos inicializada correctamente")
    except Exception as e:
        logger.error(f"❌ Error inicializando DB: {e}")

init_db()

# ==================== RUTAS API ====================


# ✅ AÑADIR OFERTA (con descripción)


@app.route("/api/ofertas", methods=["POST"])
@requiere_api_key
def add_oferta():
    try:
        data = request.json
        conn = conectar()
        c = conn.cursor()


        logger.info(f"📦 Recibido POST: nombre={data.get('nombre', '')[:30]}...")
        c.execute("""
        INSERT INTO ofertas (nombre, precio, link, imagen, categoria, descripcion, activo)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (data.get("nombre"), data.get("precio"), data.get("link"), data.get("imagen"),
              data.get("categoria"), data.get("descripcion", ""), data.get("activo", True)))

        
        logger.info(f"📦 Recibido POST: nombre={data.get('nombre', '')[:30]}..., desc_len={len(data.get('descripcion', ''))}")
        
        c.execute("""
        INSERT INTO ofertas (nombre, precio, link, imagen, categoria, descripcion, activo)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (
            data.get("nombre"),
            data.get("precio"),
            data.get("link"),
            data.get("imagen"),
            data.get("categoria"),
            data.get("descripcion", ""),
            data.get("activo", True)
        ))
        


        conn.commit()
        conn.close()
        return jsonify({"status": "ok"})
    except Exception as e:
        logger.error(f"❌ Error add_oferta: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

# ✅ OBTENER OFERTAS
@app.route("/api/ofertas", methods=["GET"])
def get_ofertas():
    try:
        categoria = request.args.get("categoria")
        activos = request.args.get("activos", "true")
        


        # ✅ Paginación desde la DB
        page = max(1, int(request.args.get("page", 1)))
        limit = min(100, max(1, int(request.args.get("limit", 20))))
        offset = (page - 1) * limit
        
        conn = conectar()
        c = conn.cursor()
        
        conditions = []
        params = []
        if activos.lower() == "true":
            conditions.append("activo=TRUE")
        if categoria:
            conditions.append("categoria=%s")
            params.append(categoria)
            
        where_clause = ""
        if conditions:
            where_clause = "WHERE " + " AND ".join(conditions)
            
        # 1️⃣ Contar total para metadata
        c.execute(f"SELECT COUNT(*) FROM ofertas {where_clause}", tuple(params))
        total_items = c.fetchone()[0]
        total_pages = (total_items + limit - 1) // limit
        
        # 2️⃣ Obtener SOLO esta página
        c.execute(f"""
            SELECT id, nombre, precio, link, imagen, categoria, descripcion, activo, fecha_creacion,
                   COALESCE(votos_calientes, 0), COALESCE(votos_frios, 0)
            FROM ofertas {where_clause}
            ORDER BY fecha_creacion DESC
            LIMIT %s OFFSET %s
        """, tuple(params) + (limit, offset))

        conn = conectar()
        c = conn.cursor()
        
        if activos.lower() == "true":
            if categoria:
                c.execute("""
                    SELECT * FROM ofertas 
                    WHERE categoria=%s AND activo=TRUE 
                    ORDER BY fecha_creacion DESC
                """, (categoria,))
            else:
                c.execute("""
                    SELECT * FROM ofertas 
                    WHERE activo=TRUE 
                    ORDER BY fecha_creacion DESC
                """)
        else:
            if categoria:
                c.execute("""
                    SELECT * FROM ofertas 
                    WHERE categoria=%s 
                    ORDER BY fecha_creacion DESC
                """, (categoria,))
            else:
                c.execute("""
                    SELECT * FROM ofertas 
                    ORDER BY fecha_creacion DESC
                """)


        
        rows = c.fetchall()
        conn.close()
        
        ofertas = []
        for r in rows:
            ofertas.append({


                "id": r[0], "nombre": r[1], "precio": r[2], "link": r[3], "imagen": r[4],
                "categoria": r[5], "descripcion": str(r[6]) if r[6] else "",
                "activo": bool(r[7]) if r[7] is not None else True,
                "fecha_creacion": str(r[8]) if r[8] else None,
                "votos_calientes": r[9], "votos_frios": r[10]


                "id": r[0],
                "nombre": r[1],
                "precio": r[2],
                "link": r[3],
                "imagen": r[4],
                "categoria": r[5],
                "descripcion": str(r[6]) if len(r) > 6 and r[6] is not None else "",
                "activo": bool(r[7]) if len(r) > 7 else True,
                "fecha_creacion": str(r[8]) if len(r) > 8 else None


            })
            
        return jsonify({
            "ofertas": ofertas,
            "pagination": {
                "page": page,
                "limit": limit,
                "total": total_items,
                "pages": total_pages,
                "has_next": page < total_pages
            }
        })
    except Exception as e:
        logger.error(f"❌ Error get_ofertas: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500



@app.route("/api/ofertas/<int:id>/activo", methods=["PATCH", "OPTIONS"])
@requiere_api_key
def update_activo(id):
    if request.method == "OPTIONS":
        return jsonify({"status": "ok"}), 200
    try:
        data = request.json
        conn = conectar()
        c = conn.cursor()
        c.execute("UPDATE ofertas SET activo=%s, ultima_verificacion=NOW() WHERE id=%s",
                  (data.get("activo", False), id))
        conn.commit()
        conn.close()
        return jsonify({"status": "ok", "activo": data.get("activo", False)})

# ✅ ACTUALIZAR ESTADO ACTIVO/INACTIVO - ✅ RUTA CORREGIDA
@app.route("/api/ofertas/<int:id>/activo", methods=["PATCH"])
def update_activo(id):
    try:
        data = request.json
        activo = data.get("activo", False)
        
        conn = conectar()
        c = conn.cursor()
        
        c.execute("""
        UPDATE ofertas 
        SET activo=%s, ultima_verificacion=NOW() 
        WHERE id=%s
        """, (activo, id))
        
        conn.commit()
        conn.close()
        
        return jsonify({"status": "ok", "activo": activo})


    except Exception as e:
        logger.error(f"❌ Error update_activo: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500



@app.route("/api/ofertas/<int:id>", methods=["PATCH", "OPTIONS"])
@requiere_api_key
def update_descripcion(id):
    if request.method == "OPTIONS":
        return jsonify({"status": "ok"}), 200
    try:
        data = request.json
        if "descripcion" in data:
            conn = conectar()
            c = conn.cursor()
            c.execute("UPDATE ofertas SET descripcion=%s WHERE id=%s", (data["descripcion"], id))
            conn.commit()
            conn.close()

# ✅ NUEVA RUTA: ACTUALIZAR DESCRIPCIÓN (para migración)
@app.route("/api/ofertas/<int:id>", methods=["PATCH"])
def update_descripcion(id):
    """Actualiza solo el campo descripción de una oferta"""
    try:
        data = request.json
        conn = conectar()
        c = conn.cursor()
        
        # Solo actualizar descripción si se proporciona
        if "descripcion" in data:
            c.execute("""
            UPDATE ofertas 
            SET descripcion=%s 
            WHERE id=%s
            """, (data["descripcion"], id))
            conn.commit()
            logger.info(f"✅ Descripción actualizada para producto {id}")
        
        conn.close()


        return jsonify({"status": "ok"})
    except Exception as e:
        logger.error(f"❌ Error update_descripcion: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500



@app.route("/api/ofertas/<int:id>", methods=["DELETE", "OPTIONS"])
@requiere_api_key

# ✅ ELIMINAR OFERTA
@app.route("/api/ofertas/<int:id>", methods=["DELETE"])


def delete_oferta(id):
    if request.method == "OPTIONS":
        return jsonify({"status": "ok"}), 200
    try:
        conn = conectar()
        c = conn.cursor()
        c.execute("DELETE FROM ofertas WHERE id=%s", (id,))
        conn.commit()
        conn.close()
        return jsonify({"status": "deleted"})
    except Exception as e:
        logger.error(f"❌ Error delete_oferta: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500




# ✅ OBTENER ESTADÍSTICAS


@app.route("/api/estadisticas", methods=["GET"])
def get_estadisticas():
    try:
        conn = conectar()
        c = conn.cursor()


        c.execute("SELECT COUNT(*) FROM ofertas")
        total = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM ofertas WHERE activo=TRUE")
        activos = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM ofertas WHERE activo=FALSE")
        inactivos = c.fetchone()[0]
        conn.close()
        return jsonify({"total": total, "activos": activos, "inactivos": inactivos})

        
        c.execute("SELECT COUNT(*) FROM ofertas")
        total = c.fetchone()[0]
        
        c.execute("SELECT COUNT(*) FROM ofertas WHERE activo=TRUE")
        activos = c.fetchone()[0]
        
        c.execute("SELECT COUNT(*) FROM ofertas WHERE activo=FALSE")
        inactivos = c.fetchone()[0]
        
        conn.close()
        
        return jsonify({
            "total": total,
            "activos": activos,
            "inactivos": inactivos
        })


    except Exception as e:
        logger.error(f"❌ Error get_estadisticas: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500



# ==================== RUTAS COMUNIDAD: VOTOS Y COMENTARIOS ====================

@app.route("/api/ofertas/<int:id>/voto", methods=["POST", "OPTIONS"])
def votar_oferta(id):
    if request.method == "OPTIONS":
        return jsonify({"status": "ok"}), 200
    try:
        data = request.json
        tipo = data.get("tipo")
        if tipo not in ["caliente", "frio"]:
            return jsonify({"status": "error", "message": "Tipo inválido"}), 400
        conn = conectar()
        c = conn.cursor()
        if tipo == "caliente":
            c.execute("UPDATE ofertas SET votos_calientes = COALESCE(votos_calientes, 0) + 1 WHERE id=%s", (id,))
        else:
            c.execute("UPDATE ofertas SET votos_frios = COALESCE(votos_frios, 0) + 1 WHERE id=%s", (id,))
        conn.commit()
        c.execute("SELECT COALESCE(votos_calientes, 0), COALESCE(votos_frios, 0) FROM ofertas WHERE id=%s", (id,))
        row = c.fetchone()
        conn.close()
        return jsonify({"status": "ok", "calientes": row[0], "frios": row[1]})
    except Exception as e:
        logger.error(f"❌ Error votar_oferta: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/api/ofertas/<int:id>/comentarios", methods=["GET", "OPTIONS"])
def get_comentarios(id):
    if request.method == "OPTIONS":
        return jsonify({"status": "ok"}), 200
    try:
        conn = conectar()
        c = conn.cursor()
        c.execute("SELECT id, usuario, texto, fecha FROM comentarios WHERE oferta_id=%s AND activo=TRUE ORDER BY fecha DESC", (id,))
        rows = c.fetchall()
        conn.close()
        return jsonify([{"id": r[0], "usuario": r[1], "texto": r[2], "fecha": str(r[3])} for r in rows])
    except Exception as e:
        logger.error(f"❌ Error get_comentarios: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/api/ofertas/<int:id>/comentarios", methods=["POST", "OPTIONS"])
def add_comentario(id):
    if request.method == "OPTIONS":
        return jsonify({"status": "ok"}), 200
    try:
        data = request.json
        usuario = (data.get("usuario") or "Anónimo")[:50]
        texto = (data.get("texto") or "").strip()
        if not texto or len(texto) > 500:
            return jsonify({"status": "error", "message": "Comentario inválido"}), 400
        conn = conectar()
        c = conn.cursor()
        c.execute("INSERT INTO comentarios (oferta_id, usuario, texto) VALUES (%s, %s, %s)", (id, usuario, texto))
        conn.commit()
        conn.close()
        return jsonify({"status": "ok"})
    except Exception as e:
        logger.error(f"❌ Error add_comentario: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500



# ==================== RUN APP ====================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
