import streamlit as st
import requests
import time
import json

st.set_page_config(
    page_title="Cardano Multichart",
    page_icon="◈",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.markdown("""
<style>
#MainMenu, footer, header { visibility: hidden; }
.block-container { padding: 8px 12px !important; max-width: 100% !important; }
.stApp { background: #0d0f14; }
div[data-testid="stRadio"] label { font-family: monospace !important; font-size: 11px !important; }
div[data-testid="stRadio"] div[role="radiogroup"] { flex-direction: row; gap: 4px; }
div[data-testid="stTextInput"] input {
    background: #111318 !important; border: 1px solid #1e2330 !important;
    color: #e2e8f0 !important; font-family: monospace !important; font-size: 11px !important;
}
.stButton > button {
    background: transparent !important; border: 1px solid #1e2330 !important;
    color: #64748b !important; font-family: monospace !important; font-size: 11px !important;
}
div[data-testid="column"] { padding: 0 2px !important; }
</style>
""", unsafe_allow_html=True)

CHART_URL = "https://charts.dhapi.io"
API_URL   = "https://api-us.dexhunterv3.app"

# Token IDs đúng format DexHunter (policy_id + hex_name)
TOKENS = [
    {"ticker": "LQ",    "id": "da8c30857834c6ae7203935b89278c532b3995245295456f993e1d244c51"},
    {"ticker": "NIGHT", "id": "0691b2fecca1ac4f53cb6dfb00b7013e561d1f34403b957cbb5af1fa4e49474854"},
    {"ticker": "IAG",   "id": "d894897411707efa755a76deb66d26dfd50593f2e70863e1661e98a07494147"},
    {"ticker": "SNEK",  "id": "279c909f348e533da5808898f87f9a14bb2c3dfbbacccd631d927a3f534e454b"},
    {"ticker": "HOSKY", "id": "a0028f350aaabe0545fdcb56b039bfb08e4bb4d8c4d7c3c7d481d235484f534b59"},
    {"ticker": "MIN",   "id": "29d222ce763455e3d7a09a665ce554f00ac89d2e99a1a83d267170c64d494e"},
    {"ticker": "FLDT",  "id": "f43a62fdc3965df486de8a0d32fe800963589c41b38946602a0dc534c454c4c4f"},
    {"ticker": "BOS",   "id": "64978a5eff5cbb34c86e9869ee8a0bb0b8b99e7f4babb6b0f4b0a2f24f584f53"},
]

TF_PERIODS  = {"15m":"15min","1H":"1hour","4H":"4hour","1D":"1day"}
TF_RANGE    = {"15m":2*24*3600,"1H":7*24*3600,"4H":30*24*3600,"1D":180*24*3600}

if "api_key" not in st.session_state:
    st.session_state.api_key = ""
if "cache" not in st.session_state:
    st.session_state.cache = {}

# ── Header ──
c1,c2,c3,c4 = st.columns([2,3,4,2])
with c1:
    st.markdown('<p style="font-family:monospace;font-size:13px;font-weight:700;color:#00d4aa;margin:6px 0">◈ ADA MULTICHART</p>', unsafe_allow_html=True)
with c2:
    tf = st.radio("TF", list(TF_PERIODS.keys()), index=1, horizontal=True, label_visibility="collapsed")
with c3:
    key_in = st.text_input("key", value=st.session_state.api_key,
                            placeholder="Paste DexHunter API key...",
                            label_visibility="collapsed", type="password")
    if key_in:
        st.session_state.api_key = key_in
with c4:
    ca, cb = st.columns([1,1])
    with ca:
        do_refresh = st.button("↺")
    with cb:
        if st.session_state.api_key:
            st.markdown('<p style="color:#00d4aa;font-size:10px;font-family:monospace;margin:8px 0">● Live</p>', unsafe_allow_html=True)
        else:
            st.markdown('<p style="color:#f03e3e;font-size:10px;font-family:monospace;margin:8px 0">⚠ Key</p>', unsafe_allow_html=True)

st.divider()

def fetch_ohlcv(token_id, period, range_secs, api_key):
    ck = f"{token_id}_{period}_{int(time.time()//300)}"
    if ck in st.session_state.cache and not do_refresh:
        return st.session_state.cache[ck], None
    now = int(time.time())
    try:
        r = requests.post(
            f"{CHART_URL}/charts",
            json={"tokenIn":"","tokenOut":token_id,"period":period,"from":now-range_secs,"to":now},
            headers={"X-Partner-Id":api_key,"Content-Type":"application/json"},
            timeout=10
        )
        if r.status_code != 200:
            return None, f"HTTP {r.status_code}: {r.text[:100]}"
        data = r.json()
        # DexHunter có thể trả list thẳng hoặc {data: [...]}
        candles = data if isinstance(data, list) else data.get("data", data.get("candles", data.get("ohlcv", [])))
        st.session_state.cache[ck] = candles
        return candles, None
    except Exception as e:
        return None, str(e)

def fmt_price(p):
    if not p or p == 0: return "—"
    if p < 0.000001: return f"{p:.2e}"
    if p < 0.001:    return f"{p:.6f}"
    if p < 1:        return f"{p:.4f}"
    return f"{p:.2f}"

def render_card(ticker, candles, err):
    if err:
        st.markdown(f"""
        <div style="background:#111318;border:1px solid #1e2330;border-radius:6px;
                    padding:8px 10px;height:260px;display:flex;flex-direction:column">
            <div style="font-family:monospace;font-size:11px;font-weight:700;
                        color:#e2e8f0;margin-bottom:4px">{ticker}/ADA</div>
            <div style="color:#f03e3e;font-family:monospace;font-size:9px;
                        word-break:break-all">⚠ {err}</div>
        </div>""", unsafe_allow_html=True)
        return

    if not candles:
        st.markdown(f"""
        <div style="background:#111318;border:1px solid #1e2330;border-radius:6px;
                    padding:8px 10px;height:260px;display:flex;align-items:center;
                    justify-content:center;font-family:monospace;font-size:10px;color:#374151">
            {ticker} — No data
        </div>""", unsafe_allow_html=True)
        return

    # Parse candles — thử nhiều key name khác nhau
    valid = []
    for c in candles:
        try:
            if isinstance(c, (list, tuple)) and len(c) >= 5:
                t,o,h,l,cl = int(c[0]),float(c[1]),float(c[2]),float(c[3]),float(c[4])
                v = float(c[5]) if len(c)>5 else 0
            elif isinstance(c, dict):
                t  = int(c.get("time",  c.get("timestamp", c.get("t", 0))))
                o  = float(c.get("open",  c.get("o", 0)))
                h  = float(c.get("high",  c.get("h", 0)))
                l  = float(c.get("low",   c.get("l", 0)))
                cl = float(c.get("close", c.get("c", 0)))
                v  = float(c.get("volume",c.get("v", 0)))
            else:
                continue
            if t > 0 and cl > 0:
                valid.append({"time":t,"open":o,"high":h,"low":l,"close":cl,"volume":v})
        except:
            continue

    valid.sort(key=lambda x: x["time"])

    if not valid:
        # Show raw sample để debug
        sample = str(candles[0])[:120] if candles else "empty"
        st.markdown(f"""
        <div style="background:#111318;border:1px solid #1e2330;border-radius:6px;
                    padding:8px;height:260px;font-family:monospace;font-size:9px;color:#64748b">
            <b style="color:#e2e8f0">{ticker}</b> — parse error<br>
            sample: {sample}
        </div>""", unsafe_allow_html=True)
        return

    last = valid[-1]
    prev = valid[-2] if len(valid)>1 else last
    chg  = ((last["close"]-prev["close"])/prev["close"]*100) if prev["close"] else 0
    cc   = "#00d4aa" if chg>=0 else "#f03e3e"
    cs   = f"+{chg:.2f}%" if chg>=0 else f"{chg:.2f}%"

    cdata = json.dumps(valid)

    # Tách JS ra khỏi f-string để tránh conflict dấu {}
    div_html = (
        '<div style="background:#111318;border:1px solid #1a1d26;border-radius:6px;'
        'overflow:hidden;height:260px;display:flex;flex-direction:column">'
        '<div style="padding:5px 10px;border-bottom:1px solid #1a1d26;'
        'display:flex;align-items:center;flex-shrink:0">'
        f'<span style="font-family:monospace;font-size:11px;font-weight:700;color:#e2e8f0">{ticker}</span>'
        '<span style="font-family:monospace;font-size:9px;color:#2d3748;margin-left:4px">/ADA</span>'
        f'<span style="font-family:monospace;font-size:11px;color:#e2e8f0;margin-left:auto">{fmt_price(last["close"])}</span>'
        f'<span style="font-family:monospace;font-size:10px;color:{cc};margin-left:8px;font-weight:600">{cs}</span>'
        '</div>'
        f'<div id="c_{ticker}" style="flex:1;min-height:0"></div>'
        '</div>'
    )

    js_html = """
    <script src="https://cdnjs.cloudflare.com/ajax/libs/lightweight-charts/4.1.3/lightweight-charts.standalone.production.js"></script>
    <script>
    (function() {
        var el = document.getElementById('c_TICKER');
        if (!el) return;
        var chart = LightweightCharts.createChart(el, {
            layout: { background: { color: '#111318' }, textColor: '#374151' },
            grid: { vertLines: { color: '#1a1d26' }, horzLines: { color: '#1a1d26' } },
            rightPriceScale: { borderColor: '#1e2330', scaleMargins: { top: 0.05, bottom: 0.2 } },
            timeScale: { borderColor: '#1e2330', timeVisible: true, secondsVisible: false },
            handleScroll: true, handleScale: true,
        });
        var cSeries = chart.addCandlestickSeries({
            upColor: '#00d4aa', downColor: '#f03e3e',
            borderUpColor: '#00d4aa', borderDownColor: '#f03e3e',
            wickUpColor: '#00d4aa', wickDownColor: '#f03e3e',
        });
        var vSeries = chart.addHistogramSeries({
            color: '#7c5cfc33', priceFormat: { type: 'volume' }, priceScaleId: 'vol'
        });
        chart.priceScale('vol').applyOptions({ scaleMargins: { top: 0.82, bottom: 0 } });
        var d = CDATA;
        cSeries.setData(d.map(function(c) { return { time: c.time, open: c.open, high: c.high, low: c.low, close: c.close }; }));
        vSeries.setData(d.map(function(c) { return { time: c.time, value: c.volume, color: c.close >= c.open ? '#00d4aa22' : '#f03e3e22' }; }));
        chart.timeScale().fitContent();
        new ResizeObserver(function() {
            var r = el.getBoundingClientRect();
            if (r.width > 0 && r.height > 0) chart.resize(r.width, r.height);
        }).observe(el);
    })();
    </script>
    """.replace('TICKER', ticker).replace('CDATA', cdata)

    st.components.v1.html(div_html + js_html, height=264, scrolling=False)

if not st.session_state.api_key:
    st.markdown("""
    <div style="text-align:center;padding:80px;font-family:monospace;color:#64748b">
        <div style="font-size:40px;margin-bottom:16px">◈</div>
        <div style="font-size:14px;color:#e2e8f0;margin-bottom:8px">Nhập DexHunter API Key</div>
        <div style="font-size:11px">app.dexhunter.io/partners → <span style="color:#00d4aa">Keys tab</span></div>
    </div>""", unsafe_allow_html=True)
    st.stop()

period    = TF_PERIODS[tf]
rng       = TF_RANGE[tf]
api_key   = st.session_state.api_key

row1 = st.columns(4, gap="small")
row2 = st.columns(4, gap="small")

for i, tok in enumerate(TOKENS):
    col = row1[i] if i < 4 else row2[i-4]
    with col:
        candles, err = fetch_ohlcv(tok["id"], period, rng, api_key)
        render_card(tok["ticker"], candles, err)
