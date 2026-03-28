from flask import Flask, request, jsonify
from flask_cors import CORS
import psycopg2
import os
import logging
from urllib.parse import urlparse
from datetime import datetime

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
def add_oferta():
    try:
        data = request.json
        conn = conectar()
        c = conn.cursor()
        
        logger.info(f"📦 Recibido POST: nombre={data.get('nombre', '')[:30]}..., desc_len={len(str(data.get('descripcion', '')))}")
        
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

# ✅ OBTENER OFERTAS - ✅ CONSULTA CON COLUMNAS EXPLÍCITAS
@app.route("/api/ofertas", methods=["GET"])
def get_ofertas():
    try:
        categoria = request.args.get("categoria")
        activos = request.args.get("activos", "true")
        
        conn = conectar()
        c = conn.cursor()
        
        # ✅ CONSULTA CON NOMBRES DE COLUMNAS EXPLÍCITOS
        if activos.lower() == "true":
            if categoria:
                c.execute("""
                    SELECT id, nombre, precio, link, imagen, categoria, descripcion, activo, fecha_creacion 
                    FROM ofertas 
                    WHERE categoria=%s AND activo=TRUE 
                    ORDER BY fecha_creacion DESC
                """, (categoria,))
            else:
                c.execute("""
                    SELECT id, nombre, precio, link, imagen, categoria, descripcion, activo, fecha_creacion 
                    FROM ofertas 
                    WHERE activo=TRUE 
                    ORDER BY fecha_creacion DESC
                """)
        else:
            if categoria:
                c.execute("""
                    SELECT id, nombre, precio, link, imagen, categoria, descripcion, activo, fecha_creacion 
                    FROM ofertas 
                    WHERE categoria=%s 
                    ORDER BY fecha_creacion DESC
                """, (categoria,))
            else:
                c.execute("""
                    SELECT id, nombre, precio, link, imagen, categoria, descripcion, activo, fecha_creacion 
                    FROM ofertas 
                    ORDER BY fecha_creacion DESC
                """)
        
        rows = c.fetchall()
        conn.close()
        
        # ✅ CONVERTIR FILAS A DICCIONARIOS USANDO NOMBRES DE COLUMNAS
        ofertas = []
        for r in rows:
            ofertas.append({
                "id": r[0],
                "nombre": r[1],
                "precio": r[2],
                "link": r[3],
                "imagen": r[4],
                "categoria": r[5],
                "descripcion": str(r[6]) if r[6] is not None else "",  # ✅ AHORA SÍ ES DESCRIPCIÓN
                "activo": bool(r[7]) if r[7] is not None else True,    # ✅ AHORA SÍ ES ACTIVO
                "fecha_creacion": str(r[8]) if r[8] is not None else None
            })
        
        return jsonify(ofertas)
    except Exception as e:
        logger.error(f"❌ Error get_ofertas: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

# ✅ ACTUALIZAR ESTADO ACTIVO/INACTIVO - ✅ SINTAXIS CORREGIDA
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

# ✅ ACTUALIZAR DESCRIPCIÓN (para migración) - ✅ SINTAXIS CORREGIDA
@app.route("/api/ofertas/<int:id>", methods=["PATCH"])
def update_descripcion(id):
    """Actualiza solo el campo descripción de una oferta"""
    try:
        data = request.json
        conn = conectar()
        c = conn.cursor()
        
        # ✅ CORREGIDO: Verificar si "descripcion" está en data
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

# ✅ ELIMINAR OFERTA - ✅ SINTAXIS CORREGIDA
@app.route("/api/ofertas/<int:id>", methods=["DELETE"])
def delete_oferta(id):
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
        
        return jsonify({
            "total": total,
            "activos": activos,
            "inactivos": inactivos
        })
    except Exception as e:
        logger.error(f"❌ Error get_estadisticas: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

# ==================== RUN APP ====================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
