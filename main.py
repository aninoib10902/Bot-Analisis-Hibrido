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
        # 1. Gráfica
        chart_image = fetcher.generate_chart_image(ticker)
        if chart_image:
            await context.bot.send_photo(
                chat_id=update.effective_chat.id, 
                photo=chart_image,
                caption=f"Gráfica técnica para {ticker}."
            )

        # 2. Datos
        precio, rsi = fetcher.get_stock_data(ticker)
        noticias = fetcher.get_recent_news(ticker)

        # 3. FinBERT (SOLUCIÓN IA: Le damos solo los textos puros)
        textos_para_ia = [n.get('title', '') for n in noticias] if noticias else []
        estado_ia, iss_score = await engine.analyze(textos_para_ia)

        # 4. Persistencia
        try:
            guardar_analisis(ticker, iss_score)
        except Exception as db_error:
            logger.error(f"Error BD: {db_error}")

        # 5. Lógica de inversión
        status_tecnico = "SOBRECOMPRA ⚠️" if rsi and rsi >= 70 else ("SOBREVENTA ✅" if rsi and rsi <= 30 else "Neutral ⚖️")
        
        if iss_score > 0.10 and (rsi and rsi < 65):
            conclusion = "🚀 Oportunidad: Sentimiento positivo en zona técnica aceptable."
        elif iss_score < -0.10 and (rsi and rsi > 35):
            conclusion = "📉 Riesgo: Sentimiento negativo detectado."
        else:
            conclusion = "⏳ Mercado estable. Sin señales fuertes."

        # 6. Formateo HTML (SOLUCIÓN TELEGRAM: Sanitizamos y creamos el enlace)
        titulares_html = ""
        if noticias:
            for noticia in noticias[:3]:
                titulo_ingles = noticia.get('title', 'Sin título')
                link = noticia.get('link', '#')
                
                # Traducimos
                try:
                    # Forzamos la traducción a string simple
                    titulo_espanol = str(GoogleTranslator(source='en', target='es').translate(titulo_ingles))
                except Exception as e:
                    logger.error(f"Error en traducción: {e}")
                    titulo_espanol = "Traducción no disponible"
                    
                # Sanitizamos
                titulo_en_seguro = html.escape(titulo_ingles)
                titulo_es_seguro = html.escape(titulo_espanol)
                
                # CONSTRUCCIÓN FORZADA (Sin espacios extraños)
                titulares_html += f"• <a href='{link}'>{titulo_en_seguro}</a>\n🇪🇸 <i>{titulo_es_seguro}</i>\n"
        else:
            titulares_html = "• No hay noticias disponibles.\n"

        reporte = (
            f"📊 <b>REPORTE SINTÉTICO: {ticker}</b>\n"
            f"💵 Precio: <code>${precio or 'N/A'}</code>\n\n"
            f"🧠 <b>SENTIMIENTO (FinBERT):</b>\n"
            f"Score ISS: <code>{iss_score}</code> ({estado_ia})\n"
            f"📰 <b>Fuentes analizadas:</b>\n{titulares_html}\n"
            f"📈 <b>TÉCNICO:</b>\nValor: <code>{rsi or 'N/A'}</code> | Estado: {status_tecnico}\n\n"
            f"💡 <b>CONCLUSIÓN:</b> <i>{conclusion}</i>"
        )

        await update.message.reply_text(reporte, parse_mode=ParseMode.HTML)
        
        try:
            await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=status_msg.message_id)
        except:
            pass

    except Exception as e:
        logger.error(f"Error procesando {ticker}: {e}")
        await update.message.reply_text("❌ Ocurrió un error crítico en el procesamiento del análisis.")

def main():
    logger.info("Iniciando bot profesional...")
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler('start', start_command))
    app.add_handler(CommandHandler('analizar', analizar_comando))
    app.add_handler(CommandHandler('top', top_comando))
    logger.info("Bot en línea. Escuchando peticiones...")
    init_db()
    app.run_polling()

if __name__ == '__main__':
    main()