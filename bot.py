import os
import requests
import time
import random
from datetime import datetime

# --- 1. SEGRETI ---
TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
CHAT_ID = os.environ["CHAT_ID"]
GEMINI_API_KEY = os.environ["GEMINI_API_KEY"] 

# --- 2. IL MOTORE DI ROTAZIONE SETTORIALE (6 Settori, 15 Ticker l'uno) ---
SETTORI = {
    "XLK": { # TECH & SOFTWARE
        "nome_settore": "💻 TECH / SOFTWARE",
        "tickers": {
            "Microsoft": "MSFT", "Apple": "AAPL", "Salesforce": "CRM", "Adobe": "ADBE", 
            "Intuit": "INTU", "ServiceNow": "NOW", "Oracle": "ORCL", "Palo Alto": "PANW", 
            "Fortinet": "FTNT", "CrowdStrike": "CRWD", "Snowflake": "SNOW", "Datadog": "DDOG", 
            "Palantir": "PLTR", "Reddit": "RDDT", "Ibotta": "IBTA" 
        }
    },
    "SMH": { # AI & SEMICONDUTTORI
        "nome_settore": "🧠 AI & CHIP",
        "tickers": {
            "Nvidia": "NVDA", "AMD": "AMD", "TSMC": "TSM", "ASML": "ASML", 
            "Broadcom": "AVGO", "Qualcomm": "QCOM", "Texas Instr": "TXN", "Applied Mat": "AMAT", 
            "Micron": "MU", "Intel": "INTC", "ARM": "ARM", "SuperMicro": "SMCI", 
            "Astera Labs": "ALAB", "CoreWeave": "CRWV", "Marvell": "MRVL" 
        }
    },
    "XLF": { # BANCHE E FINANZA
        "nome_settore": "🏦 FINANZA",
        "tickers": {
            "JPMorgan": "JPM", "BofA": "BAC", "Wells Fargo": "WFC", "Citigroup": "C", 
            "Goldman Sachs": "GS", "Morgan Stanley": "MS", "Amex": "AXP", "Visa": "V", 
            "Mastercard": "MA", "BlackRock": "BLK", "S&P Global": "SPGI", "CME Group": "CME", 
            "Coinbase": "COIN", "MoneyLion": "MNY", "Robinhood": "HOOD"
        }
    },
    "XLE": { # ENERGIA E OIL
        "nome_settore": "🛢️ ENERGIA",
        "tickers": {
            "Exxon": "XOM", "Chevron": "CVX", "ConocoPhillips": "COP", "Schlumberger": "SLB", 
            "EOG Resources": "EOG", "Marathon": "MPC", "Pioneer": "PXD", "Valero": "VLO", 
            "Occidental": "OXY", "Hess": "HES", "Halliburton": "HAL", "Baker Hughes": "BKR", 
            "Williams": "WMB", "BKV Corp": "BKV", "TXO Partners": "TXO" 
        }
    },
    "ITA": { # DIFESA E AEROSPAZIO
        "nome_settore": "🪖 DIFESA E AEROSPAZIO",
        "tickers": {
            "Lockheed": "LMT", "RTX Corp": "RTX", "Northrop": "NOC", "Gen Dynamics": "GD", 
            "Boeing": "BA", "TransDigm": "TDG", "Heico": "HEI", "Howmet": "HWM", 
            "L3Harris": "LHX", "Textron": "TXT", "Moog": "MOG-A", "Spirit Aero": "SPR", 
            "Woodward": "WWD", "Loar Group": "LOAR", "PSQ Holdings": "PSQH" 
        }
    },
    "XBI": { # BIOTECH & HEALTH
        "nome_settore": "🧬 BIOTECH & HEALTH",
        "tickers": {
            "Eli Lilly": "LLY", "Novo Nordisk": "NVO", "UnitedHealth": "UNH", "J&J": "JNJ", 
            "Merck": "MRK", "AbbVie": "ABBV", "Thermo Fisher": "TMO", "Pfizer": "PFE", 
            "Amgen": "AMGN", "Gilead": "GILD", "Vertex": "VRTX", "Regeneron": "REGN", 
            "Illumina": "ILMN", "CG Oncology": "CGON", "Kyverna": "KYTX" 
        }
    }
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
            time.sleep(2)

def chiedi_analisi_ai(ticker, id_seg, prezzo, var_perc, vol_molt, trend_txt, atr, corpo, dist_max, dist_min, giorni_utili):
    url = f"https://generativelanguage.googleapis.com/v1/models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}"
    giorno = datetime.utcnow().strftime("%A")
    ora_utc = datetime.utcnow().strftime("%H:%M")
    
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
        return response.json()['candidates'][0]['content']['parts'][0]['text'].strip()
    except Exception as e:
        return "Analisi AI temporaneamente non disponibile a causa di un timeout di rete."

def identifica_settore_migliore(session):
    """Scansiona gli ETF e trova la forza basandosi ESCLUSIVAMENTE sulla chiusura del giorno precedente."""
    print("Analisi Rotazione Settoriale (Lettura chiusure giorno precedente)...")
    miglior_etf = None
    miglior_perf = -999.0
    
    for etf in SETTORI.keys():
        try:
            # Scarichiamo gli ultimi 5 giorni per sicurezza
            url = f"https://query2.finance.yahoo.com/v8/finance/chart/{etf}?interval=1d&range=5d"
            resp = session.get(url, timeout=5).json()
            chiusure = resp['chart']['result'][0]['indicators']['quote'][0]['close']
            
            # Filtriamo eventuali dati vuoti
            chiusure = [c for c in chiusure if c is not None]
            
            # LOGICA DI CALCOLO:
            # chiusure[-1] = Candela di oggi (Live, in formazione, da ignorare)
            # chiusure[-2] = Candela di ieri (Ultima sessione completata)
            # chiusure[-3] = Candela dell'altro ieri
            if len(chiusure) >= 3:
                c_ieri = chiusure[-2]
                c_altro_ieri = chiusure[-3]
                
                perf = ((c_ieri - c_altro_ieri) / c_altro_ieri) * 100
                print(f"ETF {etf} ({SETTORI[etf]['nome_settore']}): {perf:+.2f}%")
                
                if perf > miglior_perf:
                    miglior_perf = perf
                    miglior_etf = etf
        except Exception:
            pass
        time.sleep(1)
        
    print(f"\n=> SETTORE LEADER IDENTIFICATO (Su base ieri): {SETTORI[miglior_etf]['nome_settore']} ({miglior_etf})\n")
    return miglior_etf, miglior_perf

def analizza_mercati():
    session = requests.Session()
    session.headers.update({'User-Agent': 'Mozilla/5.0'})
    
    # 1. Trova il settore leader del giorno precedente
    etf_leader, perf_leader = identifica_settore_migliore(session)
    
    if not etf_leader:
        print("Errore nel recupero ETF. Esco.")
        return
        
    if perf_leader < -0.5:
        print("Il mercato sta crollando ovunque (Leader negativo). Pausa operativa per protezione capitale.")
        return 
        
    tickers_da_analizzare = SETTORI[etf_leader]["tickers"]
    print(f"Avvio analisi quantitativa oraria sui 15 ticker del settore {etf_leader}...")
    
    # 2. Scansiona SOLO i ticker del settore forte per l'operatività intraday/swing
    for nome, ticker in tickers_da_analizzare.items():
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
            massimo_candela = massimi[-2]  
            minimo_candela = minimi[-2]    
            volume_attuale = volumi[-2]
            
            media_volume = sum(volumi[-22:-2]) / 20
            sma_50 = sum(chiusure[-51:-1]) / 50  
            var_perc = ((prezzo_attuale - prezzo_apertura) / prezzo_apertura) * 100
            corpo_candela = abs(prezzo_attuale - prezzo_apertura)
            
            trs = [max(massimi[i]-minimi[i], abs(massimi[i]-chiusure[i-1]), abs(minimi[i]-chiusure[i-1])) for i in range(-15, -1)]
            atr_14 = sum(trs) / len(trs)

            massimo_mensile = max(massimi)
            minimo_mensile = min(minimi)
            distanza_massimo_perc = ((massimo_mensile - prezzo_attuale) / prezzo_attuale) * 100
            distanza_minimo_perc = ((prezzo_attuale - minimo_mensile) / prezzo_attuale) * 100

            ora_utc = datetime.utcnow().hour
            offset_apertura = 1.0 if ora_utc in [14, 15] else 0.0
            soglia_breakout = 1.5 + offset_apertura
            soglia_spinta = 2.0 + offset_apertura
            soglia_assorbimento = 2.5 + offset_apertura

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
                    url_daily = f"https://query2.finance.yahoo.com/v8/finance/chart/{ticker}?interval=1d&range=1y"
                    try:
                        time.sleep(1)
                        resp_daily = session.get(url_daily, timeout=5)
                        chiusure_daily = [c for c in resp_daily.json()['chart']['result'][0]['indicators']['quote'][0]['close'] if c is not None]
                        
                        if len(chiusure_daily) >= 200:
                            sma_200_daily = sum(chiusure_daily[-200:]) / 200
                            if var_perc > 0 and prezzo_attuale < sma_200_daily:
                                print(f"  └─ 🛑 SCARTATO: Contro Macro-Trend (Sotto SMA200)")
                                continue 
                            elif var_perc < 0 and prezzo_attuale > sma_200_daily:
                                continue
                    except Exception:
                        pass

                    url_quote = f"https://query2.finance.yahoo.com/v7/finance/quote?symbols={ticker}"
                    try:
                        time.sleep(1) 
                        earnings_ts = session.get(url_quote, timeout=5).json().get("quoteResponse", {}).get("result", [{}])[0].get("earningsTimestamp")
                        giorni_agli_utili = int((earnings_ts - time.time()) / 86400) if earnings_ts else "Sconosciuti"
                    except Exception:
                        giorni_agli_utili = "Non disponibili"
                        
                    if var_perc > 0:
                        prezzo_ingresso = massimo_candela
                        ordine_txt = f"🟢 BUY STOP (Long): {prezzo_ingresso:.2f} $"
                        sl = prezzo_ingresso - (atr_14 * 2)
                        tp = prezzo_ingresso + (atr_14 * 4)
                    else:
                        prezzo_ingresso = minimo_candela
                        ordine_txt = f"🔴 SELL STOP (Short): {prezzo_ingresso:.2f} $"
                        sl = prezzo_ingresso + (atr_14 * 2)
                        tp = prezzo_ingresso - (atr_14 * 4)

                    is_in_trend = (var_perc > 0 and prezzo_attuale > sma_50) or (var_perc < 0 and prezzo_attuale < sma_50)
                    trend_txt = "🟢 A FAVORE DEL TREND" if is_in_trend else "⚠️ CONTRO-TREND"
                    sma_txt = "SOPRA SMA50" if prezzo_attuale > sma_50 else "SOTTO SMA50"
                    molt_vol = volume_attuale / media_volume

                    commento_ai = chiedi_analisi_ai(
                        ticker=nome, id_seg=id_seg, prezzo=prezzo_attuale, var_perc=var_perc, 
                        vol_molt=molt_vol, trend_txt=f"{sma_txt} ({trend_txt})", atr=atr_14, 
                        corpo=corpo_candela, dist_max=distanza_massimo_perc, dist_min=distanza_minimo_perc, 
                        giorni_utili=giorni_agli_utili
                    )

                    titolo_emo = "🚀" if var_perc > 0 else "🩸"
                    msg = (f"{titolo_emo} {id_seg}: {nome.upper()}\n"
                           f"📊 Rotazione: {SETTORI[etf_leader]['nome_settore']}\n"
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
        time.sleep(random.uniform(1.5, 3.0))

if __name__ == "__main__":
    analizza_mercati()
