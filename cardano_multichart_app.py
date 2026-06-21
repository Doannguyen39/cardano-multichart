import streamlit as st
import requests
import time
import plotly.graph_objects as go

# Auto-refresh component. Import an toàn: nếu chưa thêm vào requirements.txt
# thì app vẫn chạy (chỉ tắt auto + nhắc cài), KHÔNG crash.
try:
    from streamlit_autorefresh import st_autorefresh
    HAS_AUTOREFRESH = True
except Exception:
    HAS_AUTOREFRESH = False

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
div[data-testid="column"] { padding: 0 2px !important; }
</style>
""", unsafe_allow_html=True)

CHART_URL = "https://charts.dhapi.io"
API_URL   = "https://api-us.dexhunterv3.app"

TOKENS = [
    {"ticker": "LQ",    "id": "da8c30857834c6ae7203935b89278c532b3995245295456f993e1d244c51"},
    {"ticker": "NIGHT", "id": "0691b2fecca1ac4f53cb6dfb00b7013e561d1f34403b957cbb5af1fa4e49474854"},
    {"ticker": "IAG",   "id": "5d16cc1a177b5d9ba9cfa9793b07e60f1fb70fea1f8aef064415d114494147"},
    {"ticker": "SNEK",  "id": "279c909f348e533da5808898f87f9a14bb2c3dfbbacccd631d927a3f534e454b"},
    {"ticker": "HOSKY", "id": "a0028f350aaabe0545fdcb56b039bfb08e4bb4d8c4d7c3c7d481c235484f534b59"},
    {"ticker": "MIN",   "id": "29d222ce763455e3d7a09a665ce554f00ac89d2e99a1a83d267170c64d494e"},
    {"ticker": "FLDT",  "id": "577f0b1342f8f8f4aed3388b80a8535812950c7a892495c0ecdf0f1e0014df10464c4454"},
    {"ticker": "BOS",   "id": "1fa8a8909a66bb5c850c1fc3fe48903a5879ca2c1c9882e9055eef8d0014df10424f5320546f6b656e"},
]

TF_PERIODS = {"15m":"15min","1H":"1hour","4H":"4hour","1D":"1day"}
TF_RANGE   = {"15m":2*24*3600,"1H":7*24*3600,"4H":30*24*3600,"1D":180*24*3600}

# Interval auto-refresh (giây) → nhãn hiển thị
REFRESH_OPTS = {30: "30s", 60: "1m", 120: "2m", 300: "5m"}

if "api_key" not in st.session_state:
    st.session_state.api_key = ""
if "ada_usd" not in st.session_state:
    st.session_state.ada_usd = 0.0
if "cache" not in st.session_state:
    st.session_state.cache = {}

# ── Lấy giá ADA/USD ──────────────────────────────────────────────
def get_ada_price(api_key):
    try:
        r = requests.get(f"{API_URL}/swap/adaValue",
                         headers={"X-Partner-Id": api_key}, timeout=5)
        v = r.json()
        return float(v) if isinstance(v, (int,float)) else float(str(v).strip())
    except:
        return 0.0

# ── Fetch OHLCV ──────────────────────────────────────────────────
def fetch_ohlcv(token_id, period, range_secs, api_key):
    # Cache theo token+period; chỉ fetch lại khi do_refresh=True (bấm ↺ hoặc auto-tick).
    # Bỏ time-bucket cũ (//300) vì nó vừa chặn auto-refresh dưới 5 phút, vừa rò rỉ cache.
    ck = f"{token_id}_{period}"
    if ck in st.session_state.cache and not do_refresh:
        return st.session_state.cache[ck], None
    now = int(time.time())
    try:
        r = requests.post(
            f"{CHART_URL}/charts",
            json={"tokenIn":"","tokenOut":token_id,"period":period,
                  "from":now-range_secs,"to":now},
            headers={"X-Partner-Id":api_key,"Content-Type":"application/json"},
            timeout=10
        )
        if r.status_code != 200:
            return None, f"HTTP {r.status_code}"
        data = r.json()
        candles = data if isinstance(data, list) else \
                  data.get("data", data.get("candles", data.get("ohlcv", [])))
        st.session_state.cache[ck] = candles
        return candles, None
    except Exception as e:
        return None, str(e)

# ── Parse candles ────────────────────────────────────────────────
def parse_candles(raw, ada_usd=1.0):
    from datetime import datetime, timezone
    valid = []
    for c in raw:
        try:
            if isinstance(c, dict):
                # Timestamp: thử unix trước, rồi ISO string
                raw_t = c.get("unix", c.get("time", c.get("t", 0)))
                if not raw_t:
                    ts_str = c.get("timestamp", "")
                    if ts_str:
                        dt = datetime.fromisoformat(ts_str.replace("Z","+00:00"))
                        raw_t = int(dt.timestamp())
                t  = int(raw_t) if raw_t else 0
                o  = float(c.get("open",  c.get("o", 0))) * ada_usd
                h  = float(c.get("high",  c.get("h", 0))) * ada_usd
                l  = float(c.get("low",   c.get("l", 0))) * ada_usd
                cl = float(c.get("close", c.get("c", 0))) * ada_usd
                v  = float(c.get("volume",c.get("v", 0)))
            elif isinstance(c, (list,tuple)) and len(c) >= 5:
                t,o,h,l,cl = int(c[0]),float(c[1])*ada_usd,float(c[2])*ada_usd,float(c[3])*ada_usd,float(c[4])*ada_usd
                v = float(c[5])*ada_usd if len(c)>5 else 0
            else:
                continue
            if t > 0 and cl > 0:
                dt_utc = datetime.fromtimestamp(t, tz=timezone.utc)
                valid.append({"dt":dt_utc,"o":o,"h":h,"l":l,"c":cl,"v":v})
        except:
            continue
    valid.sort(key=lambda x: x["dt"])
    return valid

# ── Build Plotly candlestick ─────────────────────────────────────
def make_chart(candles, ticker):
    if not candles:
        fig = go.Figure()
        fig.add_annotation(text="No data", x=0.5, y=0.5, showarrow=False,
                           font=dict(color="#374151", size=12))
    else:
        dts  = [c["dt"] for c in candles]
        opens  = [c["o"] for c in candles]
        highs  = [c["h"] for c in candles]
        lows   = [c["l"] for c in candles]
        closes = [c["c"] for c in candles]
        vols   = [c["v"] for c in candles]
        colors = ["#00d4aa" if c["c"]>=c["o"] else "#f03e3e" for c in candles]

        fig = go.Figure()
        # Volume bars
        fig.add_trace(go.Bar(
            x=dts, y=vols,
            marker_color=colors,
            opacity=0.25,
            yaxis="y2",
            showlegend=False,
            name="Vol"
        ))
        # Candlestick
        fig.add_trace(go.Candlestick(
            x=dts,
            open=opens, high=highs, low=lows, close=closes,
            increasing_line_color="#00d4aa",
            decreasing_line_color="#f03e3e",
            increasing_fillcolor="#00d4aa",
            decreasing_fillcolor="#f03e3e",
            showlegend=False,
            name=ticker
        ))

    fig.update_layout(
        margin=dict(l=0,r=4,t=0,b=0),
        paper_bgcolor="#111318",
        plot_bgcolor="#111318",
        xaxis=dict(
            showgrid=True, gridcolor="#1a1d26",
            color="#374151", tickfont=dict(size=9),
            rangeslider=dict(visible=False),
            showline=False,
        ),
        yaxis=dict(
            showgrid=True, gridcolor="#1a1d26",
            color="#374151", tickfont=dict(size=9),
            side="right", showline=False,
        ),
        yaxis2=dict(
            overlaying="y", side="right",
            showgrid=False, showticklabels=False,
            domain=[0,0.2],
        ),
        height=220,
    )
    fig.update_xaxes(showspikes=True, spikecolor="#374151", spikethickness=1)
    fig.update_yaxes(showspikes=True, spikecolor="#374151", spikethickness=1)
    return fig

def fmt_usd(p):
    if not p or p == 0: return "—"
    if p < 0.000001: return f"${p:.2e}"
    if p < 0.001:    return f"${p:.6f}"
    if p < 1:        return f"${p:.4f}"
    if p < 1000:     return f"${p:.2f}"
    return f"${p:,.0f}"

# ── Header ───────────────────────────────────────────────────────
c1,c2,c3,c4,c5 = st.columns([2, 2, 3.4, 2.4, 1.4])
with c1:
    st.markdown('<p style="font-family:monospace;font-size:13px;font-weight:700;'
                'color:#00d4aa;margin:6px 0">◈ ADA MULTICHART</p>',
                unsafe_allow_html=True)
with c2:
    tf = st.radio("TF", list(TF_PERIODS.keys()), index=1,
                  horizontal=True, label_visibility="collapsed")
with c3:
    key_in = st.text_input("key", value=st.session_state.api_key,
                            placeholder="Paste DexHunter API key...",
                            label_visibility="collapsed", type="password")
    if key_in:
        st.session_state.api_key = key_in
with c4:
    a1, a2 = st.columns([1, 1])
    with a1:
        auto = st.toggle("Auto", value=True, help="Tự refresh dữ liệu theo chu kỳ (dùng rerun, KHÔNG reload trang nên không mất API key)")
    with a2:
        interval = st.selectbox("int", list(REFRESH_OPTS.keys()), index=1,
                                format_func=lambda s: REFRESH_OPTS[s],
                                label_visibility="collapsed")
with c5:
    ca,cb = st.columns([1,1])
    with ca:
        manual_btn = st.button("↺")
    with cb:
        if st.session_state.api_key:
            st.markdown('<p style="color:#00d4aa;font-size:10px;'
                        'font-family:monospace;margin:8px 0">● Live</p>',
                        unsafe_allow_html=True)
        else:
            st.markdown('<p style="color:#f03e3e;font-size:10px;'
                        'font-family:monospace;margin:8px 0">⚠ Key</p>',
                        unsafe_allow_html=True)

# ── Auto-refresh: chỉ gọi 1 LẦN, dùng rerun (giữ session_state/api_key) ──────────
refresh_count = 0
if auto and HAS_AUTOREFRESH:
    refresh_count = st_autorefresh(interval=interval * 1000, key="ada_auto")

_prev = st.session_state.get("_auto_count", None)
auto_ticked = bool(auto) and (refresh_count != _prev)   # True khi timer vừa tick
st.session_state["_auto_count"] = refresh_count

# do_refresh = bấm nút thủ công HOẶC auto vừa tick → fetch lại tất cả
do_refresh = bool(manual_btn) or auto_ticked

if auto and not HAS_AUTOREFRESH:
    st.caption("⚠️ Auto chưa chạy được — thêm dòng `streamlit-autorefresh` vào **requirements.txt** rồi reboot app.")

st.divider()

if not st.session_state.api_key:
    st.markdown("""
    <div style="text-align:center;padding:80px;font-family:monospace;color:#64748b">
        <div style="font-size:40px;margin-bottom:16px">◈</div>
        <div style="font-size:14px;color:#e2e8f0;margin-bottom:8px">Nhập DexHunter API Key</div>
        <div style="font-size:11px">app.dexhunter.io/partners →
            <span style="color:#00d4aa">Keys tab</span></div>
    </div>""", unsafe_allow_html=True)
    st.stop()

api_key  = st.session_state.api_key
period   = TF_PERIODS[tf]
rng      = TF_RANGE[tf]

# Lấy ADA/USD (refresh mỗi lần do_refresh, hoặc lần đầu khi còn 0)
if do_refresh or st.session_state.ada_usd == 0.0:
    st.session_state.ada_usd = get_ada_price(api_key)
ada_usd = st.session_state.ada_usd if st.session_state.ada_usd > 0 else 1.0

# ── Grid 4×2 ─────────────────────────────────────────────────────
row1 = st.columns(4, gap="small")
row2 = st.columns(4, gap="small")

for i, tok in enumerate(TOKENS):
    col = row1[i] if i < 4 else row2[i-4]
    with col:
        raw, err = fetch_ohlcv(tok["id"], period, rng, api_key)

        # Header
        if raw and not err:
            candles = parse_candles(raw, ada_usd)
            if candles:
                last = candles[-1]
                prev = candles[-2] if len(candles)>1 else last
                chg  = ((last["c"]-prev["c"])/prev["c"]*100) if prev["c"] else 0
                cc   = "#00d4aa" if chg>=0 else "#f03e3e"
                cs   = f"+{chg:.2f}%" if chg>=0 else f"{chg:.2f}%"
                st.markdown(
                    f'<div style="font-family:monospace;font-size:10px;'
                    f'padding:4px 2px;display:flex;gap:8px;align-items:center">'
                    f'<b style="color:#e2e8f0;font-size:11px">{tok["ticker"]}</b>'
                    f'<span style="color:#374151">/USD</span>'
                    f'<span style="color:#e2e8f0;margin-left:auto">{fmt_usd(last["c"])}</span>'
                    f'<span style="color:{cc};font-weight:600">{cs}</span>'
                    f'</div>',
                    unsafe_allow_html=True
                )
                fig = make_chart(candles, tok["ticker"])
            else:
                st.markdown(f'<div style="font-family:monospace;font-size:10px;'
                            f'color:#374151;padding:4px">{tok["ticker"]} — parse error</div>',
                            unsafe_allow_html=True)
                fig = make_chart([], tok["ticker"])
        else:
            st.markdown(f'<div style="font-family:monospace;font-size:10px;'
                        f'color:#f03e3e;padding:4px">{tok["ticker"]} — {err or "no data"}</div>',
                        unsafe_allow_html=True)
            fig = make_chart([], tok["ticker"])

        st.plotly_chart(fig, use_container_width=True,
                        config={"displayModeBar":False})

# Footer + trạng thái auto
_auto_txt = (f"· auto {REFRESH_OPTS[interval]}" if (auto and HAS_AUTOREFRESH) else "· auto off")
st.markdown(
    f'<p style="text-align:center;font-family:monospace;font-size:9px;'
    f'color:#1e2330;margin-top:2px">DexHunter Charts API · Cardano on-chain {_auto_txt}</p>',
    unsafe_allow_html=True
)
