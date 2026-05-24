import os
import requests
import json
import time
import random
from datetime import datetime
from bs4 import BeautifulSoup
import re


# --- 1. SEGRETI ---
TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
CHAT_ID = os.environ["CHAT_ID"]
GEMINI_API_KEY = os.environ["GEMINI_API_KEY"] 
FLASHALPHA_API_KEY = os.environ["FLASHALPHA_API_KEY"] # <-- Nuovo segreto per il GEX

# --- 2. IL MOTORE DI ROTAZIONE SETTORIALE (6 Settori, 15 Ticker l'uno con 2 IPO/High-Beta) ---
SETTORI = {
    "XLK": { # TECH & SOFTWARE
        "nome_settore": "💻 TECH / SOFTWARE",
        "tickers": {
            # Core (13): Alta liquidità e volatilità intra-settimanale
            "Microsoft": "MSFT", "Apple": "AAPL", "Salesforce": "CRM", "Adobe": "ADBE", 
            "ServiceNow": "NOW", "Oracle": "ORCL", "Palo Alto": "PANW", "CrowdStrike": "CRWD", 
            "Palantir": "PLTR", "Meta": "META", "Netflix": "NFLX", "Snowflake": "SNOW", "Datadog": "DDOG",
            # IPO/High-Beta Recenti (2)
            "Reddit": "RDDT", "Rubrik": "RBRK" 
        }
    },
    "SMH": { # AI & SEMICONDUTTORI
        "nome_settore": "🧠 AI & CHIP",
        "tickers": {
            # Core (13)
            "Nvidia": "NVDA", "AMD": "AMD", "TSMC": "TSM", "ASML": "ASML", 
            "Broadcom": "AVGO", "Qualcomm": "QCOM", "Applied Mat": "AMAT", "Intel": "INTC", 
            "Micron": "MU", "Texas Instr": "TXN", "Marvell": "MRVL", "Monolithic": "MPWR", "ARM": "ARM",
            # IPO/High-Beta Recenti (2)
            "Astera Labs": "ALAB", "CoreWeave": "CRWV" 
        }
    },
    "XLF": { # BANCHE E FINANZA
        "nome_settore": "🏦 FINANZA",
        "tickers": {
            # Core (13)
            "JPMorgan": "JPM", "BofA": "BAC", "Wells Fargo": "WFC", "Citigroup": "C", 
            "Goldman Sachs": "GS", "Morgan Stanley": "MS", "Visa": "V", "Mastercard": "MA", 
            "Coinbase": "COIN", "Robinhood": "HOOD", "SoFi": "SOFI", "Upstart": "UPST", "Affirm": "AFRM",
            # IPO/High-Beta Recenti (2)
            "Bowhead Specialty": "BOW", "MoneyLion": "MNY" 
        }
    },
    "XLE": { # ENERGIA E OIL
        "nome_settore": "🛢️ ENERGIA",
        "tickers": {
            # Core (13)
            "Exxon": "XOM", "Chevron": "CVX", "ConocoPhillips": "COP", "Schlumberger": "SLB", 
            "EOG Resources": "EOG", "Marathon": "MPC", "Occidental": "OXY", "Valero": "VLO", 
            "Williams": "WMB", "Halliburton": "HAL", "Pioneer": "PXD", "Hess": "HES", "Baker Hughes": "BKR",
            # IPO/High-Beta Recenti (2)
            "BKV Corp": "BKV", "TXO Partners": "TXO" 
        }
    },
    "ITA": { # DIFESA E AEROSPAZIO
        "nome_settore": "🪖 DIFESA E AEROSPAZIO",
        "tickers": {
            # Core (13)
            "Lockheed": "LMT", "RTX Corp": "RTX", "Northrop": "NOC", "Gen Dynamics": "GD", 
            "Boeing": "BA", "TransDigm": "TDG", "Heico": "HEI", "L3Harris": "LHX", 
            "Textron": "TXT", "Howmet": "HWM", "Spirit Aero": "SPR", "Woodward": "WWD", "Moog": "MOG-A",
            # IPO/High-Beta Recenti (2)
            "Loar Group": "LOAR", "AST SpaceMobile": "ASTS" 
        }
    },
    "XBI": { # BIOTECH & HEALTH
        "nome_settore": "🧬 BIOTECH & HEALTH",
        "tickers": {
            # Core (13)
            "Eli Lilly": "LLY", "Novo Nordisk": "NVO", "UnitedHealth": "UNH", "J&J": "JNJ", 
            "Merck": "MRK", "AbbVie": "ABBV", "Pfizer": "PFE", "Vertex": "VRTX", 
            "Amgen": "AMGN", "Gilead": "GILD", "Regeneron": "REGN", "Intuitive Surg": "ISRG", "CRISPR": "CRSP",
            # IPO/High-Beta Recenti (2)
            "CG Oncology": "CGON", "Kyverna": "KYTX" 
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
        f"Oggi è {giorno}, ore {ora_utc} UTC.\n"
        f"Contesto Macro (S&P500): Il Gamma Exposure (GEX) è {gex_val}M, Regime: {gex_regime}. "
        f"Se il GEX è Positivo, prediligi prese di beneficio rapide sulle resistenze. Se Negativo, tollera volatilità e allarga gli stop.\n\n"
        f"Valuta questo segnale su {ticker}:\n"
        f"- Segnale: {id_seg} a {prezzo:.2f}$ ({var_perc:+.2f}% oggi)\n"
        f"- Volume: {vol_molt:.1f}x la media\n"
        f"- Trend: {trend_txt}\n"
        f"- Volatilità: Corpo candela {corpo:.2f}$ (Media ATR {atr:.2f}$)\n"
        f"- Struttura Grafica: Distanza dal Massimo Mensile {dist_max:.1f}%, dal Minimo {dist_min:.1f}%.\n"
        f"- Utili: Mancano {giorni_utili} giorni.\n\n"
        f"Scrivi un commento operativo (max 3 frasi). Correla il setup del ticker al regime GEX attuale per validare il Rischio/Rendimento. "
        f"Se mancano meno di 7 giorni agli utili, blocca categoricamente l'ingresso."
    )
    
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    headers = {'Content-Type': 'application/json'}
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=20)
        response.raise_for_status()
        return response.json()['candidates'][0]['content']['parts'][0]['text'].strip()
    except Exception as e:
        return "Analisi AI temporaneamente non disponibile a causa di un timeout di rete."

def recupera_utili_sicuri(ticker, session):
    """Sistema di ridondanza dati: tenta Yahoo Finance, se fallisce usa Finviz."""
    # --- PIANO A: Yahoo Finance ---
    url_quote = f"https://query2.finance.yahoo.com/v7/finance/quote?symbols={ticker}"
    try:
        time.sleep(1) 
        resp = session.get(url_quote, timeout=5).json()
        earnings_ts = resp.get("quoteResponse", {}).get("result", [{}])[0].get("earningsTimestamp")
        if earnings_ts:
            return int((earnings_ts - time.time()) / 86400)
    except Exception:
        pass # Yahoo ha fallito o ha restituito un dato vuoto, passo al Piano B
        
    # --- PIANO B: Web Scraping su Finviz ---
    try:
        # Non aggiungo un print per non sporcare il tuo terminale pulito, agisce in background
        url_finviz = f"https://finviz.com/quote.ashx?t={ticker}"
        # Mascheriamo la chiamata per non farci bloccare dal firewall di Finviz
        headers_finviz = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        time.sleep(random.uniform(1.5, 2.5)) 
        
        resp_finviz = session.get(url_finviz, headers=headers_finviz, timeout=10)
        if resp_finviz.status_code == 200:
            soup = BeautifulSoup(resp_finviz.text, 'html.parser')
            # Cerca la cella che contiene il testo 'Earnings'
            td_earnings = soup.find('td', string=re.compile('Earnings'))
            if td_earnings:
                # Estrae il valore dalla cella a destra (es. "May 07 / amc")
                valore_data = td_earnings.find_next_sibling('td').text.strip()
                
                # Estrae solo il mese e il giorno tramite Regex (es. "May 07")
                match = re.search(r'([a-zA-Z]{3}\s\d{1,2})', valore_data)
                if match:
                    clean_date = match.group(1)
                    anno_corrente = datetime.utcnow().year
                    # Converte la stringa in una data matematica
                    data_utili = datetime.strptime(f"{clean_date} {anno_corrente}", "%b %d %Y")
                    giorni_mancanti = (data_utili - datetime.utcnow()).days
                    
                    # Correzione di fine anno: se la data è troppo vecchia (es. dicembre)
                    # e siamo a gennaio, sposta la data all'anno successivo
                    if giorni_mancanti < -300: 
                        data_utili = data_utili.replace(year=anno_corrente + 1)
                        giorni_mancanti = (data_utili - datetime.utcnow()).days
                        
                    return giorni_mancanti
    except Exception:
        pass
        
    # Se entrambi i piani falliscono in modo catastrofico
    return "Sconosciuti"

def identifica_settori_migliori(session):
    print("Analisi Rotazione Settoriale (Lettura chiusure giorno precedente)...")
    risultati_settori = []
    
    for etf in SETTORI.keys():
        try:
            url = f"https://query2.finance.yahoo.com/v8/finance/chart/{etf}?interval=1d&range=5d"
            resp = session.get(url, timeout=5).json()
            chiusure = resp['chart']['result'][0]['indicators']['quote'][0]['close']
            
            chiusure = [c for c in chiusure if c is not None]
            
            if len(chiusure) >= 3:
                c_ieri = chiusure[-2]
                c_altro_ieri = chiusure[-3]
                
                perf = ((c_ieri - c_altro_ieri) / c_altro_ieri) * 100
                print(f"ETF {etf} ({SETTORI[etf]['nome_settore']}): {perf:+.2f}%")
                risultati_settori.append((etf, perf))
        except Exception:
            pass
        time.sleep(1)
        
    risultati_settori.sort(key=lambda x: x[1], reverse=True)
    top_3 = risultati_settori[:3] if len(risultati_settori) >= 3 else risultati_settori
    
    if top_3:
        print("\n=> SETTORI LEADER IDENTIFICATI (Su base ieri):")
        for etf, perf in top_3:
            print(f"   - {SETTORI[etf]['nome_settore']} ({etf}) con {perf:+.2f}%")
    print()
    
    return top_3

def recupera_gex_sp500():
    """Recupera il GEX giornaliero: usa la cache locale se presente, altrimenti chiama l'API."""
    cache_file = "gex_cache.json"
    oggi_str = datetime.utcnow().strftime("%Y-%m-%d")
    
    # --- 1. LETTURA DALLA CACHE ---
    if os.path.exists(cache_file):
        try:
            with open(cache_file, "r") as f:
                cache = json.load(f)
                # Se la data nella cache è uguale a oggi, NON chiamare l'API
                if cache.get("data") == oggi_str:
                    print(f"✅ GEX recuperato dalla cache di oggi ({oggi_str}). Nessuna chiamata API consumata.")
                    return cache.get("gex_value"), cache.get("gex_regime")
        except Exception as e:
            print(f"⚠️ Errore lettura cache GEX, forzo chiamata API: {e}")

    # --- 2. CHIAMATA API (Solo 1 volta al giorno) ---
    print("🔄 Nessuna cache valida per oggi. Richiesta GEX a FlashAlpha in corso...")
    url_flashalpha = "https://lab.flashalpha.com/v1/gex?ticker=SPX"
    headers = {"X-Api-Key": FLASHALPHA_API_KEY}
    
    try:
        response = requests.get(url_flashalpha, headers=headers, timeout=10)
        response.raise_for_status()
        dati = response.json()
        
        gex_value = dati.get("gex_absolute", 0) 
        gex_regime = "POSITIVO (Bassa Volatilità/Mean Reversion)" if gex_value > 0 else "NEGATIVO (Alta Volatilità/Trend Esteso)"
        
        # --- 3. SALVATAGGIO NELLA CACHE ---
        with open(cache_file, "w") as f:
            json.dump({
                "data": oggi_str,
                "gex_value": gex_value,
                "gex_regime": gex_regime
            }, f)
            
        print("💾 Cache GEX aggiornata e salvata con successo.")
        return gex_value, gex_regime
        
    except Exception as e:
        print(f"❌ Errore recupero GEX API: {e}")
        # In caso di errore API, proviamo a usare la cache vecchia se esiste, altrimenti fallback neutro
        if os.path.exists(cache_file):
            with open(cache_file, "r") as f:
                old_cache = json.load(f)
                print("⚠️ Uso dati GEX di ieri come fallback d'emergenza.")
                return old_cache.get("gex_value"), old_cache.get("gex_regime")
        return 0, "SCONOSCIUTO"

def analizza_mercati():
    session = requests.Session()
    session.headers.update({'User-Agent': 'Mozilla/5.0'})

     # 1. Recupero GEX a livello globale
    gex_val, gex_regime = recupera_gex_sp500()
    print(f"Market Regime GEX: {gex_val} - {gex_regime}")
    
    top_settori = identifica_settori_migliori(session)
    if not top_settori:
        print("Errore nel recupero ETF. Esco.")
        return
        
    miglior_etf_assoluto, miglior_perf_assoluta = top_settori[0]
    if miglior_perf_assoluta < -0.5:
        print("Il mercato sta crollando ovunque (Leader assoluto negativo). Pausa operativa per protezione capitale.")
        return 
        
    for etf_leader, perf_leader in top_settori:
        tickers_da_analizzare = SETTORI[etf_leader]["tickers"]
        print(f"Avvio analisi quantitativa oraria sui 10 ticker del settore {etf_leader}...")
        
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
                offset_apertura = 0.5 if ora_utc in [14, 15] else 0.0
                soglia_breakout = 1.3 + offset_apertura
                soglia_spinta = 1.8 + offset_apertura
                soglia_assorbimento = 2.2 + offset_apertura

                print(f"[{nome}] P: {prezzo_attuale:.2f} | SMA50: {sma_50:.2f} | Vol: {volume_attuale} (Media: {media_volume:.0f}) | ATR: {atr_14:.2f}")

                # --- 1. CERCHIAMO I 3 TRIGGER SUL GRAFICO ORARIO ---
                if media_volume > 0 and volume_attuale >= (media_volume * soglia_breakout):
                    id_seg_temp = None
                    
                    if corpo_candela >= atr_14:
                        id_seg_temp = "BREAKOUT VOLATILITÀ"
                    elif (0.4 * atr_14) <= corpo_candela < atr_14 and volume_attuale >= (media_volume * soglia_spinta):
                        id_seg_temp = "SPINTA / COSTRUZIONE TREND"
                    elif corpo_candela < (0.4 * atr_14) and volume_attuale >= (media_volume * soglia_assorbimento):
                        id_seg_temp = "ASSORBIMENTO ISTITUZIONALE"

                    if id_seg_temp:
                        url_daily = f"https://query2.finance.yahoo.com/v8/finance/chart/{ticker}?interval=1d&range=1y"
                        try:
                            time.sleep(1)
                            resp_daily = session.get(url_daily, timeout=5)
                            quote_daily = resp_daily.json()['chart']['result'][0]['indicators']['quote'][0]
                            
                            valid_daily = [(c, l, h) for c, l, h in zip(quote_daily['close'], quote_daily['low'], quote_daily['high']) if c is not None and l is not None and h is not None]
                            
                            if len(valid_daily) >= 200:
                                c_daily = [v[0] for v in valid_daily]
                                l_daily = [v[1] for v in valid_daily]
                                h_daily = [v[2] for v in valid_daily]
                                
                                sma_50_daily = sum(c_daily[-50:]) / 50
                                sma_200_daily = sum(c_daily[-200:]) / 200
                                distanza_sma50 = abs(prezzo_attuale - sma_50_daily) / sma_50_daily
                                
                                # --- 2. LOGICA PULLBACK: Validazione sul Daily ---
                                id_seg = None
                                if var_perc >= 0 and prezzo_attuale > sma_200_daily and distanza_sma50 <= 0.03:
                                    id_seg = f"🎯 PULLBACK D1 + {id_seg_temp}"
                                    sl_strutturale = min(l_daily[-10:]) - (0.2 * atr_14) 
                                    tp_strutturale = massimo_mensile
                                elif var_perc < 0 and prezzo_attuale < sma_200_daily and distanza_sma50 <= 0.03:
                                    id_seg = f"🎯 PULLBACK D1 + {id_seg_temp}"
                                    sl_strutturale = max(h_daily[-10:]) + 0.10 
                                    tp_strutturale = minimo_mensile
                                else:
                                    print(f"  └─ 🛑 SCARTATO: Non a contatto con SMA50 Daily (Dist: {distanza_sma50:.1%}) o Contro Trend")
                                    continue
                            else:
                                continue
                        except Exception as e:
                            print(f"  └─ 🛑 Errore dati Daily: {e}")
                            continue

                          # Richiama il sistema a doppia fonte (YF + Finviz)
                        giorni_agli_utili = recupera_utili_sicuri(ticker, session)

                            
                        # --- 3. CALCOLO STOP E TARGET STRUTTURALI ---
                        if var_perc >= 0:
                            prezzo_ingresso = massimo_candela
                            ordine_txt = f"🟢 BUY STOP (Long): {prezzo_ingresso:.2f} $"
                            sl = sl_strutturale
                            tp = tp_strutturale if tp_strutturale > (prezzo_ingresso + atr_14) else prezzo_ingresso + ((prezzo_ingresso - sl) * 2)
                        else:
                            prezzo_ingresso = minimo_candela
                            ordine_txt = f"🔴 SELL STOP (Short): {prezzo_ingresso:.2f} $"
                            sl = sl_strutturale
                            tp = tp_strutturale if tp_strutturale < (prezzo_ingresso - atr_14) else prezzo_ingresso - ((sl - prezzo_ingresso) * 2)

                        is_in_trend = (var_perc >= 0 and prezzo_attuale > sma_50) or (var_perc < 0 and prezzo_attuale < sma_50)
                        trend_txt = "🟢 A FAVORE DEL TREND" if is_in_trend else "⚠️ CONTRO-TREND"
                        sma_txt = "SOPRA SMA50" if prezzo_attuale > sma_50 else "SOTTO SMA50"
                        molt_vol = volume_attuale / media_volume

                        commento_ai = chiedi_analisi_ai(
                        ticker=nome, id_seg=id_seg, prezzo=prezzo_attuale, var_perc=var_perc, 
                        vol_molt=molt_vol, trend_txt=f"{sma_txt} ({trend_txt})", atr=atr_14, 
                        corpo=corpo_candela, dist_max=distanza_massimo_perc, dist_min=distanza_minimo_perc, 
                        giorni_utili=giorni_agli_utili
                        )

                        # --- NUOVA GESTIONE DEL MESSAGGIO (LONG vs SHORT) ---
                        if var_perc >= 0:
                            # Setup LONG (Eseguibile per portafogli Cash)
                            msg = (f"🚀 {id_seg}: {nome.upper()}\n"
                               f"🌐 SPX GEX: {gex_val} ({'🟢' if gex_val > 0 else '🔴'} Regime: {gex_regime.split(' ')[0]})\n"
                               f"📊 Rotazione: {SETTORI[etf_leader]['nome_settore']}\n"
                               f"Contesto: {sma_txt} | {trend_txt}\n"
                               f"Prezzo Chiusura: {prezzo_attuale:.2f} $ ({var_perc:+.2f}%)\n"
                               f"Volume: {molt_vol:.1f}x media\n"
                               f"------------------------\n"
                               f"⏳ INGRESSO IN CONFERMA:\n"
                               f"{ordine_txt}\n"
                               f"🎯 TARGET NETTO: {tp:.2f} $\n"
                               f"🛑 STOP LOSS STRUTTURALE: {sl:.2f} $\n"
                               f"------------------------\n"
                               f"🤖 ANALISI:\n{commento_ai}")
                        else:
                            # Setup SHORT (Avviso blocco operativo)
                            msg = (f"🩸 {id_seg}: {nome.upper()}\n"
                                   f"📊 Rotazione: {SETTORI[etf_leader]['nome_settore']}\n"
                                   f"Contesto: {sma_txt} | {trend_txt}\n"
                                   f"Prezzo Chiusura: {prezzo_attuale:.2f} $ ({var_perc:+.2f}%)\n"
                                   f"Volume: {molt_vol:.1f}x media\n"
                                   f"------------------------\n"
                                   f"⚠️ BLOCCO OPERATIVO (NO LEVA):\n"
                                   f"Questo è un setup Ribassista (Short verso {tp:.2f}$). "
                                   f"Poiché la tua strategia è 100% Cash/Senza Leva, l'operazione non è statisticamente sicura né eseguibile. "
                                   f"Notifica fornita solo per Market Intelligence. Resta liquido.\n"
                                   f"------------------------\n"
                                   f"🤖 ANALISI DELL'ESPERTO:\n{commento_ai}")
                        
                        invia_notifica(msg)

                    
            except Exception as e:
                print(f"Errore su {nome}: {e}")
            time.sleep(random.uniform(1.5, 3.0))

if __name__ == "__main__":
    analizza_mercati()
