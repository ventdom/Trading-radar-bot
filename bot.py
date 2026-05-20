import os
import requests
import time
import random
from datetime import datetime

# --- 1. SEGRETI (Presi da GitHub Actions) ---
TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
CHAT_ID = os.environ["CHAT_ID"]
GEMINI_API_KEY = os.environ["GEMINI_API_KEY"] 

# --- 2. PARAMETRI E TICKERS (Bilanciati a 20 Slot) ---
TICKERS = {
    "Nvidia": "NVDA", "Tesla": "TSLA", "TSMC": "TSM", "ASML": "ASML", 
    "AMD": "AMD", "Intel": "INTC", "Eli Lilly": "LLY", "Novo Nordisk": "NVO",
    "SuperMicro": "SMCI", "Palantir": "PLTR", "CrowdStrike": "CRWD", 
    "ARM": "ARM", "Coinbase": "COIN",
    "JPMorgan": "JPM", "Visa": "V", 
    "Walmart": "WMT", "Costco": "COST",
    "ExxonMobil": "XOM", "Caterpillar": "CAT", 
    "Lockheed": "LMT"
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

def chiedi_analisi_ai(ticker, id_seg, prezzo, var_perc, vol_molt, trend_txt, atr, corpo, dist_max, dist_min, giorni_utili):
    """Interroga l'API di Gemini con Orologio, Struttura Grafica e Calendario Utili"""
    # URL Aggiornato alla versione stabile (v1) e al modello 2.5 per annientare l'errore 404
    url = f"https://generativelanguage.googleapis.com/v1/models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}"
    
    # Il Bot è consapevole del tempo
    giorno = datetime.utcnow().strftime("%A")
    ora_utc = datetime.utcnow().strftime("%H:%M")
    
    # PROMPT INTATTO AL 100%
    prompt = (
        f"Sei un Risk Manager e consulente di Swing Trading quantitativo (no leva, hold 1-2 settimane). "
        f"Oggi è {giorno}, ore {ora_utc} UTC. (Wall Street apre alle 13:30 e chiude alle 20:00 UTC). "
        f"Valuta questo segnale su {ticker}:\n"
        f"- Segnale: {id_seg} a {prezzo:.2f}$ ({var_perc:+.2f}% oggi)\n"
        f"- Volume: {vol_molt:.1f}x la media\n"
        f"- Trend: {trend_txt}\n"
        f"- Volatilità: Corpo candela {corpo:.2f}$ (Media ATR {atr:.2f}$)\n"
        f"- Struttura Grafica: Distanza dal Massimo Mensile (Resistenza) {dist_max:.1f}%, dal Minimo (Supporto) {dist_min:.1f}%.\n"
        f"- Rischio Trimestrale: Mancano {giorni_utili} giorni alla pubblicazione degli utili.\n\n"
        f"Scrivi un breve e tagliente commento operativo (massimo 3 frasi). "
        f"Valuta il Rischio/Rendimento basandoti sulle resistenze. Usa giorno e ora per filtrare le false partenze o la FOMO. "
        f"Se mancano meno di 7 giorni agli utili (earnings), blocca categoricamente l'ingresso per rischio crollo."
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
        return "Analisi AI temporaneamente non disponibile a causa di un timeout di rete."

def analizza_mercati():
    print("Avvio analisi quantitativa con Motore AI Generativo Integrato...")
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
            
            # Dati della candela di segnale (quella appena chiusa)
            prezzo_attuale = chiusure[-2]
            prezzo_apertura = aperture[-2]
            massimo_candela = massimi[-2]  # <-- NUOVO: Massimo per Buy Stop
            minimo_candela = minimi[-2]    # <-- NUOVO: Minimo per Sell Stop
            volume_attuale = volumi[-2]
            
            media_volume = sum(volumi[-22:-2]) / 20
            sma_50 = sum(chiusure[-51:-1]) / 50  
            var_perc = ((prezzo_attuale - prezzo_apertura) / prezzo_apertura) * 100
            corpo_candela = abs(prezzo_attuale - prezzo_apertura)
            
            trs = [max(massimi[i]-minimi[i], abs(massimi[i]-chiusure[i-1]), abs(minimi[i]-chiusure[i-1])) for i in range(-15, -1)]
            atr_14 = sum(trs) / len(trs)

            # --- Calcolo Resistenze e Supporti ---
            massimo_mensile = max(massimi)
            minimo_mensile = min(minimi)
            distanza_massimo_perc = ((massimo_mensile - prezzo_attuale) / prezzo_attuale) * 100
            distanza_minimo_perc = ((prezzo_attuale - minimo_mensile) / prezzo_attuale) * 100

            # --- Filtro Dinamico di Apertura ---
            ora_utc = datetime.utcnow().hour
            offset_apertura = 1.0 if ora_utc in [14, 15] else 0.0
            
            soglia_breakout = 1.5 + offset_apertura
            soglia_spinta = 2.0 + offset_apertura
            soglia_assorbimento = 2.5 + offset_apertura

            # --- IL BATTITO CARDIACO DEL BOT (LOG SU SCHERMO INTATTO) ---
            print(f"[{nome}] P: {prezzo_attuale:.2f} | SMA50: {sma_50:.2f} | Vol: {volume_attuale} (Media: {media_volume:.0f}) | ATR: {atr_14:.2f}")

            if media_volume > 0 and volume_attuale >= (media_volume * soglia_breakout):
                id_seg = None
                
                if corpo_candela >= atr_14:
                    id_seg = "BREAKOUT VOLATILITÀ"
                elif (0.3 * atr_14) <= corpo_candela < atr_14 and volume_attuale >= (media_volume * soglia_spinta):
                    id_seg = "SPINTA / COSTRUZIONE TREND"
                elif corpo_candela < (0.3 * atr_14) and volume_attuale >= (media_volume * soglia_assorbimento):
                    id_seg = "ASSORBIMENTO ISTITUZIONALE"

                if id_seg:
                    # --- Filtro Multi-Timeframe (SMA 200 Daily) ---
                    url_daily = f"https://query2.finance.yahoo.com/v8/finance/chart/{ticker}?interval=1d&range=1y"
                    try:
                        time.sleep(1)
                        resp_daily = session.get(url_daily, timeout=5)
                        dati_daily = resp_daily.json()
                        chiusure_daily = dati_daily['chart']['result'][0]['indicators']['quote'][0]['close']
                        chiusure_daily = [c for c in chiusure_daily if c is not None]
                        
                        if len(chiusure_daily) >= 200:
                            sma_200_daily = sum(chiusure_daily[-200:]) / 200
                            
                            if var_perc > 0 and prezzo_attuale < sma_200_daily:
                                print(f"  └─ 🛑 SCARTATO: Falso Breakout Long (Prezzo {prezzo_attuale:.2f} sotto SMA200 Daily {sma_200_daily:.2f})")
                                continue 
                            elif var_perc < 0 and prezzo_attuale > sma_200_daily:
                                print(f"  └─ 🛑 SCARTATO: Falso Breakout Short (Prezzo {prezzo_attuale:.2f} sopra SMA200 Daily {sma_200_daily:.2f})")
                                continue
                    except Exception:
                        pass 

                    # --- CHIAMATA NINJA PER LE TRIMESTRALI ---
                    url_quote = f"https://query2.finance.yahoo.com/v7/finance/quote?symbols={ticker}"
                    try:
                        time.sleep(1) 
                        resp_quote = session.get(url_quote, timeout=5)
                        dati_quote = resp_quote.json()
                        earnings_ts = dati_quote.get("quoteResponse", {}).get("result", [{}])[0].get("earningsTimestamp")
                        
                        giorni_agli_utili = "Sconosciuti"
                        if earnings_ts:
                            giorni_agli_utili = int((earnings_ts - time.time()) / 86400)
                    except Exception:
                        giorni_agli_utili = "Non disponibili"
                        
                    # --- NUOVO: LOGICA INGRESSO IN CONFERMA ---
                    # Identifica il prezzo esatto a cui piazzare l'ordine pendente
                    if var_perc > 0:
                        prezzo_ingresso = massimo_candela
                        ordine_txt = f"🟢 BUY STOP (Long): {prezzo_ingresso:.2f} $"
                    else:
                        prezzo_ingresso = minimo_candela
                        ordine_txt = f"🔴 SELL STOP (Short): {prezzo_ingresso:.2f} $"

                    # SL e TP vengono calcolati partendo dal prezzo di ingresso effettivo
                    distanza_sl = atr_14 * 2
                    distanza_tp = atr_14 * 4
                    
                    if var_perc > 0:
                        sl = prezzo_ingresso - distanza_sl
                        tp = prezzo_ingresso + distanza_tp
                    else:
                        sl = prezzo_ingresso + distanza_sl
                        tp = prezzo_ingresso - distanza_tp

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
                        corpo=corpo_candela,
                        dist_max=distanza_massimo_perc,
                        dist_min=distanza_minimo_perc,
                        giorni_utili=giorni_agli_utili
                    )

                    # --- COSTRUZIONE NOTIFICA (Aggiornata con l'ordine in conferma) ---
                    titolo_emo = "🚀" if var_perc > 0 else "🩸"
                    msg = (f"{titolo_emo} {id_seg}: {nome.upper()}\n"
                           f"Contesto: {sma_txt} | {trend_txt}\n"
                           f"Prezzo Chiusura: {prezzo_attuale:.2f} $ ({var_perc:+.2f}%)\n"
                           f"Volume: {molt_vol:.1f}x media\n"
                           f"Volatilità: Corpo {corpo_candela:.2f}$ (ATR {atr_14:.2f}$)\n"
                           f"------------------------\n"
                           f"⏳ INGRESSO IN CONFERMA:\n"
                           f"{ordine_txt}\n"
                           f"🎯 TARGET NETTO: {tp:.2f} $\n"
                           f"🛑 STOP LOSS: {sl:.2f} $\n"
                           f"------------------------\n"
                           f"🤖 ANALISI DELL'ESPERTO:\n{commento_ai}")
                    
                    invia_notifica(msg)
                
        except Exception as e:
            print(f"Errore su {nome}: {e}")
        
        # Pausa randomica per non sovraccaricare le API
        time.sleep(random.uniform(1.5, 3.0))

if __name__ == "__main__":
    analizza_mercati()
