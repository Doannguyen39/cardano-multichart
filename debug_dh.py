import streamlit as st
import requests
import json
import time

st.set_page_config(page_title="DH Debug", layout="wide")
st.title("DexHunter API Debug")

api_key = st.text_input("API Key", type="password")

if api_key:
    NIGHT = "0691b2fecca1ac4f53cb6dfb00b7013e561d1f34403b957cbb5af1fa4e49474854"
    now   = int(time.time())
    from_ts = now - 7*24*3600

    st.subheader("POST /charts — Raw Response")
    try:
        r = requests.post(
            "https://charts.dhapi.io/charts",
            json={"tokenIn": "", "tokenOut": NIGHT, "period": "1hour", "from": from_ts, "to": now},
            headers={"X-Partner-Id": api_key, "Content-Type": "application/json"},
            timeout=10
        )
        st.write(f"Status: {r.status_code}")
        st.write(f"Headers: {dict(r.headers)}")
        raw = r.text[:3000]
        st.code(raw)
        
        try:
            data = r.json()
            st.write("Type:", type(data))
            if isinstance(data, list) and len(data) > 0:
                st.write("First item:", data[0])
            elif isinstance(data, dict):
                st.write("Keys:", list(data.keys()))
                for k,v in data.items():
                    st.write(f"  {k}:", str(v)[:200])
        except:
            st.write("Not JSON")
    except Exception as e:
        st.error(f"Error: {e}")
