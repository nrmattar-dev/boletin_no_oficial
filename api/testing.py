import time
from datetime import datetime, timedelta
from typing import List, Dict, Optional

# --- Mock de Clases y Funciones ---

class MockDatabaseHandler:
    def __init__(self):
        print("MockDatabaseHandler: Inicializado.")

    def __enter__(self):
        print("MockDatabaseHandler: Contexto de DB abierto (simulado).")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        print("MockDatabaseHandler: Contexto de DB cerrado (simulado).")

    def obtener_avisos_para_scraping(self, dias_atras: int) -> List[Dict]:
        print(f"MockDatabaseHandler: Simulating fetching avisos for {dias_atras} days.")
        if dias_atras == 0:
            return [
                {"Id": 1001, "Título": "Título de Aviso 1 (Hoy)", "Texto": "Texto completo del aviso 1 hoy...", "Enlace": "http://example.com/aviso1_hoy", "FechaPublicacion": str(datetime.today().date())},
                {"Id": 1002, "Título": "Título de Aviso 2 (Hoy)", "Texto": "Texto completo del aviso 2 hoy...", "Enlace": "http://example.com/aviso2_hoy", "FechaPublicacion": str(datetime.today().date())}
            ]
        elif dias_atras == 1:
            ayer = (datetime.today() - timedelta(days=1)).date()
            return [
                {"Id": 999, "Título": "Título de Aviso A (Ayer)", "Texto": "Texto completo del aviso A ayer...", "Enlace": "http://example.com/avisoA_ayer", "FechaPublicacion": str(ayer)},
                {"Id": 1000, "Título": "Título de Aviso B (Ayer)", "Texto": "Texto completo del aviso B ayer...", "Enlace": "http://example.com/avisoB_ayer", "FechaPublicacion": str(ayer)}
            ]
        return []

    def insertar_aviso(self, aviso: Dict):
        print(f"MockDatabaseHandler: Simulating insert for Aviso ID {aviso.get('Id', 'N/A')}")
        return True

    def obtener_avisos_pendientes_resumir(self) -> List[Dict]:
        print("MockDatabaseHandler: Simulating fetching pending avisos.")
        return [
            {"Id": 2001, "Texto": "Texto largo para ser resumido por el LLM simulado..."},
            {"Id": 2002, "Texto": "Otro texto de ejemplo, suficientemente largo como para requerir resumen..."}
        ]

    def guardar_resumen(self, aviso_id: int, resumen: str, modelo: str):
        print(f"MockDatabaseHandler: Saving resumen for Aviso ID {aviso_id}, modelo {modelo}. Resumen: {resumen[:50]}...")

    def obtener_resumenes_del_dia(self, fecha: datetime) -> str:
        print(f"MockDatabaseHandler: Simulating fetching daily summaries for {fecha.date()}.")
        return f"Resumen simulado 1 para {fecha.date()}. Resumen simulado 2 para {fecha.date()}."

    def guardar_resumen_diario(self, fecha: datetime, resumen: str, modelo: str):
        print(f"MockDatabaseHandler: Saving daily resumen for {fecha.date()}, modelo {modelo}. Resumen: {resumen[:50]}...")

    def existe_resumen_para_fecha(self, fecha: datetime) -> bool:
        print(f"MockDatabaseHandler: Check if resumen exists for {fecha.date()} (always False).")
        return False


class MockLLMService:
    def __init__(self, api_name: str, simulate_error: bool = False):
        self.api_name = api_name
        self.simulate_error = simulate_error
        print(f"MockLLMService: Inicializado para {api_name}. Simulate Error: {simulate_error}")

    def generate_summary(self, text: str) -> Optional[str]:
        print(f"MockLLMService: Generating summary with {self.api_name}, text length: {len(text)}")
        if self.simulate_error:
            print("MockLLMService: 💥 Simulating LLM Error!")
            return None
        return f"Resumen simulado generado por {self.api_name}: '{text[:50]}...'"


# --- Simulaciones ---

def simulate_obtener(db: MockDatabaseHandler, simulate_error: bool = False) -> bool:
    print("\n--- SIMULANDO OBTENER.PY ---")
    if simulate_error:
        print("Error simulado en Obtener.")
        return False

    for dias in range(2):
        avisos = db.obtener_avisos_para_scraping(dias)
        for aviso in avisos:
            if not db.insertar_aviso(aviso):
                print(f"Error simulando insertar aviso ID {aviso['Id']}")
                return False
            print(f"Aviso '{aviso['Título'][:30]}...' procesado.")
            time.sleep(0.05)
    return True


def simulate_resumir(db: MockDatabaseHandler, llm: MockLLMService, simulate_error: bool = False) -> bool:
    print("\n--- SIMULANDO RESUMIR.PY ---")
    if simulate_error:
        print("Error simulado en Resumir.")
        return False

    avisos = db.obtener_avisos_pendientes_resumir()
    for aviso in avisos:
        resumen = llm.generate_summary(aviso["Texto"])
        if resumen:
            db.guardar_resumen(aviso["Id"], resumen, llm.api_name)
        else:
            print(f"Error generando resumen para Aviso ID {aviso['Id']}")
            return False
        time.sleep(0.05)
    return True


def simulate_resumir_dia(db: MockDatabaseHandler, llm: MockLLMService, simulate_error: bool = False) -> bool:
    print("\n--- SIMULANDO RESUMIR_DIA.PY ---")
    if simulate_error:
        print("Error simulado en ResumirDia.")
        return False

    hoy = datetime.today()
    if db.existe_resumen_para_fecha(hoy):
        print("Resumen diario ya existe. Omitiendo.")
        return True

    contenido = db.obtener_resumenes_del_dia(hoy)
    if not contenido:
        print("No hay contenido para resumen diario.")
        return True

    resumen = llm.generate_summary(contenido)
    if resumen:
        db.guardar_resumen_diario(hoy, resumen, llm.api_name)
    else:
        print("Error generando resumen diario.")
        return False
    return True


# --- Handler para Vercel Serverless ---

async def handler(req, res):
    print("--- FUNCION SERVERLESS INICIADA ---")

    query = req.query or {}
    simulate_general_error = query.get("simulate_error", "false").lower() == "true"
    simulate_error_step = query.get("simulate_error_step")
    simulate_llm_error = query.get("simulate_llm_error", "false").lower() == "true"
    api_seleccionada = query.get("api_seleccionada", "GEMINI")

    with MockDatabaseHandler() as db:
        # Paso 1: Obtener
        if simulate_general_error or simulate_error_step == "obtener":
            if not simulate_obtener(db, simulate_error=True):
                return res.status(500).json({"error": "Fallo en Obtener."})
        else:
            if not simulate_obtener(db):
                return res.status(500).json({"error": "Fallo inesperado en Obtener."})

        # Paso 2: Resumir individual
        llm = MockLLMService(api_seleccionada, simulate_error=simulate_llm_error)
        if simulate_general_error or simulate_error_step == "resumir":
            if not simulate_resumir(db, llm, simulate_error=True):
                return res.status(500).json({"error": "Fallo en Resumir."})
        else:
            if not simulate_resumir(db, llm):
                return res.status(500).json({"error": "Fallo inesperado en Resumir."})

        # Paso 3: Resumen diario
        llm_dia = MockLLMService(api_seleccionada, simulate_error=simulate_llm_error)
        if simulate_general_error or simulate_error_step == "resumir_dia":
            if not simulate_resumir_dia(db, llm_dia, simulate_error=True):
                return res.status(500).json({"error": "Fallo en ResumirDia."})
        else:
            if not simulate_resumir_dia(db, llm_dia):
                return res.status(500).json({"error": "Fallo inesperado en ResumirDia."})

    print("--- PROCESO COMPLETADO CON ÉXITO ---")
    return res.status(200).json({"message": "Flujo de prueba completado exitosamente."})