import streamlit as st
import pandas as pd
import random
import time

# ==========================================
# 1. PAGE CONFIG & MOBILE CSS
# ==========================================
st.set_page_config(
    page_title="Wash Trade Detector",
    page_icon="🛡️",
    layout="wide"
)

st.markdown("""
    <style>
    .block-container { padding-top: 1rem; padding-bottom: 1rem; }
    [data-testid="stMetricValue"] { font-size: 1.6rem !important; }
    h2 { font-size: 1.4rem !important; font-weight: 700; margin-bottom: 0.2rem; }
    </style>
""", unsafe_allow_html=True)

# State initialization
if "trade_history" not in st.session_state:
    st.session_state.trade_history = []
if "monitored_tokens" not in st.session_state:
    st.session_state.monitored_tokens = {}

# ==========================================
# 2. SIDEBAR CONFIGURATION
# ==========================================
st.sidebar.header("⚙️ Detection Thresholds")

dust_threshold = st.sidebar.number_input(
    "Dust Trade Cutoff ($ USD)", min_value=0.1, max_value=50.0, value=1.0, step=0.5
)
max_dust_ratio = st.sidebar.slider(
    "Max Allowed Dust Ratio (%)", min_value=5, max_value=90, value=25
) / 100.0

max_wallet_reuse = st.sidebar.slider(
    "Max Allowed Wallet Reuse (%)", min_value=5, max_value=90, value=35
) / 100.0

st.sidebar.markdown("---")
st.sidebar.header("🌐 Chain Filters")
enable_solana = st.sidebar.checkbox("Solana", value=True)
enable_bnb = st.sidebar.checkbox("BNB Chain", value=True)
enable_evm = st.sidebar.checkbox("EVM / Robinhood", value=True)

# ==========================================
# 3. CORE WASH TRADING DETECTOR ENGINE
# ==========================================
def analyze_token_buffer(trades: list[dict]) -> dict:
    if len(trades) < 4:
        return {"is_organic": True, "flags": [], "dust_ratio": 0.0, "wallet_reuse": 0.0}

    df = pd.DataFrame(trades)
    total_txns = len(df)

    dust_count = len(df[df["usd_val"] < dust_threshold])
    dust_ratio = dust_count / total_txns

    unique_wallets = df["trader"].nunique()
    wallet_reuse = 1.0 - (unique_wallets / total_txns)

    buys = len(df[df["type"] == "buy"])
    buy_ratio = buys / total_txns

    flags = []
    if dust_ratio > max_dust_ratio:
        flags.append(f"DUST_PADDING ({int(dust_ratio*100)}%)")
    if wallet_reuse > max_wallet_reuse:
        flags.append(f"RECYCLED_WALLETS ({unique_wallets}/{total_txns})")
    if total_txns >= 8 and (buy_ratio >= 0.90 or buy_ratio <= 0.10):
        flags.append(f"ONE_SIDED_TAPE ({buys}B / {total_txns-buys}S)")

    return {
        "is_organic": len(flags) == 0,
        "flags": flags,
        "dust_ratio": dust_ratio,
        "wallet_reuse": wallet_reuse,
        "buy_ratio": buy_ratio
    }

# ==========================================
# 4. MOCK DATA GENERATOR
# ==========================================
def generate_mock_trade():
    chains = []
    if enable_solana: chains.append("Solana")
    if enable_bnb: chains.append("BNB")
    if enable_evm: chains.append("EVM")
    
    if not chains:
        return None

    chain = random.choice(chains)
    tokens = {
        "Solana": ["SOL/BONK", "SOL/WIF", "SOL/PUMP"],
        "BNB": ["BNB/CAKE", "BNB/FOUR"],
        "EVM": ["ETH/UNI", "ETH/PEPE"]
    }
    
    is_bot = random.random() < 0.3
    trader = "0xBot1234...5678" if is_bot else f"0x{random.randint(1000, 9999)}...{random.randint(1000, 9999)}"
    usd_val = random.uniform(0.1, 0.8) if is_bot else random.uniform(5.0, 500.0)

    return {
        "chain": chain,
        "symbol": random.choice(tokens[chain]),
        "trader": trader,
        "usd_val": usd_val,
        "type": random.choice(["buy", "sell"]),
        "timestamp": time.strftime("%H:%M:%S")
    }

# ==========================================
# 5. UI CONTROLS & METRICS
# ==========================================
st.markdown("## 🛡️ Multi-Chain Wash Trade Detector")

col1, col2 = st.columns([2, 1])
with col1:
    run_stream = st.toggle("Start Live Stream", value=True)
with col2:
    if st.button("Clear History", use_container_width=True):
        st.session_state.trade_history = []
        st.session_state.monitored_tokens = {}
        st.rerun()

# Metrics row
m1, m2, m3 = st.columns(3)
flagged_count = sum(
    1 for t, buf in st.session_state.monitored_tokens.items()
    if not analyze_token_buffer(buf)["is_organic"]
)

m1.metric("Total Trades", len(st.session_state.trade_history))
m2.metric("Active Pairs", len(st.session_state.monitored_tokens))
m3.metric("Flagged Pairs", flagged_count)

st.markdown("---")

# ==========================================
# 6. STREAM LOOP & DISPLAY TABLES
# ==========================================
if run_stream:
    trade = generate_mock_trade()
    if trade:
        st.session_state.trade_history.insert(0, trade)
        if len(st.session_state.trade_history) > 100:
            st.session_state.trade_history.pop()

        sym = trade["symbol"]
        if sym not in st.session_state.monitored_tokens:
            st.session_state.monitored_tokens[sym] = []
        
        st.session_state.monitored_tokens[sym].append(trade)
        if len(st.session_state.monitored_tokens[sym]) > 15:
            st.session_state.monitored_tokens[sym].pop(0)

# Build tables for clean vs flagged pairs
clean_matrix = []
flagged_matrix = []

if st.session_state.monitored_tokens:
    for token, buf in st.session_state.monitored_tokens.items():
        res = analyze_token_buffer(buf)
        row = {
            "Token": token,
            "Dust Ratio": f"{int(res['dust_ratio']*100)}%",
            "Wallet Reuse": f"{int(res['wallet_reuse']*100)}%",
            "Txns": len(buf),
            "Flags": ", ".join(res["flags"]) if res["flags"] else "None"
        }
        if res["is_organic"]:
            clean_matrix.append(row)
        else:
            flagged_matrix.append(row)

# Displays
st.subheader("✅ Passed / Clean Pairs")
if clean_matrix:
    st.dataframe(pd.DataFrame(clean_matrix), use_container_width=True)
else:
    st.info("No clean pairs detected in current window.")

st.subheader("🚨 Flagged / Manipulated Pairs")
if flagged_matrix:
    st.dataframe(pd.DataFrame(flagged_matrix), use_container_width=True)
else:
    st.success("No manipulated pairs flagged.")

st.subheader("⚡ Live Transaction Tape")
if st.session_state.trade_history:
    st.dataframe(pd.DataFrame(st.session_state.trade_history), use_container_width=True)

# Loop trigger
if run_stream:
    time.sleep(0.5)
    st.rerun()
