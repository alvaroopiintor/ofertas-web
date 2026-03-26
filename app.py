from flask import Flask, request, jsonify
from flask_cors import CORS
import psycopg2
import os
from urllib.parse import urlparse
from datetime import datetime

app = Flask(__name__)  # ✅ CORREGIDO: __name__ con doble guión
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
        
        # ✅ Verificar y añadir columnas si no existen (para tablas existentes)
        c.execute("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name='ofertas'
        """)
        
        columnas_existentes = [row[0] for row in c.fetchall()]
        
        if 'descripcion' not in columnas_existentes:
            print("⚠️ Añadiendo columna 'descripcion'...")
            c.execute("ALTER TABLE ofertas ADD COLUMN descripcion TEXT")
        
        if 'activo' not in columnas_existentes:
            print("⚠️ Añadiendo columna 'activo'...")
            c.execute("ALTER TABLE ofertas ADD COLUMN activo BOOLEAN DEFAULT TRUE")
        
        if 'fecha_creacion' not in columnas_existentes:
            print("⚠️ Añadiendo columna 'fecha_creacion'...")
            c.execute("ALTER TABLE ofertas ADD COLUMN fecha_creacion TIMESTAMP DEFAULT NOW()")
        
        if 'ultima_verificacion' not in columnas_existentes:
            print("⚠️ Añadiendo columna 'ultima_verificacion'...")
            c.execute("ALTER TABLE ofertas ADD COLUMN ultima_verificacion TIMESTAMP DEFAULT NOW()")
        
        conn.commit()
        conn.close()
        print("✅ Base de datos inicializada correctamente")
    except Exception as e:
        print(f"❌ Error inicializando DB: {e}")

init_db()

# ==================== RUTAS API ====================

# ✅ AÑADIR OFERTA (con descripción)
@app.route("/api/ofertas", methods=["POST"])
def add_oferta():
    try:
        data = request.json
        conn = conectar()
        c = conn.cursor()
        
        c.execute("""
        INSERT INTO ofertas (nombre, precio, link, imagen, categoria, descripcion, activo)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (
            data.get("nombre"),
            data.get("precio"),
            data.get("link"),
            data.get("imagen"),
            data.get("categoria"),
            data.get("descripcion", ""),  # ✅ NUEVO: descripción opcional
            data.get("activo", True)       # ✅ NUEVO: activo por defecto
        ))
        
        conn.commit()
        conn.close()
        return jsonify({"status": "ok"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# ✅ OBTENER OFERTAS (filtra solo activas por defecto)
@app.route("/api/ofertas", methods=["GET"])
def get_ofertas():
    try:
        categoria = request.args.get("categoria")
        activos = request.args.get("activos", "true")  # ✅ Parámetro opcional
        
        conn = conectar()
        c = conn.cursor()
        
        # ✅ FILTRAR SOLO PRODUCTOS ACTIVOS POR DEFECTO
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
            # Si se piden todos (activos + inactivos)
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
                "id": r[0],
                "nombre": r[1],
                "precio": r[2],
                "link": r[3],
                "imagen": r[4],
                "categoria": r[5],
                "descripcion": r[6] if len(r) > 6 else "",
                "activo": r[7] if len(r) > 7 else True,
                "fecha_creacion": str(r[8]) if len(r) > 8 else None
            })
        
        return jsonify(ofertas)
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# ✅ ACTUALIZAR ESTADO ACTIVO/INACTIVO (NUEVA RUTA)
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
        return jsonify({"status": "error", "message": str(e)}), 500

# ✅ ELIMINAR OFERTA
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
        return jsonify({"status": "error", "message": str(e)}), 500

# ✅ OBTENER ESTADÍSTICAS (NUEVA RUTA)
@app.route("/api/estadisticas", methods=["GET"])
def get_estadisticas():
    try:
        conn = conectar()
        c = conn.cursor()
        
        # Total productos
        c.execute("SELECT COUNT(*) FROM ofertas")
        total = c.fetchone()[0]
        
        # Activos
        c.execute("SELECT COUNT(*) FROM ofertas WHERE activo=TRUE")
        activos = c.fetchone()[0]
        
        # Inactivos
        c.execute("SELECT COUNT(*) FROM ofertas WHERE activo=FALSE")
        inactivos = c.fetchone()[0]
        
        conn.close()
        
        return jsonify({
            "total": total,
            "activos": activos,
            "inactivos": inactivos
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# ==================== RUN APP ====================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
