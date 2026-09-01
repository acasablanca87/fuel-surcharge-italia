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
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@700;800;900&family=Titillium+Web:ital,wght@0,300;0,400;0,600;0,700;0,900;1,400&display=swap');

    html, body, [class*="css"], .stMarkdown, .stSelectbox, .stRadio, .stNumberInput, .stDateInput {
        font-family: 'Titillium Web', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif !important;
    }

    .main-header {
        font-family: 'Plus Jakarta Sans', sans-serif !important;
        font-size: 2.1rem;
        font-weight: 800;
        text-transform: uppercase;
        letter-spacing: 0.8px;
        margin-bottom: 1.2rem;
        color: var(--text-color) !important;
    }

    /* GRASSETTO SUI MENU A TENDINA */
    div[data-baseweb="select"] {
        font-weight: 600 !important;
    }

    /* HERO CARD ADATTIVA */
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

# --- GESTIONE STATO INIZIALE & URL (ANTI-RACE CONDITION) ---
price_type_options = {
    "pompa": "Prezzo Globale (alla pompa)",
    "imponibile": "Prezzo Imponibile (SENZA IVA ma con Accise)",
    "netto": "Prezzo Netto Industriale (SENZA IVA e SENZA ACCISE)"
}
price_keys = {
    "pompa": "prezzo_pompa",
    "imponibile": "imponibile",
    "netto": "netto"
}

# Inizializzazione Session State dai parametri URL solo la prima volta
if "price_type" not in st.session_state:
    qp_pt = st.query_params.get("price_type", "pompa")
    st.session_state["price_type"] = qp_pt if qp_pt in price_type_options else "pompa"

if "weight" not in st.session_state:
    try:
        st.session_state["weight"] = int(st.query_params.get("weight", 30))
    except (ValueError, TypeError):
        st.session_state["weight"] = 30

if "granularity" not in st.session_state:
    qp_gr = st.query_params.get("granularity", "mensile")
    st.session_state["granularity"] = "Settimanale" if str(qp_gr).lower() == "settimanale" else "Mensile"

# Callback per sincronizzare l'URL solo quando l'utente agisce sui controlli
def sync_url():
    st.query_params["price_type"] = st.session_state.get("price_type", "pompa")
    st.query_params["weight"] = str(st.session_state.get("weight", 30))
    st.query_params["granularity"] = str(st.session_state.get("granularity", "Mensile")).lower()

# --- HEADER ISTITUZIONALE ---
col_h1, col_h2 = st.columns([2.8, 1.2])
with col_h1:
    st.markdown("""
    <div class="main-header">FUEL SURCHARGE ITALIA</div>
    <div style="font-size: 0.82rem; font-weight: 700; color: #64748b; letter-spacing: 1.2px; text-transform: uppercase; margin-top: -15px; margin-bottom: 12px;">
        da Rilevazioni Ufficiali di Gasolio Auto
    </div>
    """, unsafe_allow_html=True)

with col_h2:
    # Estrazione della data ufficiale dell'ultima rilevazione MASE in formato italiano (GG/MM/AAAA)
    if weekly_list:
        raw_latest_date = weekly_list[-1]["data"]
        try:
            last_mase_date = datetime.strptime(raw_latest_date, "%Y-%m-%d").strftime("%d/%m/%Y")
        except (ValueError, TypeError):
            last_mase_date = raw_latest_date
    else:
        last_mase_date = "N/D"

    st.markdown(f"""
    <div style="display: flex; align-items: center; justify-content: flex-end; gap: 10px; padding-top: 2px;">
        <img src="https://upload.wikimedia.org/wikipedia/commons/0/00/Emblem_of_Italy.svg" alt="Repubblica Italiana" width="34" height="34" style="opacity: 0.95;" />
        <div style="text-align: right;">
            <span class="source-badge">Dati Ufficiali MASE</span><br>
            <span style="font-size: 0.75rem; color: #64748b;">Rilevazione del: {last_mase_date}</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

# --- 1 & 2. PANNELLO DI CONTROLLO CONFIGURAZIONE (CARD UNIFICATA) ---
with st.container(border=True):
    st.markdown("##### Parametri generali da impostare")

    r1_col1, r1_col2 = st.columns(2)
    with r1_col1:
        selected_price_type = st.selectbox(
            "Prezzo Ministeriale:",
            options=list(price_type_options.keys()),
            format_func=lambda x: price_type_options[x],
            key="price_type",
            on_change=sync_url
        )
        active_key = price_keys[selected_price_type]

    with r1_col2:
        fuel_weight_pct = st.selectbox(
            "Incidenza costo gasolio:",
            options=list(range(1, 101)),
            format_func=lambda x: f"{x}%",
            key="weight",
            on_change=sync_url
        )

    r2_col1, r2_col2 = st.columns(2)
    with r2_col1:
        target_mode = st.selectbox(
            "MODALITÀ del periodo base (periodo target):",
            options=["Anno solare", "Singolo Mese", "Range personalizzato (da / a)"],
            key="target_mode"
        )

    target_price = 0.0
    target_price_pompa = 0.0
    target_price_imponibile = 0.0
    target_price_netto = 0.0
    target_label = ""
    target_end_date = date(2025, 12, 31)

    with r2_col2:
        if target_mode == "Anno solare":
            available_years = sorted(list(annual_dict.keys()), reverse=True)
            default_year_idx = available_years.index("2025") if "2025" in available_years else 0
            sel_year = st.selectbox("PERIODO TARGET anno solare:", available_years, index=default_year_idx, key="sel_year")
            target_data = annual_dict.get(sel_year, {})
            target_price = target_data.get(active_key, 0.0)
            target_price_pompa = target_data.get("prezzo_pompa", 0.0)
            target_price_imponibile = target_data.get("imponibile", 0.0)
            target_price_netto = target_data.get("netto", 0.0)
            target_label = f"Media Anno {sel_year}"
            target_end_date = date(int(sel_year), 12, 31)

        elif target_mode == "Singolo Mese":
            df_m = pd.DataFrame(monthly_list)
            df_m["label"] = df_m["nome_mese"] + " " + df_m["anno"].astype(str)
            month_options = df_m["label"].tolist()[::-1]
            sel_month = st.selectbox("PERIODO TARGET mese:", month_options, index=0, key="sel_month")
            matched_row = df_m[df_m["label"] == sel_month].iloc[0]
            target_price = matched_row[active_key]
            target_price_pompa = matched_row["prezzo_pompa"]
            target_price_imponibile = matched_row["imponibile"]
            target_price_netto = matched_row["netto"]
            target_label = f"Media {sel_month}"
            y_val, m_val = int(matched_row["anno"]), int(matched_row["mese"])
            last_day = calendar.monthrange(y_val, m_val)[1]
            target_end_date = date(y_val, m_val, last_day)

        else: # Range Personalizzato
            max_avail_date = get_week_meta(weekly_list[-1]["data"])["obs_end"] if weekly_list else date.today()
            def_end_date = min(date(2025, 12, 31), max_avail_date)
            
            sub_col1, sub_col2 = st.columns(2)
            with sub_col1:
                d_start = st.date_input("PERIODO TARGET data inizio:", value=date(2025, 1, 1), max_value=max_avail_date, key="d_start")
            with sub_col2:
                d_end = st.date_input("PERIODO TARGET data fine:", value=def_end_date, max_value=max_avail_date, key="d_end")
            
            # Filtraggio sulla reale finestra di rilevazione (Lunedì-Domenica)
            matched_target_rows = []
            for item in weekly_list:
                meta = get_week_meta(item["data"])
                if meta["obs_end"] >= d_start and meta["obs_start"] <= d_end:
                    matched_target_rows.append(item)
            df_filtered = pd.DataFrame(matched_target_rows)
            
            if len(df_filtered) > 0:
                target_price = float(df_filtered[active_key].mean())
                target_price_pompa = float(df_filtered["prezzo_pompa"].mean())
                target_price_imponibile = float(df_filtered["imponibile"].mean())
                target_price_netto = float(df_filtered["netto"].mean())
                target_label = f"Media {d_start.strftime('%d/%m/%y')} - {d_end.strftime('%d/%m/%y')}"
                target_end_date = d_end
            else:
                st.error("Nessuna rilevazione trovata per il range selezionato.")
                target_price = 1.0
                target_price_pompa = 1.0
                target_price_imponibile = 1.0
                target_price_netto = 1.0
                target_end_date = d_end

    st.markdown("<hr style='margin: 14px 0; border: none; border-top: 1px solid rgba(128,128,128,0.18);'>", unsafe_allow_html=True)

    p_col1, p_col2 = st.columns(2)

    with p_col1:
        granularity = st.radio(
            "Granularità Periodo da Valutare:",
            options=["Mensile", "Settimanale"],
            horizontal=True,
            key="granularity",
            on_change=sync_url
        )

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
                "**Mese di Rilevazione Gasolio:**",
                options=month_dropdown_options,
                format_func=lambda x: x[0],
                key="sel_eval_month"
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
        commercial_app_text = f"Percentuale rilevata su {eval_month_name} {eval_year}, convenzionalmente valida per la fatturazione di {next_month_name} {next_year} (salvo diversi accordi tra le parti)."

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
                "**Settimana di Rilevazione Gasolio:**",
                options=week_dropdown_options,
                format_func=lambda x: x[0],
                key="sel_eval_week"
            )
            
        selected_record = selected_week_tuple[1]
        selected_meta = selected_week_tuple[2]
        current_price = selected_record.get(active_key, 0.0)
        current_eval_label = selected_meta["label"]
        commercial_app_text = "Percentuale rilevata sulla settimana selezionata, convenzionalmente valida per la fatturazione della settimana successiva (salvo diversi accordi tra le parti)."

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
        <b>NOTA:</b> {commercial_app_text}
    </div>
</div>
""", unsafe_allow_html=True)

# --- 3. TABELLA SCAGLIONI PREVISIONALI (3 COLONNE) ---
st.markdown("### Matrice a scaglioni (passi da 0,5%)")
st.caption("Forchette del prezzo gasolio con relativo Fuel Surcharge applicabile.")

central_step = round(surcharge_pct * 2) / 2
steps = [round(central_step + i * 0.5, 2) for i in range(-5, 6)]

table_rows = []
for s in steps:
    s_min = s - 0.25
    s_max = s + 0.25
    
    p_min = target_price * (1 + (s_min / fuel_weight_pct))
    p_max = target_price * (1 + (s_max / fuel_weight_pct))
    
    is_current = (s_min <= surcharge_pct < s_max)
    
    if is_current:
        stato_str = f"ATTUALE • {fmt_it(current_price, 3)} €/L ({current_eval_label})"
    else:
        stato_str = ""
    
    table_rows.append({
        "Forchetta Prezzo Gasolio": f"da {fmt_it(p_min, 3)} € a {fmt_it(p_max, 3)} €",
        "Fuel Surcharge": f"{fmt_it(s, 2, sign=True)} %",
        "Stato / Riferimento": stato_str
    })

df_steps = pd.DataFrame(table_rows)

# Funzione di stile per evidenziare la riga ATTUALE
def highlight_current_row(row):
    if "ATTUALE" in str(row["Stato / Riferimento"]):
        return ["background-color: rgba(220, 38, 38, 0.15); font-weight: 700; color: #dc2626;"] * len(row)
    return [""] * len(row)

styled_df = df_steps.style.apply(highlight_current_row, axis=1)
st.dataframe(styled_df, use_container_width=True, hide_index=True)

# --- 4. GRAFICI, CONSULTAZIONE & SIMULATORE (4 TAB) ---
st.markdown("---")
st.markdown("### Analisi Storica, Consultazione e Simulazione")

tab_chart, tab_surcharge, tab_lookup, tab_simulator = st.tabs([
    "Andamento Storico Prezzi", 
    "Trend Fuel Surcharge (%)",
    "Consultazione Libera Prezzi",
    "Simulatore Libero (What-If)"
])

with tab_chart:
    st.markdown("###### Evoluzione Prezzo Gasolio Auto Italia (Rilevazioni Settimanali MASE)")
    df_w_all = pd.DataFrame(weekly_list)
    
    latest_date_str = weekly_list[-1]["data"]
    latest_dt = datetime.strptime(latest_date_str, "%Y-%m-%d").date()
    start_3y_dt = latest_dt - timedelta(days=3 * 365)
    
    fig_prices = go.Figure()
    fig_prices.add_trace(go.Scatter(
        x=df_w_all["data"], y=df_w_all["prezzo_pompa"],
        mode="lines", name="Alla Pompa",
        line=dict(color="#2563eb", width=2)
    ))
    fig_prices.add_trace(go.Scatter(
        x=df_w_all["data"], y=df_w_all["imponibile"],
        mode="lines", name="Imponibile (no IVA)",
        line=dict(color="#6366f1", width=1.5, dash="dot")
    ))
    fig_prices.add_trace(go.Scatter(
        x=df_w_all["data"], y=df_w_all["netto"],
        mode="lines", name="Netto Industriale",
        line=dict(color="#f59e0b", width=1.8)
    ))
    fig_prices.add_trace(go.Scatter(
        x=df_w_all["data"], y=df_w_all["accisa"],
        mode="lines", name="Accisa",
        line=dict(color="#10b981", width=1.5)
    ))
    
    fig_prices.update_layout(
        xaxis=dict(
            title="Data Rilevazione",
            range=[start_3y_dt.strftime("%Y-%m-%d"), latest_date_str],
            rangeselector=dict(
                buttons=list([
                    dict(count=1, label="1 Anno", step="year", stepmode="backward"),
                    dict(count=3, label="3 Anni", step="year", stepmode="backward"),
                    dict(count=5, label="5 Anni", step="year", stepmode="backward"),
                    dict(label="Tutto", step="all")
                ]),
                bgcolor="rgba(128, 128, 128, 0.12)",
                activecolor="#0284c7",
                font=dict(family="Titillium Web, sans-serif", size=11),
                y=1.18,
                x=0
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
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="left",
            x=0,
            font=dict(size=11)
        ),
        margin=dict(l=10, r=10, t=75, b=20),
        template="plotly_white",
        font=dict(family="Titillium Web, sans-serif")
    )
    st.plotly_chart(fig_prices, use_container_width=True, config={"displayModeBar": False})

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
        st.markdown(f"###### Confronto Evoluzione Fuel Surcharge (Post {target_label})")
        df_sur = pd.DataFrame(surcharge_points)
        
        fig_sur = go.Figure()
        fig_sur.add_hline(y=0, line_dash="dash", line_color="#94a3b8", annotation_text="Base Target (0,00%)")
        
        fig_sur.add_trace(go.Scatter(
            x=df_sur["data_label"],
            y=df_sur["sur_pompa"],
            mode="lines+markers",
            name="Base Pompa",
            line=dict(color="#2563eb", width=2.2),
            marker=dict(size=5, color="#1d4ed8"),
            hovertemplate="<b>%{x}</b><br>Surcharge Base Pompa: %{y:.2f}%<extra></extra>"
        ))
        
        fig_sur.add_trace(go.Scatter(
            x=df_sur["data_label"],
            y=df_sur["sur_netto"],
            mode="lines+markers",
            name="Base Netto Industriale",
            line=dict(color="#f59e0b", width=2.2, dash="dot"),
            marker=dict(size=5, color="#d97706"),
            hovertemplate="<b>%{x}</b><br>Surcharge Base Netto: %{y:.2f}%<extra></extra>"
        ))
        
        fig_sur.update_layout(
            xaxis_title="Periodo",
            yaxis_title="Percentuale Surcharge (%)",
            hovermode="x unified",
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="left",
                x=0,
                font=dict(size=11)
            ),
            xaxis=dict(
                automargin=True,
                tickangle=-45,
                nticks=8
            ),
            margin=dict(l=10, r=10, t=35, b=20),
            template="plotly_white",
            font=dict(family="Titillium Web, sans-serif")
        )
        st.plotly_chart(fig_sur, use_container_width=True, config={"displayModeBar": False})
    else:
        st.info(f"Il Periodo Target selezionato ({target_label}) coincide con i dati più recenti disponibili. Seleziona un Periodo Base antecedente (es. Anno 2025) per osservare l'evoluzione del Fuel Surcharge nel tempo.")

with tab_lookup:
    st.markdown("###### Consultazione Rapida Rilevazioni Ufficiali MASE (Gasolio Auto)")
    
    # Calcolo date predefinite intelligenti (ancorate alla più recente domenica MASE)
    if weekly_list:
        latest_meta_w = get_week_meta(weekly_list[-1]["data"])
        default_rng_end = latest_meta_w["obs_end"] # Ultima domenica rilevata (es. 23/08/2026)
        default_rng_start = default_rng_end.replace(day=1) # 1° giorno di quel mese (es. 01/08/2026)
    else:
        default_rng_end = date.today()
        default_rng_start = default_rng_end.replace(day=1)

    lk_col1, lk_col2 = st.columns([1.5, 2.5])
    with lk_col1:
        lookup_mode = st.selectbox(
            "Criterio di Ricerca:",
            options=["Intervallo Date (da / a)", "Anno solare", "Singolo Mese", "Settimana Specifica", "Data Esatta (Giorno)"],
            index=0,
            key="lk_mode"
        )
        
    p_pompa_res, p_imp_res, p_net_res, p_acc_res, p_iva_res = 0.0, 0.0, 0.0, 0.0, 0.0
    info_badge_text = ""
    
    with lk_col2:
        if lookup_mode == "Intervallo Date (da / a)":
            sub_d1, sub_d2 = st.columns(2)
            with sub_d1:
                rng_start = st.date_input("Data Inizio:", value=default_rng_start, max_value=default_rng_end, key="lk_rng_start")
            with sub_d2:
                rng_end = st.date_input("Data Fine:", value=default_rng_end, max_value=default_rng_end, key="lk_rng_end")
                
            matched_lk_rows = []
            for item in weekly_list:
                meta = get_week_meta(item["data"])
                if meta["obs_end"] >= rng_start and meta["obs_start"] <= rng_end:
                    matched_lk_rows.append(item)
            df_rng_filt = pd.DataFrame(matched_lk_rows)
            
            if len(df_rng_filt) > 0:
                p_pompa_res = float(df_rng_filt["prezzo_pompa"].mean())
                p_imp_res = float(df_rng_filt["imponibile"].mean())
                p_net_res = float(df_rng_filt["netto"].mean())
                p_acc_res = float(df_rng_filt["accisa"].mean())
                p_iva_res = float(df_rng_filt["iva"].mean())
                min_p = df_rng_filt["prezzo_pompa"].min()
                max_p = df_rng_filt["prezzo_pompa"].max()
                info_badge_text = f"Media calcolata su {len(df_rng_filt)} rilevazioni settimanali • Min: {fmt_it(min_p, 3)} €/L - Max: {fmt_it(max_p, 3)} €/L"
            else:
                st.error("Nessun dato trovato per l'intervallo selezionato.")

        elif lookup_mode == "Anno solare":
            avail_y = sorted(list(annual_dict.keys()), reverse=True)
            sel_y = st.selectbox("Seleziona Anno Solare:", avail_y, index=0, key="lk_year")
            res_obj = annual_dict.get(sel_y, {})
            p_pompa_res = res_obj.get("prezzo_pompa", 0.0)
            p_imp_res = res_obj.get("imponibile", 0.0)
            p_net_res = res_obj.get("netto", 0.0)
            p_acc_res = res_obj.get("accisa", 0.0)
            p_iva_res = res_obj.get("iva", 0.0)
            info_badge_text = f"Dato aggregato annuale ufficiale MASE per l'anno {sel_y}"

        elif lookup_mode == "Singolo Mese":
            df_m_lk = pd.DataFrame(monthly_list)
            df_m_lk["label"] = df_m_lk["nome_mese"] + " " + df_m_lk["anno"].astype(str)
            m_opts = df_m_lk["label"].tolist()[::-1]
            sel_m = st.selectbox("Seleziona Mese:", m_opts, index=0, key="lk_month")
            row_matched = df_m_lk[df_m_lk["label"] == sel_m].iloc[0]
            p_pompa_res = row_matched["prezzo_pompa"]
            p_imp_res = row_matched["imponibile"]
            p_net_res = row_matched["netto"]
            p_acc_res = row_matched["accisa"]
            p_iva_res = row_matched["iva"]
            info_badge_text = f"Dato consolidato mensile ufficiale MASE per {sel_m}"

        elif lookup_mode == "Settimana Specifica":
            w_opts = []
            for item in reversed(weekly_list):
                w_opts.append((get_week_meta(item["data"])["label"], item))
            sel_w_tuple = st.selectbox("Seleziona Settimana:", w_opts, format_func=lambda x: x[0], key="lk_week")
            item_row = sel_w_tuple[1]
            p_pompa_res = item_row["prezzo_pompa"]
            p_imp_res = item_row["imponibile"]
            p_net_res = item_row["netto"]
            p_acc_res = item_row["accisa"]
            p_iva_res = item_row["iva"]
            info_badge_text = f"Rilevazione ufficiale del {datetime.strptime(item_row['data'], '%Y-%m-%d').strftime('%d/%m/%Y')}"

        else: # Data Esatta (Giorno)
            sel_exact_day = st.date_input("Seleziona Data del Trasporto / Documento:", value=default_rng_end, max_value=default_rng_end, key="lk_day")
            
            matched_item = None
            matched_meta = None
            for item in reversed(weekly_list):
                meta = get_week_meta(item["data"])
                dt_rel = datetime.strptime(item["data"], "%Y-%m-%d").date()
                if meta["obs_start"] <= sel_exact_day <= meta["obs_end"] or sel_exact_day == dt_rel:
                    matched_item = item
                    matched_meta = meta
                    break
            if not matched_item:
                matched_item = weekly_list[-1]
                matched_meta = get_week_meta(weekly_list[-1]["data"])
                
            p_pompa_res = matched_item["prezzo_pompa"]
            p_imp_res = matched_item["imponibile"]
            p_net_res = matched_item["netto"]
            p_acc_res = matched_item["accisa"]
            p_iva_res = matched_item["iva"]
            info_badge_text = f"Giorno richiesto: {sel_exact_day.strftime('%d/%m/%Y')} • Rilevazione MASE in vigore: {matched_meta['label']}"

    # Visualizzazione Card Risultati Quick Lookup
    st.markdown(f"<div style='margin-top: 12px; margin-bottom: 8px; font-size: 0.82rem; color: #64748b;'><b>Dettaglio:</b> {info_badge_text}</div>", unsafe_allow_html=True)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Prezzo alla Pompa", f"{fmt_it(p_pompa_res, 3)} €/L")
    c2.metric("Imponibile (senza IVA)", f"{fmt_it(p_imp_res, 3)} €/L")
    c3.metric("Netto Industriale", f"{fmt_it(p_net_res, 3)} €/L")
    c4.metric("Accisa di Legge", f"{fmt_it(p_acc_res, 4)} €/L", f"IVA: {fmt_it(p_iva_res, 3)} €/L")

with tab_simulator:
    st.markdown("###### Simulatore di Fuel Surcharge su Prezzo Ipotetico / Manuale (What-If)")
    st.markdown(f"<div style='font-size: 0.80rem; color: #64748b; margin-top: -6px; margin-bottom: 12px;'>Base di prezzo di riferimento: <b>{price_type_options[selected_price_type]}</b> (modificabile nei parametri generali in alto)</div>", unsafe_allow_html=True)
    
    # Prezzo stimato pre-compilato dinamicamente con il risultato calcolato nella Consultazione Libera
    if active_key == "prezzo_pompa":
        sim_default_eval = p_pompa_res if p_pompa_res > 0 else (current_price if current_price > 0 else 1.800)
    elif active_key == "imponibile":
        sim_default_eval = p_imp_res if p_imp_res > 0 else (current_price if current_price > 0 else 1.450)
    else:
        sim_default_eval = p_net_res if p_net_res > 0 else (current_price if current_price > 0 else 0.850)

    sim_col1, sim_col2, sim_col3 = st.columns(3)
    with sim_col1:
        sim_p_base = st.number_input(
            "Prezzo TARGET (€/L):",
            min_value=0.500,
            max_value=3.500,
            value=float(target_price) if target_price > 0 else 1.650,
            step=0.005,
            format="%.3f",
            key="sim_base"
        )
    with sim_col2:
        sim_p_eval = st.number_input(
            "Prezzo Gasolio Ipotetico / Stimato (€/L):",
            min_value=0.500,
            max_value=3.500,
            value=float(sim_default_eval),
            step=0.005,
            format="%.3f",
            key="sim_eval"
        )
    with sim_col3:
        sim_weight = st.selectbox(
            "Incidenza Gasolio (%):",
            options=list(range(1, 101)),
            index=fuel_weight_pct - 1,
            format_func=lambda x: f"{x}%",
            key="sim_weight_sel"
        )
        
    sim_delta = sim_p_eval - sim_p_base
    sim_delta_pct = (sim_delta / sim_p_base) * 100 if sim_p_base > 0 else 0.0
    sim_surcharge_pct = sim_delta_pct * (sim_weight / 100.0)
    
    # Scaglione corrispondente
    sim_step_center = round(sim_surcharge_pct * 2) / 2
    sim_p_min_bracket = sim_p_base * (1 + ((sim_step_center - 0.25) / sim_weight))
    sim_p_max_bracket = sim_p_base * (1 + ((sim_step_center + 0.25) / sim_weight))
    
    sim_class = "hero-positive" if sim_surcharge_pct > 0.0001 else ("hero-negative" if sim_surcharge_pct < -0.0001 else "hero-neutral")
    
    st.markdown(f"""
    <div class="hero-card" style="margin-top: 14px;">
        <div class="hero-title">Fuel Surcharge Simulato (Scenario Manuale)</div>
        <div class="hero-value {sim_class}">{fmt_it(sim_surcharge_pct, 2, sign=True)} %</div>
        <div>
            <span class="metric-pill"><b>Prezzo Ipotetico:</b> {fmt_it(sim_p_eval, 3)} €/L</span>
            <span class="metric-pill"><b>Prezzo Target:</b> {fmt_it(sim_p_base, 3)} €/L</span>
            <span class="metric-pill"><b>Variazione Stimata:</b> {fmt_it(sim_delta_pct, 2, sign=True)}%</span>
            <span class="metric-pill"><b>Fascia Matrice:</b> da {fmt_it(sim_p_min_bracket, 3)} € a {fmt_it(sim_p_max_bracket, 3)} € (scaglione {fmt_it(sim_step_center, 2, sign=True)}%)</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

# --- 5. NOTA METODOLOGICA & GUIDA ALL'UTILIZZO ---
st.markdown("---")
st.markdown("##### Nota Metodologica e Guida all'Utilizzo")

m_col1, m_col2 = st.columns(2)

with m_col1:
    st.markdown("""
    <div style="background-color: var(--secondary-background-color); border: 1px solid rgba(128, 128, 128, 0.2); border-radius: 8px; padding: 18px 20px; font-size: 0.82rem; line-height: 1.55; color: var(--text-color); height: 100%;">
        <div style="font-weight: 700; font-size: 0.88rem; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 10px; color: var(--text-color);">
            Metodologia e Formule di Calcolo
        </div>
        <ul style="margin: 0; padding-left: 18px;">
            <li style="margin-bottom: 8px;"><b>Variazione Prezzo Gasolio (Δ%):</b> Calcola lo scostamento percentuale tra il prezzo del carburante del periodo di valutazione (<i>P<sub>attuale</sub></i>) e il prezzo del periodo base contrattuale (<i>P<sub>target</sub></i>):<br>
            <code>Δ% = ((P<sub>attuale</sub> - P<sub>target</sub>) / P<sub>target</sub>) × 100</code></li>
            <li style="margin-bottom: 8px;"><b>Quota di Incidenza Costo (Peso %):</b> Il Fuel Surcharge finale è ottenuto moltiplicando la variazione <code>Δ%</code> per l'incidenza del gasolio sul costo chilometrico totale (default 30%, in linea con le tabelle indicative dei costi di esercizio MIT per veicoli pesanti):<br>
            <code>Fuel Surcharge % = Δ% × Incidenza %</code></li>
            <li style="margin-bottom: 8px;"><b>Matrice a Scaglioni (±0,5%):</b> Ogni scaglione tariffario copre una forchetta centrata di ±0,25%. Le soglie di prezzo minimo e massimo sono calcolate tramite formula analitica inversa a partire dal Prezzo Base.</li>
            <li><b>Confronto Basi di Prezzo:</b> Le variazioni percentuali su <i>Prezzo Globale alla Pompa</i> e <i>Imponibile (senza IVA)</i> sono matematicamente identiche (l'aliquota IVA al 22% è costante e si elide). Il calcolo su <i>Netto Industriale</i> evidenzia invece la variazione pura della materia prima petrolifera, escludendo l'effetto ammortizzatore dell'accisa fissa.</li>
        </ul>
    </div>
    """, unsafe_allow_html=True)

with m_col2:
    st.markdown("""
    <div style="background-color: var(--secondary-background-color); border: 1px solid rgba(128, 128, 128, 0.2); border-radius: 8px; padding: 18px 20px; font-size: 0.82rem; line-height: 1.55; color: var(--text-color); height: 100%;">
        <div style="font-weight: 700; font-size: 0.88rem; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 10px; color: var(--text-color);">
            Parametri di Default, Interattività e Fonti
        </div>
        <ul style="margin: 0; padding-left: 18px;">
            <li style="margin-bottom: 8px;"><b>Configurazione di Default all'Avvio:</b> Il sistema si apre pre-configurato su <i>Prezzo Globale alla Pompa</i>, <i>Incidenza 30%</i>, <i>Periodo Base Anno Solare 2025</i> e <i>Rilevazione più recente disponibile</i>.</li>
            <li style="margin-bottom: 8px;"><b>Personalizzazione Dinamica:</b> L'utente può modificare liberamente tutti i parametri: cambiare la base di prezzo, impostare qualsiasi percentuale di incidenza, selezionare periodi target su base annuale, mensile o intervalli di date personalizzati, e consultare qualsiasi mese o settimana storica.</li>
            <li style="margin-bottom: 8px;"><b>Link Condivisibili (URL Query):</b> Qualsiasi combinazione di parametri impostata dall'utente viene sincronizzata nell'indirizzo URL del browser, consentendo di copiare e inviare link già pre-configurati per contratti specifici.</li>
            <li><b>Automazione e Fonti Ufficiali:</b> I dati sono acquisiti direttamente tramite API Open Data dal <i>Ministero dell'Ambiente e della Sicurezza Energetica (DGSAIE)</i>. Le rilevazioni settimanali si aggiornano ogni martedì (dopo le ore 12:00) e i dati mensili vengono consolidati nei primi giorni del mese successivo.</li>
        </ul>
    </div>
    """, unsafe_allow_html=True)

# --- FOOTER ISTITUZIONALE ---
st.markdown("---")
st.markdown("""
<div style="text-align: center; margin-top: 15px; margin-bottom: 25px; font-size: 0.82rem; color: #64748b;">
    Fonte Dati Ufficiali: <a href="https://sisen.mase.gov.it/dgsaie/prezzi-settimanali-carburanti" target="_blank" style="color: #0284c7; text-decoration: none; font-weight: 600;">Ministero dell'Ambiente e della Sicurezza Energetica (DGSAIE) ↗</a><br>
    <span style="font-size: 0.75rem; opacity: 0.85;">Fuel Surcharge Italia • Indice di monitoraggio e simulazione adeguamento costo gasolio</span>
</div>
""", unsafe_allow_html=True)
