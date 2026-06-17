import streamlit as st
import streamlit.components.v1 as components
import requests
import time
import json

st.set_page_config(
    page_title="Cardano Multichart",
    page_icon="◈",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ─── CSS ───────────────────────────────────────────────────────────────────
st.markdown("""
<style>
#MainMenu, footer, header { visibility: hidden; }
.block-container { padding: 8px 12px !important; max-width: 100% !important; }
.stApp { background: #0d0f14; }
div[data-testid="stRadio"] > label { color: #64748b !important; font-size: 11px !important; }
div[data-testid="stRadio"] div[role="radiogroup"] { flex-direction: row; gap: 4px; }
div[data-testid="stRadio"] label { font-family: monospace !important; }
div[data-testid="stTextInput"] input {
    background: #111318 !important;
    border: 1px solid #1e2330 !important;
    color: #e2e8f0 !important;
    font-family: monospace !important;
    font-size: 11px !important;
}
.stButton button {
    background: transparent !important;
    border: 1px solid #1e2330 !important;
    color: #64748b !important;
    font-family: monospace !important;
    font-size: 11px !important;
}
.stButton button:hover {
    border-color: #00d4aa !important;
    color: #00d4aa !important;
}
div[data-testid="column"] { padding: 0 4px !important; }
</style>
""", unsafe_allow_html=True)

# ─── Constants ─────────────────────────────────────────────────────────────
CHART_URL = "https://charts.dhapi.io"
API_URL   = "https://api-us.dexhunterv3.app"

TOKENS = [
    {"ticker": "LQ",    "id": "da8c30857834c6ae7203935b89278c532b3995245295456f993e1d2464d494e"},
    {"ticker": "NIGHT", "id": "0691b2fecca1ac4f53cb6dfb00b7013e561d1f34403b957cbb5af1fa4e49474854"},
    {"ticker": "IAG",   "id": "d894897411707efa755a76deb66d26dfd50593f2e70863e1661e98a07494147"},
    {"ticker": "SNEK",  "id": "279c909f348e533da5808898f87f9a14bb2c3dfbbacccd631d927a3f534e454b"},
    {"ticker": "HOSKY", "id": "a0028f350aaabe0545fdcb56b039bfb08e4bb4d8c4d7c3c7d481d235484f534b59"},
    {"ticker": "MIN",   "id": "29d222ce763455e3d7a09a665ce554f00ac89d2e99a1a83d267170c64d494e"},
    {"ticker": "FLDT",  "id": "f43a62fdc3965df486de8a0d32fe800963589c41b38946602a0dc534c454c4c4f"},
    {"ticker": "BOS",   "id": "64978a5eff5cbb34c86e9869ee8a0bb0b8b99e7f4babb6b0f4b0a2f24f584f53"},
]

TF_PERIODS = {
    "15m":  "15min",
    "1H":   "1hour",
    "4H":   "4hour",
    "1D":   "1day",
}

TF_SECONDS = {
    "15m":  15*60,
    "1H":   60*60,
    "4H":   4*60*60,
    "1D":   24*60*60,
}

TF_RANGE = {       # bao nhiêu giây data để load
    "15m":  2*24*3600,    # 2 ngày
    "1H":   7*24*3600,    # 7 ngày
    "4H":   30*24*3600,   # 30 ngày
    "1D":   180*24*3600,  # 6 tháng
}

# ─── Session state ──────────────────────────────────────────────────────────
if "api_key" not in st.session_state:
    st.session_state.api_key = ""
if "cache" not in st.session_state:
    st.session_state.cache = {}

# ─── Header ─────────────────────────────────────────────────────────────────
c1, c2, c3, c4 = st.columns([2, 3, 3, 2])
with c1:
    st.markdown('<p style="font-family:monospace;font-size:13px;font-weight:700;color:#00d4aa;margin:6px 0">◈ ADA MULTICHART</p>', unsafe_allow_html=True)
with c2:
    tf = st.radio("TF", list(TF_PERIODS.keys()), index=1, horizontal=True, label_visibility="collapsed")
with c3:
    api_key_input = st.text_input("API Key", value=st.session_state.api_key,
                                   placeholder="Paste DexHunter API key...",
                                   label_visibility="collapsed", type="password")
    if api_key_input:
        st.session_state.api_key = api_key_input
with c4:
    col_refresh, col_info = st.columns([1,2])
    with col_refresh:
        do_refresh = st.button("↺ Refresh")
    with col_info:
        if st.session_state.api_key:
            st.markdown('<p style="color:#00d4aa;font-size:10px;font-family:monospace;margin:8px 0">● Live</p>', unsafe_allow_html=True)
        else:
            st.markdown('<p style="color:#f03e3e;font-size:10px;font-family:monospace;margin:8px 0">⚠ No key</p>', unsafe_allow_html=True)

st.divider()

# ─── Fetch OHLCV ────────────────────────────────────────────────────────────
def fetch_ohlcv(token_id, period_str, range_secs, api_key):
    cache_key = f"{token_id}_{period_str}_{int(time.time()//300)}"  # cache 5 phút
    if cache_key in st.session_state.cache and not do_refresh:
        return st.session_state.cache[cache_key]

    now  = int(time.time())
    from_ts = now - range_secs
    try:
        r = requests.post(
            f"{CHART_URL}/charts",
            json={"tokenIn": "", "tokenOut": token_id, "period": period_str, "from": from_ts, "to": now},
            headers={"X-Partner-Id": api_key, "Content-Type": "application/json"},
            timeout=8
        )
        r.raise_for_status()
        data = r.json()
        candles = data.get("data", data) if isinstance(data, dict) else data
        st.session_state.cache[cache_key] = candles
        return candles
    except Exception as e:
        return None

def fetch_price(token_id, api_key):
    try:
        r = requests.get(
            f"{API_URL}/swap/averagePrice/ADA/{token_id}",
            headers={"X-Partner-Id": api_key},
            timeout=5
        )
        r.raise_for_status()
        d = r.json()
        return float(d.get("price_ba", 0))
    except:
        return None

# ─── Build chart HTML với lightweight-charts ──────────────────────────────
def build_chart_html(candles, ticker, price_now):
    if not candles:
        return f"""
        <div style="width:100%;height:220px;display:flex;align-items:center;
             justify-content:center;background:#111318;font-family:monospace;
             font-size:11px;color:#f03e3e;">
            ⚠ No data — check API key
        </div>"""

    # Format candles
    valid = []
    for c in candles:
        try:
            t = int(c.get("time", c.get("timestamp", 0)))
            o = float(c.get("open",  0))
            h = float(c.get("high",  0))
            l = float(c.get("low",   0))
            cl= float(c.get("close", 0))
            v = float(c.get("volume", 0))
            if t > 0 and cl > 0:
                valid.append({"time":t,"open":o,"high":h,"low":l,"close":cl,"volume":v})
        except:
            pass

    valid.sort(key=lambda x: x["time"])
    if not valid:
        return f'<div style="color:#f03e3e;font-family:monospace;font-size:11px;padding:8px">No valid candles</div>'

    last  = valid[-1]
    prev  = valid[-2] if len(valid) > 1 else last
    chg   = ((last["close"] - prev["close"]) / prev["close"] * 100) if prev["close"] else 0
    chg_c = "#00d4aa" if chg >= 0 else "#f03e3e"
    chg_s = f"+{chg:.2f}%" if chg >= 0 else f"{chg:.2f}%"

    price_str = f"{last['close']:.6f}" if last['close'] < 0.01 else f"{last['close']:.4f}"

    candles_js = json.dumps(valid)

    return f"""
    <div style="background:#111318;height:230px;display:flex;flex-direction:column;overflow:hidden">
        <div style="display:flex;align-items:center;padding:5px 10px;
                    border-bottom:1px solid #1a1d26;flex-shrink:0;height:26px">
            <span style="font-family:monospace;font-size:11px;font-weight:700;
                         color:#e2e8f0;letter-spacing:0.08em">{ticker}</span>
            <span style="font-family:monospace;font-size:10px;color:#2d3748;margin-left:6px">/ADA</span>
            <span style="font-family:monospace;font-size:11px;font-weight:600;
                         color:#e2e8f0;margin-left:auto">{price_str}</span>
            <span style="font-family:monospace;font-size:10px;font-weight:600;
                         color:{chg_c};margin-left:8px">{chg_s}</span>
        </div>
        <div id="chart_{ticker}" style="flex:1;min-height:0"></div>
    </div>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/lightweight-charts/4.1.3/lightweight-charts.standalone.production.js"></script>
    <script>
    (function() {{
        const el = document.getElementById('chart_{ticker}');
        if (!el) return;
        const chart = LightweightCharts.createChart(el, {{
            layout: {{ background:{{color:'#111318'}}, textColor:'#64748b' }},
            grid: {{ vertLines:{{color:'#1a1d26'}}, horzLines:{{color:'#1a1d26'}} }},
            crosshair: {{ mode: LightweightCharts.CrosshairMode.Normal }},
            rightPriceScale: {{ borderColor:'#232730', scaleMargins:{{top:0.05,bottom:0.2}} }},
            timeScale: {{ borderColor:'#232730', timeVisible:true, secondsVisible:false }},
            handleScroll: true,
            handleScale: true,
        }});
        const cs = chart.addCandlestickSeries({{
            upColor:'#00d4aa', downColor:'#f03e3e',
            borderUpColor:'#00d4aa', borderDownColor:'#f03e3e',
            wickUpColor:'#00d4aa', wickDownColor:'#f03e3e',
        }});
        const vs = chart.addHistogramSeries({{
            color:'#7c5cfc44', priceFormat:{{type:'volume'}}, priceScaleId:'vol'
        }});
        chart.priceScale('vol').applyOptions({{scaleMargins:{{top:0.82,bottom:0}}}});

        const raw = {candles_js};
        cs.setData(raw.map(c => ({{time:c.time,open:c.open,high:c.high,low:c.low,close:c.close}})));
        vs.setData(raw.map(c => ({{
            time:c.time, value:c.volume,
            color: c.close>=c.open?'#00d4aa33':'#f03e3e33'
        }})));
        chart.timeScale().fitContent();

        const ro = new ResizeObserver(() => {{
            const r = el.getBoundingClientRect();
            if(r.width>0 && r.height>0) chart.resize(r.width, r.height);
        }});
        ro.observe(el);
    }})();
    </script>
    """

# ─── Main grid ───────────────────────────────────────────────────────────────
if not st.session_state.api_key:
    st.markdown("""
    <div style="text-align:center;padding:60px;font-family:monospace;color:#64748b">
        <div style="font-size:32px;margin-bottom:16px">◈</div>
        <div style="font-size:14px;color:#e2e8f0;margin-bottom:8px">Nhập DexHunter API Key để bắt đầu</div>
        <div style="font-size:11px">Lấy tại: <span style="color:#00d4aa">app.dexhunter.io/partners → Keys tab</span></div>
    </div>
    """, unsafe_allow_html=True)
    st.stop()

period_str  = TF_PERIODS[tf]
range_secs  = TF_RANGE[tf]
api_key     = st.session_state.api_key

# Grid 4×2
row1 = st.columns(4, gap="small")
row2 = st.columns(4, gap="small")
rows = row1 + row2

for i, (col, tok) in enumerate(zip(rows, TOKENS)):
    with col:
        candles = fetch_ohlcv(tok["id"], period_str, range_secs, api_key)
        price   = fetch_price(tok["id"], api_key) if candles else None
        html    = build_chart_html(candles, tok["ticker"], price)
        components.html(html, height=232, scrolling=False)

# Auto refresh hint
st.markdown(
    '<p style="text-align:center;font-family:monospace;font-size:9px;'
    'color:#1e2330;margin-top:4px">DexHunter Charts API · Cardano on-chain data</p>',
    unsafe_allow_html=True
)
