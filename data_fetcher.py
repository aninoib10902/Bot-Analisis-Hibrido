import yfinance as yf
import urllib.request
import xml.etree.ElementTree as ET
import pandas as pd
import mplfinance as mpf
import io

class DataFetcher:
    def __init__(self):
        pass

    def get_stock_data(self, ticker):
        try:
            stock = yf.Ticker(ticker)
            df = stock.history(period="6mo")
            if df.empty or len(df) < 14: return None, None
            
            change = df['Close'].diff()
            gain = change.clip(lower=0)
            loss = -change.clip(upper=0)
            avg_gain = gain.ewm(com=13, adjust=False).mean()
            avg_loss = loss.ewm(com=13, adjust=False).mean()
            rs = avg_gain / avg_loss
            rsi = 100 - (100 / (1 + rs))
            return round(df['Close'].iloc[-1], 2), round(rsi.iloc[-1], 2)
        except: return None, None

    def get_recent_news(self, ticker):
        """Extrae titulares y URLs en formato diccionario."""
        try:
            url = f"https://feeds.finance.yahoo.com/rss/2.0/headline?s={ticker}&region=US&lang=en-US"
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req) as response: xml_data = response.read()
            root = ET.fromstring(xml_data)
            
            noticias = []
            for item in root.findall('.//item')[:10]:
                titulo = item.find('title').text if item.find('title') is not None else "Sin título"
                link = item.find('link').text if item.find('link') is not None else "#"
                # AHORA DEVUELVE EL DICCIONARIO COMPLETO
                noticias.append({'title': titulo, 'link': link})
            return noticias
        except: return []

    def generate_chart_image(self, ticker):
        try:
            stock = yf.Ticker(ticker)
            df = stock.history(period="6mo")
            if df.empty: return None

            image_buffer = io.BytesIO()
            mc = mpf.make_marketcolors(base_mpf_style='yahoo', up='g', down='r', inherit=True)
            s = mpf.make_mpf_style(base_mpf_style='nightclouds', marketcolors=mc)

            mpf.plot(df, type='candle', style=s, title=f'\n{ticker} (6 Meses)',
                     ylabel='Precio ($)', volume=True, ylabel_lower='Volumen',
                     savefig=dict(fname=image_buffer, dpi=100, bbox_inches='tight'))
            
            image_buffer.seek(0)
            return image_buffer
        except Exception as e:
            return None

fetcher = DataFetcher()