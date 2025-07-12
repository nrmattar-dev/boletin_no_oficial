import os
import json
import time
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from http.server import BaseHTTPRequestHandler

# --- Mock de Clases y Funciones (No se conectan a DB real ni a APIs reales) ---

class MockDatabaseHandler:
    """Simula operaciones de base de datos sin conectarse."""
    def __init__(self):
        print("MockDatabaseHandler: Inicializado.")

    def __enter__(self):
        print("MockDatabaseHandler: Contexto de DB abierto (simulado).")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        print("MockDatabaseHandler: Contexto de DB cerrado (simulado).")

    def obtener_avisos_para_scraping(self, dias_atras: int) -> List[Dict]:
        """Simula la obtención de avisos para scraping."""
        print(f"MockDatabaseHandler: Simulating fetching avisos for {dias_atras} days.")
        # Devuelve datos dummy
        if dias_atras == 0: # Hoy
            return [
                {"Id": 1001, "Título": "Título de Aviso 1 (Scraping Hoy)", "Texto": "Texto completo del aviso 1 hoy...", "Enlace": "http://example.com/aviso1_hoy", "FechaPublicacion": str(datetime.today().date())},
                {"Id": 1002, "Título": "Título de Aviso 2 (Scraping Hoy)", "Texto": "Texto completo del aviso 2 hoy...", "Enlace": "http://example.com/aviso2_hoy", "FechaPublicacion": str(datetime.today().date())}
            ]
        elif dias_atras == 1: # Ayer
            ayer = (datetime.today() - timedelta(days=1)).date()
            return [
                {"Id": 999, "Título": "Título de Aviso A (Scraping Ayer)", "Texto": "Texto completo del aviso A ayer...", "Enlace": "http://example.com/avisoA_ayer", "FechaPublicacion": str(ayer)},
                {"Id": 1000, "Título": "Título de Aviso B (Scraping Ayer)", "Texto": "Texto completo del aviso B ayer...", "Enlace": "http://example.com/avisoB_ayer", "FechaPublicacion": str(ayer)}
            ]
        return []

    def insertar_aviso(self, aviso: Dict):
        """Simula la inserción de un aviso."""
        print(f"MockDatabaseHandler: Simulating insert for Aviso ID {aviso.get('Id', 'N/A')}")
        # No hace nada, solo loggea
        return True # Simula éxito

    def obtener_avisos_pendientes_resumir(self) -> List[Dict]:
        """Simula la obtención de avisos pendientes de resumir."""
        print("MockDatabaseHandler: Simulating fetching pending avisos for summary.")
        # Devuelve algunos avisos con texto para resumir
        return [
            {"Id": 2001, "Texto": "Este es un texto largo para ser resumido por el LLM simulado. Contiene mucha información relevante y algunos detalles que deberían ser compactados en un resumen conciso."},
            {"Id": 2002, "Texto": "Otro texto de ejemplo, quizás un poco más corto, pero aún lo suficientemente largo como para requerir un resumen. La idea es simular el proceso real."},
        ]

    def guardar_resumen(self, aviso_id: int, resumen: str, modelo: str):
        """Simula el guardado de un resumen."""
        print(f"MockDatabaseHandler: Simulating saving summary for Aviso ID {aviso_id} with model {modelo}. Summary: {resumen[:50]}...")

    def obtener_resumenes_del_dia(self, fecha: datetime) -> str:
        """Simula la obtención de resúmenes de un día."""
        print(f"MockDatabaseHandler: Simulating fetching daily summaries for {fecha.date()}.")
        # Devuelve un string concatenado de resúmenes simulados
        return f"Resumen simulado 1 para {fecha.date()}. Resumen simulado 2 para {fecha.date()}. Resumen simulado 3 para {fecha.date()}."

    def guardar_resumen_diario(self, fecha: datetime, resumen: str, modelo: str):
        """Simula el guardado del resumen diario."""
        print(f"MockDatabaseHandler: Simulating saving daily summary for {fecha.date()} with model {modelo}. Summary: {resumen[:50]}...")

    def existe_resumen_para_fecha(self, fecha: datetime) -> bool:
        """Simula si ya existe un resumen diario para la fecha."""
        print(f"MockDatabaseHandler: Simulating check for existing daily summary for {fecha.date()}. Always returns False.")
        return False


class MockLLMService:
    """Simula la interacción con una API de LLM (Gemini/OpenRouter)."""
    def __init__(self, api_name: str, simulate_error: bool = False):
        self.api_name = api_name
        self.simulate_error = simulate_error
        print(f"MockLLMService: Inicializado para {api_name}. Simulate Error: {simulate_error}")

    def generate_summary(self, text: str) -> Optional[str]:
        """Simula la generación de un resumen."""
        print(f"MockLLMService: Simulating summary generation using {self.api_name} for text length {len(text)}.")
        if self.simulate_error:
            print("MockLLMService: 💥 SIMULATING LLM ERROR!")
            return None
        
        # Devuelve un resumen simulado
        return f"Este es un resumen simulado del texto '{text[:50]}...' generado por {self.api_name}."

# --- Funciones de Simulación de Flujo ---

def simulate_obtener(db: MockDatabaseHandler, simulate_error: bool = False) -> bool:
    """Simula el proceso de scraping (Obtener.py)."""
    print("\n--- SIMULATING OBTENER.PY ---")
    if simulate_error:
        print("SIMULATING OBTENER.PY: 💥 ERROR AL INICIAR EL SCRAPING.")
        return False

    print("Simulating scraping process.")
    # Simular la obtención de datos para hoy y ayer
    for dias_atras in range(2): # 0 para hoy, 1 para ayer
        avisos = db.obtener_avisos_para_scraping(dias_atras)
        if not avisos:
            print(f"Simulating Obtener: No new avisos for day {dias_atras}.")
            continue
        
        for aviso in avisos:
            if not db.insertar_aviso(aviso):
                print(f"Simulating Obtener: Failed to 'insert' aviso {aviso['Id']}.")
                return False # Simula fallo si la inserción falla
            print(f"Simulating Obtener: Aviso '{aviso['Título'][:30]}...' 'processed'.")
            time.sleep(0.1) # Pequeña pausa simulada

    print("--- OBTENER.PY SIMULATION COMPLETE ---")
    return True

def simulate_resumir(db: MockDatabaseHandler, llm_service: MockLLMService, simulate_error: bool = False) -> bool:
    """Simula el proceso de resumen individual (Resumir.py)."""
    print("\n--- SIMULATING RESUMIR.PY ---")
    if simulate_error:
        print("SIMULATING RESUMIR.PY: 💥 ERROR AL INICIAR EL RESUMEN INDIVIDUAL.")
        return False

    print("Simulating individual summary process.")
    avisos_pendientes = db.obtener_avisos_pendientes_resumir()
    if not avisos_pendientes:
        print("Simulating Resumir: No pending avisos to summarize.")
        return True

    for aviso in avisos_pendientes:
        resumen = llm_service.generate_summary(aviso["Texto"])
        if resumen:
            db.guardar_resumen(aviso["Id"], resumen, llm_service.api_name)
            print(f"Simulating Resumir: Summary 'saved' for Aviso ID {aviso['Id']}.")
        else:
            print(f"Simulating Resumir: Failed to generate summary for Aviso ID {aviso['Id']}.")
            return False # Simula fallo si el resumen falla
        time.sleep(0.1) # Pequeña pausa simulada

    print("--- RESUMIR.PY SIMULATION COMPLETE ---")
    return True

def simulate_resumir_dia(db: MockDatabaseHandler, llm_service: MockLLMService, simulate_error: bool = False) -> bool:
    """Simula el proceso de resumen diario (ResumirDia.py)."""
    print("\n--- SIMULATING RESUMIR_DIA.PY ---")
    if simulate_error:
        print("SIMULATING RESUMIR_DIA.PY: 💥 ERROR AL INICIAR EL RESUMEN DIARIO.")
        return False

    print("Simulating daily summary process.")
    hoy = datetime.today()
    
    if db.existe_resumen_para_fecha(hoy):
        print("Simulating ResumirDia: Daily summary already 'exists' for today. Skipping.")
        return True
    
    contenido_del_dia = db.obtener_resumenes_del_dia(hoy)
    if not contenido_del_dia:
        print("Simulating ResumirDia: No content to summarize for today.")
        return True

    resumen_diario = llm_service.generate_summary(contenido_del_dia)
    if resumen_diario:
        db.guardar_resumen_diario(hoy, resumen_diario, llm_service.api_name)
        print("Simulating ResumirDia: Daily summary 'saved'.")
    else:
        print("Simulating ResumirDia: Failed to generate daily summary.")
        return False # Simula fallo si el resumen diario falla

    print("--- RESUMIR_DIA.PY SIMULATION COMPLETE ---")
    return True

# --- Handler para Vercel Serverless Function ---

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        """Handle GET requests as Vercel Serverless Function."""
        print("--- INICIANDO SCRIPT DE TESTING (Vercel Serverless Function) ---")
        
        # Parse query parameters
        query_params = {}
        if '?' in self.path:
            query_string = self.path.split('?')[1]
            query_params = dict(pair.split('=') for pair in query_string.split('&'))
        
        simulate_general_error = query_params.get("simulate_error", "false").lower() == "true"
        simulate_error_step = query_params.get("simulate_error_step") # 'obtener', 'resumir', 'resumir_dia'
        simulate_llm_error = query_params.get("simulate_llm_error", "false").lower() == "true"
        api_seleccionada = query_params.get("api_seleccionada", "GEMINI") # Para mock LLM

        # Iniciar la simulación con el manejador de base de datos mock
        with MockDatabaseHandler() as db:
            # Paso 1: Simular Obtener.py
            if simulate_general_error or simulate_error_step == 'obtener':
                print("TESTING: Flag 'simulate_error' o 'simulate_error_step=obtener' activado. Simulating Obtener.py with error.")
                success_obtener = simulate_obtener(db, simulate_error=True)
            else:
                print("TESTING: Simulating Obtener.py normally.")
                success_obtener = simulate_obtener(db)

            if not success_obtener:
                print("TESTING: Obtener.py simulation failed. Aborting.")
                self.send_response(500)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"error": "Testing failed: Obtener.py simulation had an error."}).encode())
                return
            
            # Paso 2: Simular Resumir.py
            llm_mock_resumir = MockLLMService(api_seleccionada, simulate_error=simulate_llm_error)
            if simulate_general_error or simulate_error_step == 'resumir':
                print("TESTING: Flag 'simulate_error' o 'simulate_error_step=resumir' activado. Simulating Resumir.py with error.")
                success_resumir = simulate_resumir(db, llm_mock_resumir, simulate_error=True)
            else:
                print("TESTING: Simulating Resumir.py normally.")
                success_resumir = simulate_resumir(db, llm_mock_resumir)

            if not success_resumir:
                print("TESTING: Resumir.py simulation failed. Aborting.")
                self.send_response(500)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"error": "Testing failed: Resumir.py simulation had an error."}).encode())
                return

            # Paso 3: Simular ResumirDia.py
            llm_mock_resumir_dia = MockLLMService(api_seleccionada, simulate_error=simulate_llm_error)
            if simulate_general_error or simulate_error_step == 'resumir_dia':
                print("TESTING: Flag 'simulate_error' o 'simulate_error_step=resumir_dia' activado. Simulating ResumirDia.py with error.")
                success_resumir_dia = simulate_resumir_dia(db, llm_mock_resumir_dia, simulate_error=True)
            else:
                print("TESTING: Simulating ResumirDia.py normally.")
                success_resumir_dia = simulate_resumir_dia(db, llm_mock_resumir_dia)
            
            if not success_resumir_dia:
                print("TESTING: ResumirDia.py simulation failed. Aborting.")
                self.send_response(500)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"error": "Testing failed: ResumirDia.py simulation had an error."}).encode())
                return

        print("\n--- SCRIPT DE TESTING COMPLETADO EXITOSAMENTE ---")
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps({"message": "Testing flow completed successfully."}).encode())

# Vercel requiere esta función para manejar las solicitudes
def vercel_handler(request):
    handler = Handler(request, ('localhost', 8000), None)
    handler.do_GET()
    return handler