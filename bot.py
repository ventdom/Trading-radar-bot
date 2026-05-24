import os
import requests
import json
import time
import random
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
import re

# --- 1. SEGRETI ---
TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
CHAT_ID = os.environ["CHAT_ID"]
GEMINI_API_KEY = os.environ["GEMINI_API_KEY"] 
FLASHALPHA_API_KEY = os.environ["FLASHALPHA_API_KEY"] 

# --- 2. IL MOTORE DI ROTAZIONE SETTORIALE E PROXY GEX ---
PROXY_SETTORI = {
    "XLK": "AAPL",  # Tech
    "SMH": "NVDA",  # AI & Chip
    "XLF": "JPM",   # Finanza
    "XLE": "XOM",   # Energia
    "ITA": "LMT",   # Difesa
    "XBI": "LLY"    # Biotech
}

SETTORI = {
    "XLK": { # TECH & SOFTWARE
        "nome_settore": "💻 TECH / SOFTWARE",
        "tickers": {
            "Microsoft": "MSFT", "Apple": "AAPL", "Salesforce": "CRM", "Adobe": "ADBE", 
            "ServiceNow": "NOW", "Oracle": "ORCL", "Palo Alto": "PANW", "CrowdStrike": "CRWD", 
            "Palantir": "PLTR", "Meta": "META", "Netflix": "NFLX", "Snowflake": "SNOW", "Datadog": "DDOG",
            "Reddit": "RDDT", "Rubrik": "RBRK" 
        }
    },
    "SMH": { # AI & SEMICONDUTTORI
        "nome_settore": "🧠 AI & CHIP",
        "tickers": {
            "Nvidia": "NVDA", "AMD": "AMD", "TSMC": "TSM", "ASML": "ASML", 
            "Broadcom": "AVGO", "Qualcomm": "QCOM", "Applied Mat": "AMAT", "Intel": "INTC", 
            "Micron": "MU", "Texas Instr": "TXN", "Marvell": "MRVL", "Monolithic": "MPWR", "ARM": "ARM",
            "Astera Labs": "ALAB", "CoreWeave": "CRWV" 
        }
    },
    "XLF": { # BANCHE E FINANZA
        "nome_settore": "🏦 FINANZA",
        "tickers": {
            "JPMorgan": "JPM", "BofA": "BAC", "Wells Fargo": "WFC", "Citigroup": "C", 
            "Goldman Sachs": "GS", "Morgan Stanley": "MS", "Visa": "V", "Mastercard": "MA", 
            "Coinbase": "COIN", "Robinhood": "HOOD", "SoFi": "SOFI", "Upstart": "UPST", "Affirm": "AFRM",
            "Bowhead Specialty": "BOW", "MoneyLion": "MNY" 
        }
    },
    "XLE": { # ENERGIA E OIL
        "nome_settore": "🛢️ ENERGIA",
        "tickers": {
            "Exxon": "XOM", "Chevron": "CVX", "ConocoPhillips": "COP", "Schlumberger": "SLB", 
            "EOG Resources": "EOG", "Marathon": "MPC", "Occidental": "OXY", "Valero": "VLO", 
            "Williams": "WMB", "Halliburton": "HAL", "Pioneer": "PXD", "Hess": "HES", "Baker Hughes": "BKR",
            "BKV Corp": "BKV", "TXO Partners": "TXO" 
        }
    },
    "ITA": { # DIFESA E AEROSPAZIO
        "nome_settore": "🪖 DIFESA E AEROSPAZIO",
        "tickers": {
            "Lockheed": "LMT", "RTX Corp": "RTX", "Northrop": "NOC", "Gen Dynamics": "GD", 
            "Boeing": "BA", "TransDigm": "TDG", "Heico": "HEI", "L3Harris": "LHX", 
            "Textron": "TXT", "Howmet": "HWM", "Spirit Aero": "SPR", "Woodward": "WWD", "Moog": "MOG-A",
            "Loar Group": "LOAR", "AST SpaceMobile": "ASTS" 
        }
    },
    "XBI": { # BIOTECH & HEALTH
        "nome_settore": "🧬 BIOTECH & HEALTH",
        "tickers": {
            "Eli Lilly": "LLY", "Novo Nordisk": "NVO", "UnitedHealth": "UNH", "J&J": "JNJ", 
            "Merck": "MRK", "AbbVie": "ABBV", "Pfizer": "PFE", "Vertex": "VRTX", 
            "Amgen": "AMGN", "Gilead": "GILD", "Regeneron": "REGN", "Intuitive Surg": "ISRG", "CRISPR": "CRSP",
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
        except Exception:
            time.sleep(2)

def chiedi_analisi_ai(ticker, id_seg, prezzo, var_perc, vol_molt, trend_txt, atr, corpo, dist_max, dist_min, giorni_utili, gex_val, gex_regime, proxy_ticker, vix_ratio, vix_stato):
    url = f"https://generativelanguage.googleapis.com/v1/models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}"
    giorno = datetime.utcnow().strftime("%A")
    ora_utc = datetime.utcnow().strftime("%H:%M")
    
    prompt = (
        f"Sei un Risk Manager e consulente di Swing Trading quantitativo (no leva, hold 1-2 settimane). "
        f"Oggi è {giorno}, ore {ora_utc} UTC.\n"
        f"CONTESTO MACRO (VIX Term Structure): Il rapporto VIX/VIX3M è {vix_ratio:.2f} ({vix_stato}). "
        f"Se in Contango (< 1), il mercato prezza normalità. Se in Backwardation (> 1), le istituzioni prezzano panico imminente.\n"
        f"CONTESTO SETTORIALE (Leader GEX): L'Alpha Proxy del settore è {proxy_ticker}. Il suo Gamma Exposure (GEX) è {gex_val}M, Regime: {gex_regime}.\n"
        f"Usa questi dati: avvisa se la VIX Term Structure indica pericolo, e valuta se il GEX del leader supporta (Positivo) o indebolisce (Negativo) la rotazione settoriale.\n\n"
        f"Valuta questo segnale su {ticker}:\n"
        f"- Segnale: {id_seg} a {prezzo:.2f}$ ({var_perc:+.2f}% oggi)\n"
        f"- Volume: {vol_molt:.1f}x la media\n"
        f"- Trend: {trend_txt}\n"
        f"- Volatilità: Corpo candela {corpo:.2f}$ (Media ATR {atr:.2f}$)\n"
        f"- Struttura Grafica: Distanza dal Massimo Mensile {dist_max:.1f}%, dal Minimo {dist_min:.1f}%.\n"
        f"- Utili: Mancano {giorni_utili} giorni.\n\n"
        f"Scrivi un commento operativo (max 3 frasi). Correla il setup del ticker alla salute GEX del suo leader e allo stato del VIX per validare il Rischio/Rendimento. "
        f"Se mancano meno di 7 giorni agli utili, blocca categoricamente l'ingresso."
    )
    
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    headers = {'Content-Type': 'application/json'}
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=20)
        response.raise_for_status()
        return response.json()['candidates'][0]['content']['parts'][0]['text'].strip()
    except Exception:
        return "Analisi AI temporaneamente non disponibile a causa di un timeout di rete."

def recupera_utili_sicuri(ticker, session):
    url_quote = f"https://query2.finance.yahoo.com/v7/finance/quote?symbols={ticker}"
    try:
        time.sleep(1) 
        resp = session.get(url_quote, timeout=5).json()
        earnings_ts = resp.get("quoteResponse", {}).get("result", [{}])[0].get("earningsTimestamp")
        if earnings_ts:
            return int((earnings_ts - time.time()) / 86400)
    except Exception:
        pass
        
    try:
        url_finviz = f"https://finviz.com/quote.ashx?t={ticker}"
        headers_finviz = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        time.sleep(random.uniform(1.5, 2.5)) 
        
        resp_finviz = session.get(url_finviz, headers=headers_finviz, timeout=10)
        if resp_finviz.status_code == 200:
            soup = BeautifulSoup(resp_finviz.text, 'html.parser')
            td_earnings = soup.find('td', string=re.compile('Earnings'))
            if td_earnings:
                valore_data = td_earnings.find_next_sibling('td').text.strip()
                match = re.search(r'([a-zA-Z]{3}\s\d{1,2})', valore_data)
                if match:
                    clean_date = match.group(1)
                    anno_corrente = datetime.utcnow().year
                    data_utili = datetime.strptime(f"{clean_date} {anno_corrente}", "%b %d %Y")
                    giorni_mancanti = (data_utili - datetime.utcnow()).days
                    
                    if giorni_mancanti < -300: 
                        data_utili = data_utili.replace(year=anno_corrente + 1)
                        giorni_mancanti = (data_utili - datetime.utcnow()).days
                    return giorni_mancanti
    except Exception:
        pass
        
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

def recupera_vix_term_structure(session):
    """Calcola il rapporto tra VIX e VIX3M per identificare Backwardation o Contango."""
    try:
        # Recupero VIX (30 giorni)
        url_vix = "https://query2.finance.yahoo.com/v8/finance/chart/^VIX?interval=1d&range=5d"
        resp_vix = session.get(url_vix, timeout=5).json()
        vix_close = [c for c in resp_vix['chart']['result'][0]['indicators']['quote'][0]['close'] if c is not None]
        vix_attuale = vix_close[-1]

        # Recupero VIX3M (3 mesi)
        url_vix3m = "https://query2.finance.yahoo.com/v8/finance/chart/^VIX3M?interval=1d&range=5d"
        resp_vix3m = session.get(url_vix3m, timeout=5).json()
        vix3m_close = [c for c in resp_vix3m['chart']['result'][0]['indicators']['quote'][0]['close'] if c is not None]
        vix3m_attuale = vix3m_close[-1]

        rapporto = vix_attuale / vix3m_attuale
        stato = "BACKWARDATION (Paura Immediata)" if rapporto > 1 else "CONTANGO (Mercato Sano)"
        
        return vix_attuale, vix3m_attuale, rapporto, stato
    except Exception:
        return 0, 0, 0, "SCONOSCIUTO"

def recupera_gex_settoriale(etf_leader):
    """Recupera il GEX del Proxy di Settore: usa la cache se valida, altrimenti API."""
    proxy_ticker = PROXY_SETTORI.get(etf_leader, "AAPL")
    cache_file = "gex_cache.json"
    
    oggi = datetime.utcnow()
    oggi_str = oggi.strftime("%Y-%m-%d")
    
    # --- CALCOLO PROSSIMA SCADENZA OPZIONI (VENERDÌ) ---
    # weekday(): 0=Lunedì, 4=Venerdì, 6=Domenica.
    giorni_al_venerdi = (4 - oggi.weekday()) % 7
    # Se è venerdì sera a mercati chiusi (dopo le 20 UTC), puntiamo al venerdì della settimana successiva
    if giorni_al_venerdi == 0 and oggi.hour >= 20:
        giorni_al_venerdi = 7
        
    prossimo_venerdi = oggi + timedelta(days=giorni_al_venerdi)
    scadenza_opzioni = prossimo_venerdi.strftime("%Y-%m-%d")
    
    if os.path.exists(cache_file):
        try:
            with open(cache_file, "r") as f:
                cache = json.load(f)
                if cache.get("data") == oggi_str and cache.get("ticker") == proxy_ticker:
                    print(f"✅ GEX Proxy ({proxy_ticker}) recuperato da cache. Zero API consumate.")
                    return cache.get("gex_value"), cache.get("gex_regime"), proxy_ticker
        except Exception as e:
            print(f"⚠️ Errore cache GEX: {e}")

    print(f"🔄 Nessuna cache per oggi. Richiesta GEX {proxy_ticker} (Scadenza: {scadenza_opzioni}) a FlashAlpha...")
    
    # --- NUOVO URL CON IL PARAMETRO EXPIRATION ---
    url_flashalpha = f"https://lab.flashalpha.com/v1/exposure/gex/{proxy_ticker}?expiration={scadenza_opzioni}"
    
    headers = {
        "X-Api-Key": FLASHALPHA_API_KEY.strip(),
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    
    try:
        response = requests.get(url_flashalpha, headers=headers, timeout=10)
        
        if response.status_code != 200:
            print(f"🛑 ERRORE SERVER {response.status_code}: {response.text}")
            response.raise_for_status()
        dati = response.json()
        
        gex_value = dati.get("net_gex", 0) 
        gex_regime = "POSITIVO (Stabilità/Mean Reversion)" if gex_value > 0 else "NEGATIVO (Alta Volatilità/Trend Esteso)"
        
        with open(cache_file, "w") as f:
            json.dump({
                "data": oggi_str,
                "ticker": proxy_ticker,
                "gex_value": gex_value,
                "gex_regime": gex_regime
            }, f)
            
        print("💾 Cache GEX aggiornata e salvata con successo.")
        return gex_value, gex_regime, proxy_ticker
        
    except Exception as e:
        print(f"❌ Errore recupero GEX API: {e}")
        if os.path.exists(cache_file):
            with open(cache_file, "r") as f:
                old_cache = json.load(f)
                print("⚠️ Uso dati GEX in fallback.")
                return old_cache.get("gex_value", 0), old_cache.get("gex_regime", "SCONOSCIUTO"), old_cache.get("ticker", proxy_ticker)
        return 0, "SCONOSCIUTO", proxy_ticker

def analizza_mercati():
    session = requests.Session()
    session.headers.update({'User-Agent': 'Mozilla/5.0'})

    top_settori = identifica_settori_migliori(session)
    if not top_settori:
        print("Errore nel recupero ETF. Esco.")
        return
        
    miglior_etf_assoluto, miglior_perf_assoluta = top_settori[0]
    if miglior_perf_assoluta < -0.5:
        print("Il mercato sta crollando ovunque (Leader assoluto negativo). Pausa operativa per protezione capitale.")
        return 
        
    # Calcolo VIX Term Structure
    vix_val, vix3m_val, vix_ratio, vix_stato = recupera_vix_term_structure(session)
    print(f"VIX Term Structure: {vix_ratio:.2f} - {vix_stato}")

    # Calcolo del GEX solo sul settore LEADER assoluto (top_settori[0]) per massimizzare l'efficienza
    etf_leader_assoluto = top_settori[0][0]
    gex_val, gex_regime, proxy_ticker = recupera_gex_settoriale(etf_leader_assoluto)
    print(f"Leader GEX ({proxy_ticker}): {gex_val} - {gex_regime}")
        
    for etf_leader, perf_leader in top_settori:
        tickers_da_analizzare = SETTORI[etf_leader]["tickers"]
        print(f"Avvio analisi quantitativa oraria sui ticker del settore {etf_leader}...")
        
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

                        giorni_agli_utili = recupera_utili_sicuri(ticker, session)

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

                        # Passiamo i nuovi parametri VIX alla AI
                        commento_ai = chiedi_analisi_ai(
                            ticker=nome, id_seg=id_seg, prezzo=prezzo_attuale, var_perc=var_perc, 
                            vol_molt=molt_vol, trend_txt=f"{sma_txt} ({trend_txt})", atr=atr_14, 
                            corpo=corpo_candela, dist_max=distanza_massimo_perc, dist_min=distanza_minimo_perc, 
                            giorni_utili=giorni_agli_utili, gex_val=gex_val, gex_regime=gex_regime, 
                            proxy_ticker=proxy_ticker, vix_ratio=vix_ratio, vix_stato=vix_stato
                        )

                        if var_perc >= 0:
                            msg = (f"🚀 {id_seg}: {nome.upper()}\n"
                               f"👑 LEADER GEX ({proxy_ticker}): {gex_val} M ({'🟢' if gex_val > 0 else '🔴'} {gex_regime.split(' ')[0]})\n"
                               f"📉 VIX TERM STR: {vix_ratio:.2f} ({'🔴' if vix_ratio > 1 else '🟢'} {vix_stato.split(' ')[0]})\n"
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
                            msg = (f"🩸 {id_seg}: {nome.upper()}\n"
                                   f"👑 LEADER GEX ({proxy_ticker}): {gex_val} M ({'🟢' if gex_val > 0 else '🔴'} {gex_regime.split(' ')[0]})\n"
                                   f"📉 VIX TERM STR: {vix_ratio:.2f} ({'🔴' if vix_ratio > 1 else '🟢'} {vix_stato.split(' ')[0]})\n"
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
