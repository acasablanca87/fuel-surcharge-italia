import json
from pathlib import Path
from datetime import datetime, date
import streamlit as st
import pandas as pd
import plotly.graph_objects as go

# --- CONFIGURAZIONE PAGINA STREAMLIT ---
st.set_page_config(
    page_title="Fuel Surcharge Italia | Benchmark Gasolio Autotrasporto",
    page_icon="⛽",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- STILE CSS PERSONALIZZATO (MODERN DARK/LIGHT RESPONSIVE) ---
st.markdown("""
<style>
    .main-header {
        font-size: 2.2rem;
        font-weight: 800;
        letter-spacing: -0.5px;
        margin-bottom: 0px;
    }
    .sub-header {
        color: #6c757d;
        font-size: 0.95rem;
        margin-bottom: 1.5rem;
    }
    .hero-card {
        background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
        border: 1px solid #334155;
        border-radius: 16px;
        padding: 24px;
        color: #ffffff;
        box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.2);
        margin-bottom: 1.5rem;
    }
    .hero-title {
        font-size: 0.85rem;
        text-transform: uppercase;
        letter-spacing: 1.2px;
        color: #94a3b8;
        font-weight: 600;
    }
    .hero-value {
        font-size: 3.5rem;
        font-weight: 900;
        line-height: 1.1;
        margin: 10px 0;
    }
    .hero-positive { color: #f87171; }
    .hero-negative { color: #4ade80; }
    .hero-neutral { color: #cbd5e1; }
    .metric-pill {
        display: inline-block;
        background: rgba(255, 255, 255, 0.08);
        border-radius: 8px;
        padding: 6px 12px;
        margin-right: 8px;
        font-size: 0.85rem;
    }
    .source-badge {
        font-size: 0.8rem;
        background-color: #e0f2fe;
        color: #0369a1;
        padding: 4px 10px;
        border-radius: 20px;
        font-weight: 600;
        display: inline-block;
    }
</style>
""", unsafe_allow_html=True)

# --- CARICAMENTO DATI CERTIFICATI MASE ---
@st.cache_data(ttl=3600)
def load_data() -> dict:
    data_path = Path("data/gasolio_mase.json")
    if not data_path.exists():
        import fetch_data
        fetch_data.process_data()
    with open(data_path, "r", encoding="utf-8") as f:
        return json.load(f)

data = load_data()
weekly_list = data.get("weekly_history", [])
monthly_list = data.get("monthly_history", [])
annual_dict = data.get("annual_averages", {})
metadata = data.get("metadata", {})

# --- LETTURA / SCRITTURA PARAMETRI URL ---
query_params = st.query_params
qp_price_type = query_params.get("price_type", "pompa")
qp_weight = int(query_params.get("weight", 30))
qp_view = query_params.get("view", "monthly")

# --- HEADER ISTITUZIONALE ---
col_h1, col_h2 = st.columns([3, 1])
with col_h1:
    st.markdown('<div class="main-header">⛽ Fuel Surcharge Italia</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="sub-header">Indice Ufficiale di Adeguamento Carburante per l\'Autotrasporto Merci (D.Lgs. 286/2005)</div>', unsafe_allow_html=True)

with col_h2:
    last_up = metadata.get("last_updated", "N/D")[:10]
    st.markdown(f"""
    <div style="text-align: right; padding-top: 10px;">
        <span class="source-badge">● MASE Ufficiale</span><br>
        <span style="font-size: 0.75rem; color: #64748b;">Aggiornato al: {last_up}</span>
    </div>
    """, unsafe_allow_html=True)

# --- 1. FILTRI GLOBALI A MONTE ---
st.markdown("##### ⚙️ Configurazione Parametri Globali")
cfg_col1, cfg_col2, cfg_col3 = st.columns([1.5, 1.5, 1])

price_type_options = {
    "pompa": "Prezzo alla Pompa (Globale con IVA)",
    "imponibile": "Imponibile B2B (Netto + Accise)",
    "netto": "Netto Industriale (Senza Tasse)"
}
price_keys = {
    "pompa": "prezzo_pompa",
    "imponibile": "imponibile",
    "netto": "netto"
}

with cfg_col1:
    selected_price_type = st.selectbox(
        "Base di Prezzo Ministeriale:",
        options=list(price_type_options.keys()),
        format_func=lambda x: price_type_options[x],
        index=list(price_type_options.keys()).index(qp_price_type) if qp_price_type in price_type_options else 0
    )
    active_key = price_keys[selected_price_type]

with cfg_col2:
    target_mode = st.selectbox(
        "Modalità Periodo Base (Target):",
        options=["Anno Solare", "Singolo Mese", "Range Personalizzato (Da / A)"]
    )

with cfg_col3:
    fuel_weight_pct = st.number_input(
        "Incidenza Gasolio (%):",
        min_value=1,
        max_value=100,
        value=qp_weight,
        step=1,
        help="Standard MIT per veicoli pesanti: 25% - 35% (Default: 30%)"
    )

# Sincronizza parametri nell'URL per condivisione link
st.query_params["price_type"] = selected_price_type
st.query_params["weight"] = str(fuel_weight_pct)
st.query_params["view"] = qp_view

# --- DETERMINAZIONE PREZZO TARGET ---
target_price = 0.0
target_label = ""

if target_mode == "Anno Solare":
    available_years = sorted(list(annual_dict.keys()), reverse=True)
    default_year_idx = available_years.index("2025") if "2025" in available_years else 0
    sel_year = st.selectbox("Seleziona Anno Solare di Riferimento:", available_years, index=default_year_idx)
    target_data = annual_dict.get(sel_year, {})
    target_price = target_data.get(active_key, 0.0)
    target_label = f"Media Anno {sel_year}"

elif target_mode == "Singolo Mese":
    df_m = pd.DataFrame(monthly_list)
    df_m["label"] = df_m["nome_mese"] + " " + df_m["anno"].astype(str)
    month_options = df_m["label"].tolist()[::-1]
    sel_month = st.selectbox("Seleziona Mese di Riferimento:", month_options, index=0)
    matched_row = df_m[df_m["label"] == sel_month].iloc[0]
    target_price = matched_row[active_key]
    target_label = f"Media {sel_month}"

else: # Range Personalizzato
    r_col1, r_col2 = st.columns(2)
    with r_col1:
        d_start = st.date_input("Data Inizio:", value=date(2025, 1, 1))
    with r_col2:
        d_end = st.date_input("Data Fine:", value=date(2025, 12, 31))
    
    df_w = pd.DataFrame(weekly_list)
    df_w["data_dt"] = pd.to_datetime(df_w["data"]).dt.date
    mask = (df_w["data_dt"] >= d_start) & (df_w["data_dt"] <= d_end)
    df_filtered = df_w.loc[mask]
    
    if len(df_filtered) > 0:
        target_price = round(df_filtered[active_key].mean(), 4)
        target_label = f"Media dal {d_start.strftime('%d/%m/%Y')} al {d_end.strftime('%d/%m/%Y')}"
    else:
        st.error("Nessuna rilevazione MASE trovata per il range selezionato.")
        target_price = 1.0

# --- 2. HERO SECTION & DUAL-TOGGLE ---
st.markdown("---")

view_col1, view_col2 = st.columns([1.5, 2.5])
with view_col1:
    view_selection = st.radio(
        "Periodo di Fatturazione Attuale:",
        options=["Mensile (M-1)", "Settimanale (W-1)"],
        horizontal=True,
        index=0 if qp_view == "monthly" else 1
    )

# Determinazione Prezzo Attuale
if "Mensile" in view_selection:
    current_record = monthly_list[-1]
    current_price = current_record.get(active_key, 0.0)
    current_label = f"{current_record.get('nome_mese')} {current_record.get('anno')} (M-1)"
else:
    current_record = weekly_list[-1]
    current_price = current_record.get(active_key, 0.0)
    current_label = f"Settimana {current_record.get('data')} (W-1)"

# CALCOLO SURCHARGE
delta_price = current_price - target_price
delta_price_pct = (delta_price / target_price) * 100 if target_price > 0 else 0.0
surcharge_pct = delta_price_pct * (fuel_weight_pct / 100.0)

# CLASSIFICAZIONE COLORE
if surcharge_pct > 0.001:
    val_class = "hero-positive"
    sign_prefix = "+"
elif surcharge_pct < -0.001:
    val_class = "hero-negative"
    sign_prefix = ""
else:
    val_class = "hero-neutral"
    sign_prefix = ""

# RENDERING HERO CARD
st.markdown(f"""
<div class="hero-card">
    <div class="hero-title">Fuel Surcharge Applicabile ({view_selection})</div>
    <div class="hero-value {val_class}">{sign_prefix}{surcharge_pct:.2f} %</div>
    <div style="margin-top: 15px;">
        <span class="metric-pill">⛽ <b>Prezzo Attuale:</b> {current_price:.4f} €/L ({current_label})</span>
        <span class="metric-pill">🎯 <b>Prezzo Base:</b> {target_price:.4f} €/L ({target_label})</span>
        <span class="metric-pill">📊 <b>Variazione Grezza:</b> {sign_prefix}{delta_price_pct:.2f}%</span>
        <span class="metric-pill">⚖️ <b>Peso Applicato:</b> {fuel_weight_pct}%</span>
    </div>
</div>
""", unsafe_allow_html=True)

# --- 3. TABELLA SCAGLIONI PREVISIONALI (+- 0.5%) ---
st.markdown("### 📋 Matrice a Scaglioni Previsionali (Passi da 0,5%)")
st.caption("Forchette di oscillazione del gasolio per pianificazione e trasparenza tariffaria contrattuale.")

# Generazione scaglioni centrati attorno al surcharge attuale
central_step = round(surcharge_pct * 2) / 2 # arrotonda allo 0.5 più vicino
steps = [round(central_step + i * 0.5, 2) for i in range(-5, 6)]

table_rows = []
for s in steps:
    # Formula inversa per calcolare le soglie di prezzo Da / A
    s_min = s - 0.25
    s_max = s + 0.25
    
    p_min = target_price * (1 + (s_min / fuel_weight_pct))
    p_max = target_price * (1 + (s_max / fuel_weight_pct))
    
    is_current = (s_min <= surcharge_pct < s_max)
    
    table_rows.append({
        "Stato": "👉 ATTUALE" if is_current else "",
        "Fuel Surcharge": f"{'+' if s > 0 else ''}{s:.2f} %",
        "Prezzo Minimo (€/L)": f"{p_min:.4f}",
        "Prezzo Massimo (€/L)": f"{p_max:.4f}",
        "Forchetta Prezzo Gasolio": f"Da {p_min:.4f} € a {p_max:.4f} €"
    })

df_steps = pd.DataFrame(table_rows)
st.dataframe(df_steps, use_container_width=True, hide_index=True)

# --- 4. GRAFICO STORICO & TRACKER ACCISE ---
st.markdown("---")
st.markdown("### 📈 Trend Storico Ufficiale e Tracker Fiscale")

tab_chart, tab_accise = st.tabs(["📊 Andamento Storico Prezzi", "🏛️ Monitor Accise & Imposte"])

with tab_chart:
    df_w_all = pd.DataFrame(weekly_list)
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df_w_all["data"], y=df_w_all["prezzo_pompa"],
        mode="lines", name="Alla Pompa (Totale)",
        line=dict(color="#3b82f6", width=2)
    ))
    fig.add_trace(go.Scatter(
        x=df_w_all["data"], y=df_w_all["imponibile"],
        mode="lines", name="Imponibile B2B (Netto + Accise)",
        line=dict(color="#10b981", width=1.5, dash="dot")
    ))
    fig.add_trace(go.Scatter(
        x=df_w_all["data"], y=df_w_all["netto"],
        mode="lines", name="Netto Industriale (Materia Prima)",
        line=dict(color="#f59e0b", width=1.5)
    ))
    
    fig.update_layout(
        title="Evoluzione Prezzo Gasolio Auto Italia (Rilevazioni Settimanali MASE)",
        xaxis_title="Data Rilevazione",
        yaxis_title="Euro al Litro (€/L)",
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=20, r=20, t=60, b=20),
        template="plotly_white"
    )
    st.plotly_chart(fig, use_container_width=True)

with tab_accise:
    latest_accisa = weekly_list[-1]["accisa"]
    latest_iva = weekly_list[-1]["iva"]
    latest_pompa = weekly_list[-1]["prezzo_pompa"]
    accisa_pct = (latest_accisa / latest_pompa) * 100 if latest_pompa > 0 else 0
    
    col_a1, col_a2, col_a3 = st.columns(3)
    col_a1.metric("Accisa Corrente", f"{latest_accisa:.4f} €/L", f"{accisa_pct:.1f}% sul prezzo pompa")
    col_a2.metric("Aliquota IVA", "22.0%", f"{latest_iva:.4f} €/L")
    col_a3.metric("Imposte Totali sul Gasolio", f"{(latest_accisa + latest_iva):.4f} €/L", f"{((latest_accisa + latest_iva)/latest_pompa*100):.1f}% del prezzo finale")
    
    st.markdown("""
    #### ℹ️ Note Fiscali per l'Autotrasporto:
    * L'**Accisa** è un importo fisso in euro/litro stabilito per legge e non varia con le oscillazioni del greggio, tranne in caso di decreti governativi dedicati.
    * Le aziende di autotrasporto merci in conto proprio o conto terzi (con mezzi di massa massima pari o superiore a 7,5 tonnellate) hanno diritto al rimborso parziale periodico dell'accisa (c.d. **Carbon Tax / Gasolio Professionale** tramite Agenzia delle Dogane).
    """)
