from transformers import pipeline
import asyncio
from concurrent.futures import ThreadPoolExecutor

class SentimentEngine:
    def __init__(self):
        # El modelo se carga UNA sola vez al iniciar la clase
        self.nlp = pipeline("sentiment-analysis", model="ProsusAI/finbert")
        self.executor = ThreadPoolExecutor(max_workers=2)

    def _inferir(self, headlines):
        return self.nlp(headlines)

    async def analyze(self, headlines):
        if not headlines:
            return "Neutral 🟡", 0.0
        
        # Ejecución asíncrona para no congelar el bot
        loop = asyncio.get_event_loop()
        resultados = await loop.run_in_executor(self.executor, self._inferir, headlines)
        
        puntaje_total = sum((res['score'] if res['label'] == 'positive' else -res['score']) for res in resultados)
        iss = round(puntaje_total / len(headlines), 2)
        
        estado = "Positivo 🟢" if iss > 0.15 else ("Negativo 🔴" if iss < -0.15 else "Neutral 🟡")
        return estado, iss

# Instancia global para usar en el bot
engine = SentimentEngine()
