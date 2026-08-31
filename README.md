# ⛽ FUEL SURCHARGE ITALIA
> **Indice e simulatore ufficiale di adeguamento costo carburante per l'autotrasporto merci (Gasolio Auto).**

[![Stato Dati MASE](https://github.com/acasablanca87/fuel-surcharge-italia/actions/workflows/update_data.yml/badge.svg)](https://github.com/acasablanca87/fuel-surcharge-italia/actions/workflows/update_data.yml)
[![Live WebApp](https://img.shields.io/badge/Online-GitHub%20Pages%20(WebAssembly)-0284c7?style=flat&logo=github)](https://acasablanca87.github.io/fuel-surcharge-italia/)
[![Python Version](https://img.shields.io/badge/Python-3.13%20%7C%203.14-blue?logo=python)](https://www.python.org/)
[![Framework](https://img.shields.io/badge/Framework-Streamlit%20%2F%20Stlite-FF4B4B?logo=streamlit)](https://streamlit.io/)

---

## 📌 Indice dei Contenuti
1. [Panoramica del Progetto](#-panoramica-del-progetto)
2. [Link Ufficiali e Accesso](#-link-ufficiali-e-accesso)
3. [Architettura di Sistema & Stack Tecnologico](#-architettura-di-sistema--stack-tecnologico)
4. [Pipeline Dati & Aggiornamenti Automatici (ETL)](#-pipeline-dati--aggiornamenti-automatici-etl)
5. [Modello Matematico & Metodologia di Calcolo](#-modello-matematico--metodologia-di-calcolo)
6. [Struttura della Repository](#-struttura-della-repository)
7. [Guida allo Sviluppo Locale (Mac & Windows)](#-guida-allo-sviluppo-locale-mac--windows)
8. [Parametri URL Condivisibili (Query Params)](#-parametri-url-condivisibili-query-params)
9. [Roadmap & Idee per Future Iterazioni](#-roadmap--idee-per-future-iterazioni)

---

## 📖 Panoramica del Progetto

**Fuel Surcharge Italia** è una web application concepita per eliminare fogli di calcolo manuali, errori di inserimento e contestazioni tariffarie tra vettori, spedizionieri e committenti nel settore del trasporto merci su gomma in Italia.

### Punti di Forza:
* **Fonte Primaria Certificata:** I prezzi del gasolio auto sono acquisiti direttamente dalle API Open Data del **Ministero dell'Ambiente e della Sicurezza Energetica (MASE - DGSAIE)**.
* **Architettura Serverless Zero-Sleep:** L'app pubblica gira in **WebAssembly (Stlite)** su GitHub Pages. Non ha server di backend che vanno in standby, garantendo un'operatività 24/7 a costo zero.
* **Flessibilità Contrattuale:** Consente di calcolare e simulare il sovrapprezzo carburante su base **Mensile** (con slittamento mese precedente $M-1$ o consuntivo diretto) e su base **Settimanale** (spot week $W-1$).
* **Trasparenza Fiscale:** Supporta le 3 diverse basi di prezzo adottate nel mercato: **Prezzo Globale alla Pompa**, **Imponibile B2B (extra-rete/cisterne)** e **Netto Industriale**.

---

## 🌐 Link Ufficiali e Accesso

* **Applicazione Web Online (Desktop & Mobile):**  
  👉 **`https://acasablanca87.github.io/fuel-surcharge-italia/`**
* **Repository GitHub:**  
  👉 **`https://github.com/acasablanca87/fuel-surcharge-italia`**
* **Fonte Dati Ministeriale MASE:**  
  👉 [Portale Open Data DGSAIE Prezzi Carburanti](https://sisen.mase.gov.it/dgsaie/prezzi-settimanali-carburanti)

---

## 🏗️ Architettura di Sistema & Stack Tecnologico

Il sistema adotta un'architettura disaccoppiata ad alte prestazioni:

```
[Server MASE DGSAIE]
        │
        ▼ (Ogni Martedì ore 11:30 UTC)
[GitHub Actions (Robot CI/CD)]
        │ ──► Esegue fetch_data.py
        │ ──► Filtra solo Gasolio Auto (Codice 2)
        │ ──► Converte da €/1.000L a €/L
        ▼
[data/gasolio_mase.json] (Unica Sorgente di Verità < 50KB)
        │
        ├─────────────────────────────────────────┐
        ▼                                         ▼
[Esecuzione Locale]                     [Deploy WebAssembly (Cloud)]
Streamlit su Python 3.13/3.14           Stlite (@stlite/mountable) su GitHub Pages
(Visualizzazione dev / offline)         (Accesso pubblico istantaneo senza server)
```

### Componenti dello Stack:
* **Linguaggio:** Python 3.13+ (Core ETL) / JavaScript ES6 (Stlite WebAssembly mounting).
* **Interfaccia Utente:** Streamlit 1.40+ con tipografia istituzionale PA Italiana (**Titillium Web**) e header corporate (**Plus Jakarta Sans**).
* **Grafici:** Plotly Graph Objects (serie storiche responsive, zoom presets a 1/3/5/All anni e confronto bi-curva).
* **Automazione:** GitHub Actions con runtime Node 24.

---

## ⚙️ Pipeline Dati & Aggiornamenti Automatici (ETL)

Il file `fetch_data.py` interroga settimanalmente i due endpoint ufficiali del Ministero:

1. **Endpoint Settimanale:**  
   `https://sisen.mase.gov.it/dgsaie/api/v1/weekly-prices/report/export?type=ALL&format=JSON&lang=it`
2. **Endpoint Mensile & Annuale:**  
   `https://sisen.mase.gov.it/dgsaie/api/v1/monthly-prices/export?format=JSON&lang=it`

### Regole di Elaborazione:
* **Filtro Univoco:** Viene isolato solo il prodotto con `"CODICE_PRODOTTO": 2` (*Gasolio auto*).
* **Aggregati Annuali Ufficiali:** Per le medie annuali (es. Anno 2025) viene prelevato direttamente il dato certificato MASE con `"CODICE_MESE": 13` (*"NOME_MESE": "Anno"*), azzerando approssimazioni matematiche.
* **Conversione Unità di Misura:** I valori ministeriali espressi in €/1.000 litri vengono divisi per $1.000$ per ottenere la precisione esatta in **€/Litro**.

---

## 📐 Modello Matematico & Metodologia di Calcolo

### 1. Variazione Percentuale del Carburante ($\Delta\%$)
Calcola lo scostamento relativo tra il prezzo del periodo in esame ($P_{\text{attuale}}$) e il prezzo target/base contrattuale ($P_{\text{target}}$):
$$\Delta\% = \left( \frac{P_{\text{attuale}} - P_{\text{target}}}{P_{\text{target}}} \right) \times 100$$

### 2. Fuel Surcharge Ponderato
La percentuale applicabile alla tariffa di trasporto è ottenuta moltiplicando $\Delta\%$ per la quota di incidenza del gasolio sui costi complessivi (default **30%**, conforme alla forchetta 25-35% delle tabelle dei costi di esercizio MIT):
$$\text{Fuel Surcharge \%} = \Delta\% \times \text{Incidenza \%} = \Delta\% \times 0,30$$

### 3. Matrice a Scaglioni (Passi da 0,5%)
Per garantire trasparenza preventiva, ogni scaglione tariffario $S$ copre un intervallo di $\pm 0,25\%$. Le soglie di oscillazione $[P_{\text{min}}, P_{\text{max}}]$ entro cui il gasolio può muoversi prima di far scattare lo scaglione successivo sono calcolate tramite formula inversa:
$$P_{\text{soglia}} = P_{\text{target}} \times \left(1 + \frac{S \pm 0,25}{\text{Incidenza \%}}\right)$$

### 4. Le 3 Basi di Prezzo
* **Prezzo Globale (alla Pompa):** Comprende Prodotto + Accise + IVA 22%.
* **Prezzo Imponibile (senza IVA):** Comprende Prodotto + Accise (standard acquisti extra-rete per cisterne aziendali).  
  *Nota di calcolo:* Poiché l'aliquota IVA è costante al 22%, la percentuale di Surcharge calcolata su base Globale e su base Imponibile è **identica al centesimo**, ma le soglie in €/L della tabella riflettono i valori esatti senza IVA.
* **Prezzo Netto Industriale:** Esclude sia IVA che Accise. Riflette la variazione pura della materia prima petrolifera, generando percentuali di variazione più marcate.

---

## 📁 Struttura della Repository

```text
fuel-surcharge-italia/
├── .github/
│   └── workflows/
│       └── update_data.yml       # Automazione settimanale GitHub Actions (Martedì 11:30 UTC)
├── data/
│   └── gasolio_mase.json         # Dataset unificato storicizzato (2005 - Oggi)
├── app.py                        # Codice principale Streamlit (UI, Logica, Reattività)
├── fetch_data.py                 # Script ETL di scaricamento e parsing dati MASE
├── index.html                    # Entrypoint WebAssembly (Stlite) per GitHub Pages
├── requirements.txt              # Dipendenze Python (Streamlit, Pandas, Plotly)
├── .gitignore                    # Regole di esclusione file locali e di cache
└── README.md                     # Documentazione tecnica del progetto
```

---

## 💻 Guida allo Sviluppo Locale (Mac & Windows)

### Requisiti:
* **Python 3.10+** (consigliato 3.13 o 3.14).
* **Git** installato e configurato.

### 1. Clonare il Progetto
```bash
# macOS (nella cartella ~/Projects) o Windows (in C:\Projects)
git clone https://github.com/acasablanca87/fuel-surcharge-italia.git
cd fuel-surcharge-italia
```

### 2. Installare le Dipendenze
```bash
pip install -r requirements.txt
```

### 3. Aggiornare i Dati Manualmente (Opzionale)
```bash
python fetch_data.py
```

### 4. Avviare l'Applicazione in Locale
```bash
# Avvio standard
streamlit run app.py

# Oppure (se il comando streamlit non è nel PATH di Windows)
python -m streamlit run app.py
```
L'app si aprirà automaticamente su `http://localhost:8501`.

### 5. Sincronizzazione Modifiche con GitHub & Web
Per salvare le modifiche e pubblicarle istantaneamente su GitHub Pages:
```bash
git add app.py
git commit -m "descrizione della modifica"
git pull --rebase && git push
```

---

## 🔗 Parametri URL Condivisibili (Query Params)

L'applicazione supporta il deep-linking tramite parametri URL per condividere configurazioni contrattuali pre-impostate:

| Parametro | Valori Ammessi | Descrizione |
| :--- | :--- | :--- |
| `price_type` | `pompa`, `imponibile`, `netto` | Seleziona la base di prezzo ministeriale |
| `weight` | Intero da `1` a `100` (es. `30`, `28`) | Imposta la percentuale di incidenza costo gasolio |
| `granularity` | `mensile`, `settimanale` | Seleziona la granularità temporale di valutazione |

*Esempio di link pre-configurato per contratti B2B al 28% su base Imponibile:*  
`https://acasablanca87.github.io/fuel-surcharge-italia/?price_type=imponibile&weight=28&granularity=mensile`

---

## 🚀 Roadmap & Idee per Future Iterazioni

Spunti architetturali per future sessioni di sviluppo:
- [ ] **Esportazione Prospetti:** Pulsante per scaricare la Matrice a Scaglioni in formato Excel (.xlsx) o estratto tariffario in PDF.
- [ ] **Grafico con Eventi Chiave:** Annotazioni visive sul grafico dei prezzi per evidenziare shock fiscali (es. tagli e ripristini accise).
- [ ] **Integrazione AI / Assistente LLM:** Chatbot interattivo integrato per interrogare la serie storica dei prezzi in linguaggio naturale (es. tramite API Gemini / OpenAI).
- [ ] **Dominio Personalizzato:** Collegamento di un dominio di secondo livello (es. `fuelsurchargeitalia.it`).

---

*Progetto sviluppato con approccio Vibe-Coding e architettura Serverless WebAssembly.*
```