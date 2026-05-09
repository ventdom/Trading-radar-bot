import os
import requests

# --- 1. LEGGIAMO I SEGRETI DALLA CASSAFORTE DI GITHUB ---
TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
CHAT_ID = os.environ["CHAT_ID"]

# --- 2. ASSET DA MONITORARE E PARAMETRI ---
TICKERS = {"Oro": "GC=F", "Petrolio": "CL=F", "Gas": "NG=F"}
SOGLIA_VOLUME = 2.0  
SOGLIA_PREZZO = 1.0  

def invia_notifica(messaggio):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    dati = {"chat_id": CHAT_ID, "text": messaggio}
    try:
        requests.post(url, data=dati)
    except:
        pass 

def analizza_mercati():
    print("Avvio analisi...")
    invia_notifica("🤖 Ciao dal Cloud! Il server Microsoft ha fatto un controllo con successo.")
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    for nome, ticker in TICKERS.items():
        try:
            url = f"https://query2.finance.yahoo.com/v8/finance/chart/{ticker}?interval=1h&range=5d"
            response = requests.get(url, headers=headers)
            
            if response.status_code != 200:
                continue
                
            dati = response.json()
            risultato = dati['chart']['result'][0]
            chiusure = risultato['indicators']['quote'][0]['close']
            aperture = risultato['indicators']['quote'][0]['open']
            volumi = risultato['indicators']['quote'][0]['volume']
            
            chiusure = [c for c in chiusure if c is not None]
            aperture = [a for a in aperture if a is not None]
            volumi = [v for v in volumi if v is not None]
            
            if len(chiusure) < 20:
                continue
                
            prezzo_attuale = chiusure[-1]
            prezzo_apertura = aperture[-1]
            volume_attuale = volumi[-1]
            
            volumi_passati = volumi[-21:-1]
            media_volume = sum(volumi_passati) / len(volumi_passati)
            variazione_perc = ((prezzo_attuale - prezzo_apertura) / prezzo_apertura) * 100
            
            print(f"[{nome}] P: {prezzo_attuale:.2f} | Vol: {volume_attuale} | Var: {variazione_perc:.2f}%")

            if volume_attuale > (media_volume * SOGLIA_VOLUME) and abs(variazione_perc) >= SOGLIA_PREZZO:
                direzione = "📉 GROSSA VENDITA/CROLLO" if variazione_perc < 0 else "📈 ACQUISTO/IMPENNATA"
                msg = (f"🚨 ALLARME {nome.upper()} 🚨\n\n{direzione}\nPrezzo: {prezzo_attuale:.2f} $\nVariazione Oraria: {variazione_perc:.2f}%\nVolume: {volume_attuale} contratti\n(Media: {media_volume:.0f})")
                invia_notifica(msg)
                
        except Exception as e:
            pass

# ESEGUE IL CONTROLLO UNA SOLA VOLTA E SI SPEGNE
if __name__ == "__main__":
    analizza_mercati()
