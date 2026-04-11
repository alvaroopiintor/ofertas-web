import os
import time
import logging
import tempfile
import requests
from PIL import Image, ImageDraw, ImageFont
import telebot
from amazon_paapi import AmazonApi
from datetime import datetime, timedelta
from dotenv import load_dotenv  # ← AÑADIR ESTO

# 🔹 CARGAR VARIABLES DEL ARCHIVO .env (solo en desarrollo local)
load_dotenv()  # ← AÑADIR ESTO

# ==================== CONFIGURACIÓN ====================
TOKEN = os.environ.get("TOKEN")
API_SECRET_KEY = os.environ.get("API_SECRET_KEY", "clave_desarrollo_local_123")
CHAT_ID = os.environ.get("CHAT_ID")
ACCESS_KEY = os.environ.get("ACCESS_KEY")
SECRET_KEY = os.environ.get("SECRET_KEY")
PARTNER_TAG = "spainlinks-21"
ARCHIVO_HISTORIAL = "historial_asins.txt"
API_BASE = "https://ofertas-web.onrender.com"

# Umbrales de descuento
DESCUENTO_MINIMO = 15
DESCUENTO_PARA_DESACTIVAR = 10  # Si baja de esto, se marca como inactivo
PRODUCTOS_POR_KEYWORD = 5
PAUSA_ENTRE_PRODUCTOS = 2

# ==================== LOGGING ====================
# ✅ CAMBIO 1: Eliminar archivo log, solo mostrar en consola
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        # ✅ COMENTADO: logging.FileHandler('bot_amazon.log', encoding='utf-8'),
        logging.StreamHandler()  # ✅ Solo consola
    ]
)
logger = logging.getLogger(__name__)

# ==================== INICIALIZACIÓN ====================
bot = telebot.TeleBot(TOKEN)

try:
    amazon = AmazonApi(ACCESS_KEY, SECRET_KEY, PARTNER_TAG, country="ES")
    logger.info("✅ Amazon API conectada correctamente")
except Exception as e:
    logger.error(f"❌ Error conectando Amazon API: {e}")
    exit(1)

# ==================== MAPEO DE CATEGORÍAS ====================
# ==================== MAPEO DE CATEGORÍAS ====================
CATEGORIAS_MAP = {
    'tecnologia': ['auriculares', 'móvil', 'tablet', 'ordenador', 'laptop', 'pc',
                   'teclado', 'ratón', 'monitor', 'smartwatch', 'cámara', 'drone',
                   'iphone', 'samsung', 'xiaomi', 'huawei', 'usb', 'cable', 'cargador', 
                   'batería', 'powerbank', 'webcam', 'bluetooth', 'wifi', 'router', 
                   'ssd', 'disco duro', 'fire tv', 'chromecast', 'rgb', 'kindle', 'ereader',
                   'impresora', 'altavoz inteligente', 'podcast', 'tocadiscos', 'tv', 
                   'television', 'micro sd', 'cristal templado', 'soporte movil', 'led'],
                   
    'hogar': ['aspirador', 'cafetera', 'batidora', 'microondas', 'nevera', 'lavadora',
              'secadora', 'plancha', 'lámpara', 'silla', 'mesa', 'sofá', 'cama',
              'almohada', 'toalla', 'cortina', 'mueble', 'freidora', 'air fryer',
              'taper', 'botella', 'termo', 'humidificador', 'organizador', 'caja',
              'ventilador', 'sartén', 'olla', 'cuchillo', 'jardín', 'maceta', 
              'herramienta', 'taladro', 'alfombra', 'colchón', 'funda nordica', 
              'alexa', 'bricolaje', 'limpieza', 'fregona', 'escoba', 'tendedero'],
              
    'moda': ['zapatos', 'camiseta', 'pantalón', 'vestido', 'chaqueta', 'abrigo',
             'bolsa', 'cartera', 'reloj', 'gafas', 'sombrero', 'ropa',
             'zapatillas', 'botas', 'sandalias', 'sudadera', 'vaqueros', 'falda',
             'nike', 'adidas', 'crocs', 'chanclas', 'outfit', 'chandal', 'cinturón',
             'joyería', 'pulsera', 'collar', 'anillo', 'pijama', 'ropa interior', 
             'calcetines', 'bolso', 'bandolera', 'gorra', 'leggings', 'mallas', 
             'bufanda', 'paraguas', 'billetera'],
             
    'belleza': ['secador', 'plancha pelo', 'skincare', 'serum', 'crema',
                'maquillaje', 'espejo', 'cepillo', 'depiladora', 'afeitadora',
                'uñas', 'esmalte', 'rodillo', 'gua sha', 'perfume', 'colonia', 
                'champú', 'acondicionador', 'mascarilla', 'protector solar', 'barba',
                'cosmética', 'labial', 'rizador', 'limpiador facial', 'oral b', 'tensiometro'],
                
    'deportes': ['pesas', 'yoga', 'correr', 'bicicleta', 'gimnasio', 'fitness',
                 'fútbol', 'tenis', 'cinturon gimnasio', 'guantes', 'rodilleras', 'comba',
                 'mancuernas', 'proteina', 'creatina', 'padel', 'raqueta', 'natación', 
                 'camping', 'tienda campaña', 'saco dormir', 'patinete', 'scooter',
                 'suplemento', 'aminoacidos', 'balón', 'esterilla', 'running'],
                 
    'juguetes': ['lego', 'muñeca', 'peluche', 'juguete', 'puzzle', 'juego de mesa', 
                 'montessori', 'barbie', 'hot wheels', 'playmobil', 'nerf', 'plastilina', 
                 'coche radiocontrol', 'disfraz', 'juegos de cartas', 'piscina hinchable', 
                 'educativo', 'bricolaje juguete'],
                 
    'mascotas': ['perro', 'gato', 'comida perro', 'comida gato', 'correa', 'cama mascota', 
                 'mascota', 'rascador', 'comedero', 'bebedero', 'transportin', 'acuario', 
                 'pecera', 'arena gato', 'arnés', 'juguete perro', 'juguete gato',
                 'pienso', 'chucherias', 'collar antiparasitario', 'pipeta'],

    'videojuegos': ['ps5', 'playstation', 'xbox', 'nintendo switch', 'videojuego', 
                    'dualshock', 'dualsense', 'gamepass', 'ps plus', 'mando pc', 
                    'nintendo ds', 'ea sports', 'fifa', 'gta', 'consola', 'gaming'],
    
    'bebes_ninos': ['pañal', 'dodot', 'carrito bebe', 'sillita coche', 'chupete', 
                    'biberón', 'cuna', 'trona', 'sacaleches', 'toallitas bebe', 
                    'ropa bebe', 'mordedor', 'isofix', 'vigilabebes', 'recien nacido', 'infantil'],
    
    'comida_bebida': ['café', 'nespresso', 'dolce gusto', 'chocolate', 'vino', 'cerveza', 
                      'licor', 'ginebra', 'whisky', 'ron', 'aceite de oliva', 'supermercado', 
                      'dulce', 'snack', 'alimentación', 'jamón', 'embutido'],
    
    'viajes': ['maleta', 'mochila viaje', 'neceser', 'candado tsa', 'almohada viaje', 
               'adaptador enchufe', 'equipaje', 'organizadores maleta', 'bolsa de viaje', 
               'ryanair', 'vueling', 'bascula equipaje'],
    
    'ocio': ['libro', 'novela', 'pintura', 'manualidades', 'papelería', 'cuaderno', 
             'rotuladores', 'acuarelas', 'cómics', 'manga', 'vinilo', 'cd'],
    
    'gratis': ['gratis', 'muestra gratuita', '100% descuento', '0 euros', 'prueba gratis'],
    
    'varios': ['pilas', 'papel higienico', 'mascarillas', 'bolsas basura', 'cinta adhesiva', 
               'pegamento', 'baterias aa', 'baterias aaa', 'recambios']
}

def obtener_categoria(nombre_producto):
    """Analiza el nombre y asigna categoría correcta"""
    nombre_lower = nombre_producto.lower()
    for categoria, keywords in CATEGORIAS_MAP.items():
        for keyword in keywords:
            if keyword in nombre_lower:
                return categoria
    return 'varios' # Todo lo que no encaje, va a Varios

# ==================== FUNCIONES DE HISTORIAL ====================
def cargar_historial():
    """Carga los ASINs ya procesados"""
    if os.path.exists(ARCHIVO_HISTORIAL):
        with open(ARCHIVO_HISTORIAL, "r", encoding='utf-8') as f:
            return set(line.strip() for line in f)
    return set()

def guardar_en_historial(asin):
    """Guarda un ASIN en el historial"""
    with open(ARCHIVO_HISTORIAL, "a", encoding='utf-8') as f:
        f.write(f"{asin}\n")

productos_procesados = cargar_historial()
logger.info(f"📦 Historial cargado: {len(productos_procesados)} productos")

# ==================== FUNCIONES DE IMAGEN ====================
def cargar_fuente(tamanio, negrita=False):
    """Intenta cargar fuentes del sistema robustas"""
    fuentes_bold = ["arialbd.ttf", "DejaVuSans-Bold.ttf", "FreeSansBold.ttf", "LiberationSans-Bold.ttf"]
    fuentes_regular = ["arial.ttf", "DejaVuSans.ttf", "FreeSans.ttf", "LiberationSans.ttf"]
    
    lista = fuentes_bold if negrita else fuentes_regular
    
    for fuente in lista:
        try:
            return ImageFont.truetype(fuente, tamanio)
        except IOError:
            continue
    
    return ImageFont.load_default()

def crear_imagen(imagen_url, antes, ahora):
    """Crea la imagen con logo, precios y diseño profesional"""
    try:
        directorio_actual = os.path.dirname(os.path.abspath(__file__))
        ruta_logo = os.path.join(directorio_actual, "logo.png")
        
        img_data = requests.get(imagen_url, timeout=10).content
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as f:
            f.write(img_data)
            img_path = f.name
        
        producto_img = Image.open(img_path).convert("RGBA")
        canvas_size = 1080
        new_img = Image.new('RGB', (canvas_size, canvas_size), 'white')
        
        banner_h = 160
        linea_naranja_h = 15
        banner_y = canvas_size - banner_h
        linea_y = banner_y - linea_naranja_h
        espacio_img = linea_y
        
        w_ratio = canvas_size / float(producto_img.size[0])
        h_ratio = espacio_img / float(producto_img.size[1])
        ratio = min(w_ratio, h_ratio) * 0.85
        
        new_w = int(float(producto_img.size[0]) * ratio)
        new_h = int(float(producto_img.size[1]) * ratio)
        producto_img = producto_img.resize((new_w, new_h), Image.Resampling.LANCZOS)
        
        bg = Image.new("RGB", producto_img.size, (255, 255, 255))
        if len(producto_img.split()) == 4:
            bg.paste(producto_img, mask=producto_img.split()[3])
        else:
            bg.paste(producto_img)
        
        new_img.paste(bg, ((canvas_size - new_w) // 2, (espacio_img - new_h) // 2))
        
        draw = ImageDraw.Draw(new_img)
        draw.rectangle([(0, linea_y), (canvas_size, banner_y)], fill="#ff9900")
        draw.rectangle([(0, banner_y), (canvas_size, canvas_size)], fill="#222222")
        
        if os.path.exists(ruta_logo):
            logo_externo = Image.open(ruta_logo).convert("RGBA")
            alto_deseado_logo = int(banner_h * 2)
            ancho_original, alto_original = logo_externo.size
            ratio_logo = alto_deseado_logo / alto_original
            nuevo_ancho_logo = int(ancho_original * ratio_logo)
            logo_externo = logo_externo.resize((nuevo_ancho_logo, alto_deseado_logo), Image.Resampling.LANCZOS)
            pos_x_logo = 10
            pos_y_logo = banner_y + (banner_h - alto_deseado_logo) // 3
            new_img.paste(logo_externo, (pos_x_logo, pos_y_logo), mask=logo_externo)
        
        font_ahora = cargar_fuente(110, negrita=True)
        font_antes = cargar_fuente(65, negrita=False)
        
        ahora_texto = f"{ahora}"
        try:
            bbox_ahora = draw.textbbox((0, 0), ahora_texto, font=font_ahora)
            ancho_ahora = bbox_ahora[2] - bbox_ahora[0]
        except:
            ancho_ahora = 300
        
        pos_ahora_x = (canvas_size - ancho_ahora) // 2
        pos_ahora_y = banner_y + 20
        draw.text((pos_ahora_x, pos_ahora_y), ahora_texto, fill="white", font=font_ahora)
        
        antes_texto = f"{antes}"
        try:
            bbox_antes = draw.textbbox((0, 0), antes_texto, font=font_antes)
            ancho_antes = bbox_antes[2] - bbox_antes[0]
            alto_antes = bbox_antes[3] - bbox_antes[1]
        except:
            ancho_antes = 150
            alto_antes = 30
        
        pos_antes_x = canvas_size - ancho_antes - 40
        pos_antes_y = banner_y + 55
        draw.text((pos_antes_x, pos_antes_y), antes_texto, fill="#cccccc", font=font_antes)
        
        try:
            y_tachado = pos_antes_y + (alto_antes // 2) + 5
            draw.line([(pos_antes_x - 5, y_tachado), (pos_antes_x + ancho_antes + 5, y_tachado)], fill="#e71a1a", width=6)
        except:
            pass
        
        out_path = tempfile.mktemp(suffix='.jpg')
        new_img.save(out_path, quality=95)
        return out_path
        
    except Exception as e:
        logger.error(f"❌ Error creando imagen: {e}")
        return None

# ==================== FUNCIONES DE ENVÍO ====================
def enviar_producto(nombre, precio, precio_antes, descuento, imagen_url, url, keyword, categoria):
    """Envía el producto a Telegram con el diseño limpio"""
    img_file = crear_imagen(imagen_url, precio_antes, precio)
    if not img_file:
        return False
    
    mensaje = (f"🔥 <b>{nombre}</b> | #{keyword.replace(' ', '')} #Amazon\n\n"
               f"📉 <b>DESCUENTO:</b> {descuento}%\n"
               f"🔥 <b>Precio:</b> {precio}\n"
               f"❌ <b>Antes:</b> {precio_antes}\n\n"
               f"👉 <a href='{url}'>Ver oferta aquí</a>")
    
    try:
        with open(img_file, 'rb') as photo:
            bot.send_photo(CHAT_ID, photo, caption=mensaje, parse_mode='HTML')
        logger.info(f"✅ Enviado a Telegram: {nombre[:50]}...")
        return True
    except Exception as e:
        logger.error(f"❌ Error Telegram: {e}")
        return False
    finally:
        if os.path.exists(img_file):
            os.unlink(img_file)

# ✅ FUNCIÓN ACTUALIZADA: Envía producto a la web CON DESCRIPCIÓN
def enviar_a_web(nombre, precio, precio_antes, link, imagen, categoria, descripcion="", activo=True):
    """Envía el producto a la API web con descripción"""
    try:
        response = requests.post(f"{API_BASE}/api/ofertas", json={
            "nombre": nombre,
            "precio": precio,
            "precio_antes": precio_antes,
            "link": link,
            "imagen": imagen,
            "categoria": categoria,
            "descripcion": descripcion,  # ✅ NUEVO CAMPO
            "activo": activo
        }, headers={"X-API-KEY": API_SECRET_KEY}, 
                         timeout=10)
        
        if response.status_code == 200:
            logger.info(f"✅ Producto enviado a web: {nombre[:50]}... - Categoría: {categoria}")
            return True
        else:
            logger.error(f"❌ Error web ({response.status_code}): {response.text}")
            return False
    except Exception as e:
        logger.error(f"❌ Error enviando a web: {e}")
        return False

# ✅ NUEVA FUNCIÓN: Extraer descripción del producto desde Amazon
def extraer_descripcion(item):
    """Extrae una descripción del producto desde la API de Amazon"""
    try:
        descripcion_parts = []
        
        # 1. Intentar obtener características (features)
        if hasattr(item, 'item_info') and item.item_info:
            if hasattr(item.item_info, 'features') and item.item_info.features:
                features = item.item_info.features.display_values
                if features:
                    for feature in features[:5]:  # Máximo 5 características
                        descripcion_parts.append(f"• {feature}")
        
        # 2. Si no hay features, usar información del producto
        if not descripcion_parts:
            if hasattr(item.item_info, 'by_line_info') and item.item_info.by_line_info:
                if hasattr(item.item_info.by_line_info, 'brand') and item.item_info.by_line_info.brand:
                    marca = item.item_info.by_line_info.brand.display_value
                    descripcion_parts.append(f"Marca: {marca}")
            
            if hasattr(item.item_info, 'product_info') and item.item_info.product_info:
                if hasattr(item.item_info.product_info, 'color') and item.item_info.product_info.color:
                    color = item.item_info.product_info.color.display_value
                    descripcion_parts.append(f"Color: {color}")
        
        # 3. Si todavía no hay descripción, crear una básica
        if not descripcion_parts:
            titulo = item.item_info.title.display_value if hasattr(item.item_info, 'title') else "Producto"
            descripcion_parts.append(f"Producto destacado: {titulo[:100]}...")
            descripcion_parts.append("• Consulta todos los detalles en la página oficial de Amazon")
        
        # 4. Unir todas las partes con saltos de línea
        descripcion = "\n".join(descripcion_parts)
        
        logger.info(f"✅ Descripción extraída: {len(descripcion)} caracteres")
        return descripcion
        
    except Exception as e:
        logger.error(f"❌ Error extrayendo descripción: {e}")
        return "• Producto disponible en Amazon\n• Consulta todos los detalles y características en la página oficial\n• Envío rápido y seguro"

# ✅ FUNCIÓN PARA MARCAR PRODUCTO INACTIVO
def marcar_producto_inactivo(producto_id):
    """Marca un producto como inactivo en la web"""
    try:
        response = requests.patch(f"{API_BASE}/api/ofertas/{producto_id}/activo",
                                  json={"activo": False}, headers={"X-API-KEY": API_SECRET_KEY}, 
                          timeout=10)
        if response.status_code == 200:
            logger.info(f"⚠️ Producto {producto_id} marcado como INACTIVO")
            return True
        else:
            logger.warning(f"⚠️ No se pudo desactivar producto {producto_id}")
            return False
    except Exception as e:
        logger.error(f"❌ Error marcando inactivo: {e}")
        return False

# ==================== VERIFICACIÓN DE PRODUCTOS ====================
def extraer_asin(link):
    """Extrae el ASIN limpio de un link de Amazon"""
    if not link or '/dp/' not in link:
        return None
    # Extraer parte después de /dp/
    asin_parte = link.split('/dp/')[-1]
    # Eliminar parámetros (?tag=...) y slash adicional
    asin = asin_parte.split('/')[0].split('?')[0]
    # Validar ASIN (10 caracteres alfanuméricos)
    if len(asin) == 10 and asin.isalnum():
        return asin.upper()
    return None

def verificar_producto_amazon(asin, amazon_api=None):
    """Verifica si un producto sigue teniendo descuento en Amazon"""
    # Usar API global si no se pasa una específica
    api = amazon_api or amazon
    
    if not api or not asin:
        logger.warning(f"⚠️ ASIN inválido: {asin}")
        return {'encontrado': False, 'descuento': 0}
    
    try:
        # Buscar producto por ASIN
        productos = api.search_items(keywords=asin, item_count=1)
        
        if not productos or not productos.items:
            logger.warning(f"⚠️ ASIN {asin} no encontrado en Amazon")
            return {'encontrado': False, 'descuento': 0}
        
        item = productos.items[0]
        
        # ✅ Manejo seguro de ofertas (offers_v2 o offers)
        ofertas = getattr(item, 'offers_v2', None) or getattr(item, 'offers', None)
        
        if not ofertas or not getattr(ofertas, 'listings', None):
            logger.info(f"ℹ️ {asin}: Sin ofertas disponibles")
            return {'encontrado': False, 'descuento': 0}
        
        price_obj = ofertas.listings[0].price
        
        # ✅ VERIFICAR QUE MONEY EXISTA
        if not hasattr(price_obj, 'money') or not price_obj.money:
            logger.warning(f"⚠️ {asin}: Sin información de precio")
            return {'encontrado': False, 'descuento': 0}
        
        # ✅ VERIFICAR QUE SAVINGS EXISTA Y NO SEA NONE
        savings = getattr(price_obj, 'savings', None)
        
        if not savings:
            logger.info(f"ℹ️ {asin}: Sin descuento disponible (precio normal)")
            return {'encontrado': True, 'descuento': 0}  # Producto existe pero sin descuento
        
        # ✅ VERIFICAR QUE PERCENTAGE EXISTA
        porcentaje = getattr(savings, 'percentage', 0)
        
        logger.info(f"✅ {asin}: Descuento actual = {porcentaje}%")
        
        return {'encontrado': True, 'descuento': porcentaje}
        
    except AttributeError as e:
        logger.error(f"❌ Error de atributo en {asin}: {e}")
        return {'encontrado': False, 'descuento': 0}
    except Exception as e:
        logger.error(f"❌ Error verificando {asin}: {e}")
        return {'encontrado': False, 'descuento': 0}

def obtener_productos_activos():
    """Obtiene todos los productos activos usando paginación para no colapsar el servidor (Evita Error 502)"""
    productos_totales = []
    pagina = 1
    limite = 100  # Descargamos de 100 en 100
    
    logger.info("⏳ Conectando con la base de datos...")
    
    while True:
        try:
            # Pedimos una página específica
            url = f"{API_BASE}/api/ofertas?activos=true&page={pagina}&limit={limite}"
            response = requests.get(url, timeout=30)
            
            if response.status_code == 200:
                datos = response.json()
                ofertas = datos.get("ofertas", [])
                
                # Si la lista viene vacía, significa que ya hemos llegado al final
                if not ofertas:
                    break 
                    
                productos_totales.extend(ofertas)
                logger.info(f"   ↳ Descargados {len(productos_totales)} productos hasta ahora (Página {pagina})...")
                
                pagina += 1
                time.sleep(0.5) # Pequeña pausa para que Render respire entre páginas
                
            else:
                logger.error(f"❌ Error HTTP {response.status_code} en página {pagina}")
                break
                
        except Exception as e:
            logger.error(f"❌ Error de red descargando productos: {e}")
            break
            
    return productos_totales


def verificar_productos_antiguos():
    """Verifica TODOS los productos activos de la base de datos sin importar la fecha"""
    logger.info("🔄 Iniciando verificación de TODOS los productos activos...")
    productos = obtener_productos_activos()
    logger.info(f"📦 Productos descargados de la web para revisar: {len(productos)}")
    
    if not productos:
        logger.info("✅ No hay productos que verificar")
        return {'verificados': 0, 'desactivados': 0}
    
    verificados = 0
    desactivados = 0
    
    for producto in productos:
        try:
            producto_id = producto.get('id')
            nombre = producto.get('nombre', 'Desconocido')[:40]
            link = producto.get('link', '')
            
            logger.info(f"🔍 Verificando producto {producto_id}: {nombre}...")
            
            asin = extraer_asin(link)
            if not asin:
                continue
            
            resultado = verificar_producto_amazon(asin)
            
            if not resultado['encontrado']:
                logger.warning(f"❌ Producto {producto_id} no encontrado en Amazon → DESACTIVANDO")
                if marcar_producto_inactivo(producto_id):
                    desactivados += 1
            elif resultado['descuento'] < DESCUENTO_PARA_DESACTIVAR:
                logger.warning(f"⚠️ Producto {producto_id} descuento bajo ({resultado['descuento']}%) → DESACTIVANDO")
                if marcar_producto_inactivo(producto_id):
                    desactivados += 1
            else:
                logger.info(f"✅ Producto {producto_id} sigue activo ({resultado['descuento']}%)")
                verificados += 1
            
            time.sleep(1)
            
        except Exception as e:
            logger.error(f"❌ Error verificando producto {producto.get('id')}: {e}")
            continue
    
    logger.info(f"✅ Verificación completada: {verificados} verificados, {desactivados} desactivados")
    return {'verificados': verificados, 'desactivados': desactivados}


# ==================== BÚSQUEDA PRINCIPAL ====================
def buscar_ofertas():
    """Busca ofertas nuevas en Amazon"""
    total = 0
    exitosos = 0
    fallidos = 0
    
    logger.info("🚀 INICIANDO BÚSQUEDA DE OFERTAS...")
    logger.info(f"📝 Keywords a procesar: {len(KEYWORDS)}")
    
    for i, keyword in enumerate(KEYWORDS, 1):
        logger.info(f"🔍 [{i}/{len(KEYWORDS)}] Buscando: {keyword}")
        time.sleep(2)
        
        try:
            productos = amazon.search_items(keywords=keyword, item_count=PRODUCTOS_POR_KEYWORD)
            
            if not productos or not productos.items:
                logger.warning(f"⚠️ Sin resultados para: {keyword}")
                continue
            
            for item in productos.items:
                total += 1
                
                if item.asin in productos_procesados:
                    logger.debug(f"⏭️ Saltando ASIN ya procesado: {item.asin}")
                    continue
                
                try:
                    ofertas = item.offers_v2.listings if hasattr(item, 'offers_v2') and item.offers_v2 else item.offers.listings
                    
                    if not ofertas:
                        continue
                    
                    price_obj = ofertas[0].price
                    
                    # ✅ VERIFICAR QUE MONEY EXISTA
                    if not hasattr(price_obj, 'money') or not price_obj.money:
                        logger.warning(f"⚠️ {item.asin}: Sin información de precio")
                        continue
                    
                    precio_actual = price_obj.money.display_amount
                    
                    # ✅ VERIFICAR QUE SAVINGS EXISTA Y NO SEA NONE
                    savings = getattr(price_obj, 'savings', None)
                    
                    if not savings:
                        logger.info(f"ℹ️ {item.asin}: Sin descuento (precio normal) - SALTANDO")
                        continue  # ✅ Saltar productos sin descuento
                    
                    # ✅ VERIFICAR QUE PERCENTAGE EXISTA
                    descuento = getattr(savings, 'percentage', 0)
                    
                    if descuento < DESCUENTO_MINIMO:
                        logger.debug(f"⏭️ Descuento insuficiente ({descuento}%): {item.item_info.title.display_value[:40]}...")
                        continue
                    
                    precio_antes = price_obj.saving_basis.money.display_amount if hasattr(price_obj, 'saving_basis') and price_obj.saving_basis else "N/A"
                    categoria_real = obtener_categoria(item.item_info.title.display_value)
                    
                    # ✅ EXTRAER DESCRIPCIÓN DEL PRODUCTO
                    descripcion_producto = extraer_descripcion(item)
                    
                    # Enviar a Telegram
                    if enviar_producto(
                        item.item_info.title.display_value, 
                        precio_actual, 
                        precio_antes, 
                        descuento, 
                        item.images.primary.large.url, 
                        item.detail_page_url, 
                        keyword,
                        categoria_real
                    ):
                        # ✅ Enviar a Web CON DESCRIPCIÓN
                        if enviar_a_web(
                            nombre=item.item_info.title.display_value,
                            precio=precio_actual,
                            precio_antes=precio_antes,
                            link=item.detail_page_url,
                            imagen=item.images.primary.large.url,
                            categoria=categoria_real,
                            descripcion=descripcion_producto,  # ✅ AÑADIR DESCRIPCIÓN
                            activo=True
                        ):
                            exitosos += 1
                            productos_procesados.add(item.asin)
                            guardar_en_historial(item.asin)
                            logger.info(f"✅ Producto guardado: {item.item_info.title.display_value[:40]}...")
                        else:
                            fallidos += 1
                    else:
                        fallidos += 1
                    
                    time.sleep(PAUSA_ENTRE_PRODUCTOS)
                    
                except AttributeError as e:
                    logger.warning(f"⚠️ Error de atributo en {item.asin}: {e}")
                    fallidos += 1
                    continue
                except Exception as e:
                    logger.error(f"❌ Error procesando item: {e}")
                    fallidos += 1
                    continue
                    
        except Exception as e:
            logger.error(f"❌ Error en keyword '{keyword}': {e}")
            continue
    
    logger.info("=" * 50)
    logger.info(f"✅ FIN DE BÚSQUEDA")
    logger.info(f"📊 Total procesados: {total}")
    logger.info(f"✅ Exitosos: {exitosos}")
    logger.info(f"❌ Fallidos: {fallidos}")
    logger.info(f"📦 Historial total: {len(productos_procesados)} productos")
    logger.info("=" * 50)
    
    return exitosos

# ==================== KEYWORDS (ACTUALIZADAS Y BALANCEADAS) ====================
KEYWORDS = [
    # 🎯 KEYWORDS DE CONVERSIÓN GENERAL
    "mejor calidad precio", "top ventas amazon", "ofertas flash", 
    "descuentos amazon hoy", "amazon finds", "chollos amazon", "liquidación",

    # 💻 TECNOLOGÍA (¡AMPLIADA!)
    "altavoz inteligente alexa", "enchufe inteligente wifi", "bombillas led inteligentes",
    "kindle paperwhite", "tablet barata estudiantes", "proyector portatil cine",
    "auriculares cancelacion ruido", "barra de sonido tv", "fire tv stick 4k",
    "microfono condensador podcast", "webcam 1080p stream", "disco duro externo 2tb",
    "ssd interno 1tb", "powerbank carga rapida", "cargador inalambrico iphone",
    "impresora 3d principiantes", "tocadiscos vinilo bluetooth", "repetidor wifi potente",
    "auriculares bluetooth inalambricos", "raton inalambrico ergonomico", "teclado mecanico gaming",
    "monitor pc 27 pulgadas", "cable usb c carga rapida", "funda iphone transparente",
    "cristal templado movil", "soporte movil coche", "camara vigilancia wifi",
    "tarjeta micro sd 128gb", "memoria usb 64gb", "hub usb c macbook", "tira led wifi",

    # 👗 MODA Y ACCESORIOS (¡AMPLIADA!)
    "reloj casio vintage", "reloj inteligente mujer", "gafas de sol polarizadas",
    "mochila portatil impermeable", "bolso bandolera mujer", "cartera rfid hombre",
    "cinturon cuero hombre", "joyeria plata ley mujer", "pulsera pandora",
    "zapatillas blancas casual", "botas invierno impermeables", "pijama algodon invierno",
    "pack calcetines deportivos", "ropa interior calvin klein", "chaqueta impermeable the north face",
    "sudadera basica capucha", "pantalones vaqueros levis", "ropa deportiva mujer gym",
    "zapatillas running hombre", "sandalias mujer verano", "botas chelsea mujer",
    "camisetas basicas algodon", "vestido casual mujer", "leggings push up",
    "abrigo lana invierno", "chaqueta vaquera mujer", "gorra beisbol", 
    "sombrero paja playa", "paraguas plegable resistente", "guantes tactiles invierno",
    "bufanda manta mujer", "bolso tote grande", "billetera mujer piel",

    # 🐾 MASCOTAS
    "cama perro antiestres", "rascador gato arbol", "comedero automatico gato",
    "fuente agua gatos", "pienso perro oferta", "arena gatos aglomerante",
    "arnes perro antitirones", "transportin perro homologado", "juguetes interactivos perro",
    "chucherias para perros", "cepillo quitapelos mascota", "collar antiparasitario perro",
    "acuario completo", "filtro pecera", "juguetes hierba gatera",
    
    # 🎲 JUGUETES
    "juegos de mesa familiares", "lego star wars", "juguetes montessori madera",
    "cocinita madera infantil", "coche radiocontrol bateria", "barbie oferta",
    "playmobil city action", "puzzle 1000 piezas", "nerf elite", 
    "juegos educativos 3 años", "juegos educativos 6 años", "disfraces infantiles",
    "pizarra magica infantil", "plastilina play doh", "cuentos infantiles",

    # 🏡 HOGAR Y JARDÍN
    "freidora sin aceite 5l", "robot aspirador fregasuelos", "cafetera superautomatica",
    "juego sartenes induccion", "cuchillos cocina profesional", "taper cristal hermetico",
    "purificador aire alergias", "humificador aceites esenciales", "lampara mesilla tactil",
    "funda nordica algodon", "almohada viscoelastica cervical", "colchon viscoelastico barato",
    "organizador armario tela", "zapatero recibidor", "silla oficina ergonomica",
    "herramientas bricolaje maletin", "taladro percutor bateria", "manguera jardin extensible",
    "luces solares exterior", "tendedero plegable", "aspiradora escoba sin cable",

    # 💄 BELLEZA Y CUIDADO PERSONAL
    "perfume mujer original", "colonia hombre oferta", "crema hidratante acido hialuronico",
    "serum retinol facial", "mascarilla pelo dañado", "champus sin sulfatos",
    "protector solar facial 50", "plancha pelo ceramica", "secador pelo profesional",
    "recortadora barba electrica", "maquina afeitar hombre", "depiladora luz pulsada",
    "kit uñas gel completo", "esmalte semipermanente colores", "limpiador facial ultrasonico",
    "rodillo jade masaje", "cepillo alisador pelo", "irrigador dental profesional",

    # 🏋️ DEPORTES Y AIRE LIBRE
    "pala padel carbono", "pelotas padel", "zapatillas padel",
    "smartwatch deportivo gps", "pulsera actividad xiaomi", "cinta de correr plegable",
    "bicicleta spinning casa", "juego mancuernas ajustables", "esterilla yoga antideslizante",
    "bandas de resistencia musculacion", "proteina whey isolate", "creatina monohidrato pura",
    "tienda de campaña 4 personas", "saco de dormir invierno", "linterna led recargable",
    "botella agua acero inoxidable", "patinete electrico adulto", "casco bicicleta",

    # 👶 BEBÉS Y NIÑOS
    "regalos recien nacido", "vigilabebes con camara", "silla paseo bebe",
    "pañales dodot", "toallitas bebe", "silla coche isofix", "carrito bebe",
    "sacaleches electrico", "parque infantil bebe", "trona bebe",

    # 🎮 VIDEOJUEGOS
    "juegos ps5", "nintendo switch oferta", "mando xbox", "auriculares gaming", 
    "playstation 5 consola", "silla gaming", "dualshock", "tarjeta ps plus",

    # 🍷 COMIDA Y BEBIDA
    "cafe en grano", "capsulas nespresso", "capsulas dolce gusto", "ginebra oferta",
    "whisky", "vino tinto", "aceite de oliva virgen extra", "jamon iberico", "chocolate",

    # ✈️ VIAJES
    "maleta cabina ryanair", "mochila viaje cabina", "almohada cervical viaje",
    "neceser viaje mujer", "organizadores maleta", "candado tsa", "bascula equipaje",

    # 🎲 OCIO
    "libros mas vendidos", "juegos de mesa adultos", "material manualidades", 
    "comics", "novela negra", "juego de cartas"
]

# Eliminar duplicados automáticamente
KEYWORDS = list(dict.fromkeys(KEYWORDS))

# ==================== MENÚ PRINCIPAL ====================
def mostrar_menu():
    """Muestra el menú de opciones"""
    print("\n" + "=" * 50)
    print("🤖 SPAIN LINKS - BOT AMAZON")
    print("=" * 50)
    print("1. 🔍 Buscar ofertas nuevas")
    print("2. 🔄 Verificar productos antiguos")
    print("3. 📊 Ver estadísticas")
    print("4. 🧹 Limpiar historial")
    print("5. ❌ Salir")
    print("=" * 50)

def ver_estadisticas():
    """Muestra estadísticas del bot"""
    print("\n📊 ESTADÍSTICAS")
    print(f"   Productos en historial: {len(productos_procesados)}")
    print(f"   Keywords configuradas: {len(KEYWORDS)}")
    print(f"   Descuento mínimo: {DESCUENTO_MINIMO}%")
    print(f"   Descuento para desactivar: {DESCUENTO_PARA_DESACTIVAR}%")

def limpiar_historial():
    """Limpia el archivo de historial"""
    confirmacion = input("\n⚠️ ¿Seguro que quieres limpiar el historial? (s/n): ")
    if confirmacion.lower() == 's':
        if os.path.exists(ARCHIVO_HISTORIAL):
            os.remove(ARCHIVO_HISTORIAL)
            productos_procesados.clear()
            logger.info("✅ Historial limpiado correctamente")
        else:
            logger.info("ℹ️ No hay historial que limpiar")
    else:
        logger.info("ℹ️ Operación cancelada")

# ==================== MAIN ====================
if __name__ == "__main__":
    print("\n" + "=" * 50)
    print("🤖 SPAIN LINKS - BOT AMAZON")
    print("=" * 50)
    print("✅ Bot iniciado correctamente")
    print(f"📦 Historial: {len(productos_procesados)} productos")
    print(f"🔍 Keywords: {len(KEYWORDS)}")
    print("=" * 50 + "\n")
    
    while True:
        mostrar_menu()
        opcion = input("\nSelecciona una opción (1-5): ").strip()
        
        if opcion == "1":
            buscar_ofertas()
        elif opcion == "2":
            verificar_productos_antiguos()
        elif opcion == "3":
            ver_estadisticas()
        elif opcion == "4":
            limpiar_historial()
        elif opcion == "5":
            print("\n👋 ¡Hasta pronto!")
            break
        else:
            print("\n❌ Opción no válida. Intenta de nuevo.")
        
        input("\nPresiona Enter para continuar...")
