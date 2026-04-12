from flask import Flask, request, jsonify, render_template, abort
from flask_cors import CORS
from psycopg2 import pool
from contextlib import contextmanager
import os
import logging
from urllib.parse import urlparse
from functools import wraps
# NUEVOS IMPORTS PARA USUARIOS Y SEGURIDAD
from werkzeug.security import generate_password_hash, check_password_hash
import jwt
import datetime
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
import secrets
import string
from dotenv import load_dotenv # <--- AÑADE ESTO

load_dotenv()  # <--- 2. La ejecutas antes de cualquier otra cosa

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
JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "super_secreto_para_tokens_jwt_12345") # NUEVO
GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID")

def requiere_api_key(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        api_key = request.headers.get('X-API-KEY')
        if not api_key or api_key != API_SECRET_KEY:
            return jsonify({"status": "error", "message": "No autorizado"}), 401
        return f(*args, **kwargs)
    return decorated


def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization')
        
        if not token:
            return jsonify({"status": "error", "message": "Falta el token de sesión"}), 401
        
        try:
            # Quitamos la palabra 'Bearer ' si existe
            if token.startswith('Bearer '):
                token = token.split(" ")[1]
                
            data = jwt.decode(token, JWT_SECRET_KEY, algorithms=["HS256"])
            current_user_id = data['usuario_id']
        except Exception as e:
            return jsonify({"status": "error", "message": "Token inválido o expirado"}), 401
            
        return f(current_user_id, *args, **kwargs)
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

            # --- NUEVAS TABLAS PARA EL SISTEMA DE USUARIOS ---
            c.execute("""
                CREATE TABLE IF NOT EXISTS usuarios (
                    id SERIAL PRIMARY KEY,
                    email TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    nombre TEXT NOT NULL,
                    fecha_registro TIMESTAMP DEFAULT NOW(),
                    activo BOOLEAN DEFAULT TRUE
                )
            """)

            c.execute("""
                CREATE TABLE IF NOT EXISTS favoritos (
                    usuario_id INT REFERENCES usuarios(id) ON DELETE CASCADE,
                    oferta_id INT REFERENCES ofertas(id) ON DELETE CASCADE,
                    fecha_agregado TIMESTAMP DEFAULT NOW(),
                    PRIMARY KEY (usuario_id, oferta_id)
                )
            """)
            
            c.execute("""
                CREATE TABLE IF NOT EXISTS votos_usuarios (
                    usuario_id INT REFERENCES usuarios(id) ON DELETE CASCADE,
                    oferta_id INT REFERENCES ofertas(id) ON DELETE CASCADE,
                    tipo_voto VARCHAR(10) NOT NULL,
                    fecha_voto TIMESTAMP DEFAULT NOW(),
                    PRIMARY KEY (usuario_id, oferta_id)
                )
            """)
            # -------------------------------------------------

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

@app.route("/login")
def pagina_login():
    return render_template("login.html", meta={"title": "Iniciar Sesión - SPAIN LINKS"})

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
            conn.commit()
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
    # 3. Lógica de Ordenación en BD
    order_by = "ORDER BY fecha_creacion DESC"
    if sort == "votes":
        order_by = "ORDER BY (votos_calientes - votos_frios) DESC"
    elif sort == "price-asc":
        order_by = "ORDER BY CAST(NULLIF(regexp_replace(replace(precio, ',', '.'), '[^0-9.]', '', 'g'), '') AS NUMERIC) ASC NULLS LAST"
    elif sort == "price-desc":
        order_by = "ORDER BY CAST(NULLIF(regexp_replace(replace(precio, ',', '.'), '[^0-9.]', '', 'g'), '') AS NUMERIC) DESC NULLS LAST"
    elif sort == "discount-desc":
        order_by = """ORDER BY 
            CASE 
                WHEN precio_antes IS NOT NULL AND precio_antes != 'N/A' AND precio IS NOT NULL 
                     AND CAST(NULLIF(regexp_replace(replace(precio_antes, ',', '.'), '[^0-9.]', '', 'g'), '') AS NUMERIC) > 0
                THEN (CAST(NULLIF(regexp_replace(replace(precio_antes, ',', '.'), '[^0-9.]', '', 'g'), '') AS NUMERIC) - CAST(NULLIF(regexp_replace(replace(precio, ',', '.'), '[^0-9.]', '', 'g'), '') AS NUMERIC)) / CAST(NULLIF(regexp_replace(replace(precio_antes, ',', '.'), '[^0-9.]', '', 'g'), '') AS NUMERIC)
                ELSE 0 
            END DESC NULLS LAST"""
    elif sort == "discount-asc":
        order_by = """ORDER BY 
            CASE 
                WHEN precio_antes IS NOT NULL AND precio_antes != 'N/A' AND precio IS NOT NULL 
                     AND CAST(NULLIF(regexp_replace(replace(precio_antes, ',', '.'), '[^0-9.]', '', 'g'), '') AS NUMERIC) > 0
                THEN (CAST(NULLIF(regexp_replace(replace(precio_antes, ',', '.'), '[^0-9.]', '', 'g'), '') AS NUMERIC) - CAST(NULLIF(regexp_replace(replace(precio, ',', '.'), '[^0-9.]', '', 'g'), '') AS NUMERIC)) / CAST(NULLIF(regexp_replace(replace(precio_antes, ',', '.'), '[^0-9.]', '', 'g'), '') AS NUMERIC)
                ELSE 0 
            END ASC NULLS LAST"""

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
    """Devuelve las estadísticas avanzadas (Marketing) y categorías para el frontend"""
    try:
        with get_db_connection() as conn:
            c = conn.cursor()
            
            # 1. Contar ofertas activas
            c.execute("SELECT COUNT(*) FROM ofertas WHERE activo=TRUE")
            activos = c.fetchone()[0] or 0
            
            # 2. Contar chollos publicados HOY (FOMO)
            c.execute("SELECT COUNT(*) FROM ofertas WHERE DATE(fecha_creacion) = CURRENT_DATE AND activo=TRUE")
            chollos_hoy = c.fetchone()[0] or 0
            
            # 3. Sumar todos los votos de la comunidad (Prueba Social)
            c.execute("SELECT SUM(votos_calientes), SUM(votos_frios) FROM ofertas")
            votos = c.fetchone()
            votos_totales = (votos[0] or 0) + (votos[1] or 0)
            
            # 4. Calcular el Mayor Descuento actual de forma segura
            c.execute("SELECT precio, precio_antes FROM ofertas WHERE activo=TRUE AND precio_antes IS NOT NULL AND precio_antes != 'N/A'")
            precios_rows = c.fetchall()
            
            mayor_descuento = 0
            for precio_final, precio_original in precios_rows:
                if precio_final and precio_original:
                    try:
                        # Limpiamos el texto "12,99€" a número 12.99
                        p_num = float(str(precio_final).replace('€', '').replace('.', '').replace(',', '.').strip())
                        pa_num = float(str(precio_original).replace('€', '').replace('.', '').replace(',', '.').strip())
                        if pa_num > 0:
                            desc = round(((pa_num - p_num) / pa_num) * 100)
                            if desc > mayor_descuento:
                                mayor_descuento = desc
                    except Exception:
                        pass # Ignora si algún precio tiene texto raro
            
            # 5. Contar por categorías
            c.execute("SELECT categoria, COUNT(*) FROM ofertas WHERE activo=TRUE GROUP BY categoria")
            categorias_dict = {row[0]: row[1] for row in c.fetchall()}
            
        return jsonify({
            "activos": activos,
            "chollos_hoy": chollos_hoy,
            "votos_totales": votos_totales,
            "mayor_descuento": mayor_descuento,
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
@token_required  # <--- NUESTRO GUARDIÁN DE SEGURIDAD
def votar(current_user_id, id):
    tipo = request.json.get("tipo") # 'caliente' o 'frio'
    
    if tipo not in ['caliente', 'frio']:
        return jsonify({"status": "error", "message": "Tipo de voto inválido"}), 400

    try:
        with get_db_connection() as conn:
            c = conn.cursor()
            
            # 1. Comprobar si el usuario ya ha votado esta oferta
            c.execute("SELECT tipo_voto FROM votos_usuarios WHERE usuario_id = %s AND oferta_id = %s", (current_user_id, id))
            voto_existente = c.fetchone()
            
            # VARIABLE PARA SABER SI EL VOTO FUE AÑADIDO, CAMBIADO O QUITADO
            accion = None 

            if voto_existente:
                tipo_anterior = voto_existente[0]
                
                if tipo_anterior == tipo:
                    # Si pulsa el MISMO botón -> Quitar el voto
                    c.execute("DELETE FROM votos_usuarios WHERE usuario_id = %s AND oferta_id = %s", (current_user_id, id))
                    col_restar = "votos_calientes" if tipo == "caliente" else "votos_frios"
                    c.execute(f"UPDATE ofertas SET {col_restar} = GREATEST(0, {col_restar} - 1) WHERE id = %s", (id,))
                    accion = "quitado"
                else:
                    # Si pulsa el botón CONTRARIO -> Cambiar el voto
                    c.execute("UPDATE votos_usuarios SET tipo_voto = %s WHERE usuario_id = %s AND oferta_id = %s", (tipo, current_user_id, id))
                    
                    if tipo == "caliente":
                        c.execute("UPDATE ofertas SET votos_calientes = votos_calientes + 1, votos_frios = GREATEST(0, votos_frios - 1) WHERE id = %s", (id,))
                    else:
                        c.execute("UPDATE ofertas SET votos_frios = votos_frios + 1, votos_calientes = GREATEST(0, votos_calientes - 1) WHERE id = %s", (id,))
                    accion = "cambiado"
            else:
                # Si NUNCA ha votado -> Añadir el voto
                c.execute("INSERT INTO votos_usuarios (usuario_id, oferta_id, tipo_voto) VALUES (%s, %s, %s)", (current_user_id, id, tipo))
                col_sumar = "votos_calientes" if tipo == "caliente" else "votos_frios"
                c.execute(f"UPDATE ofertas SET {col_sumar} = {col_sumar} + 1 WHERE id = %s", (id,))
                accion = "añadido"

            conn.commit()
            
            # Devolver los nuevos totales
            c.execute("SELECT votos_calientes, votos_frios FROM ofertas WHERE id=%s", (id,))
            r = c.fetchone()
            
        return jsonify({
            "status": "ok", 
            "accion": accion,
            "calientes": r[0], 
            "frios": r[1],
            "voto_actual": tipo if accion != "quitado" else None
        })
        
    except Exception as e:
        logger.error(f"Error en voto: {e}")
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
@token_required # <--- Solo usuarios con "llave"
def add_comentario(current_user_id, id):
    data = request.json
    texto = data.get("texto", "").strip()
    
    if not texto:
        return jsonify({"status": "error", "message": "El comentario no puede estar vacío"}), 400

    try:
        with get_db_connection() as conn:
            c = conn.cursor()
            
            # 1. Buscamos el nombre REAL del usuario en la tabla 'usuarios'
            c.execute("SELECT nombre FROM usuarios WHERE id = %s", (current_user_id,))
            resultado = c.fetchone()
            
            if not resultado:
                return jsonify({"status": "error", "message": "Usuario no encontrado"}), 404
                
            nombre_real = resultado[0]
            
            # 2. Insertamos el comentario con el nombre verificado
            c.execute("""
                INSERT INTO comentarios (oferta_id, usuario, texto) 
                VALUES (%s, %s, %s)
            """, (id, nombre_real, texto))
            
            conn.commit()
            
        return jsonify({"status": "ok", "usuario": nombre_real})
        
    except Exception as e:
        logger.error(f"Error añadiendo comentario: {e}")
        return jsonify({"status": "error", "message": "Error al publicar el comentario"}), 500


# ==================== SISTEMA DE USUARIOS ====================

@app.route("/api/registro", methods=["POST"])
def registrar_usuario():
    data = request.json
    email = data.get("email", "").strip().lower()
    password = data.get("password", "")
    nombre = data.get("nombre", "").strip()

    if not email or not password or not nombre:
        return jsonify({"status": "error", "message": "Faltan campos obligatorios"}), 400

    if len(password) < 6:
        return jsonify({"status": "error", "message": "La contraseña debe tener al menos 6 caracteres"}), 400

    try:
        with get_db_connection() as conn:
            c = conn.cursor()
            
            # 1. Comprobar si el email ya existe
            c.execute("SELECT id FROM usuarios WHERE email = %s", (email,))
            if c.fetchone():
                return jsonify({"status": "error", "message": "Este email ya está registrado"}), 409
            
            # 2. Crear el Hash de la contraseña (Seguridad)
            hash_pw = generate_password_hash(password)
            
            # 3. Guardar el nuevo usuario en la base de datos
            c.execute("""
                INSERT INTO usuarios (email, password_hash, nombre)
                VALUES (%s, %s, %s)
                RETURNING id, nombre, email
            """, (email, hash_pw, nombre))
            
            nuevo_usuario = c.fetchone()
            conn.commit()
            
            return jsonify({
                "status": "ok", 
                "message": "Usuario registrado correctamente",
                "usuario": {
                    "id": nuevo_usuario[0],
                    "nombre": nuevo_usuario[1],
                    "email": nuevo_usuario[2]
                }
            })
            
    except Exception as e:
        logger.error(f"Error en registro: {e}")
        return jsonify({"status": "error", "message": "Error interno del servidor"}), 500



@app.route("/api/login", methods=["POST"])
def login():
    data = request.json
    email = data.get("email", "").strip().lower()
    password = data.get("password", "")

    if not email or not password:
        return jsonify({"status": "error", "message": "Email y contraseña requeridos"}), 400

    try:
        with get_db_connection() as conn:
            c = conn.cursor()
            # 1. Buscar al usuario por email
            c.execute("SELECT id, nombre, password_hash FROM usuarios WHERE email = %s AND activo = TRUE", (email,))
            usuario = c.fetchone()
            
            # 2. Verificar si existe y si la contraseña coincide
            if usuario and check_password_hash(usuario[2], password):
                # 3. Crear el Token JWT (Válido por 24 horas)
                token = jwt.encode({
                    'usuario_id': usuario[0],
                    'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=24)
                }, JWT_SECRET_KEY, algorithm="HS256")
                
                return jsonify({
                    "status": "ok",
                    "token": token,
                    "usuario": {
                        "id": usuario[0],
                        "nombre": usuario[1]
                    }
                })
            else:
                return jsonify({"status": "error", "message": "Credenciales inválidas"}), 401
                
    except Exception as e:
        logger.error(f"Error en login: {e}")
        return jsonify({"status": "error", "message": "Error en el servidor"}), 500


@app.route("/api/google-login", methods=["POST"])
def google_login():
    data = request.json
    token_google = data.get("credential")
    
    if not token_google:
        return jsonify({"status": "error", "message": "Token no proporcionado"}), 400
        
    try:
        # 1. Validar el token con los servidores de Google
        idinfo = id_token.verify_oauth2_token(token_google, google_requests.Request(), GOOGLE_CLIENT_ID)
        
        email = idinfo['email']
        nombre = idinfo.get('name', 'Usuario')
        
        with get_db_connection() as conn:
            c = conn.cursor()
            # 2. Buscar si el usuario ya existe
            c.execute("SELECT id, nombre FROM usuarios WHERE email = %s AND activo = TRUE", (email,))
            usuario = c.fetchone()
            
            if not usuario:
                # 3. Si no existe, lo registramos automáticamente.
                # Generamos una contraseña aleatoria de 32 caracteres que nadie conocerá.
                alphabet = string.ascii_letters + string.digits
                random_password = ''.join(secrets.choice(alphabet) for i in range(32))
                hash_pw = generate_password_hash(random_password)
                
                c.execute("""
                    INSERT INTO usuarios (email, password_hash, nombre)
                    VALUES (%s, %s, %s)
                    RETURNING id, nombre
                """, (email, hash_pw, nombre))
                usuario = c.fetchone()
                conn.commit()
                
            # 4. Crear nuestro propio Token de sesión (igual que en el login normal)
            token = jwt.encode({
                'usuario_id': usuario[0],
                'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=24)
            }, JWT_SECRET_KEY, algorithm="HS256")
            
            return jsonify({
                "status": "ok",
                "token": token,
                "usuario": {
                    "id": usuario[0],
                    "nombre": usuario[1]
                }
            })
    except ValueError:
        return jsonify({"status": "error", "message": "Token de Google inválido"}), 401
    except Exception as e:
        logger.error(f"Error en google login: {e}")
        return jsonify({"status": "error", "message": "Error interno del servidor"}), 500



@app.route("/api/favoritos", methods=["GET"])
@token_required
def get_favoritos(current_user_id):
    """Obtiene la lista de deseos del usuario logueado"""
    try:
        with get_db_connection() as conn:
            c = conn.cursor()
            c.execute("""
                SELECT o.id, o.nombre, o.precio, o.precio_antes, o.link, o.imagen, o.categoria 
                FROM ofertas o
                JOIN favoritos f ON o.id = f.oferta_id
                WHERE f.usuario_id = %s AND o.activo = TRUE
                ORDER BY f.fecha_agregado DESC
            """, (current_user_id,))
            rows = c.fetchall()
            
        res = [{"id": r[0], "nombre": r[1], "precio": r[2], "precio_antes": r[3], 
                "link": r[4], "imagen": r[5], "categoria": r[6]} for r in rows]
        return jsonify({"favoritos": res})
    except Exception as e:
        logger.error(f"Error obteniendo favoritos: {e}")
        return jsonify({"status": "error", "message": "No se pudieron cargar tus favoritos"}), 500

@app.route("/api/ofertas/<int:id>/favorito", methods=["POST"])
@token_required
def toggle_favorito(current_user_id, id):
    """Añade o quita un producto de favoritos"""
    try:
        with get_db_connection() as conn:
            c = conn.cursor()
            
            # Comprobar si ya existe en la tabla de favoritos
            c.execute("SELECT 1 FROM favoritos WHERE usuario_id = %s AND oferta_id = %s", (current_user_id, id))
            existe = c.fetchone()
            
            if existe:
                c.execute("DELETE FROM favoritos WHERE usuario_id = %s AND oferta_id = %s", (current_user_id, id))
                accion = "quitado"
            else:
                c.execute("INSERT INTO favoritos (usuario_id, oferta_id) VALUES (%s, %s)", (current_user_id, id))
                accion = "añadido"
                
            conn.commit()
        return jsonify({"status": "ok", "accion": accion})
    except Exception as e:
        logger.error(f"Error toggle favorito: {e}")
        return jsonify({"status": "error", "message": "Error al procesar favorito"}), 500


# ==================== RUTAS DE AJUSTES Y PERFIL ====================

@app.route("/ajustes")
def pagina_ajustes():
    return render_template("ajustes.html", meta={"title": "Ajustes de Perfil - SPAIN LINKS"})

@app.route("/api/usuarios/perfil", methods=["PUT"])
@token_required
def actualizar_perfil(current_user_id):
    data = request.json
    nombre = data.get("nombre", "").strip()
    email = data.get("email", "").strip().lower()

    if not nombre or not email:
        return jsonify({"status": "error", "message": "Nombre y email son obligatorios"}), 400

    try:
        with get_db_connection() as conn:
            c = conn.cursor()
            # Comprobar si el nuevo email ya está en uso por otro usuario
            c.execute("SELECT id FROM usuarios WHERE email = %s AND id != %s", (email, current_user_id))
            if c.fetchone():
                return jsonify({"status": "error", "message": "Este email ya está en uso por otra cuenta"}), 409

            c.execute("UPDATE usuarios SET nombre = %s, email = %s WHERE id = %s", (nombre, email, current_user_id))
            conn.commit()
            
        return jsonify({"status": "ok", "message": "Perfil actualizado", "usuario": {"id": current_user_id, "nombre": nombre, "email": email}})
    except Exception as e:
        logger.error(f"Error actualizando perfil: {e}")
        return jsonify({"status": "error", "message": "Error interno del servidor"}), 500

@app.route("/api/usuarios/password", methods=["PUT"])
@token_required
def actualizar_password(current_user_id):
    data = request.json
    password = data.get("password", "")

    if len(password) < 6:
        return jsonify({"status": "error", "message": "La contraseña debe tener al menos 6 caracteres"}), 400

    try:
        hash_pw = generate_password_hash(password)
        with get_db_connection() as conn:
            c = conn.cursor()
            c.execute("UPDATE usuarios SET password_hash = %s WHERE id = %s", (hash_pw, current_user_id))
            conn.commit()
        return jsonify({"status": "ok", "message": "Contraseña actualizada"})
    except Exception as e:
        logger.error(f"Error actualizando password: {e}")
        return jsonify({"status": "error", "message": "Error interno del servidor"}), 500

@app.route("/api/usuarios", methods=["DELETE"])
@token_required
def borrar_cuenta(current_user_id):
    try:
        with get_db_connection() as conn:
            c = conn.cursor()
            c.execute("DELETE FROM usuarios WHERE id = %s", (current_user_id,))
            conn.commit()
        return jsonify({"status": "ok", "message": "Cuenta eliminada"})
    except Exception as e:
        logger.error(f"Error borrando cuenta: {e}")
        return jsonify({"status": "error", "message": "Error interno del servidor"}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
