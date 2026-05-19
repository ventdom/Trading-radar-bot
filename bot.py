import os
import requests
import time
import random

# --- 1. SEGRETI ---
TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
CHAT_ID = os.environ["CHAT_ID"]

# --- 2. PARAMETRI E TICKERS ---
TICKERS = {
    "Nvidia": "NVDA", "Tesla": "TSLA", "TSMC": "TSM", "ASML": "ASML", 
    "AMD": "AMD", "Intel": "INTC", "Eli Lilly": "LLY", "Novo Nordisk": "NVO",
    "SuperMicro": "SMCI", "Palantir": "PLTR", "CrowdStrike": "CRWD", 
    "ARM": "ARM", "Coinbase": "COIN"
}

def invia_notifica(messaggio, tentativi=3):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    dati = {"chat_id": CHAT_ID, "text": messaggio}
    for tentativo in range(tentativi):
        try:
            response = requests.post(url, data=dati, timeout=10)
            response.raise_for_status() 
            return 
        except Exception as e:
            print(f"[ERRORE TELEGRAM] {e}")
            time.sleep(2)

def analizza_mercati():
    print("Avvio analisi quantitativa con Consulente Integrato...")
    session = requests.Session()
    session.headers.update({'User-Agent': 'Mozilla/5.0'})
    
    for nome, ticker in TICKERS.items():
        try:
            url = f"https://query2.finance.yahoo.com/v8/finance/chart/{ticker}?interval=1h&range=1mo"
            response = session.get(url, timeout=10)
            if response.status_code != 200: continue
            
            dati = response.json()
            if not dati.get('chart', {}).get('result'): continue
            
            risultato = dati['chart']['result'][0]
            quote = risultato['indicators']['quote'][0]
            
            chiusure, aperture, volumi, massimi, minimi = [], [], [], [], []
            for i in range(len(quote['close'])):
                c, o, v, h, l = quote['close'][i], quote['open'][i], quote['volume'][i], quote['high'][i], quote['low'][i]
                if None not in (c, o, v, h, l):
                    chiusure.append(c); aperture.append(o); volumi.append(v); massimi.append(h); minimi.append(l)
            
            if len(chiusure) < 52: continue
            
            prezzo_attuale = chiusure[-2]
            prezzo_apertura = aperture[-2]
            volume_attuale = volumi[-2]
            media_volume = sum(volumi[-22:-2]) / 20
            sma_50 = sum(chiusure[-51:-1]) / 50  
            var_perc = ((prezzo_attuale - prezzo_apertura) / prezzo_apertura) * 100
            corpo_candela = abs(prezzo_attuale - prezzo_apertura)
            
            trs = [max(massimi[i]-minimi[i], abs(massimi[i]-chiusure[i-1]), abs(minimi[i]-chiusure[i-1])) for i in range(-15, -1)]
            atr_14 = sum(trs) / len(trs)

            # --- RIPRISTINO DELLA STAMPA A SCHERMO (LOGGING TERMINALE) ---
            print(f"[{nome}] P: {prezzo_attuale:.2f} | SMA50: {sma_50:.2f} | Vol: {volume_attuale} (Media: {media_volume:.0f}) | ATR: {atr_14:.2f}")

            if media_volume > 0 and volume_attuale >= (media_volume * 1.5):
                id_seg = None
                
                if corpo_candela >= atr_14:
                    id_seg = "BREAKOUT"
                elif (0.3 * atr_14) <= corpo_candela < atr_14 and volume_attuale >= (media_volume * 2.0):
                    id_seg = "SPINTA"
                elif corpo_candela < (0.3 * atr_14) and volume_attuale >= (media_volume * 2.5):
                    id_seg = "ASSORBIMENTO"

                if id_seg:
                    distanza_sl = atr_14 * 2
                    distanza_tp = atr_14 * 4
                    
                    if var_perc > 0:
                        sl = prezzo_attuale - distanza_sl
                        tp = prezzo_attuale + distanza_tp
                        direzione_movimento = "RIALZISTA"
                    else:
                        sl = prezzo_attuale + distanza_sl
                        tp = prezzo_attuale - distanza_tp
                        direzione_movimento = "RIBASSISTA"

                    is_in_trend = (var_perc > 0 and prezzo_attuale > sma_50) or (var_perc < 0 and prezzo_attuale < sma_50)
                    trend_txt = "🟢 IN TREND" if is_in_trend else "⚠️ CONTRO-TREND"
                    sma_txt = "SOPRA SMA50" if prezzo_attuale > sma_50 else "SOTTO SMA50"

                    # --- MOTORE DI ANALISI E STRATEGIA OPERATIVA ---
                    commento = ""
                    if id_seg == "BREAKOUT":
                        titolo_notifica = "🚀 BREAKOUT VOLATILITÀ" if var_perc > 0 else "🩸 CROLLO STRUTTURALE"
                        if is_in_trend:
                            commento = "Spinta forte. Non inseguire il prezzo (FOMO). Inserisci ordine LIMIT a metà di questa candela oraria per sfruttare un pullback."
                        else:
                            commento = "Movimento violento ma contro la SMA50. Alta probabilità di Trappola (Bull/Bear Trap). Si raccomanda di restare fermi."
                            
                    elif id_seg == "SPINTA":
                        titolo_notifica = "↗️ SPINTA RIALZISTA" if var_perc > 0 else "↘️ PRESSIONE RIBASSISTA"
                        if is_in_trend:
                            commento = "🔥 SETUP IDEALE SWING. Accumulo istituzionale silenzioso (prezzo controllato, volumi doppi). Ottima area per iniziare la posizione."
                        else:
                            commento = "Semplice ritracciamento tecnico di breve. Non aprire posizioni contro il trend macro di fondo."
                            
                    elif id_seg == "ASSORBIMENTO":
                        titolo_notifica = "🕵️‍♂️ SOSPETTO ASSORBIMENTO"
                        commento = "Mani forti presenti con ordini limite passivi. NON entrare subito. Inserisci il ticker in Watchlist e aspetta la rottura oraria del massimo/minimo attuale."

                    msg = (f"{titolo_notifica}: {nome.upper()}\n"
                           f"Contesto: {sma_txt} | {trend_txt}\n"
                           f"Prezzo: {prezzo_attuale:.2f} $ ({var_perc:+.2f}%)\n"
                           f"Volume: {volume_attuale/media_volume:.1f}x media\n"
                           f"Volatilità: Corpo {corpo_candela:.2f}$ (ATR {atr_14:.2f}$)\n"
                           f"------------------------\n"
                           f"🎯 TARGET NETTO: {tp:.2f} $\n"
                           f"🛑 STOP LOSS: {sl:.2f} $\n"
                           f"------------------------\n"
                           f"📌 NOTA CONSULENTE:\n{commento}")
                    
                    invia_notifica(msg)
                
        except Exception as e:
            print(f"Errore su {nome}: {e}")
        
        time.sleep(random.uniform(1.0, 2.5))

if __name__ == "__main__":
    analizza_mercati()
