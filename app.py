import json
from pathlib import Path
from datetime import datetime, date, timedelta
import calendar
import streamlit as st
import pandas as pd
import plotly.graph_objects as go

# --- CONFIGURAZIONE PAGINA STREAMLIT ---
st.set_page_config(
    page_title="Fuel Surcharge Italia",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- FUNZIONI FORMATTAZIONE LOCALE ITALIANO ---
def fmt_it(val: float, decimals: int = 3, sign: bool = False) -> str:
    """Converte un valore numerico nel formato standard italiano con virgola."""
    prefix = "+" if sign and val > 0.00001 else ""
    formatted = f"{val:.{decimals}f}".replace(".", ",")
    return f"{prefix}{formatted}"

def get_week_meta(date_str: str) -> dict:
    """Calcola intervallo effettivo (Lunedì-Domenica) e numero settimana ISO."""
    dt = datetime.strptime(date_str, "%Y-%m-%d").date()
    obs_start = dt - timedelta(days=7)
    obs_end = dt - timedelta(days=1)
    iso_year, iso_week, _ = obs_start.isocalendar()
    label = f"Settimana {iso_week:02d} / {iso_year} (dal {obs_start.strftime('%d/%m')} al {obs_end.strftime('%d/%m/%Y')})"
    return {
        "raw_date": date_str,
        "label": label,
        "obs_start": obs_start,
        "obs_end": obs_end,
        "iso_week": iso_week,
        "iso_year": iso_year
    }

# --- STILE CSS ISTITUZIONALE CON FONT MASE (TITILLIUM WEB) ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Titillium+Web:ital,wght@0,300;0,400;0,600;0,700;0,900;1,400&display=swap');

    html, body, [class*="css"], .stMarkdown, .stSelectbox, .stRadio, .stNumberInput, .stDateInput {
        font-family: 'Titillium Web', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif !important;
    }

    .main-header {
        font-size: 2.1rem;
        font-weight: 700;
        letter-spacing: -0.5px;
        margin-bottom: 1.2rem;
        color: var(--text-color);
    }
    .hero-card {
        background-color: var(--secondary-background-color);
        border: 1px solid rgba(128, 128, 128, 0.25);
        border-radius: 10px;
        padding: 22px 26px;
        margin-bottom: 1.2rem;
    }
    .hero-title {
        font-size: 0.85rem;
        text-transform: uppercase;
        letter-spacing: 1.2px;
        color: var(--text-color);
        opacity: 0.75;
        font-weight: 600;
    }
    .hero-value {
        font-size: 2.6rem;
        font-weight: 800;
        line-height: 1.1;
        margin: 8px 0 14px 0;
        font-feature-settings: "tnum";
    }
    .hero-positive { color: #dc2626; }
    .hero-negative { color: #16a34a; }
    .hero-neutral { color: var(--text-color); }
    
    .metric-pill {
        display: inline-block;
        background: rgba(128, 128, 128, 0.10);
        border: 1px solid rgba(128, 128, 128, 0.18);
        border-radius: 6px;
        padding: 6px 12px;
        margin-right: 8px;
        margin-bottom: 6px;
        font-size: 0.85rem;
        color: var(--text-color);
    }
    .source-badge {
        font-size: 0.75rem;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        background-color: rgba(3, 105, 161, 0.12);
        color: #0284c7;
        border: 1px solid rgba(3, 105, 161, 0.25);
        padding: 4px 10px;
        border-radius: 4px;
        font-weight: 700;
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

# --- PARAMETRI URL ---
query_params = st.query_params
qp_price_type = query_params.get("price_type", "pompa")
if qp_price_type not in ["pompa", "netto"]:
    qp_price_type = "pompa"
qp_weight = int(query_params.get("weight", 30))
qp_granularity = query_params.get("granularity", "mensile")

# --- HEADER ISTITUZIONALE ---
col_h1, col_h2 = st.columns([3, 1])
with col_h1:
    st.markdown('<div class="main-header">Fuel Surcharge Italia</div>', unsafe_allow_html=True)

with col_h2:
    last_up = metadata.get("last_updated", "N/D")[:10]
    st.markdown(f"""
    <div style="text-align: right; padding-top: 5px;">
        <span class="source-badge">Dati Ufficiali MASE</span><br>
        <span style="font-size: 0.75rem; color: #64748b;">Rilevazione al: {last_up}</span>
    </div>
    """, unsafe_allow_html=True)

# --- 1. FILTRI GLOBALI (GRIGLIA 2x2) ---
st.markdown("##### Parametri Generali")

price_type_options = {
    "pompa": "Prezzo alla Pompa (Globale con IVA)",
    "netto": "Netto Industriale (Senza Tasse)"
}
price_keys = {
    "pompa": "prezzo_pompa",
    "netto": "netto"
}

# RIGA 1: Base Prezzo (2 Scelte) | Incidenza %
r1_col1, r1_col2 = st.columns(2)
with r1_col1:
    selected_price_type = st.selectbox(
        "Base di Prezzo Ministeriale:",
        options=list(price_type_options.keys()),
        format_func=lambda x: price_type_options[x],
        index=list(price_type_options.keys()).index(qp_price_type)
    )
    active_key = price_keys[selected_price_type]

with r1_col2:
    fuel_weight_pct = st.number_input(
        "Incidenza Costo Gasolio (%):",
        min_value=1,
        max_value=100,
        value=qp_weight,
        step=1
    )

# RIGA 2: Modalità Target | Selettore Dinamico Target
r2_col1, r2_col2 = st.columns(2)
with r2_col1:
    target_mode = st.selectbox(
        "Modalità Periodo Base (Target):",
        options=["Anno Solare", "Singolo Mese", "Range Personalizzato (Da / A)"]
    )

target_price = 0.0
target_price_pompa = 0.0
target_price_netto = 0.0
target_label = ""
target_end_date = date(2025, 12, 31)

with r2_col2:
    if target_mode == "Anno Solare":
        available_years = sorted(list(annual_dict.keys()), reverse=True)
        default_year_idx = available_years.index("2025") if "2025" in available_years else 0
        sel_year = st.selectbox("Anno Solare di Riferimento:", available_years, index=default_year_idx)
        target_data = annual_dict.get(sel_year, {})
        target_price = target_data.get(active_key, 0.0)
        target_price_pompa = target_data.get("prezzo_pompa", 0.0)
        target_price_netto = target_data.get("netto", 0.0)
        target_label = f"Media Anno {sel_year}"
        target_end_date = date(int(sel_year), 12, 31)

    elif target_mode == "Singolo Mese":
        df_m = pd.DataFrame(monthly_list)
        df_m["label"] = df_m["nome_mese"] + " " + df_m["anno"].astype(str)
        month_options = df_m["label"].tolist()[::-1]
        sel_month = st.selectbox("Mese di Riferimento:", month_options, index=0)
        matched_row = df_m[df_m["label"] == sel_month].iloc[0]
        target_price = matched_row[active_key]
        target_price_pompa = matched_row["prezzo_pompa"]
        target_price_netto = matched_row["netto"]
        target_label = f"Media {sel_month}"
        y_val, m_val = int(matched_row["anno"]), int(matched_row["mese"])
        last_day = calendar.monthrange(y_val, m_val)[1]
        target_end_date = date(y_val, m_val, last_day)

    else: # Range Personalizzato
        sub_col1, sub_col2 = st.columns(2)
        with sub_col1:
            d_start = st.date_input("Data Inizio:", value=date(2025, 1, 1))
        with sub_col2:
            d_end = st.date_input("Data Fine:", value=date(2025, 12, 31))
        
        df_w = pd.DataFrame(weekly_list)
        df_w["data_dt"] = pd.to_datetime(df_w["data"]).dt.date
        mask = (df_w["data_dt"] >= d_start) & (df_w["data_dt"] <= d_end)
        df_filtered = df_w.loc[mask]
        
        if len(df_filtered) > 0:
            target_price = float(df_filtered[active_key].mean())
            target_price_pompa = float(df_filtered["prezzo_pompa"].mean())
            target_price_netto = float(df_filtered["netto"].mean())
            target_label = f"Media {d_start.strftime('%d/%m/%y')} - {d_end.strftime('%d/%m/%y')}"
            target_end_date = d_end
        else:
            st.error("Nessuna rilevazione trovata per il range selezionato.")
            target_price = 1.0
            target_price_pompa = 1.0
            target_price_netto = 1.0
            target_end_date = d_end

# --- 2. SELETTORE PERIODO DA VALUTARE ---
st.markdown("---")

p_col1, p_col2 = st.columns(2)

with p_col1:
    granularity = st.radio(
        "Granularità Periodo da Valutare:",
        options=["Mensile", "Settimanale"],
        horizontal=True,
        index=0 if qp_granularity == "mensile" else 1
    )

# Sincronizzazione URL
st.query_params["price_type"] = selected_price_type
st.query_params["weight"] = str(fuel_weight_pct)
st.query_params["granularity"] = granularity.lower()

# Liste Dinamiche Storiche
mesi_italiani = ["Gennaio", "Febbraio", "Marzo", "Aprile", "Maggio", "Giugno", 
                 "Luglio", "Agosto", "Settembre", "Ottobre", "Novembre", "Dicembre"]

if granularity == "Mensile":
    month_dropdown_options = []
    for idx, item in enumerate(reversed(monthly_list)):
        m_name = item.get("nome_mese")
        y_num = item.get("anno")
        if idx == 0:
            label = f"Ultimo Mese Disponibile ({m_name} {y_num})"
        else:
            label = f"{m_name} {y_num}"
        month_dropdown_options.append((label, item))
    
    with p_col2:
        selected_month_tuple = st.selectbox(
            "Mese di Rilevazione Gasolio:",
            options=month_dropdown_options,
            format_func=lambda x: x[0]
        )
    
    selected_record = selected_month_tuple[1]
    current_price = selected_record.get(active_key, 0.0)
    eval_month_num = int(selected_record.get("mese"))
    eval_year = int(selected_record.get("anno"))
    eval_month_name = selected_record.get("nome_mese")
    
    if eval_month_num == 12:
        next_month_name = mesi_italiani[0]
        next_year = eval_year + 1
    else:
        next_month_name = mesi_italiani[eval_month_num]
        next_year = eval_year
        
    current_eval_label = f"{eval_month_name} {eval_year}"
    commercial_app_text = f"Fatture di {next_month_name} {next_year} (con slittamento mese precedente) oppure a consuntivo di {eval_month_name} {eval_year}"

else: # Settimanale
    weekly_meta_list = [get_week_meta(item["data"]) for item in weekly_list]
    week_dropdown_options = []
    
    for idx, meta in enumerate(reversed(weekly_meta_list)):
        item_data = weekly_list[-(idx + 1)]
        if idx == 0:
            label = f"Ultima Settimana Disponibile - {meta['label']}"
        else:
            label = meta["label"]
        week_dropdown_options.append((label, item_data, meta))
        
    with p_col2:
        selected_week_tuple = st.selectbox(
            "Settimana di Rilevazione Gasolio:",
            options=week_dropdown_options,
            format_func=lambda x: x[0]
        )
        
    selected_record = selected_week_tuple[1]
    selected_meta = selected_week_tuple[2]
    current_price = selected_record.get(active_key, 0.0)
    current_eval_label = selected_meta["label"]
    commercial_app_text = "Fatturazione settimanale o contratti a tariffa dinamica successivi alla rilevazione"

# CALCOLO SURCHARGE
delta_price = current_price - target_price
delta_price_pct = (delta_price / target_price) * 100 if target_price > 0 else 0.0
surcharge_pct = delta_price_pct * (fuel_weight_pct / 100.0)

# CLASSIFICAZIONE COLORE
if surcharge_pct > 0.00001:
    val_class = "hero-positive"
elif surcharge_pct < -0.00001:
    val_class = "hero-negative"
else:
    val_class = "hero-neutral"

# RENDERING HERO CARD
st.markdown(f"""
<div class="hero-card">
    <div class="hero-title">Fuel Surcharge Calcolato ({granularity})</div>
    <div class="hero-value {val_class}">{fmt_it(surcharge_pct, 2, sign=True)} %</div>
    <div>
        <span class="metric-pill"><b>Prezzo Rilevato:</b> {fmt_it(current_price, 3)} €/L ({current_eval_label})</span>
        <span class="metric-pill"><b>Prezzo Base:</b> {fmt_it(target_price, 3)} €/L ({target_label})</span>
        <span class="metric-pill"><b>Variazione Prezzo:</b> {fmt_it(delta_price_pct, 2, sign=True)}%</span>
        <span class="metric-pill"><b>Peso Applicato:</b> {fuel_weight_pct}%</span>
    </div>
    <div style="margin-top: 10px; font-size: 0.85rem; color: var(--text-color); opacity: 0.85;">
        <b>Applicazione Operativa:</b> {commercial_app_text}
    </div>
</div>
""", unsafe_allow_html=True)

# --- 3. TABELLA SCAGLIONI PREVISIONALI (3 COLONNE) ---
st.markdown("### Matrice a Scaglioni Previsionali (Passi da 0,5%)")
st.caption("Forchette di oscillazione del prezzo gasolio per trasparenza contrattuale preventiva.")

central_step = round(surcharge_pct * 2) / 2
steps = [round(central_step + i * 0.5, 2) for i in range(-5, 6)]

table_rows = []
for s in steps:
    s_min = s - 0.25
    s_max = s + 0.25
    
    p_min = target_price * (1 + (s_min / fuel_weight_pct))
    p_max = target_price * (1 + (s_max / fuel_weight_pct))
    
    is_current = (s_min <= surcharge_pct < s_max)
    
    table_rows.append({
        "Stato": "ATTUALE" if is_current else "",
        "Fuel Surcharge": f"{fmt_it(s, 2, sign=True)} %",
        "Forchetta Prezzo Gasolio": f"Da {fmt_it(p_min, 3)} € a {fmt_it(p_max, 3)} €"
    })

df_steps = pd.DataFrame(table_rows)
st.dataframe(df_steps, use_container_width=True, hide_index=True)

# --- 4. GRAFICI & ANALISI STORICA (2 TAB) ---
st.markdown("---")
st.markdown("### Analisi Storica e Trend Fuel Surcharge")

tab_chart, tab_surcharge = st.tabs([
    "Andamento Storico Prezzi", 
    "Trend Fuel Surcharge (%)"
])

with tab_chart:
    df_w_all = pd.DataFrame(weekly_list)
    
    # Calcolo data limite per il default a 3 anni
    latest_date_str = weekly_list[-1]["data"]
    latest_dt = datetime.strptime(latest_date_str, "%Y-%m-%d").date()
    start_3y_dt = latest_dt - timedelta(days=3 * 365)
    
    fig_prices = go.Figure()
    fig_prices.add_trace(go.Scatter(
        x=df_w_all["data"], y=df_w_all["prezzo_pompa"],
        mode="lines", name="Alla Pompa (Totale)",
        line=dict(color="#2563eb", width=2)
    ))
    fig_prices.add_trace(go.Scatter(
        x=df_w_all["data"], y=df_w_all["netto"],
        mode="lines", name="Netto Industriale (Materia Prima)",
        line=dict(color="#f59e0b", width=1.8)
    ))
    fig_prices.add_trace(go.Scatter(
        x=df_w_all["data"], y=df_w_all["accisa"],
        mode="lines", name="Accisa Fissa di Legge",
        line=dict(color="#10b981", width=1.5)
    ))
    
    fig_prices.update_layout(
        title="Evoluzione Prezzo Gasolio Auto Italia (Rilevazioni Settimanali MASE)",
        xaxis=dict(
            title="Data Rilevazione",
            range=[start_3y_dt.strftime("%Y-%m-%d"), latest_date_str],
            rangeselector=dict(
                buttons=list([
                    dict(count=1, label="1 Anno", step="year", stepmode="backward"),
                    dict(count=3, label="3 Anni", step="year", stepmode="backward"),
                    dict(count=5, label="5 Anni", step="year", stepmode="backward"),
                    dict(label="Tutto (2005)", step="all")
                ]),
                bgcolor="rgba(128, 128, 128, 0.12)",
                activecolor="#0284c7",
                font=dict(family="Titillium Web, sans-serif", size=12)
            ),
            rangeslider=dict(
                visible=True,
                thickness=0.08,
                bgcolor="rgba(128, 128, 128, 0.05)"
            ),
            type="date"
        ),
        yaxis_title="Euro al Litro (€/L)",
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.08, xanchor="right", x=1),
        margin=dict(l=20, r=20, t=75, b=20),
        template="plotly_white",
        font=dict(family="Titillium Web, sans-serif")
    )
    st.plotly_chart(fig_prices, use_container_width=True)

with tab_surcharge:
    surcharge_points = []
    
    if granularity == "Mensile":
        for row in monthly_list:
            y_r, m_r = int(row["anno"]), int(row["mese"])
            last_d = calendar.monthrange(y_r, m_r)[1]
            row_date = date(y_r, m_r, last_d)
            if row_date > target_end_date:
                p_pompa = row["prezzo_pompa"]
                d_pompa_pct = ((p_pompa - target_price_pompa) / target_price_pompa) * 100 if target_price_pompa > 0 else 0
                sur_pompa = d_pompa_pct * (fuel_weight_pct / 100.0)
                
                p_netto = row["netto"]
                d_netto_pct = ((p_netto - target_price_netto) / target_price_netto) * 100 if target_price_netto > 0 else 0
                sur_netto = d_netto_pct * (fuel_weight_pct / 100.0)
                
                surcharge_points.append({
                    "data_label": f"{row['nome_mese']} {y_r}",
                    "data_sort": row_date,
                    "sur_pompa": sur_pompa,
                    "sur_netto": sur_netto
                })
    else: # Settimanale
        for row in weekly_list:
            row_date = datetime.strptime(row["data"], "%Y-%m-%d").date()
            if row_date > target_end_date:
                p_pompa = row["prezzo_pompa"]
                d_pompa_pct = ((p_pompa - target_price_pompa) / target_price_pompa) * 100 if target_price_pompa > 0 else 0
                sur_pompa = d_pompa_pct * (fuel_weight_pct / 100.0)
                
                p_netto = row["netto"]
                d_netto_pct = ((p_netto - target_price_netto) / target_price_netto) * 100 if target_price_netto > 0 else 0
                sur_netto = d_netto_pct * (fuel_weight_pct / 100.0)
                
                w_meta = get_week_meta(row["data"])
                surcharge_points.append({
                    "data_label": f"Sett. {w_meta['iso_week']:02d}/{w_meta['iso_year']}",
                    "data_sort": row_date,
                    "sur_pompa": sur_pompa,
                    "sur_netto": sur_netto
                })
                
    if len(surcharge_points) > 0:
        df_sur = pd.DataFrame(surcharge_points)
        
        fig_sur = go.Figure()
        fig_sur.add_hline(y=0, line_dash="dash", line_color="#94a3b8", annotation_text="Base Target (0,00%)")
        
        # 1. Curva Base Pompa (Blu)
        fig_sur.add_trace(go.Scatter(
            x=df_sur["data_label"],
            y=df_sur["sur_pompa"],
            mode="lines+markers",
            name="Surcharge su Base Pompa",
            line=dict(color="#2563eb", width=2.5),
            marker=dict(size=5, color="#1d4ed8"),
            hovertemplate="<b>%{x}</b><br>Surcharge Base Pompa: %{y:.2f}%<extra></extra>"
        ))
        
        # 2. Curva Base Netto Industriale (Arancio)
        fig_sur.add_trace(go.Scatter(
            x=df_sur["data_label"],
            y=df_sur["sur_netto"],
            mode="lines+markers",
            name="Surcharge su Base Netto Industriale",
            line=dict(color="#f59e0b", width=2.5, dash="dot"),
            marker=dict(size=5, color="#d97706"),
            hovertemplate="<b>%{x}</b><br>Surcharge Base Netto: %{y:.2f}%<extra></extra>"
        ))
        
        fig_sur.update_layout(
            title=f"Confronto Evoluzione Fuel Surcharge (Post {target_label})",
            xaxis_title="Periodo",
            yaxis_title="Percentuale Surcharge (%)",
            hovermode="x unified",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            margin=dict(l=20, r=20, t=60, b=20),
            template="plotly_white",
            font=dict(family="Titillium Web, sans-serif")
        )
        st.plotly_chart(fig_sur, use_container_width=True)
    else:
        st.info(f"Il Periodo Target selezionato ({target_label}) coincide con i dati più recenti disponibili. Seleziona un Periodo Base antecedente (es. Anno 2025) per osservare l'evoluzione del Fuel Surcharge nel tempo.")
