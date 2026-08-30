import json
import urllib.request
import ssl
from pathlib import Path
from datetime import datetime

# Endpoint ufficiali MASE (DGSAIE)
URL_WEEKLY = "https://sisen.mase.gov.it/dgsaie/api/v1/weekly-prices/report/export?type=ALL&format=JSON&lang=it"
URL_MONTHLY = "https://sisen.mase.gov.it/dgsaie/api/v1/monthly-prices/export?format=JSON&lang=it"

def fetch_json(url: str) -> list[dict]:
    """Scarica il JSON dall'endpoint con User-Agent moderno."""
    headers = {"User-Agent": "Mozilla/5.0 (compatible; FuelSurchargeItalia/1.0)"}
    req = urllib.request.Request(url, headers=headers)
    ctx = ssl.create_default_context()
    
    with urllib.request.urlopen(req, context=ctx, timeout=30) as response:
        if response.status != 200:
            raise RuntimeError(f"Errore HTTP {response.status} durante il download da {url}")
        return json.loads(response.read().decode("utf-8"))

def parse_float(val: str | float | None) -> float:
    """Converte le stringhe del MASE (€/1.000L) in float €/Litro."""
    if val is None:
        return 0.0
    try:
        return round(float(str(val).replace(",", ".")) / 1000.0, 4)
    except ValueError:
        return 0.0

def process_data():
    print("🚀 [1/3] Connessione ai server MASE in corso...")
    
    # 1. Download dati
    raw_weekly = fetch_json(URL_WEEKLY)
    raw_monthly = fetch_json(URL_MONTHLY)
    
    print(f"📦 Ricevuti {len(raw_weekly)} record settimanali e {len(raw_monthly)} mensili.")

    # 2. Filtraggio Gasolio Auto (CODICE_PRODOTTO == 2)
    # --- SERIE SETTIMANALE ---
    weekly_history = []
    for row in raw_weekly:
        if row.get("CODICE_PRODOTTO") == 2 or row.get("NOME_PRODOTTO") == "Gasolio auto":
            pompa = parse_float(row.get("PREZZO"))
            accisa = parse_float(row.get("ACCISA"))
            iva = parse_float(row.get("IVA"))
            netto = parse_float(row.get("NETTO"))
            imponibile = round(netto + accisa, 4)
            
            weekly_history.append({
                "data": row.get("DATA_RILEVAZIONE"),
                "prezzo_pompa": pompa,
                "imponibile": imponibile,
                "netto": netto,
                "accisa": accisa,
                "iva": iva
            })
            
    # Ordina cronologicamente (dal più vecchio al più recente)
    weekly_history.sort(key=lambda x: x["data"])

    # --- SERIE MENSILE E ANNUALE ---
    monthly_history = []
    annual_history = {}

    for row in raw_monthly:
        if row.get("CODICE_PRODOTTO") == 2 or row.get("NOME_PRODOTTO") == "Gasolio auto":
            cod_mese = int(row.get("CODICE_MESE", 0))
            anno = int(row.get("ANNO", 0))
            pompa = parse_float(row.get("PREZZO"))
            accisa = parse_float(row.get("ACCISA"))
            iva = parse_float(row.get("IVA"))
            netto = parse_float(row.get("NETTO"))
            imponibile = round(netto + accisa, 4)
            
            item = {
                "anno": anno,
                "prezzo_pompa": pompa,
                "imponibile": imponibile,
                "netto": netto,
                "accisa": accisa,
                "iva": iva
            }

            # CODICE_MESE 13 = Medie Annuali Ufficiali
            if cod_mese == 13:
                annual_history[str(anno)] = item
            # CODICE_MESE da 1 a 12 = Mesi singoli
            elif 1 <= cod_mese <= 12:
                item["mese"] = cod_mese
                item["nome_mese"] = row.get("NOME_MESE")
                monthly_history.append(item)

    # Ordina mensile per anno e mese
    monthly_history.sort(key=lambda x: (x["anno"], x["mese"]))

    # 3. Creazione payload unificato
    output_data = {
        "metadata": {
            "source": "MASE - Ministero dell'Ambiente e della Sicurezza Energetica (DGSAIE)",
            "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "product": "Gasolio auto",
            "unit": "EUR/Litri",
            "weekly_count": len(weekly_history),
            "monthly_count": len(monthly_history),
            "annual_count": len(annual_history)
        },
        "annual_averages": annual_history,
        "monthly_history": monthly_history,
        "weekly_history": weekly_history
    }

    # 4. Salvataggio su file JSON locale
    output_dir = Path("data")
    output_dir.mkdir(exist_ok=True)
    output_file = output_dir / "gasolio_mase.json"

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)

    print(f"✅ [2/3] Elaborazione completata con successo!")
    print(f"📊 Gasolio Auto: {len(weekly_history)} settimane, {len(monthly_history)} mesi, {len(annual_history)} medie annuali.")
    print(f"💾 [3/3] File salvato in: {output_file.resolve()}")

    # Anteprima ultimo dato
    if weekly_history:
        ultimo = weekly_history[-1]
        print(f"\n🔍 ULTIMA RILEVAZIONE SETTIMANALE DISPONIBILE:")
        print(f"   📅 Data: {ultimo['data']}")
        print(f"   ⛽ Prezzo alla Pompa: {ultimo['prezzo_pompa']:.4f} €/L")
        print(f"   🏢 Imponibile B2B:    {ultimo['imponibile']:.4f} €/L")
        print(f"   🏭 Netto Industriale: {ultimo['netto']:.4f} €/L")
        print(f"   🏛️  Accisa:            {ultimo['accisa']:.4f} €/L")

if __name__ == "__main__":
    process_data()
