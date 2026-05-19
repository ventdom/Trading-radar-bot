import os
import requests
import time
import random
from datetime import datetime

# --- 1. SEGRETI (Presi da GitHub Actions) ---
TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
CHAT_ID = os.environ["CHAT_ID"]
GEMINI_API_KEY = os.environ["GEMINI_API_KEY"] # Il nuovo segreto

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

def chiedi_analisi_ai(ticker, id_seg, prezzo, var_perc, vol_molt, trend_txt, atr, corpo):
    """Interroga l'API di Gemini per un'analisi contestuale istantanea"""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
    
    # --- IL BOT ORA CONOSCE IL CALENDARIO ---
    giorno = datetime.utcnow().strftime("%A") # Es: Monday, Friday...
    ora_utc = datetime.utcnow().strftime("%H:%M") # Ora del server GitHub (UTC)
    
    prompt = (
        f"Sei un consulente esperto di Swing Trading quantitativo. "
        f"Contesto temporale attuale: Oggi è {giorno}, ore {ora_utc} UTC. (Nota: Wall Street apre alle 13:30 UTC e chiude alle 20:00 UTC). "
        f"Analizza questo segnale orario appena chiuso su {ticker}:\n"
        f"- Tipo Evento: {id_seg}\n"
        f"- Prezzo: {prezzo:.2f}$ ({var_perc:+.2f}%)\n"
        f"- Contesto Trend: {trend_txt}\n"
        f"- Anomalie Volume: {vol_molt:.1f}x la media\n"
        f"- Volatilità: Corpo candela {corpo:.2f}$ (Media ATR {atr:.2f}$)\n\n"
        f"Scrivi un breve e tagliente commento operativo (massimo 3 frasi). "
        f"Usa il giorno della settimana e l'orario per filtrare le false partenze (es. prese di profitto del venerdì, o alta volatilità di apertura). "
        f"Indica se è valido per lo swing o se è una trappola. Usa tono professionale."
    )
    
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    headers = {'Content-Type': 'application/json'}
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=12)
        response.raise_for_status()
        dati_ai = response.json()
        analisi = dati_ai['candidates'][0]['content']['parts'][0]['text'].strip()
        return analisi
    except Exception as e:
        print(f"[ERRORE AI] Impossibile generare analisi per {ticker}: {e}")
        return "Analisi AI temporaneamente non disponibile."


def analizza_mercati():
    print("Avvio analisi quantitativa con Motore AI Generativo...")
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

            # --- IL BATTITO CARDIACO DEL BOT (LOG SU SCHERMO) ---
            print(f"[{nome}] P: {prezzo_attuale:.2f} | SMA50: {sma_50:.2f} | Vol: {volume_attuale} (Media: {media_volume:.0f}) | ATR: {atr_14:.2f}")

            if media_volume > 0 and volume_attuale >= (media_volume * 1.5):
                id_seg = None
                
                if corpo_candela >= atr_14:
                    id_seg = "BREAKOUT VOLATILITÀ"
                elif (0.3 * atr_14) <= corpo_candela < atr_14 and volume_attuale >= (media_volume * 2.0):
                    id_seg = "SPINTA / COSTRUZIONE TREND"
                elif corpo_candela < (0.3 * atr_14) and volume_attuale >= (media_volume * 2.5):
                    id_seg = "ASSORBIMENTO ISTITUZIONALE"

                if id_seg:
                    distanza_sl = atr_14 * 2
                    distanza_tp = atr_14 * 4
                    
                    if var_perc > 0:
                        sl = prezzo_attuale - distanza_sl
                        tp = prezzo_attuale + distanza_tp
                    else:
                        sl = prezzo_attuale + distanza_sl
                        tp = prezzo_attuale - distanza_tp

                    is_in_trend = (var_perc > 0 and prezzo_attuale > sma_50) or (var_perc < 0 and prezzo_attuale < sma_50)
                    trend_txt = "🟢 A FAVORE DEL TREND" if is_in_trend else "⚠️ CONTRO-TREND"
                    sma_txt = "SOPRA SMA50" if prezzo_attuale > sma_50 else "SOTTO SMA50"
                    molt_vol = volume_attuale / media_volume

                    # --- CHIAMATA ALL'INTELLIGENZA ARTIFICIALE ---
                    commento_ai = chiedi_analisi_ai(
                        ticker=nome, 
                        id_seg=id_seg, 
                        prezzo=prezzo_attuale, 
                        var_perc=var_perc, 
                        vol_molt=molt_vol, 
                        trend_txt=f"{sma_txt} ({trend_txt})", 
                        atr=atr_14, 
                        corpo=corpo_candela
                    )

                    titolo_emo = "🚀" if var_perc > 0 else "🩸"
                    msg = (f"{titolo_emo} {id_seg}: {nome.upper()}\n"
                           f"Contesto: {sma_txt} | {trend_txt}\n"
                           f"Prezzo: {prezzo_attuale:.2f} $ ({var_perc:+.2f}%)\n"
                           f"Volume: {molt_vol:.1f}x media\n"
                           f"Volatilità: Corpo {corpo_candela:.2f}$ (ATR {atr_14:.2f}$)\n"
                           f"------------------------\n"
                           f"🎯 TARGET NETTO: {tp:.2f} $\n"
                           f"🛑 STOP LOSS: {sl:.2f} $\n"
                           f"------------------------\n"
                           f"🤖 ANALISI DELL'ESPERTO:\n{commento_ai}")
                    
                    invia_notifica(msg)
                
        except Exception as e:
            print(f"Errore su {nome}: {e}")
        
        # Pausa randomica per non sovraccaricare le API (Yahoo e Gemini)
        time.sleep(random.uniform(1.5, 3.0))

if __name__ == "__main__":
    analizza_mercati()
