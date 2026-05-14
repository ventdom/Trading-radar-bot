import os
import requests
import time
import random

# --- 1. SEGRETI ---
TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
CHAT_ID = os.environ["CHAT_ID"]

# --- 2. PARAMETRI E TICKERS ---

TICKERS = {
    # I Tuoi Tier 1 Originali
    "Nvidia": "NVDA", "Tesla": "TSLA", "TSMC": "TSM", "ASML": "ASML", "AMD": "AMD", 
    "Intel": "INTC", "Eli Lilly": "LLY", "Novo Nordisk": "NVO",
    # I 5 Nuovi Inserimenti ad Alta Volatilità
    "SuperMicro": "SMCI", 
    "Palantir": "PLTR", 
    "CrowdStrike": "CRWD", 
    "ARM": "ARM", 
    "Coinbase": "COIN"
}
# Le soglie fisse vengono rimosse per far spazio alla logica ATR

def invia_notifica(messaggio, tentativi=3):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    dati = {"chat_id": CHAT_ID, "text": messaggio}
    
    for tentativo in range(tentativi):
        try:
            response = requests.post(url, data=dati, timeout=10)
            response.raise_for_status() 
            return 
        except requests.exceptions.RequestException as e:
            print(f"[ERRORE TELEGRAM] Tentativo {tentativo + 1}/{tentativi} fallito: {e}")
            time.sleep(2) 
            
    print("[CRITICO] Impossibile inviare notifica Telegram. Controllare Token/Connessione.")

def analizza_mercati():
    print("Avvio analisi quantitativa (Logica ATR per Swing Trading)...")
    
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'application/json'
    })
    
    for nome, ticker in TICKERS.items():
        max_retries = 3
        dati_validi = False
        
        for attempt in range(max_retries):
            try:
                url = f"https://query2.finance.yahoo.com/v8/finance/chart/{ticker}?interval=1h&range=1mo"
                response = session.get(url, timeout=10)
                
                if response.status_code == 429:
                    attesa = (attempt + 1) * 5 
                    print(f"[{nome}] Allarme Rate Limit (429). Attendo {attesa} secondi...")
                    time.sleep(attesa)
                    continue
                
                response.raise_for_status()
                dati = response.json()
                
                if not dati.get('chart', {}).get('result'):
                    print(f"[{nome}] Errore struttura JSON: Dati vuoti.")
                    break
                    
                risultato = dati['chart']['result'][0]
                quote = risultato['indicators']['quote'][0]
                
                # Estrazione dati allineata (aggiunti High e Low per il calcolo ATR)
                chiusure, aperture, volumi, massimi, minimi = [], [], [], [], []
                for i in range(len(quote['close'])):
                    c, o, v, h, l = quote['close'][i], quote['open'][i], quote['volume'][i], quote['high'][i], quote['low'][i]
                    # Salva solo se nessun dato è nullo in quell'ora
                    if None not in (c, o, v, h, l):
                        chiusure.append(c)
                        aperture.append(o)
                        volumi.append(v)
                        massimi.append(h)
                        minimi.append(l)
                
                dati_validi = True
                break 

            except requests.exceptions.RequestException as e:
                print(f"[ERRORE HTTP API] {nome}: {e}")
                time.sleep(2)
            except Exception as e:
                print(f"[ERRORE PARSING] {nome}: {e}")
                break 
                
        if not dati_validi or len(chiusure) < 52: 
            print(f"[{nome}] Skipped: Dati insufficienti o invalidi.")
            continue
            
        # --- CALCOLI BASE ---
        prezzo_attuale = chiusure[-2]
        prezzo_apertura = aperture[-2]
        volume_attuale = volumi[-2]
        
        media_volume = sum(volumi[-22:-2]) / 20
        sma_50 = sum(chiusure[-51:-1]) / 50  
        var_perc = ((prezzo_attuale - prezzo_apertura) / prezzo_apertura) * 100
        corpo_candela = abs(prezzo_attuale - prezzo_apertura)
        
        # --- CALCOLO ATR A 14 PERIODI ---
        trs = []
        for i in range(-15, -1): # Ultime 14 candele chiuse
            h = massimi[i]
            l = minimi[i]
            c_prev = chiusure[i-1]
            # Formula True Range: max tra (H-L), abs(H-C_prev), abs(L-C_prev)
            tr = max(h - l, abs(h - c_prev), abs(l - c_prev))
            trs.append(tr)
        
        atr_14 = sum(trs) / len(trs)

        print(f"[{nome}] P: {prezzo_attuale:.2f} | Corpo: {corpo_candela:.2f} (ATR: {atr_14:.2f}) | Vol: {volume_attuale}")

        # --- LOGICA ALLARMI SWING TRADING (DINAMICA) ---
        if media_volume > 0 and volume_attuale >= (media_volume * 1.5): # Base: Volume almeno +50%
            
            trend = "🟢 RIALZISTA (> SMA 50)" if prezzo_attuale > sma_50 else "🔴 RIBASSISTA (< SMA 50)"
            segnale_tipo = None
            
            # CASO 1: BREAKOUT ESTREMO (Movimento > ATR con Volumi > 150%)
            if corpo_candela >= atr_14:
                direzione = "🚀 IMPENNATA (Breakout)" if var_perc > 0 else "🩸 CROLLO (Breakout)"
                segnale_tipo = direzione
                
            # CASO 2: COSTRUZIONE TREND - CHIUSURA DEL BUCO NERO (Movimento Sano ma Volume > 200%)
            elif (0.3 * atr_14) <= corpo_candela < atr_14 and volume_attuale >= (media_volume * 2.0):
                direzione = "↗️ SPINTA RIALZISTA" if var_perc > 0 else "↘️ PRESSIONE RIBASSISTA"
                segnale_tipo = f"{direzione} (Costruzione Trend)"
                
            # CASO 3: ASSORBIMENTO (Prezzo quasi fermo < 30% ATR, ma Volume immenso > 250%)
            elif corpo_candela < (0.3 * atr_14) and volume_attuale >= (media_volume * 2.5):
                segnale_tipo = "🕵️‍♂️ ASSORBIMENTO (Smart Money)"

            # SE ABBIAMO UN SEGNALE VALIDO, INVIA NOTIFICA
            if segnale_tipo:
                # Contesto Swing Trading (Filtro contro-trend)
                contesto = "⚠️ Contro-Trend (Attenzione)" if (var_perc > 0 and prezzo_attuale < sma_50) or (var_perc < 0 and prezzo_attuale > sma_50) else "✅ A favore di Trend"
                
                # Calcolo moltiplicatore volume per la UI
                moltiplicatore_vol = volume_attuale / media_volume
                
                msg = (f"🚨 ALLARME SWING: {nome.upper()} 🚨\n\n"
                       f"Segnale: {segnale_tipo}\n"
                       f"Contesto: {trend} | {contesto}\n\n"
                       f"Prezzo: {prezzo_attuale:.2f} $ ({var_perc:+.2f}%)\n"
                       f"Volatilità oraria: Corpo {corpo_candela:.2f}$ su base ATR {atr_14:.2f}$\n"
                       f"Volume: {volume_attuale} ({moltiplicatore_vol:.1f}x Media)")
                
                invia_notifica(msg)
                
        time.sleep(random.uniform(1.0, 2.5))

if __name__ == "__main__":
    analizza_mercati()
