from flask import Flask, render_template, request, abort
import math
import re
from markupsafe import Markup
from datetime import datetime
import os
import psycopg2
import json

app = Flask(__name__)

AVISOS_POR_PAGINA = 25  # Cantidad de avisos por página

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
    connection_url = os.getenv('POSTGRES_URL_NON_POOLING')
    # Conectar
    return psycopg2.connect(connection_url)

def obtener_fechas():
    conn = obtener_conexion()
    cursor = conn.cursor()
    cursor.execute('SELECT MIN(FechaPublicacion), MAX(Timestamp) FROM avisos')
    fecha_desde, fecha_maxima = cursor.fetchone()
    conn.close()
    if fecha_maxima:
        fecha_maxima = fecha_maxima.strftime('%Y-%m-%d') 
    return fecha_desde, fecha_maxima

def convertir_negritas(texto):
    texto_html = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', texto)
    return Markup(texto_html)

def cortar_texto(texto, limite=500):
    if len(texto) <= limite:
        return texto, ''
    corte = texto[:limite].rsplit(' ', 1)[0]
    resto = texto[len(corte):]
    return corte, resto

def obtener_avisos_paginado(pagina, fecha_filtro=None,titulo_filtro=None):
    offset = (pagina - 1) * AVISOS_POR_PAGINA
    conn = obtener_conexion()
    cursor = conn.cursor()

    base_query = '''
        SELECT Id, Titulo, Texto, TextoResumido, Enlace, FechaPublicacion, Modelo, Timestamp
        FROM avisos
    '''
    count_query = 'SELECT COUNT(*) FROM avisos'

    where_clause = ''
    conditions = []  # Initialize an empty list to hold individual conditions
    params = []      # Initialize an empty list to hold parameters for the SQL query

    if fecha_filtro:
        conditions.append("DATE(FechaPublicacion) = %s")
        params.append(fecha_filtro)

    if titulo_filtro:
        palabras = [p.strip().upper() for p in titulo_filtro.split(',') if p.strip()]
        for palabra in palabras:
            conditions.append("UPPER(Titulo) LIKE %s")
            params.append(f'%{palabra}%')

    # Construct the final where_clause
    if conditions:
        where_clause = " WHERE " + " AND ".join(conditions)     

    cursor.execute(count_query + where_clause, params)
    total_avisos = cursor.fetchone()[0]

    full_query = base_query + where_clause + ' ORDER BY FechaPublicacion DESC, Id LIMIT %s OFFSET %s'
    cursor.execute(full_query, params + [AVISOS_POR_PAGINA, offset])
    rows = cursor.fetchall()
    conn.close()

    # Mapeo manual para que se parezca a sqlite3.Row
    columnas = ['Id', 'Titulo', 'Texto', 'TextoResumido', 'Enlace', 'FechaPublicacion', 'Modelo', 'Timestamp']
    avisos = [dict(zip(columnas, row)) for row in rows]

    total_paginas = math.ceil(total_avisos / AVISOS_POR_PAGINA) if AVISOS_POR_PAGINA > 0 else 1
    return avisos, total_paginas

@app.route('/aviso/<int:id>')
def mostrar_aviso(id):
    conn = obtener_conexion()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT Id, Titulo, Texto, TextoResumido, Enlace, FechaPublicacion, Modelo, Timestamp
        FROM avisos
        WHERE Id = %s
    ''', (id,))
    row = cursor.fetchone()
    conn.close()

    if not row:
        return "Aviso no encontrado", 404

    columnas = ['Id', 'Titulo', 'Texto', 'TextoResumido', 'Enlace', 'FechaPublicacion', 'Modelo', 'Timestamp']
    aviso = dict(zip(columnas, row))

    texto_a_usar = aviso['TextoResumido'] or f"RESUMEN AÚN NO GENERADO. TEXTO COMPLETO: {aviso['Texto']}"
    corto, largo = cortar_texto(texto_a_usar)
    aviso['TextoResumidoCorto'] = convertir_negritas(corto)
    aviso['TextoResumidoLargo'] = convertir_negritas(largo)

    return render_template('aviso.html', aviso=aviso)


@app.route('/')
@app.route('/<int:pagina>')
def index(pagina=1):
    fecha_filtro = request.args.get('fecha')
    titulo_filtro = request.args.get('titulo')
    avisos_pagina, total_paginas = obtener_avisos_paginado(pagina, fecha_filtro, titulo_filtro)
    avisos_final = []

    for aviso in avisos_pagina:
        texto_a_usar = aviso['TextoResumido']
        if not texto_a_usar:
            texto_a_usar = f"RESUMEN AÚN NO GENERADO. TEXTO COMPLETO: {aviso['Texto']}"

        corto, largo = cortar_texto(texto_a_usar)
        aviso['TextoResumidoCorto'] = convertir_negritas(corto)
        aviso['TextoResumidoLargo'] = convertir_negritas(largo)

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
    app.run(debug=True, host='127.0.0.1', port=5050)
