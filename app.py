# streamlit_app.py
import requests
import streamlit as st
from datetime import datetime

# --- Currencies (major ones) ---
CURRENCIES = [
    "USD","EUR","GBP","JPY","AUD","CAD","CHF","CNY","INR","PKR","SGD","NZD",
    "SEK","NOK","RUB","BRL","ZAR","AED","SAR","MXN","TRY","HKD","IDR","THB",
    "VND","ILS"
]

# --- Offline fallback rates: USD per 1 unit of currency (approximate) ---
# Example: OFFLINE_RATES['EUR'] = how many USD is 1 EUR (≈ 1.08 USD)
OFFLINE_RATES = {
  "USD":1.0, "EUR":1.08, "GBP":1.27, "JPY":0.0068, "AUD":0.63, "CAD":0.74,
  "CHF":1.09, "CNY":0.14, "INR":0.012, "PKR":0.0033, "SGD":0.74, "NZD":0.59,
  "SEK":0.092, "NOK":0.093, "RUB":0.012, "BRL":0.19, "ZAR":0.049, "AED":0.27,
  "SAR":0.27, "MXN":0.056, "TRY":0.034, "HKD":0.128, "IDR":0.000062,
  "THB":0.027, "VND":0.000042, "ILS":0.27
}

st.set_page_config(page_title="Currency Converter", layout="centered")
st.title("Currency Converter")
st.write(
    "Converts between major currencies. "
    "Tries live rates from exchangerate.host; falls back to built-in offline rates if needed."
)

# Sidebar options
st.sidebar.header("Options")
use_offline_only = st.sidebar.checkbox("Use offline rates only", value=False)
show_table = st.sidebar.checkbox("Show conversion table to all currencies", value=False)
cache_minutes = st.sidebar.number_input("Cache live rates (minutes)", min_value=1, max_value=1440, value=60)

col1, col2 = st.columns([2,2])
with col1:
    amount = st.number_input("Amount", min_value=0.0, value=1.0, format="%.6f")
with col2:
    from_curr = st.selectbox("From", options=CURRENCIES, index=CURRENCIES.index("USD"))
    to_curr = st.selectbox("To", options=CURRENCIES, index=CURRENCIES.index("PKR"))

convert_btn = st.button("Convert")

# Caching helpers (Streamlit caches network calls so you don't spam API)
@st.cache_data(ttl=60*60)  # default 1 hour; we'll use cache_minutes in live_rates()
def _fetch_latest_rates(base):
    url = f"https://api.exchangerate.host/latest?base={base}"
    r = requests.get(url, timeout=8)
    r.raise_for_status()
    return r.json()

@st.cache_data(ttl=60*60)
def _convert_via_api(amount, frm, to):
    url = f"https://api.exchangerate.host/convert?from={frm}&to={to}&amount={amount}"
    r = requests.get(url, timeout=8)
    r.raise_for_status()
    return r.json()

def offline_convert(amount, frm, to):
    """Convert using OFFLINE_RATES (USD per 1 unit)."""
    amount = float(amount)
    # convert from 'frm' to USD
    amount_in_usd = amount * OFFLINE_RATES[frm]
    # convert USD to 'to'
    converted = amount_in_usd / OFFLINE_RATES[to]
    return converted

def try_live_convert(amount, frm, to):
    """Try the exchangerate.host convert endpoint; raises on failure."""
    data = _convert_via_api(amount, frm, to)
    if data.get("result") is None:
        raise ValueError("No result returned from API")
    return data

def try_live_table(amount, frm):
    """Get live rates for base=frm and compute conversions to all currencies."""
    data = _fetch_latest_rates(frm)
    rates = data.get("rates", {})
    rows = []
    for cur in CURRENCIES:
        if cur == frm:
            val = amount
        else:
            r = rates.get(cur)
            if r is None:
                val = None
            else:
                val = amount * r
        rows.append((cur, val))
    return data.get("date"), rows

# Conversion behavior when user clicks button
if convert_btn:
    if use_offline_only:
        try:
            converted = offline_convert(amount, from_curr, to_curr)
            st.success(f"{converted:.4f} {to_curr}  (offline rates)")
        except Exception as e:
            st.error(f"Offline conversion failed: {e}")
    else:
        # try live API first, fallback to offline
        try:
            api_data = try_live_convert(amount, from_curr, to_curr)
            val = api_data["result"]
            rate = api_data.get("info", {}).get("rate")
            date = api_data.get("date")
            st.success(f"{val:.4f} {to_curr}  (live rates)")
            if rate:
                st.caption(f"Rate: 1 {from_curr} = {rate:.6f} {to_curr}  ·  Date: {date}")
        except Exception as e:
            st.warning("Live conversion failed — using offline rates.")
            try:
                converted = offline_convert(amount, from_curr, to_curr)
                st.success(f"{converted:.4f} {to_curr}  (offline rates)")
            except Exception as e2:
                st.error(f"Both live and offline conversion failed: {e2}")

# Show table (all currencies)
if show_table:
    st.markdown("---")
    st.header(f"Convert {amount} {from_curr} → all currencies")
    if use_offline_only:
        rows = []
        for cur in CURRENCIES:
            rows.append({"currency": cur, "amount": f"{offline_convert(amount, from_curr, cur):.4f}"})
        st.table(rows)
    else:
        try:
            date, rows = try_live_table(amount, from_curr)
            # Build nice list for st.table
            pretty = []
            for cur, val in rows:
                pretty.append({"currency": cur, "amount": f"{val:.4f}" if val is not None else "N/A"})
            st.table(pretty)
            st.caption(f"Rates date: {date}")
        except Exception as e:
            st.warning("Failed to fetch live rates; showing offline fallback.")
            rows = []
            for cur in CURRENCIES:
                rows.append({"currency": cur, "amount": f"{offline_convert(amount, from_curr, cur):.4f}"})
            st.table(rows)

st.markdown("---")
st.write("Notes: Uses exchangerate.host (free, no API key). Offline rates are approximate placeholders — update if you need offline accuracy.")
