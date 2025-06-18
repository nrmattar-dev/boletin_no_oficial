from flask import Flask, render_template, request, abort, jsonify
from flask_caching import Cache
from functools import lru_cache
import math
import re
from markupsafe import Markup
from datetime import datetime
import os
import psycopg2
import json

app = Flask(__name__)

AVISOS_POR_PAGINA = 10  # Cantidad de avisos por página

@app.template_filter('js_string')
def js_string_filter(s):
    """Escapa una cadena para usarla de forma segura en JavaScript."""
    # Esto convierte cualquier cosa a texto y luego la hace segura para JavaScript
    return json.dumps(str(s))

SUSPECT_UA = ["python", "curl", "httpclient", "wget", "scrapy", "bot", "spider"]

@app.before_request
def bloquear_user_agents():
    ua = request.headers.get('User-Agent', '').lower()
    if any(palabra in ua for palabra in SUSPECT_UA):
        abort(403)

def obtener_conexion():
    #connection_url = os.getenv('POSTGRES_URL_NON_POOLING')
    connection_url = os.getenv('POSTGRES_URL_LOCAL')
    # Conectar
    return psycopg2.connect(connection_url)

@app.route('/categorias')
def categorias():
    q = request.args.get('q', '')
    if not q or len(q) < 2:
        return jsonify([])

    conn = obtener_conexion()
    cur = conn.cursor()
    cur.execute("""
        SELECT DISTINCT categoria
        FROM avisos
        WHERE UPPER(categoria) LIKE UPPER(%s)
        ORDER BY categoria
        LIMIT 20
    """, (f"%{q}%",))
    
    resultados = [row[0] for row in cur.fetchall()]
    cur.close()
    conn.close()
    return jsonify(resultados)

@lru_cache(maxsize=1)
def obtener_fechas():
    conn = obtener_conexion()
    cursor = conn.cursor()
    cursor.execute('SELECT MIN(FechaPublicacion), MAX(Timestamp) FROM avisos')
    fecha_desde, fecha_maxima = cursor.fetchone()
    conn.close()
    if fecha_maxima:
        fecha_maxima = fecha_maxima.strftime('%Y-%m-%dT%H:%M:%SZ')
    return fecha_desde, fecha_maxima

# Separar técnico y criollo
def extraer_texto_tecnico(texto):
    return texto.split('|¥|')[0].strip()

def extraer_texto_criollo(texto):
    partes = texto.split('|¥|')
    return partes[1].strip() if len(partes) > 1 else ""

def convertir_negritas(texto):
    texto_html = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', texto)
    return Markup(texto_html)

def cortar_texto(texto, limite=500):
    if len(texto) <= limite:
        return texto, ''
    corte = texto[:limite].rsplit(' ', 1)[0]
    resto = texto[len(corte):]
    return corte, resto

def formatear_criollo(texto):
    return texto.replace('|¥|', '<br><strong>En criollo:</strong> ')

def obtener_avisos_paginado(pagina, fecha_filtro=None,categoria_filtro=None,texto_filtro=None):
    offset = (pagina - 1) * AVISOS_POR_PAGINA
    conn = obtener_conexion()
    cursor = conn.cursor()

    base_query = '''
        SELECT Id, Titulo, Categoria, Texto, TextoResumido, Enlace, FechaPublicacion, Modelo, Timestamp
        FROM avisos
    '''
    count_query = 'SELECT COUNT(*) FROM avisos'

    where_clause = ''
    conditions = []  # Initialize an empty list to hold individual conditions
    params = []      # Initialize an empty list to hold parameters for the SQL query

    if fecha_filtro:
        conditions.append("DATE(FechaPublicacion) = %s")
        params.append(fecha_filtro)

    if texto_filtro:
        palabras = [p.strip().upper() for p in texto_filtro.split(',') if p.strip()]
        for palabra in palabras:
            conditions.append("(UPPER(Titulo) LIKE UPPER(%s) OR UPPER(TextoResumido) LIKE UPPER(%s))")
            params.append(f'%{palabra}%')
            params.append(f'%{palabra}%')

    if categoria_filtro:
        conditions.append("UPPER(Categoria) LIKE %s")
        params.append(f'%{categoria_filtro}%')        

    # Construct the final where_clause
    if conditions:
        where_clause = " WHERE " + " AND ".join(conditions)     

    cursor.execute(count_query + where_clause, params)
    total_avisos = cursor.fetchone()[0]

    full_query = base_query + where_clause + ' ORDER BY FechaPublicacion DESC, Categoria, Id LIMIT %s OFFSET %s'

    cursor.execute(full_query, params + [AVISOS_POR_PAGINA, offset])
    rows = cursor.fetchall()
    conn.close()

    # Mapeo manual para que se parezca a sqlite3.Row
    columnas = ['Id', 'Titulo', 'Categoria', 'Texto', 'TextoResumido', 'Enlace', 'FechaPublicacion', 'Modelo', 'Timestamp']
    avisos = [dict(zip(columnas, row)) for row in rows]

    total_paginas = math.ceil(total_avisos / AVISOS_POR_PAGINA) if AVISOS_POR_PAGINA > 0 else 1
    return avisos, total_paginas


@app.route('/resumen-diario')
def resumen_diario():
    fecha_str = request.args.get('fecha')
    fecha = datetime.now().date()

    if fecha_str:
        try:
            fecha = datetime.strptime(fecha_str, "%Y-%m-%d").date()
        except ValueError:
            pass

    conn = obtener_conexion()
    cursor = conn.cursor()
    cursor.execute('SELECT resumen, fecha, modelo FROM resumenes_diarios WHERE fecha = %s', (fecha,))
    resultado = cursor.fetchone()
    conn.close()

    if not resultado:
        return render_template('resumendiario.html',
            resumen_diario="No hay resumen disponible para esta fecha.",
            resumen_diario_criollo="",
            fecha_actual=fecha.strftime("%Y-%m-%d"),
            fecha_actualizacion=None,
            modelo="No especificado"
        )

    def convertir_asteriscos_a_negrita(texto):
        # Reemplaza texto entre **...** por <b>...</b>
        return re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', texto)

    def enlazar_palabras_clave(texto):
        def reemplazar_coincidencia(match):
            palabras = match.group(1).split(',')
            links = [f'<a href="/?texto={p.strip()}">{p.strip()}</a>' for p in palabras]
            return f'(Palabras Clave: {", ".join(links)})'

        # Busca el patrón completo de palabras clave
        return re.sub(r'\(Palabras Clave:\s*([^)]+)\)', reemplazar_coincidencia, texto)        

    def resaltar_numeradores(texto):
        puntos = texto.split('|n|')  # separar por |n|
        puntos_resaltados = []
        for p in puntos:
            # Buscar patrón "numero." al inicio y ponerlo en negrita
            p = re.sub(r'^(\d+\.)', r'<b>\1</b>', p.strip())
            puntos_resaltados.append(p)
        return '|n|'.join(puntos_resaltados)
    
    texto_resumen = convertir_asteriscos_a_negrita(resultado[0])
    # Separar por |¥|
    partes = texto_resumen.split('|¥|')
    texto_normal = enlazar_palabras_clave(resaltar_numeradores(partes[0].strip()))
    texto_criollo = enlazar_palabras_clave(resaltar_numeradores(partes[1].strip() if len(partes) > 1 else ""))
    texto_normal = '<p>' + texto_normal.replace('|n|', '</p><p>') + '</p>'
    texto_criollo = '<p>' + texto_criollo.replace('|n|', '</p><p>') + '</p>'
    return render_template('resumendiario.html',
        resumen_diario=texto_normal,
        resumen_diario_criollo=texto_criollo,
        resumen_plano=texto_resumen.replace('|¥|','\n'),
        fecha_actual=fecha.strftime("%Y-%m-%d"),
        fecha_actualizacion=resultado[1].strftime('%Y-%m-%dT%H:%M:%SZ') if resultado[1] else None,
        modelo=resultado[2] if resultado[2] else "No especificado"
    )


@app.route('/aviso/<int:id>')
def mostrar_aviso(id):
    conn = obtener_conexion()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT Id, Titulo, Categoria, Texto, TextoResumido, Enlace, FechaPublicacion, Modelo, Timestamp
        FROM avisos
        WHERE Id = %s
    ''', (id,))
    row = cursor.fetchone()
    conn.close()

    if not row:
        return "Aviso no encontrado", 404

    columnas = ['Id', 'Titulo', 'Categoria', 'Texto', 'TextoResumido', 'Enlace', 'FechaPublicacion', 'Modelo', 'Timestamp']
    aviso = dict(zip(columnas, row))

    texto_a_usar = aviso['TextoResumido'] or f"RESUMEN AÚN NO GENERADO. TEXTO COMPLETO: {aviso['Texto']}"
    texto_tecnico = extraer_texto_tecnico(texto_a_usar)
    texto_criollo = extraer_texto_criollo(texto_a_usar)

    # Cortar técnico en dos
    corto, largo = cortar_texto(texto_tecnico)

    # Convertir con negritas
    aviso['TextoResumidoCorto'] = convertir_negritas(corto)
    aviso['TextoResumidoLargo'] = convertir_negritas(largo)
    aviso['TextoResumidoCriollo'] = convertir_negritas(texto_criollo)

    return render_template('aviso.html', aviso=aviso)

cache = Cache(app, config={'CACHE_TYPE': 'SimpleCache', 'CACHE_DEFAULT_TIMEOUT': 60})

@app.route('/')
@app.route('/<int:pagina>')
@cache.cached(timeout=60, query_string=True)
def index(pagina=1):
    #fecha_filtro = request.args.get('fecha')
    fecha_filtro_str = request.args.get('fecha')
    fecha_filtro = None
    if fecha_filtro_str:
        try:
            fecha_filtro = datetime.strptime(fecha_filtro_str, "%Y-%m-%d").date()
        except ValueError:
            print(f"Fecha inválida: {fecha_filtro_str}")


    texto_filtro = request.args.get('texto')
    categoria_filtro = request.args.get('categoria')
    avisos_pagina, total_paginas = obtener_avisos_paginado(pagina, fecha_filtro, categoria_filtro, texto_filtro)
    avisos_final = []

    for aviso in avisos_pagina:
        texto_a_usar = aviso['TextoResumido']
        if not texto_a_usar:
            texto_a_usar = f"RESUMEN AÚN NO GENERADO. TEXTO COMPLETO: {aviso['Texto']}"

        texto_tecnico = extraer_texto_tecnico(texto_a_usar)
        texto_criollo = extraer_texto_criollo(texto_a_usar)

        # Cortar técnico en dos
        corto, largo = cortar_texto(texto_tecnico)

        # Convertir con negritas
        aviso['TextoResumidoCorto'] = convertir_negritas(corto)
        aviso['TextoResumidoLargo'] = convertir_negritas(largo)
        aviso['TextoResumidoCriollo'] = convertir_negritas(texto_criollo)
        avisos_final.append(aviso)

    fecha_desde, fecha_actualizacion = obtener_fechas()

    return render_template(
        'index.html',
        avisos=avisos_final,
        pagina=pagina,
        total_paginas=total_paginas,
        request=request,
        fecha_actualizacion=fecha_actualizacion,
        fecha_desde=fecha_desde
    )

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
