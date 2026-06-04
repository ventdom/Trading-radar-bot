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

# TICKER AGGIORNATI: Inserite le nuove leve IPO/High Beta per tutti i settori
SETTORI = {
    "XLK": {"nome_settore": "💻 TECH / SOFTWARE", "tickers": {"Microsoft": "MSFT", "Apple": "AAPL", "Salesforce": "CRM", "Tempus AI": "TEM", "ServiceNow": "NOW", "Ibotta": "IBTA", "Klaviyo": "KVYO", "Palo Alto": "PANW", "CrowdStrike": "CRWD", "Palantir": "PLTR", "Meta": "META", "Netflix": "NFLX", "Snowflake": "SNOW", "Datadog": "DDOG", "Reddit": "RDDT", "Rubrik": "RBRK"}},
    "SMH": {"nome_settore": "🧠 AI & CHIP", "tickers": {"Nvidia": "NVDA", "AMD": "AMD", "TSMC": "TSM", "ASML": "ASML", "Broadcom": "AVGO", "Qualcomm": "QCOM", "Credo Tech": "CRDO", "Cerebras": "CERE", "Micron": "MU", "SoundHound": "SOUN", "Marvell": "MRVL", "Monolithic": "MPWR", "ARM": "ARM", "Astera Labs": "ALAB", "CoreWeave": "CRWV"}},
    "XLF": {"nome_settore": "🏦 FINANZA E FINTECH", "tickers": {"JPMorgan": "JPM", "Sezzle": "SEZL", "Nu Holdings": "NU", "Dave": "DAVE", "Goldman Sachs": "GS", "Morgan Stanley": "MS", "Visa": "V", "Mastercard": "MA", "Coinbase": "COIN", "Robinhood": "HOOD", "SoFi": "SOFI", "Upstart": "UPST", "Affirm": "AFRM", "Bowhead Specialty": "BOW", "MoneyLion": "MNY"}},
    "XLE": {"nome_settore": "🛢️ ENERGIA", "tickers": {"Exxon": "XOM", "Fluence": "FLNC", "Kinetik": "KNTK", "Schlumberger": "SLB", "EOG Resources": "EOG", "Marathon": "MPC", "Occidental": "OXY", "Valero": "VLO", "Williams": "WMB", "Oklo": "OKLO", "Halliburton": "HAL", "Hess": "HES", "Baker Hughes": "BKR", "BKV Corp": "BKV", "TXO Partners": "TXO"}},
    "ITA": {"nome_settore": "🪖 DIFESA E SPAZIO", "tickers": {"Lockheed": "LMT", "RTX Corp": "RTX", "Northrop": "NOC", "Rocket Lab": "RKLB", "Intuitive Mach": "LUNR", "TransDigm": "TDG", "Heico": "HEI", "L3Harris": "LHX", "Joby Aviation": "JOBY", "Howmet": "HWM", "Spirit Aero": "SPR", "Woodward": "WWD", "Moog": "MOG-A", "Loar Group": "LOAR", "AST SpaceMobile": "ASTS"}},
    "XBI": {"nome_settore": "🧬 BIOTECH & HEALTH", "tickers": {"Eli Lilly": "LLY", "Novo Nordisk": "NVO", "UnitedHealth": "UNH", "Viking": "VKTX", "Merck": "MRK", "AbbVie": "ABBV", "Structure": "GPCR", "Vertex": "VRTX", "Amgen": "AMGN", "Alto Neuro": "ANRO", "Regeneron": "REGN", "Intuitive Surg": "ISRG", "CRISPR": "CRSP", "CG Oncology": "CGON", "Kyverna": "KYTX"}}
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

def chiedi_analisi_ai(ticker, id_seg, prezzo, var_perc, vol_molt, trend_txt, atr, corpo, dist_max, dist_min, giorni_utili, gex_val, gex_regime, proxy_ticker, vix_ratio, vix_stato, dix_val, dix_stato, forma_daily):
    url = f"https://generativelanguage.googleapis.com/v1/models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}"
    giorno = datetime.utcnow().strftime("%A")
    ora_utc = datetime.utcnow().strftime("%H:%M")
    
    # PROMPT SINTETICO E SEZIONE INTERNET FEELINGS
    prompt = (
        f"Sei uno SPIETATO Risk Manager Istituzionale di Swing Trading (hold 1-2 settimane, NO leva). "
        f"Il tuo compito NON è compiacere l'utente, ma PROTEGGERE IL CAPITALE. Di default, sei scettico e cerchi motivi per BOCCIARE il trade.\n"
        f"Oggi è {giorno}, ore {ora_utc} UTC.\n\n"
        f"DATI: Macro (VIX {vix_ratio:.2f} {vix_stato}), DIX ({dix_val:.1f}% {dix_stato}), GEX {proxy_ticker}: {gex_val}M.\n"
        f"SETUP: {id_seg} su {ticker} | Prezzo: {prezzo:.2f}$ | RVOL: {vol_molt:.1f}x | Daily Live: {forma_daily}.\n\n"
        f"REGOLE DI BOCCIATURA TASSATIVE (Se si verifica una di queste, il trade va SCARTATO):\n"
        f"1. Divergenza Strutturale: Se la candela Daily Live chiude sotto il 50% del suo range odierno ma il setup H1 è Long, è una Bull Trap. BOCCIA.\n"
        f"2. Clima Macro Tossico: Se il VIX è in Backwardation (>1.0) E il GEX è Negativo, non si aprono nuovi Long. BOCCIA.\n"
        f"3. Distribuzione Istituzionale: Se DIX è < 40% (Paura) e l'RVOL non supera un eccezionale 2.5x, non c'è abbastanza spinta contro-corrente. BOCCIA.\n\n"
        f"FORMATTAZIONE OBBLIGATORIA (Sintesi estrema, max 2 righe a blocco):\n"
        f"**Macro/Settore:** [Analisi]. **[Vantaggio o Pericolo?]**\n"
        f"**Valutazione Setup:** [Analisi incrociando trend {trend_txt}, ATR H1 {atr:.2f} e Candela Daily Live]. **[Conferma o Divergenza?]**\n"
        f"**Internet Feelings:** [Analisi del sentiment su X e news finanziarie dell'ultima settimana per {ticker}].\n"
        f"**Utili:** {giorni_utili}.\n\n"
        f"**Verdetto Finale:** [INIZIA TASSATIVAMENTE con '🟢 APPROVATO:' oppure '🔴 SCARTATO:'. Giustifica la scelta in massimo 2 frasi pesando le regole sopra citate]."
    )

    
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    headers = {'Content-Type': 'application/json'}
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=20)
        response.raise_for_status()
        return response.json()['candidates'][0]['content']['parts'][0]['text'].strip()
    except Exception:
        return "Analisi AI temporaneamente non disponibile."

def recupera_utili_sicuri(ticker, session):
    url_quote = f"https://query2.finance.yahoo.com/v7/finance/quote?symbols={ticker}"
    try:
        time.sleep(1) 
        resp = session.get(url_quote, timeout=5).json()
        earnings_ts = resp.get("quoteResponse", {}).get("result", [{}])[0].get("earningsTimestamp")
        if earnings_ts:
            giorni = int((earnings_ts - time.time()) / 86400)
            if 0 > giorni >= -300:
                return "Già passati (Sicuro)"
            return f"Mancano {giorni} giorni"
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
                        return f"Mancano {giorni_mancanti} giorni"
                    elif giorni_mancanti < 0:
                        return "Già passati (Sicuro)"
                    return f"Mancano {giorni_mancanti} giorni"
    except Exception:
        pass
        
    return "Dati Sconosciuti"

def identifica_settori_migliori(session):
    print("Analisi Rotazione Settoriale (ROC a 10 Giorni)...")
    risultati_settori = []
    
    for etf in SETTORI.keys():
        try:
            url = f"https://query2.finance.yahoo.com/v8/finance/chart/{etf}?interval=1d&range=1mo"
            resp = session.get(url, timeout=5).json()
            chiusure = resp['chart']['result'][0]['indicators']['quote'][0]['close']
            
            chiusure = [c for c in chiusure if c is not None]
            
            if len(chiusure) >= 12:
                c_attuale = chiusure[-1]
                c_10_giorni_fa = chiusure[-11]
                
                perf = ((c_attuale - c_10_giorni_fa) / c_10_giorni_fa) * 100
                print(f"ETF {etf} ({SETTORI[etf]['nome_settore']}): ROC 10D {perf:+.2f}%")
                risultati_settori.append((etf, perf))
        except Exception as e:
            pass
        time.sleep(1)
        
    risultati_settori.sort(key=lambda x: x[1], reverse=True)
    top_3 = risultati_settori[:3] if len(risultati_settori) >= 3 else risultati_settori
    
    if top_3:
        print("\n=> SETTORI LEADER IDENTIFICATI (Su base ROC 10D):")
        for etf, perf in top_3:
            print(f"   - {SETTORI[etf]['nome_settore']} ({etf}) con {perf:+.2f}%")
    print()
    
    return top_3

def recupera_vix_term_structure(session):
    try:
        url_vix = "https://query2.finance.yahoo.com/v8/finance/chart/^VIX?interval=1d&range=5d"
        resp_vix = session.get(url_vix, timeout=5).json()
        vix_close = [c for c in resp_vix['chart']['result'][0]['indicators']['quote'][0]['close'] if c is not None]
        vix_attuale = vix_close[-1]

        url_vix3m = "https://query2.finance.yahoo.com/v8/finance/chart/^VIX3M?interval=1d&range=5d"
        resp_vix3m = session.get(url_vix3m, timeout=5).json()
        vix3m_close = [c for c in resp_vix3m['chart']['result'][0]['indicators']['quote'][0]['close'] if c is not None]
        vix3m_attuale = vix3m_close[-1]

        rapporto = vix_attuale / vix3m_attuale
        stato = "BACKWARDATION (Paura Immediata)" if rapporto > 1 else "CONTANGO (Mercato Sano)"
        
        return vix_attuale, vix3m_attuale, rapporto, stato
    except Exception:
        return 0, 0, 0, "SCONOSCIUTO"

def recupera_dix(session):
    url = "https://squeezemetrics.com/monitor/static/DIX.csv"
    try:
        headers_csv = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        response = session.get(url, headers=headers_csv, timeout=10)
        
        if response.status_code == 200:
            lines = response.text.strip().split('\n')
            headers = [h.strip().lower() for h in lines[0].split(',')]
            
            if 'dix' in headers:
                dix_idx = headers.index('dix')
                last_line = lines[-1].split(',')
                dix_value = float(last_line[dix_idx]) * 100 
                
                if dix_value >= 45.0:
                    stato = "ACCUMULO ISTITUZIONALE (Bullish)"
                elif dix_value <= 40.0:
                    stato = "DISTRIBUZIONE / PAURA (Bearish)"
                else:
                    stato = "NEUTRALE / NESSUN VANTAGGIO"
                    
                return dix_value, stato
    except Exception as e:
        pass
        
    return 0.0, "SCONOSCIUTO"

def recupera_gex_settoriale(etf_leader):
    proxy_ticker = PROXY_SETTORI.get(etf_leader, "AAPL")
    cache_file = "gex_cache.json"  # Nome file STATICO, combacia perfettamente con radar.yml
    
    oggi = datetime.utcnow()
    oggi_str = oggi.strftime("%Y-%m-%d")
    
    giorni_al_venerdi = (4 - oggi.weekday()) % 7
    if giorni_al_venerdi == 0 and oggi.hour >= 20:
        giorni_al_venerdi = 7
        
    prossimo_venerdi = oggi + timedelta(days=giorni_al_venerdi)
    scadenza_opzioni = prossimo_venerdi.strftime("%Y-%m-%d")
    
    cache_data = {}
    
    # 1. Carica l'intero dizionario di cache se il file esiste
    if os.path.exists(cache_file):
        try:
            with open(cache_file, "r") as f:
                cache_data = json.load(f)
                
            # 2. Controlla se abbiamo già i dati validi per OGGI per questo specifico ticker
            if proxy_ticker in cache_data:
                dati_ticker = cache_data[proxy_ticker]
                if dati_ticker.get("data") == oggi_str:
                    print(f"✅ GEX Proxy ({proxy_ticker}) recuperato da cache.")
                    return dati_ticker.get("gex_value"), dati_ticker.get("gex_regime"), proxy_ticker
        except Exception as e:
            print(f"⚠️ Errore lettura cache: {e}")

    print(f"🔄 Richiesta FlashAlpha per {proxy_ticker}...")
    url_flashalpha = f"https://lab.flashalpha.com/v1/exposure/gex/{proxy_ticker}?expiration={scadenza_opzioni}"
    headers = {"X-Api-Key": FLASHALPHA_API_KEY.strip(), "User-Agent": "Mozilla/5.0"}
    
    try:
        response = requests.get(url_flashalpha, headers=headers, timeout=10)
        print(f"📡 Risposta FlashAlpha [{response.status_code}]: {response.text[:100]}")
        response.raise_for_status()
        dati = response.json()
        
        gex_value = dati.get("net_gex", 0) 
        gex_regime = "POSITIVO (Stabilità)" if gex_value > 0 else "NEGATIVO (Volatilità)"
        
        # 3. Aggiorna SOLO la chiave del ticker corrente nel dizionario e salva
        cache_data[proxy_ticker] = {
            "data": oggi_str,
            "gex_value": gex_value,
            "gex_regime": gex_regime
        }
        
        with open(cache_file, "w") as f:
            json.dump(cache_data, f, indent=4)
            
        return gex_value, gex_regime, proxy_ticker
        
    except Exception as e:
        print(f"❌ Errore API GEX {proxy_ticker}: {e}")
        return 0, "SCONOSCIUTO", proxy_ticker

def analizza_mercati():
    session = requests.Session()
    session.headers.update({'User-Agent': 'Mozilla/5.0'})

    top_settori = identifica_settori_migliori(session)
    if not top_settori:
        return
        
    miglior_etf_assoluto, miglior_perf_assoluta = top_settori[0]
    if miglior_perf_assoluta < -0.5:
        print("Il mercato sta crollando ovunque. Pausa operativa.")
        return 
        
    vix_val, vix3m_val, vix_ratio, vix_stato = recupera_vix_term_structure(session)
    dix_val, dix_stato = recupera_dix(session)

    for etf_leader, perf_leader in top_settori:
        gex_val, gex_regime, proxy_ticker = recupera_gex_settoriale(etf_leader)
        print(f"\n🚀 Analisi Settore: {etf_leader} | Proxy: {proxy_ticker}")
        tickers_da_analizzare = SETTORI[etf_leader]["tickers"]
        
        for nome, ticker in tickers_da_analizzare.items():
            try:
                print(f"🔎 Analizzando {nome} ({ticker})...")
                url = f"https://query2.finance.yahoo.com/v8/finance/chart/{ticker}?interval=1h&range=1mo"
                response = session.get(url, timeout=10)
                if response.status_code != 200: continue
                
                dati = response.json()
                if not dati.get('chart', {}).get('result'): continue
                
                risultato = dati['chart']['result'][0]
                quote = risultato['indicators']['quote'][0]
                timestamps = risultato.get('timestamp', [])
                
                chiusure, aperture, volumi, massimi, minimi, ts_validi = [], [], [], [], [], []
                
                for i in range(len(quote['close'])):
                    c, o, v, h, l = quote['close'][i], quote['open'][i], quote['volume'][i], quote['high'][i], quote['low'][i]
                    ts = timestamps[i] if i < len(timestamps) else None
                    if None not in (c, o, v, h, l, ts):
                        chiusure.append(c); aperture.append(o); volumi.append(v); massimi.append(h); minimi.append(l); ts_validi.append(ts)
                
                if len(chiusure) < 52: continue
                
                prezzo_attuale = chiusure[-2]
                prezzo_apertura = aperture[-2]
                massimo_candela = massimi[-2]  
                minimo_candela = minimi[-2]    
                volume_attuale = volumi[-2]
                ts_attuale = ts_validi[-2]
                
                ora_target = datetime.utcfromtimestamp(ts_attuale).hour
                
                volumi_stessa_ora = [
                    volumi[i] for i in range(len(volumi) - 2) 
                    if datetime.utcfromtimestamp(ts_validi[i]).hour == ora_target
                ]
                
                if len(volumi_stessa_ora) > 0:
                    media_volume = sum(volumi_stessa_ora) / len(volumi_stessa_ora)
                else:
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

                soglia_breakout = 1.3
                soglia_spinta = 1.8
                soglia_assorbimento = 2.2

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
                            
                            # RISOLUZIONE: Estrazione per calcolo "Cumulata" (Includo l'Apertura Daily)
                            valid_daily = [(c, l, h, o) for c, l, h, o in zip(quote_daily['close'], quote_daily['low'], quote_daily['high'], quote_daily['open']) if None not in (c, l, h, o)]
                            
                            if len(valid_daily) >= 200:
                                c_daily = [v[0] for v in valid_daily]
                                l_daily = [v[1] for v in valid_daily]
                                h_daily = [v[2] for v in valid_daily]
                                
                                # CALCOLO CANDELA GIORNALIERA CUMULATA (LIVE)
                                c_live, l_live, h_live, o_live = valid_daily[-1]
                                range_live = h_live - l_live
                                if range_live > 0:
                                    pos_chiusura_live = ((c_live - l_live) / range_live) * 100
                                else:
                                    pos_chiusura_live = 50.0
                                
                                forma_daily = f"Open {o_live:.2f}$ | High {h_live:.2f}$ | Low {l_live:.2f}$ | Close {c_live:.2f}$ (Chiusura al {pos_chiusura_live:.1f}% del range odierno)"

                                sma_50_daily = sum(c_daily[-50:]) / 50
                                sma_200_daily = sum(c_daily[-200:]) / 200
                                distanza_sma50 = abs(prezzo_attuale - sma_50_daily) / sma_50_daily
                                
                                id_seg = None
                                if var_perc >= 0 and prezzo_attuale > sma_200_daily and distanza_sma50 <= 0.08:
                                    id_seg = f"🎯 PULLBACK D1 + {id_seg_temp}"
                                    sl_strutturale = min(l_daily[-10:]) - (0.2 * atr_14) 
                                    tp_strutturale = massimo_mensile
                                elif var_perc < 0 and prezzo_attuale < sma_200_daily and distanza_sma50 <= 0.08:
                                    id_seg = f"🎯 PULLBACK D1 + {id_seg_temp}"
                                    sl_strutturale = max(h_daily[-10:]) + 0.10 
                                    tp_strutturale = minimo_mensile
                                else:
                                    continue
                            else:
                                continue
                        except Exception as e:
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

                        commento_ai = chiedi_analisi_ai(
                            ticker=nome, id_seg=id_seg, prezzo=prezzo_attuale, var_perc=var_perc, 
                            vol_molt=molt_vol, trend_txt=f"{sma_txt} ({trend_txt})", atr=atr_14, 
                            corpo=corpo_candela, dist_max=distanza_massimo_perc, dist_min=distanza_minimo_perc, 
                            giorni_utili=giorni_agli_utili, gex_val=gex_val, gex_regime=gex_regime, 
                            proxy_ticker=proxy_ticker, vix_ratio=vix_ratio, vix_stato=vix_stato, 
                            dix_val=dix_val, dix_stato=dix_stato, forma_daily=forma_daily
                        )

                        dix_emoji = '🟢' if dix_val >= 45.0 else '🔴' if dix_val <= 40.0 else '🟡'

                        if var_perc >= 0:
                            msg = (f"🚀 {id_seg}: {nome.upper()}\n"
                               f"👑 LEADER GEX ({proxy_ticker}): {gex_val} M ({'🟢' if gex_val > 0 else '🔴'} {gex_regime.split(' ')[0]})\n"
                               f"📉 VIX TERM STR: {vix_ratio:.2f} ({'🔴' if vix_ratio > 1 else '🟢'} {vix_stato.split(' ')[0]})\n"
                               f"🐳 DARK POOL (DIX): {dix_val:.1f}% ({dix_emoji} {dix_stato.split(' ')[0]})\n"
                               f"📊 Rotazione: {SETTORI[etf_leader]['nome_settore']}\n"
                               f"Contesto D1: {sma_txt} | {trend_txt}\n"
                               f"Prezzo H1: {prezzo_attuale:.2f} $ ({var_perc:+.2f}%)\n"
                               f"Volume H1: {molt_vol:.1f}x media RVOL\n"
                               f"Candela Daily Cumulata: Chiusura al {pos_chiusura_live:.0f}% del range odierno\n"
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
                                   f"🐳 DARK POOL (DIX): {dix_val:.1f}% ({dix_emoji} {dix_stato.split(' ')[0]})\n"
                                   f"📊 Rotazione: {SETTORI[etf_leader]['nome_settore']}\n"
                                   f"Contesto D1: {sma_txt} | {trend_txt}\n"
                                   f"Prezzo H1: {prezzo_attuale:.2f} $ ({var_perc:+.2f}%)\n"
                                   f"Volume H1: {molt_vol:.1f}x media RVOL\n"
                                   f"Candela Daily Cumulata: Chiusura al {pos_chiusura_live:.0f}% del range odierno\n"
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
