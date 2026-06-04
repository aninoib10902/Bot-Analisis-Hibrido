import os
import html  
import logging
from dotenv import load_dotenv
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import Application, CommandHandler, ContextTypes
from db_manager import init_db, guardar_analisis
from deep_translator import GoogleTranslator

from data_fetcher import fetcher
from sentiment_analyzer import engine 

# Configuración de Logs
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

load_dotenv()
TOKEN = os.getenv('TELEGRAM_TOKEN')

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    mensaje = (
        "🤖 **Bienvenido al Asistente de Análisis Híbrido**\n\n"
        "Este bot es una herramienta de soporte decisional diseñada para inversores. "
        "Integramos análisis técnico y análisis de sentimiento mediante IA (FinBERT) "
        "para ofrecerte una visión completa del mercado.\n\n"
        "📈 **¿Cómo usarlo?**\n"
        "• Para analizar una acción, escribe: `/analizar [TICKER]` (Ej: `/analizar MSFT`)\n"
        "• ¿No sabes qué buscar? Escribe `/top` para ver las acciones más populares.\n\n"
        "🚀 **¡Empieza ahora mismo a explorar el mercado!**"
    )
    await update.message.reply_text(mensaje, parse_mode=ParseMode.MARKDOWN)

async def top_comando(update: Update, context: ContextTypes.DEFAULT_TYPE):
    top_tickers = [
        ("AAPL", "Apple"), ("MSFT", "Microsoft"), ("GOOGL", "Alphabet"),
        ("AMZN", "Amazon"), ("NVDA", "Nvidia"), ("TSLA", "Tesla"),
        ("META", "Meta"), ("BRK.B", "Berkshire Hathaway"), ("JPM", "JPMorgan"),
        ("V", "Visa"), ("JNJ", "Johnson & Johnson"), ("WMT", "Walmart")
    ]
    
    mensaje = "🔥 **Top Acciones Populares:**\n\n"
    for ticker, nombre in top_tickers:
        mensaje += f"• <code>/{ticker}</code> - {nombre}\n"
    
    mensaje += "\n💡 *Escribe el comando del ticker (ej: /MSFT) para analizar.*"
    await update.message.reply_text(mensaje, parse_mode=ParseMode.HTML)

async def analizar_comando(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("⚠️ Indica un ticker. Ej: /analizar MSFT")
        return

    ticker = context.args[0].upper()
    status_msg = await update.message.reply_text(f"🔍 Iniciando análisis híbrido para {ticker}...")
    
    try:
        # 1. Componente Gráfico
        chart_image = fetcher.generate_chart_image(ticker)
        if chart_image:
            await context.bot.send_photo(
                chat_id=update.effective_chat.id, 
                photo=chart_image,
                caption=f"Gráfica técnica para {ticker}."
            )

        # 2. Ingesta de Datos (Capa Analítica y de Texto)
        precio, rsi = fetcher.get_stock_data(ticker)
        noticias = fetcher.get_recent_news(ticker)

        # 3. Componente Cualitativo: Inferencia Semántica (FinBERT)
        textos_para_ia = [n.get('title', '') for n in noticias] if noticias else []
        estado_ia, sentiment_score = await engine.analyze(textos_para_ia)

        # =========================================================================
        # MOTOR DE CÁLCULO FORMAL: ÍNDICE DE SALUD SINTÉTICA (ISS)
        # =========================================================================
        # A. Normalización lineal del RSI al rango hibrido [-1, 1]
        rsi_norm = (rsi - 50) / 50 if rsi is not None else 0.0
        
        # B. Asignación de Pesos Paramétricos (W1 + W2 = 1)
        w1 = 0.5  # Peso asignado al Análisis de Sentimiento
        w2 = 0.5  # Peso asignado al Análisis Técnico
        
        # C. Combinación Lineal Determinista
        iss_score = (w1 * sentiment_score) + (w2 * rsi_norm)
        # =========================================================================

        # 4. Capa de Persistencia (Base de Datos)
        try:
            guardar_analisis(ticker, iss_score)
        except Exception as db_error:
            logger.error(f"Error BD: {db_error}")

        # 5. Lógica de Inversión Basada en el ISS Unificado
        status_tecnico = "SOBRECOMPRA ⚠️" if rsi and rsi >= 70 else ("SOBREVENTA ✅" if rsi and rsi <= 30 else "Neutral ⚖️")
        
        if iss_score > 0.15:
            conclusion = "🚀 Oportunidad: Índice de Salud Sintética (ISS) óptimo. Señal de entrada respaldada por el pipeline híbrido."
        elif iss_score < -0.15:
            conclusion = "📉 Riesgo: Índice de Salud Sintética (ISS) bajista. Alta probabilidad de corrección o presión vendedora."
        else:
            conclusion = "⏳ Mercado estable. El Índice de Salud Sintética (ISS) se mantiene en un rango de volatilidad neutral."

        # 6. Procesamiento de Titulares y Formateo HTML Sanitizado
        titulares_html = ""
        if noticias:
            for noticia in noticias[:3]:
                titulo_ingles = noticia.get('title', 'Sin título')
                link = noticia.get('link', '#')
                
                # Traducción del Titular Bursátil
                try:
                    titulo_espanol = str(GoogleTranslator(source='en', target='es').translate(titulo_ingles))
                except Exception as e:
                    logger.error(f"Error en traducción: {e}")
                    titulo_espanol = "Traducción no disponible"
                    
                # Sanitización para evitar quiebres en el ParseMode de Telegram
                titulo_en_seguro = html.escape(titulo_ingles)
                titulo_es_seguro = html.escape(titulo_espanol)
                
                titulares_html += f"• <a href='{link}'>{titulo_en_seguro}</a>\n   🇪🇸 <i>{titulo_es_seguro}</i>\n"
        else:
            titulares_html = "• No hay noticias disponibles para procesar.\n"

        # 7. Construcción de la Interfaz de Salida de Datos
        reporte = (
            f"📊 <b>REPORTE DE INGENIERÍA HÍBRIDA: {ticker}</b>\n"
            f"💵 Precio Spot: <code>${precio or 'N/A'}</code>\n\n"
            f"🧠 <b>COMPONENTES DEL MOTOR DE LÓGICA:</b>\n"
            f"• Sentimiento Semántico: <code>{round(sentiment_score, 4)}</code> ({estado_ia})\n"
            f"• Oscilador RSI Escalado: <code>{round(rsi_norm, 4)}</code>\n"
            f"• <b>Índice ISS Calculado:</b> <code>{round(iss_score, 4)}</code>\n\n"
            f"📰 <b>Estructura de Fuentes (RSS):</b>\n{titulares_html}\n"
            f"📈 <b>MÉTRICAS TÉCNICAS:</b>\nValor RSI Crudo: <code>{rsi or 'N/A'}</code> | Estado: {status_tecnico}\n\n"
            f"💡 <b>DIAGNÓSTICO DECISIONAL:</b>\n<i>{conclusion}</i>"
        )

        await update.message.reply_text(reporte, parse_mode=ParseMode.HTML)
        
        try:
            await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=status_msg.message_id)
        except:
            pass

    except Exception as e:
        logger.error(f"Error crítico procesando {ticker}: {e}")
        await update.message.reply_text("❌ Ocurrió un error crítico en el procesamiento del análisis.")

def main():
    logger.info("Iniciando bot profesional...")
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler('start', start_command))
    app.add_handler(CommandHandler('analizar', analizar_comando))
    app.add_handler(CommandHandler('top', top_comando))
    logger.info("Bot en línea. Escuchando peticiones desde la nube...")
    init_db()
    app.run_polling()

if __name__ == '__main__':
    main()