```markdown
# ⛽ FUEL SURCHARGE ITALIA
> **Indice, benchmark e simulatore ufficiale di adeguamento costo carburante per l'autotrasporto merci (Gasolio Auto).**

[![Stato Dati MASE](https://github.com/acasablanca87/fuel-surcharge-italia/actions/workflows/update_data.yml/badge.svg)](https://github.com/acasablanca87/fuel-surcharge-italia/actions/workflows/update_data.yml)
[![Keep-Alive Streamlit](https://github.com/acasablanca87/fuel-surcharge-italia/actions/workflows/keep_alive.yml/badge.svg)](https://github.com/acasablanca87/fuel-surcharge-italia/actions/workflows/keep_alive.yml)
[![GitHub Pages WebAssembly](https://img.shields.io/badge/Deploy%201-GitHub%20Pages%20(Serverless)-0284c7?style=flat&logo=github)](https://acasablanca87.github.io/fuel-surcharge-italia/)
[![Streamlit Cloud Native](https://img.shields.io/badge/Deploy%202-Streamlit%20Cloud%20(Nativo)-FF4B4B?style=flat&logo=streamlit)](https://fuel-surcharge-italia.streamlit.app)
[![Python Version](https://img.shields.io/badge/Python-3.13%20%7C%203.14-blue?logo=python)](https://www.python.org/)

---

## 📌 Indice dei Contenuti
1. [Panoramica del Progetto](#-panoramica-del-progetto)
2. [Piattaforme Online Ufficiali (Doppio Canale)](#-piattaforme-online-ufficiali-doppio-canale)
3. [Architettura di Sistema & Robot CI/CD](#-architettura-di-sistema--robot-cicd)
4. [La Suite Funzionale (I 4 Tab Specialistici)](#-la-suite-funzionale-i-4-tab-specialistici)
5. [Modello Matematico & Metodologia di Calcolo](#-modello-matematico--metodologia-di-calcolo)
6. [Struttura Completa della Repository](#-struttura-completa-della-repository)
7. [Guida allo Sviluppo Locale (Mac & Windows)](#-guida-allo-sviluppo-locale-mac--windows)
8. [Parametri URL Condivisibili (Query Params)](#-parametri-url-condivisibili-query-params)
9. [Roadmap per Future Iterazioni](#-roadmap-per-future-iterazioni)

---

## 📖 Panoramica del Progetto

**Fuel Surcharge Italia** è una piattaforma digitale concepita per eliminare fogli di calcolo manuali, errori di inserimento e contestazioni tariffarie tra vettori, spedizionieri e committenti nel settore del trasporto merci su gomma in Italia.

### Punti di Forza:
* **Fonte Primaria Certificata:** Prezzi del gasolio auto acquisiti direttamente tramite API Open Data dal **Ministero dell'Ambiente e della Sicurezza Energetica (MASE - DGSAIE)**.
* **Architettura a Doppio Canale:** Esecuzione serverless in **WebAssembly (Stlite)** su GitHub Pages (zero-server, non va mai in sleep) e deploy parallelo su **Streamlit Cloud** monitorato da automazione Keep-Alive.
* **Flessibilità Contrattuale:** Calcolo su base **Mensile** (con slittamento mese precedente $M-1$ o consuntivo diretto) e su base **Settimanale** (spot week $W-1$).
* **Trasparenza Fiscale Completa:** Gestione delle 3 basi di prezzo di settore: **Prezzo Globale alla Pompa**, **Imponibile B2B (acquisti extra-rete per cisterne aziendali)** e **Netto Industriale**.

---

## 🌐 Piattaforme Online Ufficiali (Doppio Canale)

| Piattaforma | URL di Accesso | Tecnologia | Uptime / Caratteristiche |
| :--- | :--- | :--- | :--- |
| **Canale 1 (Principale)** | 👉 **[`acasablanca87.github.io/fuel-surcharge-italia`](https://acasablanca87.github.io/fuel-surcharge-italia/)** | Stlite (WebAssembly) su GitHub Pages | 🟢 **100% Serverless** (Zero backend, non può andare in sleep per definizione) |
| **Canale 2 (Nativo)** | 👉 **[`fuel-surcharge-italia.streamlit.app`](https://fuel-surcharge-italia.streamlit.app)** | Streamlit Community Cloud | 🟢 **Container Nativo** (Monitorato da Keep-Alive ogni 48 ore) |
| **Fonte Ministeriale** | 👉 [Portale DGSAIE Prezzi Carburanti](https://sisen.mase.gov.it/dgsaie/prezzi-settimanali-carburanti) | Open Data MASE | 🏛️ Aggiornato ogni Martedì |

---

## 🏗️ Architettura di Sistema & Robot CI/CD

Il sistema adotta un'architettura disaccoppiata ad alte prestazioni alimentata da **due automazioni serverless su GitHub Actions**:

```
                              [Server MASE DGSAIE]
                                       │
                                       ▼ (Ogni Martedì ore 11:30 UTC)
                         [GitHub Action: update_data.yml]
                                       │ ──► Esegue fetch_data.py
                                       │ ──► Filtra solo Gasolio Auto (Codice 2)
                                       │ ──► Converte da €/1.000L a €/L
                                       ▼
                       [data/gasolio_mase.json] (< 50KB)
                                       │
          ┌────────────────────────────┴───────────────────────────┐
          ▼                                                        ▼
[Canale 1: GitHub Pages]                                 [Canale 2: Streamlit Cloud]
Stlite WebAssembly client-side                           Container Python nativo
(index.html + app.py statici)                            (Monitorato da keep_alive.yml ogni 48h)
```

### I Robot GitHub Actions:
1. **`update_data.yml` (ETL Prezzi MASE):** Si sveglia ogni martedì alle 13:30 italiane, scarica i dati ufficiali, aggiorna la serie storica e invia un commit automatico.
2. **`keep_alive.yml` (Anti-Sleep Monitor):** Si attiva ogni 48 ore alle 09:00 italiane per effettuare un health-check sul server di Streamlit Cloud mantenendo il container sempre attivo.

---

## 🧰 La Suite Funzionale (I 4 Tab Specialistici)

Nella sezione inferiore dell'applicazione è disponibile una suite completa di 4 strumenti dedicati:

1. **📊 Andamento Storico Prezzi:** Grafico Plotly interattivo delle 4 componenti dal 2005 a oggi, con preset di zoom rapido (`1 Anno`, `3 Anni` default, `5 Anni`, `Tutto`) e range-slider inferiore.
2. **📈 Trend Fuel Surcharge (%):** Confronto bi-curva in tempo reale tra il Surcharge applicato su *Base Pompa* e su *Base Netto Industriale* calcolato a partire dal periodo target.
3. **🔍 Consultazione Libera Prezzi (Quick Lookup a 5 Vie):** Motore di ricerca istantaneo dei prezzi storici svincolato dalle formule di surcharge, con supporto per:
   * *Intervallo Date (da / a)* (preimpostato di default sul mese in corso con calcolo media, min e max).
   * *Anno Solare* (aggregati ufficiali MASE).
   * *Singolo Mese* (medie mensili consolidate).
   * *Settimana Specifica* (rilevazioni numerate ISO).
   * *Data Esatta / Documento* (inserimento del giorno del viaggio con aggancio automatico alla settimana MASE in vigore).
4. **🧮 Simulatore Libero (What-If):** Calcolatore manuale per simulare scenari previsionali o gare d'appalto impostando liberamente prezzo base, prezzo stimato e incidenza %.

---

## 📐 Modello Matematico & Metodologia di Calcolo

### 1. Variazione Percentuale del Carburante ($\Delta\%$)
Calcola lo scostamento relativo tra il prezzo del carburante del periodo di valutazione ($P_{\text{attuale}}$) e il prezzo target contrattuale ($P_{\text{target}}$):
$$\Delta\% = \left( \frac{P_{\text{attuale}} - P_{\text{target}}}{P_{\text{target}}} \right) \times 100$$

### 2. Fuel Surcharge Ponderato
Moltiplica la variazione $\Delta\%$ per la quota di incidenza del gasolio sul costo chilometrico complessivo (default **30%**, conforme alla forchetta 25-35% delle tabelle dei costi di esercizio MIT per veicoli pesanti):
$$\text{Fuel Surcharge \%} = \Delta\% \times \text{Incidenza \%} = \Delta\% \times 0,30$$

### 3. Matrice a Scaglioni (Passi da 0,5%)
Ogni scaglione tariffario $S$ copre un intervallo centrato di $\pm 0,25\%$. Le soglie di prezzo minimo e massimo $[P_{\text{min}}, P_{\text{max}}]$ entro cui il gasolio può oscillare sono calcolate tramite formula analitica inversa:
$$P_{\text{soglia}} = P_{\text{target}} \times \left(1 + \frac{S \pm 0,25}{\text{Incidenza \%}}\right)$$

### 4. Le 3 Basi di Prezzo
* **Prezzo Globale (alla Pompa):** Comprende Prodotto + Accise + IVA 22%.
* **Prezzo Imponibile (senza IVA):** Comprende Prodotto + Accise (standard per acquisti extra-rete in cisterne aziendali).  
  *Nota di calcolo:* Poiché l'IVA al 22% è costante, la percentuale di Surcharge su base Globale e su base Imponibile è **identica al centesimo**, ma le forchette in €/L della matrice riflettono i valori esatti senza IVA.
* **Prezzo Netto Industriale:** Esclude sia IVA che Accise. Riflette la variazione pura della materia prima petrolifera, generando oscillazioni percentuali più accentuate.

---

## 📁 Struttura Completa della Repository

```text
fuel-surcharge-italia/
├── .github/
│   └── workflows/
│       ├── update_data.yml       # Robot ETL MASE settimanale (Martedì 11:30 UTC)
│       └── keep_alive.yml        # Robot Keep-Alive per Streamlit Cloud (Ogni 48h)
├── data/
│   └── gasolio_mase.json         # Dataset unificato storicizzato (2005 - Oggi)
├── app.py                        # Codice principale Streamlit (UI, Logica, Reattività, 4 Tab)
├── fetch_data.py                 # Script ETL di estrazione e normalizzazione dati MASE
├── index.html                    # Entrypoint WebAssembly (Stlite) per GitHub Pages
├── requirements.txt              # Dipendenze Python (Streamlit, Pandas, Plotly)
├── .gitignore                    # Regole di esclusione file di sistema e cache
└── README.md                     # Documentazione tecnica ufficiale del progetto
```

---

## 💻 Guida allo Sviluppo Locale (Mac & Windows)

### Requisiti:
* **Python 3.10+** (consigliato 3.13 o 3.14).
* **Git** installato e configurato.

### 1. Clonare il Repository
```bash
# Su macOS (~/Projects) o Windows (C:\Projects)
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

# Su Windows (se il comando streamlit non è nel PATH)
python -m streamlit run app.py
```
L'app sarà attiva in tempo reale su `http://localhost:8501`.

### 5. Sincronizzazione Universale Git
Per inviare le modifiche e aggiornare simultaneamente sia **GitHub Pages** che **Streamlit Cloud**:
```bash
git add .
git commit -m "descrizione della modifica"
git pull --rebase && git push
```

---

## 🔗 Parametri URL Condivisibili (Query Params)

L'applicazione supporta il deep-linking tramite parametri URL per inviare configurazioni contrattuali pre-impostate via email, Teams o preventivi:

| Parametro | Valori Ammessi | Descrizione |
| :--- | :--- | :--- |
| `price_type` | `pompa`, `imponibile`, `netto` | Seleziona la base di prezzo ministeriale |
| `weight` | Intero da `1` a `100` (es. `30`, `28`) | Imposta la percentuale di incidenza costo gasolio |
| `granularity` | `mensile`, `settimanale` | Seleziona la granularità temporale di valutazione |

*Esempio di link pre-configurato per contratti B2B al 28% su base Imponibile:*  
`https://acasablanca87.github.io/fuel-surcharge-italia/?price_type=imponibile&weight=28&granularity=mensile`

---

## 🚀 Roadmap per Future Iterazioni

Spunti architetturali per sessioni di sviluppo future:
- [ ] **Esportazione Reportistica:** Download della Matrice a Scaglioni in formato Excel (.xlsx) ed estratto tariffario certificato in PDF.
- [ ] **Integrazione AI / Assistente LLM:** Box interattivo con API per interrogare lo storico dei prezzi in linguaggio naturale (es. *"Di quanto sono aumentate le accise tra il 2022 e il 2024?"*).
- [ ] **Dominio di Secondo Livello:** Collegamento di un dominio personalizzato (es. `www.fuelsurchargeitalia.it`).

---

*Progetto sviluppato con approccio Vibe-Coding e architettura Serverless WebAssembly.*
```