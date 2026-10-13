import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from app.data import REGIONS, CATEGORIES, make_demo_data, summarize

st.set_page_config(page_title="Atlas | Demand Intelligence", page_icon="📈", layout="wide")
st.markdown("""<style>
  .stApp {background: #f7f9fc; color:#17243a;}
  [data-testid="stMetric"] {background:white;border:1px solid #e1e8f0;border-radius:14px;padding:18px;}
  h1,h2,h3 {color:#14243b;}
  div[data-testid="stSidebar"] {background:#edf2f8;}
  .hero {background:linear-gradient(115deg,#102d43,#126e78);padding:27px 32px;border-radius:18px;color:white;margin-bottom:22px;}
  .hero h1 {color:white;margin:0;font-size:2.1rem;}
  .hero p {color:#c5e7e9;margin:9px 0 0;}
  .tag {letter-spacing:.1em;font-size:.7rem;font-weight:700;color:#5fe2cf;}
</style>""", unsafe_allow_html=True)

st.sidebar.markdown("### ATLAS  /  DEMO")
st.sidebar.caption("Customer-facing reference application")
region = st.sidebar.selectbox("Market", ["All markets", *REGIONS])
category = st.sidebar.selectbox("Product category", ["All categories", *CATEGORIES])
show_promo = st.sidebar.toggle("Promotional days only", value=False)

frame = make_demo_data()
if region != "All markets": frame = frame[frame.region == region]
if category != "All categories": frame = frame[frame.category == category]
if show_promo: frame = frame[frame.promotion == 1]
metrics = summarize(frame)

st.markdown("""<div class="hero"><div class="tag">DEMAND INTELLIGENCE  /  LIVE PRODUCT PROTOTYPE</div>
<h1>From forecasts to better decisions.</h1>
<p>Explore forecast quality, demand patterns and potential business impact in one workspace.</p></div>""", unsafe_allow_html=True)

st.caption("SYNTHETIC DEMONSTRATION DATA  •  This prototype does not establish actual customer savings or model performance.")
a,b,c,d = st.columns(4)
a.metric("Demand volume",f"{metrics['actual_volume']:,.0f} units")
b.metric("Baseline error (WAPE)",f"{metrics['baseline_wape']:.1f}%")
c.metric("Improved error (WAPE)",f"{metrics['improved_wape']:.1f}%")
d.metric("Relative error reduction",f"{metrics['error_reduction_pct']:.1f}%")

st.markdown("### Demand performance")
daily = frame.groupby("date",as_index=False)[["actual","baseline","improved"]].sum()
fig = go.Figure()
for name, color in [("actual","#13354c"),("baseline","#e0a15b"),("improved","#149c99")]:
    fig.add_trace(go.Scatter(x=daily.date,y=daily[name],mode="lines",name=name.title(),line=dict(color=color,width=2.7)))
fig.update_layout(height=370,margin=dict(l=0,r=0,t=10,b=0),template="plotly_white",legend=dict(orientation="h",y=1.1),xaxis_title=None,yaxis_title="Units")
st.plotly_chart(fig,use_container_width=True)

left,right=st.columns([1,1])
with left:
    st.markdown("### Explore operational assumptions")
    annual_waste = st.slider("Current annual waste cost (€M)",1.0,30.0,10.0,0.5)
    reduction = st.slider("Assumed reduction in waste (%)",0,30,8)
    annual_cost = st.number_input("Estimated annual solution costs (€)",min_value=0,value=250000,step=25000)
    gross=annual_waste*1_000_000*reduction/100
    st.metric("Illustrative net annual benefit",f"€{gross-annual_cost:,.0f}")
    st.caption("Scenario arithmetic only. Forecast-error improvements do not automatically translate to waste savings.")
with right:
    st.markdown("### Where to go next")
    st.info("**Pilot hypothesis:** better demand forecasts could support more effective production and inventory decisions. Validate using representative customer data and historical decision backtesting.")
    st.markdown("**Suggested pilot KPIs**")
    st.markdown("- Forecast WAPE vs current planning baseline\n- Inventory waste and stockout cost\n- Planner adoption and overrides\n- Operating cost and time to value")

with st.expander("See synthetic demonstration data"):
    st.dataframe(frame.tail(100),use_container_width=True,hide_index=True)
    st.download_button("Download filtered data (CSV)",frame.to_csv(index=False).encode(),"demo_data.csv","text/csv")
