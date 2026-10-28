import streamlit as st
import pandas as pd
import requests
import plotly.express as px
from datetime import date

st.set_page_config(page_title="Dólar en Costa Rica", page_icon="💱", layout="wide")

# Visual style
st.markdown("""
<style>
.block-container {padding-top: 2rem; padding-bottom: 2rem; max-width: 1200px;}
.hero {padding: 1.4rem 1.6rem; border-radius: 18px; background: linear-gradient(120deg,#182848,#4b6cb7); color: white; margin-bottom: 1rem;}
.hero h1 {color:white; margin:0; font-size:2rem;}
.hero p {color:#e8edff; margin:.45rem 0 0 0;}
.big-rate {font-size:3rem; font-weight:800; line-height:1.15; color:#182848;}
.small-label {font-size:.9rem; color:#64748b;}
</style>
""", unsafe_allow_html=True)

@st.cache_data(ttl=3600, show_spinner=False)
def get_fx(year):
    url = "https://tipodecambio.cr/api/v1/tipo-cambio/historico"
    response = requests.get(url, params={"desde": f"{year}-01-01", "hasta": f"{year}-12-31"}, timeout=25)
    response.raise_for_status()
    payload = response.json()
    if isinstance(payload, dict) and not payload.get("ok", True):
        raise ValueError(payload.get("error", "La fuente no devolvió datos"))
    data = payload.get("data", []) if isinstance(payload, dict) else payload
    if isinstance(data, dict):
        data = data.get("data", [])
    rows = []
    for item in data or []:
        dt = item.get("date") or item.get("fecha") or item.get("fechaTipoCambio")
        buy = item.get("compra") or item.get("Compra")
        sell = item.get("venta") or item.get("Venta")
        if dt and buy is not None and sell is not None:
            rows.append({"Fecha": pd.to_datetime(dt, errors="coerce"), "Compra": float(buy), "Venta": float(sell)})
    df = pd.DataFrame(rows)
    if df.empty:
        return df
    df = df.dropna(subset=["Fecha"]).sort_values("Fecha").drop_duplicates("Fecha")
    return df[df["Fecha"].dt.year == year]

st.markdown("<div class='hero'><h1>💱 El dólar en Costa Rica</h1><p>Elegí un año y consultá el tipo de cambio, su evolución y qué puede significar para la economía cotidiana.</p></div>", unsafe_allow_html=True)

current_year = date.today().year
with st.sidebar:
    st.header("Tu consulta")
    year = st.selectbox("Seleccioná el año", list(range(current_year, 1990, -1)), index=min(5, current_year-1991))
    st.caption("Los promedios se calculan con los registros diarios disponibles para el año seleccionado.")

try:
    with st.spinner(f"Cargando datos de {year}…"):
        fx = get_fx(year)
except Exception as exc:
    st.error("No pude obtener los datos históricos de la fuente en este momento.")
    st.write("No quiero mostrarte cifras inventadas. Podés probar de nuevo en unos minutos; si continúa, habrá que ajustar la conexión con la fuente de datos.")
    with st.expander("Detalle técnico (por si necesitamos revisarlo)"):
        st.code(str(exc))
    st.link_button("Consultar el tipo de cambio en el BCCR", "https://www.bccr.fi.cr/indicadores-economicos")
    st.stop()

if fx.empty:
    st.warning(f"No hay registros disponibles para {year} en la fuente consultada. Probá con otro año.")
    st.link_button("Consultar el tipo de cambio en el BCCR", "https://www.bccr.fi.cr/indicadores-economicos")
    st.stop()

avg_sell = fx["Venta"].mean()
avg_buy = fx["Compra"].mean()
start_sell = fx.iloc[0]["Venta"]
end_sell = fx.iloc[-1]["Venta"]
change = ((end_sell / start_sell) - 1) * 100 if start_sell else 0
max_sell = fx["Venta"].max()
min_sell = fx["Venta"].min()

st.markdown(f"### Resumen de {year}")
left, right = st.columns([1.25, 1])
with left:
    st.markdown("<div style='background:#f0f5ff;border:1px solid #d8e3ff;border-radius:18px;padding:1.4rem;'>", unsafe_allow_html=True)
    st.markdown("<div class='small-label'>PRECIO PROMEDIO DE VENTA DEL DÓLAR</div>", unsafe_allow_html=True)
    st.markdown(f"<div class='big-rate'>₡{avg_sell:,.2f}</div>", unsafe_allow_html=True)
    st.markdown(f"<div style='color:#334155'>En promedio, eso es lo que costó comprar US$1 en el año {year}.</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)
with right:
    st.metric("Compra promedio del dólar", f"₡{avg_buy:,.2f}", help="Promedio anual del precio de compra reportado por la fuente.")
    st.metric("Cambio del precio de venta en el año", f"{change:+.2f}%", help="Compara el primer y el último registro disponible; no es la variación entre promedios.")

st.markdown("### ¿Cómo se movió durante el año?")
fig = px.line(fx, x="Fecha", y="Venta", labels={"Fecha":"Fecha", "Venta":"Colones por US$1"},
              hover_data={"Venta":":.2f"})
fig.update_traces(line=dict(width=3), hovertemplate="%{x|%d %b %Y}<br>Venta: ₡%{y:,.2f}<extra></extra>")
fig.update_layout(margin=dict(l=10,r=10,t=10,b=10), hovermode="x unified", yaxis_tickprefix="₡", yaxis_tickformat=",.2f")
st.plotly_chart(fig, use_container_width=True)

c1,c2,c3 = st.columns(3)
c1.metric("Venta más baja registrada", f"₡{min_sell:,.2f}")
c2.metric("Venta más alta registrada", f"₡{max_sell:,.2f}")
c3.metric("Registros analizados", f"{len(fx):,}")

st.markdown("### ¿Qué significa para la economía?")
if change > 1:
    st.info(f"El precio de venta terminó {change:.2f}% por encima del primer registro disponible. Si el dólar sube, importaciones, productos cotizados en dólares y cuotas de deudas en dólares pueden requerir más colones. A la vez, quienes reciben dólares podrían obtener más colones al cambiarlos.")
elif change < -1:
    st.info(f"El precio de venta terminó {abs(change):.2f}% por debajo del primer registro disponible. Si el dólar baja, algunos pagos e importaciones en dólares pueden requerir menos colones; quienes reciben dólares podrían obtener menos colones al convertirlos.")
else:
    st.info(f"El precio de venta cambió {change:+.2f}% entre el primer y el último registro disponible. El cambio neto fue relativamente pequeño, aunque pudo haber subidas y bajadas durante el año.")
st.caption("Estos efectos son orientativos, no una prueba de causa y efecto. Influyen también la inflación, las tasas de interés, los precios internacionales y las decisiones de empresas y del BCCR.")
with st.expander("Ver los datos diarios"):
    st.dataframe(fx, use_container_width=True, hide_index=True)
    st.download_button("Descargar datos en CSV", fx.to_csv(index=False).encode("utf-8-sig"), file_name=f"tipo_cambio_{year}.csv", mime="text/csv")
st.markdown("Fuente de tipo de cambio: [API histórica consultada](https://tipodecambio.cr/api). Para verificar cifras oficiales, consultá el [Banco Central de Costa Rica (BCCR)](https://www.bccr.fi.cr/indicadores-economicos).")
