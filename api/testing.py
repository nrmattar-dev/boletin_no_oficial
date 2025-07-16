import os
import json
import time
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from http.server import BaseHTTPRequestHandler

# --- Mock de Clases y Funciones ---

class MockDatabaseHandler:
    """Simula operaciones de base de datos sin conectarse."""
    def __init__(self):
        self.avisos = []  # Almacenamiento en memoria para la simulación

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    def obtener_avisos_para_scraping(self, dias_atras: int) -> List[Dict]:
        """Simula la obtención de avisos para scraping."""
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

    def insertar_aviso(self, aviso: Dict) -> bool:
        """Simula la inserción de un aviso en la base de datos."""
        self.avisos.append(aviso)
        return True

    def obtener_avisos_para_resumir(self) -> List[Dict]:
        """Simula la obtención de avisos para resumir."""
        return self.avisos[-4:] if self.avisos else []

    def obtener_avisos_por_fecha(self, fecha: str) -> List[Dict]:
        """Simula la obtención de avisos por fecha."""
        return [aviso for aviso in self.avisos if aviso.get("FechaPublicacion") == fecha]

    def actualizar_resumen_aviso(self, aviso_id: int, resumen: str) -> bool:
        """Simula la actualización del resumen de un aviso."""
        for aviso in self.avisos:
            if aviso["Id"] == aviso_id:
                aviso["Resumen"] = resumen
                return True
        return False

    def insertar_resumen_diario(self, fecha: str, resumen: str) -> bool:
        """Simula la inserción de un resumen diario."""
        return True

class MockLLMService:
    """Simula la interacción con una API de LLM (Gemini/OpenRouter)."""
    def __init__(self, api_name: str, simulate_error: bool = False):
        self.api_name = api_name
        self.simulate_error = simulate_error

    def generate_summary(self, text: str) -> Optional[str]:
        """Simula la generación de un resumen."""
        if self.simulate_error:
            return None
        return f"Este es un resumen simulado del texto '{text[:50]}...' generado por {self.api_name}."

# --- Funciones de Simulación de Flujo ---

def simulate_obtener(db: MockDatabaseHandler, simulate_error: bool = False) -> bool:
    """Simula el proceso de scraping (Obtener.py)."""
    if simulate_error:
        return False

    for dias_atras in range(2):
        avisos = db.obtener_avisos_para_scraping(dias_atras)
        for aviso in avisos:
            if not db.insertar_aviso(aviso):
                return False
    return True

def simulate_resumir(db: MockDatabaseHandler, llm_service: MockLLMService, simulate_error: bool = False) -> bool:
    """Simula el proceso de resumir avisos individuales (Resumir.py)."""
    if simulate_error:
        return False

    avisos = db.obtener_avisos_para_resumir()
    for aviso in avisos:
        resumen = llm_service.generate_summary(aviso["Texto"])
        if not resumen:
            return False
        if not db.actualizar_resumen_aviso(aviso["Id"], resumen):
            return False
    return True

def simulate_resumir_dia(db: MockDatabaseHandler, llm_service: MockLLMService, simulate_error: bool = False) -> bool:
    """Simula el proceso de resumir el día (ResumirDia.py)."""
    if simulate_error:
        return False

    fecha = str(datetime.today().date())
    avisos = db.obtener_avisos_por_fecha(fecha)
    if not avisos:
        return False

    textos = [aviso["Texto"] for aviso in avisos]
    resumen_dia = llm_service.generate_summary("\n\n".join(textos))
    if not resumen_dia:
        return False

    return db.insertar_resumen_diario(fecha, resumen_dia)

# --- Handler para Vercel Serverless Function ---

class TestingHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        """Handle GET requests for testing endpoint"""
        try:
            # Parse query parameters
            query_params = {}
            if '?' in self.path:
                query_string = self.path.split('?')[1]
                query_params = dict(pair.split('=') for pair in query_string.split('&'))
            
            # Configuración de parámetros
            simulate_general_error = query_params.get("simulate_error", "false").lower() == "true"
            simulate_error_step = query_params.get("simulate_error_step")
            simulate_llm_error = query_params.get("simulate_llm_error", "false").lower() == "true"
            api_seleccionada = query_params.get("api_seleccionada", "GEMINI")

            # Ejecutar flujo de testing
            with MockDatabaseHandler() as db:
                # Paso 1: Simular Obtener.py
                success_obtener = simulate_obtener(db, simulate_general_error or simulate_error_step == 'obtener')
                
                if success_obtener:
                    # Paso 2: Simular Resumir.py
                    llm_service = MockLLMService(api_seleccionada, simulate_llm_error)
                    success_resumir = simulate_resumir(db, llm_service, simulate_general_error or simulate_error_step == 'resumir')
                    
                    if success_resumir:
                        # Paso 3: Simular ResumirDia.py
                        success_resumir_dia = simulate_resumir_dia(db, llm_service, simulate_general_error or simulate_error_step == 'resumir_dia')
                else:
                    success_resumir = None
                    success_resumir_dia = None
            
            # Preparar respuesta
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            
            response = {
                "status": "success",
                "results": {
                    "obtener": success_obtener,
                    "resumir": success_resumir if success_obtener else None,
                    "resumir_dia": success_resumir_dia if (success_obtener and success_resumir) else None
                },
                "parameters": {
                    "simulate_error": simulate_general_error,
                    "simulate_error_step": simulate_error_step,
                    "simulate_llm_error": simulate_llm_error,
                    "api_seleccionada": api_seleccionada
                }
            }
            
            self.wfile.write(json.dumps(response, ensure_ascii=False).encode('utf-8'))
            
        except Exception as e:
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(e)}, ensure_ascii=False).encode('utf-8'))

# Exportar el handler para Vercel
handler = TestingHandler