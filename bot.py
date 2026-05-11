import os
import requests

# --- 1. SEGRETI ---
TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
CHAT_ID = os.environ["CHAT_ID"]

# --- 2. PARAMETRI E TICKERS ---
TICKERS = {"Oro": "GC=F", "Petrolio": "CL=F", "S&P500": "SPY", "Nasdaq": "QQQ", "Nvidia": "NVDA"}

SOGLIA_VOLUME = 2.0     # Volume > 200% della media
SOGLIA_MOMENTUM = 1.0   # Movimento forte (> 1%)
SOGLIA_STABILITA = 0.2  # Movimento quasi nullo (< 0.2%)

def invia_notifica(messaggio):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    dati = {"chat_id": CHAT_ID, "text": messaggio}
    try:
        requests.post(url, data=dati)
    except:
        pass 

def analizza_mercati():
    print("Avvio analisi quantitativa...")
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    
    for nome, ticker in TICKERS.items():
        try:
            # RANGE AUMENTATO A 1 MESE per avere almeno 50 candele orarie
            url = f"https://query2.finance.yahoo.com/v8/finance/chart/{ticker}?interval=1h&range=1mo"
            response = requests.get(url, headers=headers)
            if response.status_code != 200: continue
                
            dati = response.json()
            risultato = dati['chart']['result'][0]
            chiusure = [c for c in risultato['indicators']['quote'][0]['close'] if c is not None]
            aperture = [a for a in risultato['indicators']['quote'][0]['open'] if a is not None]
            volumi = [v for v in risultato['indicators']['quote'][0]['volume'] if v is not None]
            
            # Ci servono almeno 50 ore per la Media Mobile
            if len(chiusure) < 50: continue
                
            prezzo_attuale = chiusure[-1]
            prezzo_apertura = aperture[-1]
            volume_attuale = volumi[-1]
            
            # Calcoli Statistici
            media_volume = sum(volumi[-21:-1]) / 20
            sma_50 = sum(chiusure[-50:]) / 50  # La Marea (Media a 50 ore)
            var_perc = ((prezzo_attuale - prezzo_apertura) / prezzo_apertura) * 100
            
            print(f"[{nome}] P: {prezzo_attuale:.2f} | SMA50: {sma_50:.2f} | Vol: {volume_attuale}")

            # --- LOGICA ALLARMI CON FILTRO TREND ---
            if volume_attuale > (media_volume * SOGLIA_VOLUME):
                
                # Valutazione del Trend
                trend = "🟢 TREND RIALZISTA (Sopra Media 50)" if prezzo_attuale > sma_50 else "🔴 TREND RIBASSISTA (Sotto Media 50)"
                
                # CASO A: ALLARME ROSSO (MOMENTUM)
                if abs(var_perc) >= SOGLIA_MOMENTUM:
                    direzione = "📈 IMPENNATA" if var_perc > 0 else "📉 CROLLO"
                    # Avviso di pericolo se il segnale è contro-trend
                    avviso = "⚠️ ATTENZIONE: Movimento CONTRO il trend principale (Possibile Trappola)." if (var_perc > 0 and prezzo_attuale < sma_50) or (var_perc < 0 and prezzo_attuale > sma_50) else "✅ Movimento IN LINEA col trend."
                    
                    msg = (f"🚨 ALLARME ROSSO: {nome.upper()} 🚨\n\n"
                           f"{direzione}\n"
                           f"Stato: {trend}\n"
                           f"Valutazione: {avviso}\n"
                           f"Prezzo: {prezzo_attuale:.2f} $\n"
                           f"Variazione: {var_perc:.2f}%\n"
                           f"Volume: {volume_attuale} (Media: {media_volume:.0f})")
                    invia_notifica(msg)

                # CASO B: SOSPETTO (SMART MONEY)
                elif abs(var_perc) <= SOGLIA_STABILITA:
                    msg = (f"🕵️‍♂️ SOSPETTO ISTITUZIONALE: {nome.upper()} 🕵️‍♂️\n\n"
                           f"Anomalia: Volume altissimo, Prezzo fermo.\n"
                           f"Stato: {trend}\n"
                           f"Prezzo: {prezzo_attuale:.2f} $\n"
                           f"Variazione: {var_perc:.2f}%\n"
                           f"Volume: {volume_attuale} (Media: {media_volume:.0f})")
                    invia_notifica(msg)
                
        except Exception as e:
            print(f"Errore su {nome}: {e}")

if __name__ == "__main__":
    analizza_mercati()
