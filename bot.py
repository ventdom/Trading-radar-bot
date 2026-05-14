import os
import requests
import time
import random

# --- 1. SEGRETI ---
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "INSERISCI_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID", "INSERISCI_ID")

# --- 2. PARAMETRI E TICKERS ---
TICKERS = {"Oro": "GC=F", "Petrolio": "CL=F","S&P500": "SPY", "Nasdaq": "QQQ",  "Nvidia": "NVDA",  "Tesla": "TSLA", "TSMC": "TSM",  "ASML": "ASML", "AMD": "AMD","Intel": "INTC","Eli Lilly": "LLY","Novo Nordisk": "NVO","AstraZeneca": "AZN","Bristol Myers": "BMY"}

SOGLIA_VOLUME = 2.0     
SOGLIA_MOMENTUM = 1.0   
SOGLIA_STABILITA = 0.2  

def invia_notifica(messaggio, tentativi=3):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    dati = {"chat_id": CHAT_ID, "text": messaggio}
    
    for tentativo in range(tentativi):
        try:
            # Aggiunto timeout per evitare che il bot si blocchi all'infinito
            response = requests.post(url, data=dati, timeout=10)
            response.raise_for_status() # Genera eccezione se status != 200 (es. token errato)
            return # Uscita pulita se invio riuscito
        except requests.exceptions.RequestException as e:
            print(f"[ERRORE TELEGRAM] Tentativo {tentativo + 1}/{tentativi} fallito: {e}")
            time.sleep(2) # Pausa prima del prossimo tentativo
            
    print("[CRITICO] Impossibile inviare notifica Telegram. Controllare Token/Connessione.")

def analizza_mercati():
    print("Avvio analisi quantitativa...")
    
    # 1. Ottimizzazione connessione (Previene ban IP riducendo l'overhead)
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
                
                # Gestione specifica del Rate Limit (Errore 429)
                if response.status_code == 429:
                    attesa = (attempt + 1) * 5 # Backoff: 5s, poi 10s, ecc.
                    print(f"[{nome}] Allarme Rate Limit (429). Attendo {attesa} secondi...")
                    time.sleep(attesa)
                    continue
                
                # Se c'è un altro errore HTTP (es. 404), blocca il retry e stampa
                response.raise_for_status()
                dati = response.json()
                
                # Controllo sicurezza struttura JSON
                if non dati.get('chart', {}).get('result'):
                    print(f"[{nome}] Errore struttura JSON: Dati vuoti.")
                    break
                    
                risultato = dati['chart']['result'][0]
                chiusure = [c for c in risultato['indicators']['quote'][0]['close'] if c is not None]
                aperture = [a for a in risultato['indicators']['quote'][0]['open'] if a is not None]
                volumi = [v for v in risultato['indicators']['quote'][0]['volume'] if v is not None]
                
                dati_validi = True
                break # Esce dal ciclo di retry, chiamata API riuscita

            except requests.exceptions.RequestException as e:
                print(f"[ERRORE HTTP API] {nome}: {e}")
                time.sleep(2)
            except Exception as e:
                print(f"[ERRORE PARSING] {nome}: {e}")
                break # Errore interno, inutile riprovare
                
        if not dati_validi or len(chiusure) < 51: 
            print(f"[{nome}] Skipped: Dati insufficienti o invalidi.")
            continue
            
        # --- CALCOLI STATISTICI (Rimasti invariati) ---
        prezzo_attuale = chiusure[-2]
        prezzo_apertura = aperture[-2]
        volume_attuale = volumi[-2]
        
        media_volume = sum(volumi[-22:-2]) / 20
        sma_50 = sum(chiusure[-51:-1]) / 50  
        var_perc = ((prezzo_attuale - prezzo_apertura) / prezzo_apertura) * 100
        
        print(f"[{nome}] P: {prezzo_attuale:.2f} | SMA50: {sma_50:.2f} | Vol: {volume_attuale}")

        # --- LOGICA ALLARMI ---
        if media_volume > 0 and volume_attuale > (media_volume * SOGLIA_VOLUME):
            trend = "🟢 RIALZISTA (> SMA 50)" if prezzo_attuale > sma_50 else "🔴 RIBASSISTA (< SMA 50)"
            
            if abs(var_perc) >= SOGLIA_MOMENTUM:
                direzione = "📈 IMPENNATA" if var_perc > 0 else "📉 CROLLO"
                avviso = "⚠️ CONTRO-TREND (Trappola?)" if (var_perc > 0 and prezzo_attuale < sma_50) or (var_perc < 0 and prezzo_attuale > sma_50) else "✅ IN TREND"
                msg = f"🚨 ALLARME: {nome.upper()} 🚨\n{direzione}\nTrend: {trend}\nValutazione: {avviso}\nPrezzo: {prezzo_attuale:.2f} $\nVar: {var_perc:.2f}%\nVol: {volume_attuale} (Media: {media_volume:.0f})"
                invia_notifica(msg)

            elif abs(var_perc) <= SOGLIA_STABILITA:
                msg = f"🕵️‍♂️ SOSPETTO ASSORBIMENTO: {nome.upper()} 🕵️‍♂️\nVol alto, prezzo fermo.\nTrend: {trend}\nPrezzo: {prezzo_attuale:.2f} $\nVar: {var_perc:.2f}%\nVol: {volume_attuale} (Media: {media_volume:.0f})"
                invia_notifica(msg)
                
        # 2. Prevenzione Ban IP (Jittering)
        # Introduce una pausa casuale tra 1.0 e 2.5 secondi tra ogni ticker
        time.sleep(random.uniform(1.0, 2.5))

if __name__ == "__main__":
    analizza_mercati()
