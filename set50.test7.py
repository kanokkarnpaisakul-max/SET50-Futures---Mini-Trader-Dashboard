import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
import math

# Optional auto-refresh: only if installed. If not, dashboard still works and user can refresh manually.
try:
    from streamlit_autorefresh import st_autorefresh
    st_autorefresh(interval=5000, limit=None)
except Exception:
    pass

st.set_page_config(layout="wide", page_title="SET50 Futures - Mini Trader Dashboard")

# -----------------------------
# Mock data generator
# -----------------------------

def get_mock_contract_data(contract: str):
    """Return mock snapshot for a given contract. Replace this function with API calls."""
    base = {
        "S50Z25": {"price": 814.0, "change": -1.32, "bid": 20000, "offer": 50000},
        "S50H26": {"price": 842.1, "change": +0.45, "bid": 18000, "offer": 22000},
        "S50M26": {"price": 798.75, "change": -0.62, "bid": 15000, "offer": 30000},
    }

    trades_map = {
        "S50Z25": [
            {"timestamp": "09:45", "price": 814.2, "volume": 300, "type": "Aggressive Sell"},
            {"timestamp": "11:15", "price": 814.6, "volume": 200, "type": "Aggressive Buy"},
            {"timestamp": "15:45", "price": 814.0, "volume": 500, "type": "Aggressive Sell"},
            {"timestamp": "16:05", "price": 814.8, "volume": 400, "type": "Aggressive Buy"},
        ],
        "S50H26": [
            {"timestamp": "09:30", "price": 841.8, "volume": 150, "type": "Aggressive Buy"},
            {"timestamp": "13:20", "price": 842.2, "volume": 250, "type": "Aggressive Buy"},
            {"timestamp": "15:50", "price": 842.0, "volume": 100, "type": "Aggressive Sell"},
            {"timestamp": "16:10", "price": 842.5, "volume": 300, "type": "Aggressive Buy"},
        ],
        "S50M26": [
            {"timestamp": "09:50", "price": 799.0, "volume": 400, "type": "Aggressive Sell"},
            {"timestamp": "14:10", "price": 798.5, "volume": 300, "type": "Aggressive Sell"},
            {"timestamp": "15:40", "price": 798.8, "volume": 200, "type": "Aggressive Buy"},
            {"timestamp": "16:20", "price": 799.2, "volume": 250, "type": "Aggressive Buy"},
        ],
    }

    entry = base.get(contract).copy()
    entry["trades"] = trades_map.get(contract, [])
    return entry


# -----------------------------
# Utility functions
# -----------------------------

def parse_trades(trades):
    for t in trades:
        t["dt"] = datetime.strptime(t["timestamp"], "%H:%M")
    return pd.DataFrame(trades)


def summarize_periods(trades_df):
    def summary(mask):
        buy = trades_df.loc[mask & (trades_df['type'] == 'Aggressive Buy'), 'volume'].sum()
        sell = trades_df.loc[mask & (trades_df['type'] == 'Aggressive Sell'), 'volume'].sum()
        return int(buy), int(sell), int(buy - sell)

    early = trades_df['dt'].dt.hour < 10
    mid = (trades_df['dt'].dt.hour >= 10) & (trades_df['dt'].dt.hour < 15)
    late = (trades_df['dt'].dt.hour >= 15) & (trades_df['dt'].dt.hour < 16)
    after = trades_df['dt'].dt.hour >= 16

    return {
        'early': summary(early),
        'mid': summary(mid),
        'late': summary(late),
        'after': summary(after)
    }


def compute_vwap(prices, volumes):
    try:
        return float((prices * volumes).sum() / volumes.sum())
    except Exception:
        return None


# -----------------------------
# Sidebar controls
# -----------------------------

st.sidebar.header("Dashboard Controls")
contract = st.sidebar.selectbox("เลือกสัญญา Futures", ["S50Z25", "S50H26", "S50M26"]) 
api_mode = st.sidebar.selectbox("Data source", ["Mock (local)", "SETSMART / TFEX / Provider (replace)"], index=0)

# Alert settings
alert_price = st.sidebar.number_input("Alert Price Threshold", value=820.0, step=0.5)
volume_ratio = st.sidebar.slider("Sell Volume > x times Buy Volume", min_value=1.0, max_value=5.0, value=2.0, step=0.1)
net_flow_threshold = st.sidebar.number_input("Net Flow Alert Threshold", value=-10000)

# Swing for Fibonacci
swing_high = st.sidebar.number_input("Swing High (for Fibo)", value=830.0, step=0.5)
swing_low = st.sidebar.number_input("Swing Low (for Fibo)", value=800.0, step=0.5)

# Auto-refresh toggle (if lib available)
auto_refresh = st.sidebar.checkbox("Auto refresh (if supported)", value=True)

# -----------------------------
# Data fetch (mock or placeholder for API)
# -----------------------------
with st.spinner('Fetching data...'):
    if api_mode == "Mock (local)":
        snapshot = get_mock_contract_data(contract)
    else:
        # Placeholder: user should replace with actual API calls
        snapshot = get_mock_contract_data(contract)

contract_price = snapshot["price"]
contract_change = snapshot["change"]
volume_bid = snapshot["bid"]
volume_offer = snapshot["offer"]
recent_trades = snapshot["trades"]

trades_df = parse_trades(recent_trades)

# -----------------------------
# Top: Market Overview
# -----------------------------

st.title("📊 SET50 Futures - Mini Trader Dashboard")
set_index = 1276.39
set50_index = 825.31

col1, col2, col3 = st.columns([1,1,1])
col1.metric("SET Index", f"{set_index}", "-0.91%", delta_color="inverse")
col2.metric("SET50 Index", f"{set50_index}", "-1.08%", delta_color="inverse")

# nice formatting for contract metric
delta_sign = f"{contract_change}%"
if contract_change > 0:
    delta_sign = f"+{contract_change}%"
col3.metric(contract + " (Futures)", f"{contract_price}", delta_sign)

st.markdown("---")

# -----------------------------
# Row: Liquidity (left) + Trade Flow (right)
# -----------------------------

left, right = st.columns([1,2])

with left:
    st.subheader("🏦 Liquidity & Imbalance")
    imbalance = volume_offer - volume_bid
    ratio = (volume_offer / (volume_bid + 1))
    sentiment = "Bearish Pressure" if imbalance > 1000 else ("Bullish" if imbalance < -1000 else "Neutral")

    fig_vol = go.Figure(go.Bar(
        x=["Bid", "Offer"],
        y=[volume_bid, volume_offer],
        marker_color=["green", "red"],
        text=[f"{volume_bid}", f"{volume_offer}"],
        textposition='auto'
    ))
    fig_vol.update_layout(height=300, title=f"Bid vs Offer Volume (Ratio: {ratio:.2f})")
    st.plotly_chart(fig_vol, use_container_width=True)

    st.markdown(f"**Sentiment:** {sentiment}")
    st.markdown(f"**Bid:** {volume_bid} | **Offer:** {volume_offer} | **Imbalance:** {imbalance}")

    # VWAP (mock from trades)
    if not trades_df.empty:
        vwap = compute_vwap(trades_df['price'], trades_df['volume'])
        st.markdown(f"**VWAP (from recent trades):** {vwap:.2f} ")
    else:
        st.markdown("**VWAP:** N/A")

with right:
    st.subheader("🔄 Trade Flow Timeline")
    if trades_df.empty:
        st.info("No trades in sample data")
    else:
        fig_trade = go.Figure()
        colors = {"Aggressive Buy": "green", "Aggressive Sell": "red"}
        for ttype in trades_df['type'].unique():
            df_t = trades_df[trades_df['type'] == ttype]
            fig_trade.add_trace(go.Scatter(
                x=df_t['dt'],
                y=df_t['price'],
                mode='markers',
                marker=dict(size=(df_t['volume'] / df_t['volume'].max()) * 40 + 8,
                            color=[colors.get(ttype, 'gray')] * len(df_t),
                            line=dict(width=1, color='black')),
                name=ttype,
                hovertemplate="Price: %{y}<br>Volume: %{marker.size:.0f}<extra></extra>"
            ))
        fig_trade.update_layout(height=350, xaxis_title='Time', yaxis_title='Price')
        st.plotly_chart(fig_trade, use_container_width=True)

# -----------------------------
# Alerts / Sentiment Panel
# -----------------------------

st.subheader("🚨 Alerts & Trade Signals")
buy_volume = int(trades_df.loc[trades_df['type'] == 'Aggressive Buy', 'volume'].sum())
sell_volume = int(trades_df.loc[trades_df['type'] == 'Aggressive Sell', 'volume'].sum())
net_flow = buy_volume - sell_volume

if contract_price < alert_price and sell_volume > buy_volume * volume_ratio:
    st.error(f"⚠️ PANIC ALERT: Price < {alert_price} with heavy sell flow (> {volume_ratio}x buy volume)")
elif net_flow < net_flow_threshold:
    st.warning(f"🔄 Net Flow ต่ำกว่า Threshold ({net_flow_threshold}) | Net: {net_flow}")
elif sell_volume < 400 and contract_price > (swing_low + (swing_high - swing_low) * 0.2):
    st.info("📉 แรงขายเริ่มเบาลง และราคาดีดกลับ")
elif net_flow > 0 and contract_price > (swing_low + (swing_high - swing_low) * 0.25):
    st.success("📈 สัญญาณกลับทิศ: Net Flow เป็นบวกและราคาดีดกลับ")
else:
    st.success("✅ Market Stable")

st.markdown(f"**Buy Volume:** {buy_volume} | **Sell Volume:** {sell_volume} | **Net Flow:** {net_flow}")

st.markdown("---")

# -----------------------------
# Time Period Analysis
# -----------------------------

st.subheader("🕒 Time Period Analysis")
periods = summarize_periods(trades_df) if not trades_df.empty else None
pcol1, pcol2, pcol3, pcol4 = st.columns(4)
if periods:
    pcol1.metric("ก่อน 10:00", f"Net {periods['early'][2]}", f"Buy:{periods['early'][0]} / Sell:{periods['early'][1]}")
    pcol2.metric("10:00–15:30", f"Net {periods['mid'][2]}", f"Buy:{periods['mid'][0]} / Sell:{periods['mid'][1]}")
    pcol3.metric("15:30–16:00", f"Net {periods['late'][2]}", f"Buy:{periods['late'][0]} / Sell:{periods['late'][1]}")
    pcol4.metric("หลัง 16:00", f"Net {periods['after'][2]}", f"Buy:{periods['after'][0]} / Sell:{periods['after'][1]}")
else:
    pcol1.metric("ก่อน 10:00", "Net 0", "Buy:0 / Sell:0")
    pcol2.metric("10:00–15:30", "Net 0", "Buy:0 / Sell:0")
    pcol3.metric("15:30–16:00", "Net 0", "Buy:0 / Sell:0")
    pcol4.metric("หลัง 16:00", "Net 0", "Buy:0 / Sell:0")

st.markdown("---")

# -----------------------------
# Technical: Fibonacci & Levels
# -----------------------------

st.subheader("📐 Fibonacci + Key Levels")
levels = {
    "0.0%": swing_high,
    "23.6%": swing_high - (swing_high - swing_low) * 0.236,
    "38.2%": swing_high - (swing_high - swing_low) * 0.382,
    "50.0%": swing_high - (swing_high - swing_low) * 0.5,
    "61.8%": swing_high - (swing_high - swing_low) * 0.618,
    "100.0%": swing_low
}

fib_fig = go.Figure()
# price range line
fib_fig.add_trace(go.Scatter(x=[0, 1], y=[swing_low, swing_high], mode='lines', name='Price Range', line=dict(color='blue')))
for level_name, price in levels.items():
    fib_fig.add_hline(y=price, line_dash="dash", annotation_text=level_name, annotation_position="right")

# current price marker
fib_fig.add_trace(go.Scatter(x=[0.5], y=[contract_price], mode='markers+text', text=["Current"], textposition='top center', marker=dict(size=12, color='orange')))
fib_fig.update_layout(height=350, title="Fibonacci Levels & Current Price")
st.plotly_chart(fib_fig, use_container_width=True)

st.markdown("---")

# -----------------------------
# Big Picture: News & Calendar (placeholders)
# -----------------------------

st.subheader("🌍 Big Picture & Calendar")
coln1, coln2 = st.columns([2,1])
with coln1:
    st.info("News: (placeholder) - Connect your news API or RSS feed here to show headlines that may impact SET50 Futures.")
    st.write("- Foreign flows: + / - (connect API)")
    st.write("- Global futures: ES, NK, HSI (connect provider)")

with coln2:
    st.write("Calendar")
    st.write("- 2025-10-01 : Macro Event (example)")
    st.write("- 2025-10-15 : Expiry Day (example)")

st.markdown("---")

# -----------------------------
# Footer: How to connect real API
# -----------------------------

st.caption("To connect real data: replace get_mock_contract_data() with API calls (SETSMART / SETTRADE / Databento). Use requests or provider SDK, parse JSON into same structure and update trades_df accordingly.")

# End of file
