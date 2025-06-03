from flask import Flask, render_template, request
import math
import re
from markupsafe import Markup
from datetime import datetime
import os
import psycopg2

app = Flask(__name__)

AVISOS_POR_PAGINA = 50  # Cantidad de avisos por página

def obtener_conexion():
    user = os.getenv('POSTGRES_USER')
    password = os.getenv('POSTGRES_PASSWORD')
    host = os.getenv('POSTGRES_HOST')
    port = os.getenv('POSTGRES_PORT', '5432')
    dbname = os.getenv('POSTGRES_DATABASE')

    # Armar la URL
    connection_url = f"postgresql://{user}:{password}@{host}:{port}/{dbname}"

    # Conectar
    return psycopg2.connect(connection_url)

def obtener_fechas():
    conn = obtener_conexion()
    cursor = conn.cursor()
    cursor.execute('SELECT MIN(FechaPublicacion), MAX(Timestamp) FROM avisos')
    fecha_desde, fecha_maxima = cursor.fetchone()
    conn.close()
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

def obtener_avisos_paginado(pagina, fecha_filtro=None):
    offset = (pagina - 1) * AVISOS_POR_PAGINA
    conn = obtener_conexion()
    cursor = conn.cursor()

    base_query = '''
        SELECT Id, Titulo, Texto, TextoResumido, Enlace, FechaPublicacion, Modelo, Timestamp
        FROM avisos
    '''
    count_query = 'SELECT COUNT(*) FROM avisos'

    params = []
    where_clause = ''

    if fecha_filtro:
        where_clause = ' WHERE DATE(FechaPublicacion) = %s'
        params.append(fecha_filtro)

    cursor.execute(count_query + where_clause, params)
    total_avisos = cursor.fetchone()[0]

    full_query = base_query + where_clause + ' ORDER BY Id DESC LIMIT %s OFFSET %s'
    cursor.execute(full_query, params + [AVISOS_POR_PAGINA, offset])
    rows = cursor.fetchall()
    conn.close()

    # Mapeo manual para que se parezca a sqlite3.Row
    columnas = ['Id', 'Titulo', 'Texto', 'TextoResumido', 'Enlace', 'FechaPublicacion', 'Modelo', 'Timestamp']
    avisos = [dict(zip(columnas, row)) for row in rows]

    total_paginas = math.ceil(total_avisos / AVISOS_POR_PAGINA) if AVISOS_POR_PAGINA > 0 else 1
    return avisos, total_paginas

@app.route('/')
@app.route('/<int:pagina>')
def index(pagina=1):
    fecha_filtro = request.args.get('fecha')
    avisos_pagina, total_paginas = obtener_avisos_paginado(pagina, fecha_filtro)
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
