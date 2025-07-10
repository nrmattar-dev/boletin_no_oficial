from flask import Flask, render_template, request, abort, jsonify
from flask_caching import Cache
from functools import lru_cache
import math
import json
from markupsafe import Markup
from datetime import datetime
import os
import psycopg2

app = Flask(__name__)

AVISOS_POR_PAGINA = 10  # Cantidad de avisos por página

@app.template_filter('js_string')
def js_string_filter(s):
    """Escapa una cadena para usarla de forma segura en JavaScript."""
    return json.dumps(str(s))

SUSPECT_UA = ["python", "curl", "httpclient", "wget", "scrapy", "bot", "spider"]

@app.before_request
def bloquear_user_agents():
    ua = request.headers.get('User-Agent', '').lower()
    if any(palabra in ua for palabra in SUSPECT_UA):
        abort(403)

def obtener_conexion():
    #connection_url = os.getenv('POSTGRES_URL_LOCAL')
    connection_url = os.getenv('POSTGRES_URL_NON_POOLING')
    return psycopg2.connect(connection_url)

@app.route('/categorias')
def categorias():
    q = request.args.get('q', '')
    if not q or len(q) < 2:
        return jsonify([])

    conn = obtener_conexion()
    cur = conn.cursor()
    # Modificado: Consulta directamente la tabla 'avisos' para las categorías
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
    # Modificado: Consulta directamente la tabla 'avisos' para las fechas mínima y máxima
    cursor.execute('SELECT MIN(fechapublicacion), MAX(timestamp) FROM avisos')
    fecha_desde, fecha_maxima = cursor.fetchone()
    conn.close()
    if fecha_maxima:
        fecha_maxima = fecha_maxima.strftime('%Y-%m-%dT%H:%M:%SZ')
    return fecha_desde, fecha_maxima

def obtener_avisos_paginado(pagina, fecha_filtro=None, categoria_filtro=None, texto_filtro=None):
    offset = (pagina - 1) * AVISOS_POR_PAGINA
    conn = obtener_conexion()
    cursor = conn.cursor()

    # --- Primera parte: Filtrar y contar en la tabla 'avisos' (la tabla física) ---
    # Solo seleccionamos las columnas necesarias para el filtrado y el orden
    base_select_columns = "id, fechapublicacion, categoria, titulo" # Añadimos titulo para el filtro de texto
    count_query_base = 'SELECT COUNT(*) FROM avisos'
    base_query_ids = f'SELECT {base_select_columns} FROM avisos'

    conditions = []
    params = []

    if fecha_filtro:
        conditions.append("DATE(fechapublicacion) = %s")
        params.append(fecha_filtro)

    if texto_filtro:
        palabras = [p.strip().upper() for p in texto_filtro.split(',') if p.strip()]
        for palabra in palabras:
            # Importante: Aquí solo filtramos por 'titulo' que está en la tabla 'avisos'
            conditions.append("(UPPER(titulo) LIKE UPPER(%s) OR UPPER(textoresumido) LIKE UPPER(%s))")
            params.append(f'%{palabra}%')
            params.append(f'%{palabra}%')

    if categoria_filtro:
        conditions.append("UPPER(categoria) LIKE UPPER(%s)")
        params.append(f'%{categoria_filtro}%')

    where_clause = ""
    if conditions:
        where_clause = " WHERE " + " AND ".join(conditions)

    # Obtener el total de avisos filtrados de la tabla base
    cursor.execute(count_query_base + where_clause, params)
    total_avisos = cursor.fetchone()[0]

    # Obtener los IDs de los avisos para la página actual de la tabla base
    # El orden es crucial para el paginado correcto
    full_query_ids = base_query_ids + where_clause + ' ORDER BY fechapublicacion DESC, categoria, id LIMIT %s OFFSET %s'
    cursor.execute(full_query_ids, params + [AVISOS_POR_PAGINA, offset])
    
    # Extraemos solo los IDs de los resultados de la tabla base
    ids_para_pagina = [row[0] for row in cursor.fetchall()]

    avisos = []
    if ids_para_pagina:
        # --- Segunda parte: Consultar la vista 'avisos_processed' solo para los IDs obtenidos ---
        columnas_seleccionadas_vista = "id, titulo, texto, textoresumido, textoresumidocorto, textoresumidolargo, " \
                                       "titulotecnico, titulocriollo, textoresumidocriollocorto, textoresumidocriollolargo, " \
                                       "enlace, fechapublicacion, categoria, modelo, timestamp"
        
        # Creamos una cadena de placeholders para la cláusula IN
        placeholders = ','.join(['%s'] * len(ids_para_pagina))
        
        # Consultamos la vista avisos_processed usando los IDs filtrados
        # Mantenemos el ORDER BY para asegurar que el orden de los resultados de la vista coincida con el paginado
        query_vista_procesada = f'SELECT {columnas_seleccionadas_vista} FROM avisos_processed WHERE id IN ({placeholders}) ORDER BY fechapublicacion DESC, categoria, id'
        cursor.execute(query_vista_procesada, ids_para_pagina)
        
        columnas_db = [desc[0].lower() for desc in cursor.description]
        avisos = [dict(zip(columnas_db, row)) for row in cursor.fetchall()]

        # Opcional: Si el orden de la consulta IN no es garantizado por el motor de la BD
        # y necesitas el orden exacto de 'ids_para_pagina', puedes reordenar en Python:
        # avisos.sort(key=lambda x: ids_para_pagina.index(x['id']))
        
    conn.close()

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
    columnas_seleccionadas_resumen = "fecha, texto_normal_html, texto_criollo_html, resumen_plano, modelo"
    # Esta consulta ya filtra por fecha, lo cual es eficiente para la vista. No se modifica.
    cursor.execute(f'SELECT {columnas_seleccionadas_resumen} FROM resumenes_diarios_processed WHERE fecha = %s', (fecha,))
    resultado = cursor.fetchone()
    
    columnas_db = [desc[0].lower() for desc in cursor.description]
    conn.close()

    if not resultado:
        return render_template('resumendiario.html',
            resumen_diario="No hay resumen disponible para esta fecha.",
            resumen_diario_criollo="",
            fecha_actual=fecha.strftime("%Y-%m-%d"),
            fecha_actualizacion=None,
            modelo="No especificado",
            resumen_plano=""
        )

    fila = dict(zip(columnas_db, resultado))

    return render_template('resumendiario.html',
        resumen_diario=Markup(fila['texto_normal_html']),
        resumen_diario_criollo=Markup(fila['texto_criollo_html']),
        resumen_plano=fila.get('resumen_plano', ''),
        fecha_actual=fecha.strftime("%Y-%m-%d"),
        fecha_actualizacion=fila['fecha'].strftime('%Y-%m-%dT%H:%M:%SZ') if fila['fecha'] else None,
        modelo=fila['modelo'] if fila['modelo'] else "No especificado"
    )

@app.route('/aviso/<int:id>')
def mostrar_aviso(id):
    conn = obtener_conexion()
    cursor = conn.cursor()
    
    columnas_seleccionadas = "id, titulo, texto, textoresumido, textoresumidocorto, textoresumidolargo, " \
                             "titulotecnico, titulocriollo, textoresumidocriollocorto, textoresumidocriollolargo, " \
                             "enlace, fechapublicacion, categoria, modelo, timestamp"
    # Esta consulta ya filtra por ID, lo cual es eficiente para la vista. No se modifica.
    cursor.execute(f'SELECT {columnas_seleccionadas} FROM avisos_processed WHERE id = %s', (id,))
    resultado = cursor.fetchone()
    
    columnas_db = [desc[0].lower() for desc in cursor.description]
    conn.close()

    if not resultado:
        return "Aviso no encontrado", 404

    aviso_dict = dict(zip(columnas_db, resultado))
    
    aviso_dict['textoresumidocorto'] = Markup(aviso_dict.get('textoresumidocorto', ''))
    aviso_dict['textoresumidolargo'] = Markup(aviso_dict.get('textoresumidolargo', ''))
    aviso_dict['textoresumidocriollocorto'] = Markup(aviso_dict.get('textoresumidocriollocorto', ''))
    aviso_dict['textoresumidocriollolargo'] = Markup(aviso_dict.get('textoresumidocriollolargo', ''))

    return render_template('aviso.html', aviso=aviso_dict)

cache = Cache(app, config={'CACHE_TYPE': 'SimpleCache', 'CACHE_DEFAULT_TIMEOUT': 60})

@app.route('/')
@app.route('/<int:pagina>')
@cache.cached(timeout=60, query_string=True)
def index(pagina=1):
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
        aviso['textoresumidocorto'] = Markup(aviso.get('textoresumidocorto', ''))
        aviso['textoresumidolargo'] = Markup(aviso.get('textoresumidolargo', ''))
        aviso['textoresumidocriollocorto'] = Markup(aviso.get('textoresumidocriollocorto', ''))
        aviso['textoresumidocriollolargo'] = Markup(aviso.get('textoresumidocriollolargo', ''))
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
