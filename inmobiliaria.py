import streamlit as st
import cloudscraper
from bs4 import BeautifulSoup
import time
from urllib.parse import urljoin, quote
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json
import hashlib
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import folium
from streamlit_folium import folium_static
from io import BytesIO
import re
from dataclasses import dataclass, field
from typing import List, Dict, Optional
import warnings
import google.generativeai as genai

warnings.filterwarnings('ignore')

# ─────────────────────────────────────────────────────────
# CONFIGURACIÓN DE PÁGINA
# ─────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Mendoza Inmuebles Pro",
    page_icon="🍷",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
.main { background-color: #f8f9fa; }
.hero-section {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    padding: 60px 20px; text-align: center; color: white;
    border-radius: 20px; margin-bottom: 30px;
}
.card {
    background: white; border-radius: 15px;
    box-shadow: 0 8px 20px rgba(0,0,0,0.08);
    margin-bottom: 20px; overflow: hidden;
    transition: transform 0.3s ease, box-shadow 0.3s ease;
}
.card:hover { transform: translateY(-5px); box-shadow: 0 12px 25px rgba(0,0,0,0.12); }
.card-img { width: 100%; height: 200px; object-fit: cover; }
.price { color: #27ae60; font-size: 22px; font-weight: 800; padding: 10px 15px 0; }
.info { padding: 12px 15px; font-size: 13px; }
.badge { background: #f1f2f6; padding: 4px 10px; border-radius: 6px;
    font-size: 11px; margin-right: 4px; font-weight: 600; display: inline-block; }
.stats-card { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white; padding: 20px; border-radius: 12px; }
.rec-card { background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
    color: white; padding: 18px; border-radius: 12px; margin-bottom: 10px; }
.trend-card { background: linear-gradient(135deg, #a1c4fd 0%, #c2e9fb 100%);
    padding: 18px; border-radius: 12px; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────
# MODELO DE DATOS
# ─────────────────────────────────────────────────────────
@dataclass
class Propiedad:
    id: str
    portal: str
    titulo: str
    precio: str
    precio_numerico: float
    url: str
    imagen: str
    ubicacion: str
    dormitorios: int
    banos: int
    cochera: bool
    metros_cuadrados: Optional[float] = None
    antiguedad: Optional[int] = None
    fecha_scraping: Optional[datetime] = None
    lat: Optional[float] = None
    lon: Optional[float] = None
    descripcion: Optional[str] = None
    expensas: Optional[float] = None
    moneda: str = "ARS"
    tipo_operacion: str = "Venta"
    tipo_propiedad: str = "Departamento"
    
    def to_dict(self):
        return {
            "ID": self.id,
            "Portal": self.portal,
            "Título": self.titulo,
            "Precio": self.precio,
            "Precio_Numérico": self.precio_numerico,
            "URL": self.url,
            "Imagen": self.imagen,
            "Ubicación": self.ubicacion,
            "Dormitorios": self.dormitorios,
            "Baños": self.banos,
            "Cochera": self.cochera,
            "M²": self.metros_cuadrados,
            "Antigüedad": self.antiguedad,
            "Fecha": self.fecha_scraping.strftime("%Y-%m-%d %H:%M") if self.fecha_scraping else None,
            "Latitud": self.lat,
            "Longitud": self.lon,
            "Descripción": self.descripcion,
            "Expensas": self.expensas,
            "Moneda": self.moneda,
            "Tipo_Operación": self.tipo_operacion,
            "Tipo_Propiedad": self.tipo_propiedad,
        }

# ─────────────────────────────────────────────────────────
# ZONAS DE MENDOZA
# ─────────────────────────────────────────────────────────
ZONAS_MENDOZA = {
    "Capital":           {"id_inmoclick": "20",  "slug": "mendoza",          "lat": -32.8895, "lon": -68.8458},
    "Godoy Cruz":        {"id_inmoclick": "24",  "slug": "godoy-cruz",       "lat": -32.9333, "lon": -68.8500},
    "Guaymallén":        {"id_inmoclick": "23",  "slug": "guaymallen",       "lat": -32.9000, "lon": -68.7667},
    "Las Heras":         {"id_inmoclick": "22",  "slug": "las-heras",        "lat": -32.8500, "lon": -68.8333},
    "Luján de Cuyo":     {"id_inmoclick": "25",  "slug": "lujan-de-cuyo",    "lat": -33.0333, "lon": -68.8833},
    "Maipú":             {"id_inmoclick": "21",  "slug": "maipu",            "lat": -32.9833, "lon": -68.7833},
    "Chacras de Coria":  {"id_inmoclick": "322", "slug": "chacras-de-coria", "lat": -33.0167, "lon": -68.9000},
    "Villa Nueva":       {"id_inmoclick": "26",  "slug": "villa-nueva",      "lat": -32.9167, "lon": -68.8000},
    "Rivadavia":         {"id_inmoclick": "27",  "slug": "rivadavia",        "lat": -33.1833, "lon": -68.4667},
    "San Martín":        {"id_inmoclick": "28",  "slug": "san-martin",       "lat": -33.0833, "lon": -68.4667},
    "Junín":             {"id_inmoclick": "29",  "slug": "junin",            "lat": -33.1333, "lon": -68.5833},
    "Santa Rosa":        {"id_inmoclick": "35",  "slug": "santa-rosa",       "lat": -33.1667, "lon": -68.1667},
    "La Paz":            {"id_inmoclick": "36",  "slug": "la-paz",           "lat": -33.4667, "lon": -67.5500},
    "Lavalle":           {"id_inmoclick": "33",  "slug": "lavalle",          "lat": -32.7167, "lon": -68.0167},
    "Tunuyán":           {"id_inmoclick": "30",  "slug": "tunuyan",          "lat": -33.5667, "lon": -69.0167},
    "Tupungato":         {"id_inmoclick": "31",  "slug": "tupungato",        "lat": -33.3667, "lon": -69.1333},
    "San Carlos":        {"id_inmoclick": "32",  "slug": "san-carlos",       "lat": -33.7667, "lon": -69.0500},
    "San Rafael":        {"id_inmoclick": "34",  "slug": "san-rafael",       "lat": -34.6167, "lon": -68.3333},
    "General Alvear":    {"id_inmoclick": "37",  "slug": "general-alvear",   "lat": -34.9833, "lon": -67.7000},
    "Malargüe":          {"id_inmoclick": "38",  "slug": "malargue",         "lat": -35.4667, "lon": -69.5833},
}

REGIONES_MENDOZA = {
    "🏙️ Gran Mendoza": ["Capital", "Godoy Cruz", "Guaymallén", "Las Heras", "Luján de Cuyo", "Maipú", "Chacras de Coria", "Villa Nueva"],
    "🌾 Este Mendocino": ["Rivadavia", "San Martín", "Junín", "Santa Rosa", "La Paz"],
    "🏔️ Norte": ["Lavalle"],
    "🍇 Valle de Uco": ["Tunuyán", "Tupungato", "San Carlos"],
    "🌵 Sur Mendocino": ["San Rafael", "General Alvear", "Malargüe"],
}

# ─────────────────────────────────────────────────────────
# FUNCIONES DE UTILIDAD
# ─────────────────────────────────────────────────────────
def extraer_precio_numerico(precio_str: str) -> float:
    if not precio_str:
        return 0.0
    texto = precio_str.lower().strip()
    if any(p in texto for p in ["consultar", "a convenir", "precio a", "sin precio"]):
        return 0.0
    es_usd = any(s in texto for s in ["usd", "u$s", "us$", "dólar", "dollar"])
    texto_limpio = re.sub(r"[^\d.,]", " ", texto).strip()
    numeros = re.findall(r"[\d.,]+", texto_limpio)
    if not numeros:
        return 0.0
    num_str = numeros[0]
    try:
        if "." in num_str and "," in num_str:
            if num_str.index(".") < num_str.index(","):
                num_str = num_str.replace(".", "").replace(",", ".")
            else:
                num_str = num_str.replace(",", "")
        elif "." in num_str:
            partes = num_str.split(".")
            if all(len(p) == 3 for p in partes[1:]):
                num_str = num_str.replace(".", "")
        elif "," in num_str:
            num_str = num_str.replace(",", ".")
        valor = float(num_str)
        if es_usd:
            valor *= 1150
        return valor
    except (ValueError, IndexError):
        return 0.0

def generar_id(portal: str, titulo: str, precio: str) -> str:
    return hashlib.md5(f"{portal}{titulo}{precio}".encode()).hexdigest()[:16]

def extraer_metros_cuadrados(texto: str) -> Optional[float]:
    if not texto:
        return None
    m = re.search(r"(\d+(?:[.,]\d+)?)\s*(?:m²|m2|mts²|mts2|metros?)", texto, re.IGNORECASE)
    if m:
        try:
            return float(m.group(1).replace(",", "."))
        except ValueError:
            pass
    return None

def extraer_expensas(texto: str) -> Optional[float]:
    if not texto:
        return None
    m = re.search(r"expensas?\s*[:\$]?\s*(\d[\d.,]*)", texto, re.IGNORECASE)
    if m:
        try:
            return float(re.sub(r"[^\d.]", "", m.group(1).replace(",", ".")))
        except ValueError:
            pass
    return None

def imagen_valida(url: str) -> bool:
    if not url:
        return False
    invalidos = ["base64", "placeholder", "noimage", "nophoto", "blank", "undefined"]
    return not any(inv in url.lower() for inv in invalidos)

PLACEHOLDER_IMG = "https://via.placeholder.com/400x250/cccccc/666666?text=Sin+imagen"

# ─────────────────────────────────────────────────────────
# CONSTRUCCIÓN DE URLs
# ─────────────────────────────────────────────────────────
def construir_url(portal: str, filtros: dict) -> str:
    op = "alquiler" if filtros["op"] == "Alquiler" else "venta"
    tipo = filtros["tipo"].lower().replace(" ", "-")
    zona = ZONAS_MENDOZA[filtros["loc"]]
    
    if portal == "Inmoup":
        url = f"https://www.inmoup.com.ar/{tipo}s-en-{op}?grupo={tipo}s&condicion={op}&q={quote(filtros['loc'])}&moneda=1&favoritos=0&limit=24"
        if filtros["p_max"] > 0:
            url += f"&precio%5Bmax%5D={filtros['p_max']}"
        if filtros["exp_max"] > 0:
            url += f"&expensas%5Bmax%5D={filtros['exp_max']}"
        return url
    elif portal == "Inmoclick":
        url = f"https://www.inmoclick.com.ar/inmuebles/{op}/{tipo}s?localidades={zona['id_inmoclick']}&moneda=1"
        if filtros["p_max"] > 0:
            url += f"&precio%5Bmax%5D={filtros['p_max']}"
        if filtros["amb"] > 0:
            url += f"&dormitorios={filtros['amb']}"
        return url
    elif portal == "Argenprop":
        slug_tipo = tipo.replace("-", "")
        url = f"https://www.argenprop.com/{slug_tipo}-{op}-localidad-{zona['slug']}-mendoza"
        if filtros["amb"] > 0:
            url += f"-{filtros['amb']}-dormitorios"
        if filtros.get("apto"):
            url += "-apto-credito"
        return url
    elif portal == "Zonaprop":
        slug_loc = zona["slug"]
        url = f"https://www.zonaprop.com.ar/inmuebles-{op}-mendoza"
        if slug_loc != "mendoza":
            url += f"-{slug_loc}"
        url += ".html"
        return url
    return ""

# ─────────────────────────────────────────────────────────
# SCRAPING
# ─────────────────────────────────────────────────────────
@st.cache_data(ttl=1800, show_spinner=False)
def scrapear_portal(portal: str, url: str, filtros_json: str, max_items: int = 20) -> list:
    filtros = json.loads(filtros_json)
    scraper = cloudscraper.create_scraper(
        browser={"browser": "chrome", "platform": "windows", "mobile": False}
    )
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "es-AR,es;q=0.9",
        "Connection": "keep-alive",
    }
    try:
        res = scraper.get(url, headers=headers, timeout=25)
        res.raise_for_status()
    except Exception:
        return []
    
    soup = BeautifulSoup(res.text, "html.parser")
    SELECTORES = {
        "Inmoclick": ["article.property-item", "div.property-item", "li.property-item"],
        "Inmoup":    ["article.property-item", ".item-property", ".prop-item", "article", ".item"],
        "Zonaprop":  ['div[data-qa="posting PROPERTY"]', 'div[data-qa="posting-card"]', ".postingCard", ".posting-card-container", 'div[data-qa*="posting"]'],
        "Argenprop": [".listing__item", ".list__item", ".card", "article"],
    }
    
    items = []
    for selector in SELECTORES.get(portal, ["article"]):
        items = soup.select(selector)
        if items:
            break
    if not items:
        return []
    
    propiedades_dict = []
    for item in items[:max_items]:
        try:
            texto_completo = item.get_text(" ", strip=True)
            price_sel = ['[data-qa="POSTING_CARD_PRICE"]', ".posting-card__price", ".price-value", ".card__price", ".item-price", ".price", ".listing__price", "span.price"]
            precio_texto = "Consultar"
            for sel in price_sel:
                el = item.select_one(sel)
                if el and el.text.strip():
                    precio_texto = el.text.strip()
                    break
            if precio_texto == "Consultar":
                m = re.search(r"\$\s*[\d.,]+", texto_completo)
                if m:
                    precio_texto = m.group(0).strip()
            
            titulo_sel = ['[data-qa="POSTING_CARD_ADDRESS"]', ".posting-card__title", ".card__address", ".card__title--address", ".listing__title", ".property-title", "h2", "h3", ".title"]
            titulo = ""
            for sel in titulo_sel:
                el = item.select_one(sel)
                if el and el.text.strip():
                    titulo = el.text.strip()[:100]
                    break
            if not titulo:
                img_tag = item.find("img")
                if img_tag:
                    alt = img_tag.get("alt", "")
                    titulo = alt.split("·")[0].strip()[:100] if alt else ""
            if not titulo:
                titulo = f"Propiedad {portal}"
            
            img_url = PLACEHOLDER_IMG
            img_tag = item.find("img")
            if img_tag:
                for attr in ["data-src", "src", "data-lazy", "data-original", "data-image"]:
                    candidate = img_tag.get(attr, "")
                    if candidate and imagen_valida(candidate):
                        img_url = candidate.split("?")[0]
                        break
            
            link_tag = item.find("a", href=True)
            aviso_url = urljoin(url, link_tag["href"]) if link_tag else url
            
            metros = extraer_metros_cuadrados(texto_completo)
            expensas = extraer_expensas(texto_completo)
            precio_num = extraer_precio_numerico(precio_texto)
            
            prop_dict = {
                "id": generar_id(portal, titulo, precio_texto),
                "portal": portal,
                "titulo": titulo,
                "precio": precio_texto,
                "precio_numerico": precio_num,
                "url": aviso_url,
                "imagen": img_url,
                "ubicacion": filtros["loc"],
                "dormitorios": filtros["amb"],
                "banos": filtros["banos"],
                "cochera": filtros["cochera"],
                "metros_cuadrados": metros,
                "antiguedad": None,
                "fecha_scraping": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "lat": None,
                "lon": None,
                "descripcion": None,
                "expensas": expensas,
                "moneda": "USD" if any(s in precio_texto.lower() for s in ["usd", "u$s"]) else "ARS",
                "tipo_operacion": filtros["op"],
                "tipo_propiedad": filtros["tipo"],
            }
            propiedades_dict.append(prop_dict)
        except Exception:
            continue
    return propiedades_dict

def dicts_to_propiedades(dicts: list) -> List[Propiedad]:
    result = []
    for d in dicts:
        p = Propiedad(
            id=d["id"], portal=d["portal"], titulo=d["titulo"],
            precio=d["precio"], precio_numerico=d["precio_numerico"],
            url=d["url"], imagen=d["imagen"], ubicacion=d["ubicacion"],
            dormitorios=d["dormitorios"], banos=d["banos"], cochera=d["cochera"],
            metros_cuadrados=d.get("metros_cuadrados"),
            fecha_scraping=datetime.strptime(d["fecha_scraping"], "%Y-%m-%d %H:%M") if d.get("fecha_scraping") else None,
            expensas=d.get("expensas"),
            moneda=d.get("moneda", "ARS"),
            tipo_operacion=d.get("tipo_operacion", "Venta"),
            tipo_propiedad=d.get("tipo_propiedad", "Departamento"),
        )
        result.append(p)
    return result

# ─────────────────────────────────────────────────────────
# ANALIZADOR
# ─────────────────────────────────────────────────────────
class AnalizadorInmobiliario:
    def __init__(self, propiedades: List[Propiedad]):
        self.propiedades = propiedades
        self.df = pd.DataFrame([p.to_dict() for p in propiedades])
    
    def estadisticas_basicas(self) -> dict:
        precios = self.df["Precio_Numérico"].replace(0, np.nan).dropna()
        if precios.empty:
            return {}
        return {
            "total": len(self.df),
            "con_precio": len(precios),
            "promedio": precios.mean(),
            "mediana": precios.median(),
            "minimo": precios.min(),
            "maximo": precios.max(),
            "desviacion": precios.std(),
            "q1": precios.quantile(0.25),
            "q3": precios.quantile(0.75),
        }
    
    def detectar_outliers(self) -> dict:
        precios = self.df["Precio_Numérico"].replace(0, np.nan).dropna()
        if precios.empty:
            return {"cantidad": 0, "porcentaje": 0, "inferior": 0, "superior": 0}
        q1, q3 = precios.quantile(0.25), precios.quantile(0.75)
        iqr = q3 - q1
        lo, hi = q1 - 1.5 * iqr, q3 + 1.5 * iqr
        out = precios[(precios < lo) | (precios > hi)]
        return {
            "cantidad": len(out),
            "porcentaje": round(len(out) / len(precios) * 100, 1),
            "inferior": lo,
            "superior": hi,
        }
    
    def recomendaciones(self) -> list:
        recs = []
        stats = self.estadisticas_basicas()
        if not stats:
            return recs
        outliers = self.detectar_outliers()
        recs.append({
            "nivel": "info",
            "texto": f"💰 Precio mediano del mercado: **${stats['mediana']:,.0f}**. Propiedades en este rango suelen tener mayor rotación.",
        })
        if outliers["porcentaje"] > 5:
            recs.append({
                "nivel": "warning",
                "texto": f"⚠️ Hay **{outliers['cantidad']} propiedades** ({outliers['porcentaje']}%) con precios fuera del rango normal (${outliers['inferior']:,.0f} – ${outliers['superior']:,.0f}). Revisalas para detectar oportunidades o precios erróneos.",
            })
        if stats["desviacion"] / stats["promedio"] > 0.3:
            cv = round(stats["desviacion"] / stats["promedio"] * 100, 1)
            recs.append({
                "nivel": "info",
                "texto": f"📊 Alta variabilidad de precios (CV: {cv}%). El mercado ofrece opciones muy diversas en este segmento.",
            })
        return recs
    
    def precio_por_m2(self):
        df_v = self.df[(self.df["M²"].notna()) & (self.df["M²"] > 0) & (self.df["Precio_Numérico"] > 0)].copy()
        if df_v.empty:
            return None
        df_v["p_m2"] = df_v["Precio_Numérico"] / df_v["M²"]
        return {
            "promedio": df_v["p_m2"].mean(),
            "mediana": df_v["p_m2"].median(),
            "min": df_v["p_m2"].min(),
            "max": df_v["p_m2"].max(),
            "correlacion": df_v[["Precio_Numérico", "M²"]].corr().iloc[0, 1],
        }

# ─────────────────────────────────────────────────────────
# FUNCIONES GEMINI AI
# ─────────────────────────────────────────────────────────
def procesar_busqueda_gemini(api_key: str, urls: str, prompt: str) -> str:
    """Procesa la búsqueda utilizando la API de Gemini"""
    if not api_key:
        raise ValueError("API Key no proporcionada")
    
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-2.5-flash')
        
        full_prompt = f"""
        Actúa como un experto asesor inmobiliario con años de experiencia en Mendoza, Argentina.
        
        CONTEXTO:
        El usuario está buscando propiedades y ha proporcionado las siguientes fuentes (URLs de portales):
        {urls}
        
        SOLICITUD DEL USUARIO:
        {prompt}
        
        INSTRUCCIONES:
        1. Analiza los requisitos de búsqueda.
        2. Recomienda qué tipo de propiedades buscar en esos portales.
        3. Da consejos sobre precios de mercado para esa zona.
        4. Formato: Usa markdown con negritas y listas para que sea legible.
        
        RESPUESTA:
        """
        
        response = model.generate_content(full_prompt)
        return response.text
    except Exception as e:
        raise Exception(f"Error al conectar con Gemini: {str(e)}")

# ─────────────────────────────────────────────────────────
# ESTADO DE SESIÓN
# ─────────────────────────────────────────────────────────
defaults = {
    "view": "home",
    "favoritos": [],
    "comparacion": [],
    "historial": [],
    "alertas": [],
    "datos_stats": [],
    "datos_mapa": [],
    "datos_predictivo": [],
    "pagina": 1,
    "gemini_api_key": "",
    "gemini_results": None,
}

for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ─────────────────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────────────────
with st.sidebar:
    st.title("⚙️ Filtros de búsqueda")
    
    st.markdown("**📍 Departamento**")
    region_sel = st.selectbox("Región", list(REGIONES_MENDOZA.keys()), label_visibility="collapsed")
    loc = st.selectbox("Departamento", REGIONES_MENDOZA[region_sel])
    op = st.radio("💰 Operación", ["Alquiler", "Venta"], horizontal=True)
    tipo = st.selectbox(
        "🏠 Tipo de Inmueble",
        ["Departamento", "Casa", "PH", "Terreno", "Local Comercial", "Oficina", "Cochera", "Quinta"]
    )
    
    st.divider()
    col_p1, col_p2 = st.columns(2)
    with col_p1:
        p_min = st.number_input("Precio mín. ($)", 0, 500_000_000, 0, step=100_000, format="%d")
    with col_p2:
        p_max = st.number_input("Precio máx. ($)", 0, 500_000_000, 0, step=100_000, format="%d")
    exp_max = st.number_input("💸 Expensas máx. ($)", 0, 1_000_000, 0, step=10_000, format="%d")
    
    st.divider()
    col_a1, col_a2 = st.columns(2)
    with col_a1:
        amb = st.slider("🛏️ Dormitorios", 0, 5, 0)
    with col_a2:
        banos = st.slider("🚿 Baños", 1, 4, 1)
    
    col_c1, col_c2 = st.columns(2)
    with col_c1:
        cochera = st.checkbox("🚗 Cochera")
    with col_c2:
        apto = st.checkbox("💳 Apto Crédito")
    
    superficie_min = st.number_input("📏 Superficie mínima (m²)", 0, 1000, 0, step=10)
    
    st.divider()
    buscar = st.button("🚀 BUSCAR PROPIEDADES", use_container_width=True, type="primary")
    
    st.divider()
    if st.button("🏠 Inicio", use_container_width=True):
        st.session_state.view = "home"
        st.rerun()
    if st.button("⭐ Favoritos", use_container_width=True):
        st.session_state.view = "favoritos"
        st.rerun()
    if st.button("🔔 Alertas", use_container_width=True):
        st.session_state.view = "alertas"
        st.rerun()
    if st.button("🤖 IA Gemini", use_container_width=True):
        st.session_state.view = "gemini"
        st.rerun()
    
    st.divider()
    st.markdown("**🌐 Portales**")
    portales_activos = st.multiselect(
        "Seleccionar portales",
        ["Inmoup", "Inmoclick", "Argenprop", "Zonaprop"],
        default=["Inmoup", "Inmoclick", "Argenprop", "Zonaprop"],
        label_visibility="collapsed",
    )
    
    filtros = {
        "loc": loc, "op": op, "tipo": tipo,
        "p_min": p_min, "p_max": p_max, "exp_max": exp_max,
        "amb": amb, "banos": banos, "cochera": cochera, "apto": apto,
        "superficie_min": superficie_min,
    }
    filtros_json = json.dumps(filtros, sort_keys=True)

# ─────────────────────────────────────────────────────────
# PÁGINA: HOME
# ─────────────────────────────────────────────────────────
if st.session_state.view == "home" and not buscar:
    st.markdown("""
    <div class="hero-section">
    <h1 style="font-size:50px;font-weight:900;margin-bottom:10px;">🍷 MENDOZA INMUEBLES PRO</h1>
    <p style="font-size:20px;opacity:0.9;">Buscador inteligente de propiedades en los 18 departamentos de Mendoza</p>
    <p style="font-size:14px;opacity:0.7;">Inmoup · Inmoclick · Argenprop · Zonaprop — Datos en tiempo real</p>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Portales integrados", "4", "✓")
    col2.metric("Departamentos", "20", "✓ (todos)")
    col3.metric("Cache de datos", "30 min", "⚡")
    col4.metric("Regiones", "5", "📍")
    
    st.divider()
    col_r1, col_r2, col_r3 = st.columns(3)
    with col_r1:
        st.markdown('<div class="stats-card"><h3>📊 Análisis estadístico</h3><p>Distribución de precios, outliers, correlaciones y resumen ejecutivo.</p></div>', unsafe_allow_html=True)
    with col_r2:
        st.markdown('<div class="rec-card"><h3>🗺️ Mapa interactivo</h3><p>Visualiza las propiedades sobre el mapa de Mendoza con filtros en tiempo real.</p></div>', unsafe_allow_html=True)
    with col_r3:
        st.markdown('<div class="trend-card"><h3>🤖 Predicción de precios</h3><p>Modelos ML para estimar el valor de una propiedad por sus características.</p></div>', unsafe_allow_html=True)
    
    st.divider()
    st.markdown("### 📍 Departamentos disponibles")
    for region, deptos in REGIONES_MENDOZA.items():
        st.markdown(f"**{region}:** {' · '.join(deptos)}")
    
    st.divider()
    if st.button("🚀 Comenzar búsqueda", use_container_width=True, type="primary"):
        buscar = True

# ─────────────────────────────────────────────────────────
# PÁGINA: RESULTADOS
# ─────────────────────────────────────────────────────────
if buscar or st.session_state.view == "results":
    st.session_state.view = "results"
    st.session_state.pagina = 1
    st.header(f"🏘️ {tipo}s en {op} — {loc}")
    
    with st.expander("📋 Filtros aplicados", expanded=False):
        c1, c2, c3 = st.columns(3)
        c1.write(f"**Ubicación:** {loc}\n\n**Operación:** {op}\n\n**Tipo:** {tipo}")
        c2.write(f"**Precio:** ${p_min:,} – {'Sin límite' if p_max == 0 else f'${p_max:,}'}\n\n**Expensas máx.:** {'Sin límite' if exp_max == 0 else f'${exp_max:,}'}")
        c3.write(f"**Dormitorios:** {amb if amb > 0 else 'Cualquiera'}\n\n**Baños:** {banos}\n\n**Cochera:** {'Sí' if cochera else 'No'}")
    
    progress = st.progress(0)
    status = st.empty()
    todas_dicts = []
    
    for idx, portal in enumerate(portales_activos):
        status.text(f"🔍 Buscando en {portal}...")
        progress.progress(int((idx / len(portales_activos)) * 100))
        url_portal = construir_url(portal, filtros)
        with st.expander(f"🔗 URL {portal}", expanded=False):
            st.code(url_portal)
        try:
            dicts = scrapear_portal(portal, url_portal, filtros_json, max_items=18)
            todas_dicts.extend(dicts)
            if dicts:
                st.success(f"✓ {portal}: {len(dicts)} resultados")
            else:
                st.warning(f"⚠️ {portal}: sin resultados")
        except Exception as e:
            st.error(f"❌ {portal}: {e}")
    
    progress.progress(100)
    status.text("✅ Búsqueda completada")
    time.sleep(0.5)
    progress.empty()
    status.empty()
    
    todas = dicts_to_propiedades(todas_dicts)
    
    if p_min > 0:
        todas = [p for p in todas if p.precio_numerico == 0 or p.precio_numerico >= p_min]
    if p_max > 0:
        todas = [p for p in todas if p.precio_numerico == 0 or p.precio_numerico <= p_max]
    if superficie_min > 0:
        todas = [p for p in todas if p.metros_cuadrados and p.metros_cuadrados >= superficie_min]
    
    st.session_state.datos_stats = todas
    st.session_state.datos_mapa = todas
    st.session_state.datos_predictivo = todas
    st.session_state.historial.append({"fecha": datetime.now().isoformat(), "filtros": filtros, "total": len(todas)})
    
    st.subheader(f"📊 {len(todas)} propiedades encontradas")
    
    if todas:
        analizador = AnalizadorInmobiliario(todas)
        recs = analizador.recomendaciones()
        if recs:
            st.subheader("💡 Recomendaciones")
            for r in recs:
                if r["nivel"] == "info":
                    st.info(r["texto"])
                else:
                    st.warning(r["texto"])
        
        stats = analizador.estadisticas_basicas()
        if stats:
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Precio Promedio", f"${stats['promedio']:,.0f}")
            c2.metric("Precio Mediano", f"${stats['mediana']:,.0f}")
            c3.metric("Desviación Estándar", f"${stats['desviacion']:,.0f}")
            c4.metric("Con Precio", f"{stats['con_precio']}/{stats['total']}")
        
        st.divider()
        cc1, cc2, cc3 = st.columns([2, 2, 2])
        with cc1:
            orden = st.selectbox("Ordenar por:", ["Precio ↑", "Precio ↓", "M² ↑", "M² ↓", "Sin ordenar"])
        with cc2:
            cols_grid = st.selectbox("Columnas:", [3, 4, 2], index=1)
        
        if orden == "Precio ↑":
            todas.sort(key=lambda x: x.precio_numerico if x.precio_numerico > 0 else float("inf"))
        elif orden == "Precio ↓":
            todas.sort(key=lambda x: x.precio_numerico, reverse=True)
        elif orden == "M² ↑":
            todas.sort(key=lambda x: x.metros_cuadrados if x.metros_cuadrados else float("inf"))
        elif orden == "M² ↓":
            todas.sort(key=lambda x: x.metros_cuadrados if x.metros_cuadrados else 0, reverse=True)
        
        items_pp = 12
        total_pags = max(1, (len(todas) - 1) // items_pp + 1)
        pag = st.session_state.get("pagina", 1)
        inicio = (pag - 1) * items_pp
        pag_props = todas[inicio: inicio + items_pp]
        
        cols_list = st.columns(cols_grid)
        # ✅ CORRECCIÓN CRÍTICA #1: Usar enumerate para índice único en keys
        for i, prop in enumerate(pag_props):
            with cols_list[i % cols_grid]:
                es_fav = any(f.id == prop.id for f in st.session_state.favoritos)
                precio_m2 = (
                    f"${prop.precio_numerico / prop.metros_cuadrados:,.0f}/m²"
                    if prop.metros_cuadrados and prop.metros_cuadrados > 0 and prop.precio_numerico > 0
                    else ""
                )
                m2_badge = f'<span class="badge">📏 {prop.metros_cuadrados:.0f} m²</span>' if prop.metros_cuadrados else ""
                pm2_badge = f'<span class="badge">💲 {precio_m2}</span>' if precio_m2 else ""
                exp_text = f"${prop.expensas:,.0f}" if prop.expensas else "—"
                moneda_badge = f'<span class="badge">🪙 {prop.moneda}</span>'
                
                st.markdown(f"""
                <div class="card">
                <img src="{prop.imagen}" class="card-img" onerror="this.src='{PLACEHOLDER_IMG}'">
                <div class="price">{prop.precio}</div>
                <div class="info">
                <p style="font-weight:600;margin:0 0 6px;">{prop.titulo}</p>
                <p style="color:#888;font-size:12px;margin:0 0 8px;">📍 {prop.ubicacion} · {prop.portal}</p>
                <div style="margin-bottom:8px;">
                <span class="badge">🛏️ {prop.dormitorios or "—"}</span>
                <span class="badge">🚿 {prop.banos}</span>
                {m2_badge}{pm2_badge}{moneda_badge}
                </div>
                <p style="font-size:11px;color:#666;margin:0;">
                🚗 Cochera: {"Sí" if prop.cochera else "No"} &nbsp;|&nbsp; 💸 Expensas: {exp_text}
                </p>
                </div>
                </div>
                """, unsafe_allow_html=True)
                
                b1, b2 = st.columns(2)
                with b1:
                    lbl_fav = "⭐ Guardado" if es_fav else "☆ Guardar"
                    # ✅ CORRECCIÓN CRÍTICA #1: key única con índice para evitar StreamlitDuplicateElementKey
                    if st.button(lbl_fav, key=f"fav_{prop.id}_{i}", use_container_width=True):
                        if es_fav:
                            st.session_state.favoritos = [f for f in st.session_state.favoritos if f.id != prop.id]
                        else:
                            st.session_state.favoritos.append(prop)
                        st.rerun()
                with b2:
                    st.link_button("🔗 Ver", prop.url, use_container_width=True)
        
        if total_pags > 1:
            st.divider()
            pc1, pc2, pc3 = st.columns([1, 3, 1])
            with pc1:
                if st.button("◀ Anterior") and pag > 1:
                    st.session_state.pagina = pag - 1
                    st.rerun()
            with pc2:
                st.markdown(f"<p style='text-align:center;'>Página {pag} de {total_pags}</p>", unsafe_allow_html=True)
            with pc3:
                if st.button("Siguiente ▶") and pag < total_pags:
                    st.session_state.pagina = pag + 1
                    st.rerun()
        
        st.divider()
        ac1, ac2, ac3, ac4 = st.columns(4)
        with ac1:
            if st.button("📊 Estadísticas", use_container_width=True):
                st.session_state.view = "stats"
                st.rerun()
        with ac2:
            if st.button("🗺️ Ver Mapa", use_container_width=True):
                st.session_state.view = "mapa"
                st.rerun()
        with ac3:
            if st.button("🤖 Análisis ML", use_container_width=True):
                st.session_state.view = "predictivo"
                st.rerun()
        with ac4:
            if st.button("🔔 Crear Alerta", use_container_width=True):
                st.session_state.alertas.append({
                    "filtros": filtros.copy(),
                    "fecha": datetime.now().isoformat(),
                    "activo": True,
                })
                st.success("✅ Alerta creada!")
        
        st.divider()
        st.subheader("📤 Exportar datos")
        df_export = pd.DataFrame([p.to_dict() for p in todas])
        ec1, ec2 = st.columns(2)
        with ec1:
            csv_bytes = df_export.to_csv(index=False).encode("utf-8")
            st.download_button(
                "⬇️ Descargar CSV", data=csv_bytes,
                file_name=f"mendoza_inmuebles_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                mime="text/csv", use_container_width=True
            )
        with ec2:
            xl_buf = BytesIO()
            with pd.ExcelWriter(xl_buf, engine="xlsxwriter") as writer:
                df_export.to_excel(writer, index=False, sheet_name="Propiedades")
                if stats:
                    pd.DataFrame([stats]).to_excel(writer, index=False, sheet_name="Estadísticas")
            st.download_button(
                "⬇️ Descargar Excel", data=xl_buf.getvalue(),
                file_name=f"mendoza_inmuebles_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )
    else:
        st.warning("⚠️ No se encontraron propiedades.")
        st.info("💡 Tip: Algunos portales pueden bloquearse temporalmente.")

# ─────────────────────────────────────────────────────────
# PÁGINA: ESTADÍSTICAS
# ─────────────────────────────────────────────────────────
elif st.session_state.view == "stats":
    st.header("📊 Análisis de Mercado")
    propiedades = st.session_state.datos_stats
    if not propiedades:
        st.info("Realizá una búsqueda primero.")
    else:
        analizador = AnalizadorInmobiliario(propiedades)
        stats = analizador.estadisticas_basicas()
        outliers = analizador.detectar_outliers()
        pm2 = analizador.precio_por_m2()
        df = analizador.df
        
        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("Total", stats.get("total", 0))
        c2.metric("Promedio", f"${stats.get('promedio', 0):,.0f}")
        c3.metric("Mediana", f"${stats.get('mediana', 0):,.0f}")
        c4.metric("Desv. Std.", f"${stats.get('desviacion', 0):,.0f}")
        cv = stats["desviacion"] / stats["promedio"] * 100 if stats.get("promedio") else 0
        c5.metric("Coef. Variación", f"{cv:.1f}%")
        
        st.divider()
        col1, col2 = st.columns(2)
        with col1:
            fig = px.histogram(
                df[df["Precio_Numérico"] > 0], x="Precio_Numérico",
                title="Distribución de precios", nbins=30,
                color_discrete_sequence=["#667eea"], marginal="box"
            )
            fig.update_layout(xaxis_title="Precio ($)", yaxis_title="Cantidad", showlegend=False)
            st.plotly_chart(fig, use_container_width=True)
        with col2:
            fig2 = px.box(
                df[df["Precio_Numérico"] > 0], x="Portal", y="Precio_Numérico",
                title="Precios por portal", color="Portal"
            )
            fig2.update_layout(showlegend=False)
            st.plotly_chart(fig2, use_container_width=True)
        
        col3, col4 = st.columns(2)
        with col3:
            df_valid = df[(df["M²"].notna()) & (df["M²"] > 0) & (df["Precio_Numérico"] > 0)]
            if not df_valid.empty:
                try:
                    fig3 = px.scatter(
                        df_valid, x="M²", y="Precio_Numérico", trendline="ols",
                        title="Precio vs Superficie", color="Dormitorios",
                        color_continuous_scale="Viridis"
                    )
                    st.plotly_chart(fig3, use_container_width=True)
                except Exception:
                    # ✅ CORRECCIÓN CRÍTICA #2: Fallback si statsmodels falla
                    fig3 = px.scatter(
                        df_valid, x="M²", y="Precio_Numérico",
                        title="Precio vs Superficie", color="Dormitorios",
                        color_continuous_scale="Viridis"
                    )
                    st.plotly_chart(fig3, use_container_width=True)
            else:
                st.info("No hay datos de superficie para graficar.")
        with col4:
            fig4 = px.pie(df, names="Dormitorios", title="Distribución por dormitorios",
                color_discrete_sequence=px.colors.qualitative.Pastel)
            st.plotly_chart(fig4, use_container_width=True)
        
        if pm2:
            st.divider()
            st.subheader("📐 Precio por m²")
            pc1, pc2, pc3, pc4 = st.columns(4)
            pc1.metric("Promedio/m²", f"${pm2['promedio']:,.0f}")
            pc2.metric("Mediana/m²", f"${pm2['mediana']:,.0f}")
            pc3.metric("Mínimo/m²", f"${pm2['min']:,.0f}")
            pc4.metric("Correlación Precio–M²", f"{pm2['correlacion']:.3f}")
        
        st.divider()
        st.subheader("🔍 Datos detallados")
        # ✅ CORRECCIÓN CRÍTICA #3: Incluir Precio_Numérico en cols_show
        cols_show = ["Portal", "Título", "Precio", "Precio_Numérico", "Dormitorios", "Baños", "M²", "Ubicación", "Moneda"]
        cols_exist = [c for c in cols_show if c in df.columns]
        
        # ✅ CORRECCIÓN CRÍTICA #3: Ordenar por columna que existe en el dataframe filtrado
        sort_col = "Precio_Numérico" if "Precio_Numérico" in cols_exist else (cols_exist[0] if cols_exist else None)
        if sort_col:
            st.dataframe(df[cols_exist].sort_values(sort_col), use_container_width=True, height=400)
        else:
            st.dataframe(df[cols_exist], use_container_width=True, height=400)
        
        if st.button("🔙 Volver a resultados"):
            st.session_state.view = "results"
            st.rerun()

# ─────────────────────────────────────────────────────────
# PÁGINA: MAPA
# ─────────────────────────────────────────────────────────
elif st.session_state.view == "mapa":
    st.header("🗺️ Mapa de propiedades")
    propiedades = st.session_state.datos_mapa
    if not propiedades:
        st.info("Realizá una búsqueda primero.")
    else:
        zona_central = ZONAS_MENDOZA.get(propiedades[0].ubicacion, ZONAS_MENDOZA["Capital"])
        mapa = folium.Map(location=[zona_central["lat"], zona_central["lon"]], zoom_start=12)
        
        for prop in propiedades:
            z = ZONAS_MENDOZA.get(prop.ubicacion, ZONAS_MENDOZA["Capital"])
            lat = prop.lat or z["lat"] + np.random.uniform(-0.005, 0.005)
            lon = prop.lon or z["lon"] + np.random.uniform(-0.005, 0.005)
            sup = f"{prop.metros_cuadrados:.0f} m²" if prop.metros_cuadrados else "N/A"
            exp = f"${prop.expensas:,.0f}" if prop.expensas else "N/A"
            popup_html = f"""
            <div style="min-width:220px;font-family:sans-serif;font-size:13px">
            <b>{prop.titulo}</b><br>
            <span style="color:#27ae60;font-weight:bold">{prop.precio}</span><br>
            🛏️ {prop.dormitorios} dorm. &nbsp;|&nbsp; 🚿 {prop.banos} baño<br>
            📏 {sup} &nbsp;|&nbsp; 💸 Expensas: {exp}<br>
            🌐 {prop.portal}<br>
            <a href="{prop.url}" target="_blank">Ver publicación →</a>
            </div>"""
            color = "green" if prop.precio_numerico > 0 and prop.precio_numerico < 50_000_000 else "red"
            folium.Marker(
                location=[lat, lon],
                popup=folium.Popup(popup_html, max_width=280),
                icon=folium.Icon(color=color, icon="home", prefix="fa"),
                tooltip=f"{prop.titulo[:40]} — {prop.precio}",
            ).add_to(mapa)
        
        folium_static(mapa, width=1100, height=550)
        
        df_mapa = pd.DataFrame([p.to_dict() for p in propiedades])
        validos = df_mapa[df_mapa["Precio_Numérico"] > 0]["Precio_Numérico"]
        if not validos.empty:
            mc1, mc2, mc3 = st.columns(3)
            mc1.metric("Total en mapa", len(propiedades))
            mc2.metric("Precio promedio", f"${validos.mean():,.0f}")
            mc3.metric("Precio mediano", f"${validos.median():,.0f}")
        
        if st.button("🔙 Volver a resultados"):
            st.session_state.view = "results"
            st.rerun()

# ─────────────────────────────────────────────────────────
# PÁGINA: ANÁLISIS PREDICTIVO (ML)
# ─────────────────────────────────────────────────────────
elif st.session_state.view == "predictivo":
    st.header("🤖 Análisis Predictivo")
    propiedades = st.session_state.datos_predictivo
    if not propiedades:
        st.info("Realizá una búsqueda primero.")
    else:
        df = pd.DataFrame([p.to_dict() for p in propiedades])
        df_ml = df[
            (df["Precio_Numérico"] > 0) &
            (df["M²"].notna()) & (df["M²"] > 0) &
            (df["Dormitorios"].notna()) & (df["Baños"].notna())
        ].copy()
        
        if len(df_ml) < 5:
            st.warning(f"Solo {len(df_ml)} propiedades con datos completos.")
        else:
            st.success(f"✅ {len(df_ml)} propiedades disponibles para análisis.")
            
            try:
                from sklearn.cluster import KMeans
                from sklearn.preprocessing import StandardScaler
                st.subheader("🎯 Segmentación K-Means")
                n_clusters = st.slider("Número de segmentos", 2, min(8, len(df_ml)), 3)
                scaler = StandardScaler()
                X = scaler.fit_transform(df_ml[["Dormitorios", "Baños", "M²", "Precio_Numérico"]])
                km = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
                df_ml["Cluster"] = km.fit_predict(X).astype(str)
                fig_c = px.scatter(
                    df_ml, x="M²", y="Precio_Numérico", color="Cluster",
                    size="Dormitorios", hover_data=["Portal", "Ubicación"],
                    title="Segmentación de propiedades",
                    color_discrete_sequence=px.colors.qualitative.Set2
                )
                st.plotly_chart(fig_c, use_container_width=True)
                
                st.subheader("📊 Características por segmento")
                seg_stats = df_ml.groupby("Cluster").agg(
                    Cantidad=("Precio_Numérico", "count"),
                    Precio_Prom=("Precio_Numérico", "mean"),
                    M2_Prom=("M²", "mean"),
                    Dorm_Prom=("Dormitorios", "mean"),
                ).round(1)
                seg_stats["Precio_Prom"] = seg_stats["Precio_Prom"].apply(lambda x: f"${x:,.0f}")
                st.dataframe(seg_stats, use_container_width=True)
            except ImportError:
                st.warning("scikit-learn no instalado.")
            
            try:
                from sklearn.linear_model import LinearRegression
                st.divider()
                st.subheader("💰 Predicción de precio")
                pc1, pc2, pc3 = st.columns(3)
                pred_dorm = pc1.number_input("Dormitorios", 1, 6, 2)
                pred_ban = pc2.number_input("Baños", 1, 4, 1)
                pred_m2 = pc3.number_input("Superficie m²", 20, 600, 80)
                X_train = df_ml[["Dormitorios", "Baños", "M²"]]
                y_train = df_ml["Precio_Numérico"]
                model = LinearRegression()
                model.fit(X_train, y_train)
                pred = model.predict([[pred_dorm, pred_ban, pred_m2]])[0]
                residuos = y_train - model.predict(X_train)
                std_err = np.std(residuos)
                ic_lo = max(0, pred - 1.96 * std_err)
                ic_hi = pred + 1.96 * std_err
                st.success(f"**Precio estimado:** ${pred:,.0f}")
                st.info(f"**Intervalo de confianza 95%:** ${ic_lo:,.0f} — ${ic_hi:,.0f}")
                r2 = model.score(X_train, y_train)
                st.caption(f"R² del modelo: {r2:.3f}")
            except ImportError:
                st.warning("scikit-learn no instalado.")
        
        if st.button("🔙 Volver a resultados"):
            st.session_state.view = "results"
            st.rerun()

# ─────────────────────────────────────────────────────────
# PÁGINA: GEMINI AI (NUEVA)
# ─────────────────────────────────────────────────────────
elif st.session_state.view == "gemini":
    st.header("🤖 Asistente Inmobiliario con IA Gemini")
    st.markdown("""
    Utiliza **Google Gemini 2.5 Flash** para analizar portales inmobiliarios y obtener recomendaciones personalizadas.
    
    **Instrucciones:**
    1. Ingresa tu API Key de Google AI Studio.
    2. Pega las URLs de los portales que quieres analizar.
    3. Describe qué estás buscando.
    """)
    
    with st.form("gemini_search_form", clear_on_submit=False):
        col1, col2 = st.columns([3, 1])
        with col1:
            api_key_input = st.text_input(
                "🔑 API Key de Google Gemini", 
                value=st.session_state.gemini_api_key,
                type="password",
                help="Obtén tu key gratuita en https://aistudio.google.com/app/apikey"
            )
        with col2:
            st.write("")
            st.write("")
            save_key = st.checkbox("Guardar Key", value=bool(st.session_state.gemini_api_key))
        
        urls_input = st.text_area(
            "🌐 URLs de Portales Inmobiliarios", 
            value="https://www.inmoup.com.ar, https://www.inmoclick.com.ar, https://www.argenprop.com",
            placeholder="Ingresa las URLs separadas por comas...",
            height=80
        )
        
        prompt_input = st.text_area(
            "📝 Tu Búsqueda / Prompt", 
            placeholder="Ej: Busco departamentos de 2 habitaciones en Mendoza centro por menos de USD 80000 que tengan cochera...",
            height=150
        )
        
        submitted = st.form_submit_button("🚀 Ejecutar Búsqueda con IA", use_container_width=True, type="primary")
        
        if submitted:
            if save_key and api_key_input:
                st.session_state.gemini_api_key = api_key_input
            
            if not api_key_input:
                st.error("❌ Por favor ingresa una API Key válida.")
            elif not urls_input or not prompt_input:
                st.warning("⚠️ Por favor completa las URLs y el prompt de búsqueda.")
            else:
                try:
                    with st.spinner('🤖 La IA está analizando... Esto puede tomar unos segundos.'):
                        result = procesar_busqueda_gemini(api_key_input, urls_input, prompt_input)
                        st.session_state.gemini_results = result
                        st.success("✅ Búsqueda completada exitosamente")
                except Exception as e:
                    st.error(f"❌ Error: {str(e)}")
    
    if st.session_state.gemini_results:
        st.markdown("---")
        st.subheader("📊 Resultados del Análisis")
        st.markdown(st.session_state.gemini_results)
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("📋 Copiar Respuesta", use_container_width=True):
                st.write("Respuesta copiada al portapapeles (simulado)")
        with col2:
            if st.button("🗑️ Limpiar Resultados", use_container_width=True):
                st.session_state.gemini_results = None
                st.rerun()
    
    if st.button("🔙 Volver al inicio"):
        st.session_state.view = "home"
        st.rerun()

# ─────────────────────────────────────────────────────────
# PÁGINA: FAVORITOS
# ─────────────────────────────────────────────────────────
elif st.session_state.view == "favoritos":
    st.header("⭐ Propiedades Favoritas")
    favs = st.session_state.favoritos
    if not favs:
        st.info("No tenés propiedades guardadas.")
    else:
        st.write(f"{len(favs)} propiedades guardadas")
        cols = st.columns(3)
        for i, prop in enumerate(favs):
            with cols[i % 3]:
                st.markdown(f"""
                <div class="card">
                <img src="{prop.imagen}" class="card-img" onerror="this.src='{PLACEHOLDER_IMG}'">
                <div class="price">{prop.precio}</div>
                <div class="info">
                <p><b>{prop.titulo}</b></p>
                <p style="color:#888">📍 {prop.ubicacion} · {prop.portal}</p>
                <span class="badge">🛏️ {prop.dormitorios}</span>
                <span class="badge">🚿 {prop.banos}</span>
                </div>
                </div>""", unsafe_allow_html=True)
                c1, c2 = st.columns(2)
                c1.link_button("🔗 Ver", prop.url, use_container_width=True)
                # ✅ CORRECCIÓN CRÍTICA #4: key única con índice
                if c2.button("🗑️ Quitar", key=f"rm_fav_{prop.id}_{i}", use_container_width=True):
                    st.session_state.favoritos = [f for f in st.session_state.favoritos if f.id != prop.id]
                    st.rerun()
        
        st.divider()
        df_favs = pd.DataFrame([p.to_dict() for p in favs])
        csv_favs = df_favs.to_csv(index=False).encode("utf-8")
        st.download_button("⬇️ Exportar favoritos CSV", data=csv_favs,
            file_name="favoritos_mendoza.csv", mime="text/csv")

# ─────────────────────────────────────────────────────────
# PÁGINA: ALERTAS
# ─────────────────────────────────────────────────────────
elif st.session_state.view == "alertas":
    st.header("🔔 Alertas de Precios")
    alertas = st.session_state.alertas
    if not alertas:
        st.info("No tenés alertas configuradas.")
    else:
        st.success(f"✅ {len(alertas)} alertas activas")
        for idx, alerta in enumerate(alertas):
            with st.expander(f"Alerta {idx+1} — {alerta['fecha'][:16]}", expanded=True):
                c1, c2 = st.columns(2)
                with c1:
                    f = alerta["filtros"]
                    precio_max_str = "Sin límite" if f['p_max'] == 0 else f"${f['p_max']:,}"
                    st.markdown(f"**Departamento:** {f['loc']}\n\n"
                        f"**Operación:** {f['op']}\n\n"
                        f"**Tipo:** {f['tipo']}\n\n"
                        f"**Precio:** ${f['p_min']:,} – {precio_max_str}\n\n"
                        f"**Dormitorios:** {f['amb'] or 'Cualquiera'}")
                with c2:
                    st.success("✅ Activa")
                    if st.button(f"🗑️ Eliminar", key=f"del_alerta_{idx}"):
                        st.session_state.alertas.pop(idx)
                        st.rerun()

# ─────────────────────────────────────────────────────────
# FOOTER
# ─────────────────────────────────────────────────────────
st.divider()
st.markdown(
    "<p style='text-align:center;color:#999;font-size:12px;'>"
    "© 2026 Mendoza Inmuebles Pro · Datos en tiempo real (caché 30 min) · "
    "Streamlit + Python + Scikit-learn + Plotly + Folium + Gemini AI"
    "</p>",
    unsafe_allow_html=True
)
