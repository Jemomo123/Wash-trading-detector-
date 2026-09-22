import streamlit as st
import pandas as pd
import asyncio
import random
import time

# ==========================================
# 1. PAGE CONFIGURATION & INITIALIZATION
# ==========================================
st.set_page_config(
    page_title="Multi-Chain Wash Trade Detector",
    page_icon="🛡️",
    layout="wide"
)

st.title("🛡️ Multi-Chain Wash-Trading & Manipulation Detector")
st.caption("Live streaming analytics for Solana, BNB Chain, and EVM/Robinhood Chain")

# Initialize Session State Buffers
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
    """
    Evaluates recent trade buffer for manipulation signatures.
    """
    if len(trades) < 4:
        return {"is_organic": True, "flags": [], "dust_ratio": 0.0, "wallet_reuse": 0.0}

    df = pd.DataFrame(trades)
    total_txns = len(df)

    # 1. Dust Ratio
    dust_count = len(df[df["usd_val"] < dust_threshold])
    dust_ratio = dust_count / total_txns

    # 2. Wallet Recycling Rate
    unique_wallets = df["trader"].nunique()
    wallet_reuse = 1.0 - (unique_wallets / total_txns)

    # 3. Tape Imbalance
    buys = len(df[df["type"] == "buy"])
    buy_ratio = buys / total_txns

    flags = []
    if dust_ratio > max_dust_ratio:
        flags.append(f"DUST_PADDING ({int(dust_ratio*100)}% trades < ${dust_threshold})")
    if wallet_reuse > max_wallet_reuse:
        flags.append(f"RECYCLED_WALLETS ({unique_wallets} unique in {total_txns} txns)")
    if total_txns >= 8 and (buy_ratio >= 0.90 or buy_ratio <= 0.10):
        flags.append(f"ONE_SIDED_TAPE ({buys} buys / {total_txns-buys} sells)")

    return {
        "is_organic": len(flags) == 0,
        "flags": flags,
        "dust_ratio": dust_ratio,
        "wallet_reuse": wallet_reuse,
        "buy_ratio": buy_ratio
    }

# ==========================================
# 4. MOCK DATA GENERATOR (Simulating Bitquery WS)
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
    
    # 30% chance to simulate a bot account reusing wallet addresses
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
# 5. STREAMLIT UI CONTROLS & DASHBOARD
# ==========================================
col1, col2 = st.columns([1, 2])

with col1:
    st.subheader("Stream Controls")
    run_stream = st.toggle("Start Live Stream", value=False)
    
    if st.button("Clear History"):
        st.session_state.trade_history = []
        st.session_state.monitored_tokens = {}
        st.rerun()

with col2:
    st.subheader("Live Buffer Metrics")
    m1, m2, m3 = st.columns(3)
    m1.metric("Total Streamed Trades", len(st.session_state.trade_history))
    m2.metric("Active Pairs Tracked", len(st.session_state.monitored_tokens))
    
    # Calculate overall flagged tokens
    flagged_count = sum(
        1 for t, buf in st.session_state.monitored_tokens.items()
        if not analyze_token_buffer(buf)["is_organic"]
    )
    m3.metric("Flagged Pairs", flagged_count, delta_color="inverse")

st.markdown("---")

# Pipeline Simulation Loop
if run_stream:
    trade = generate_mock_trade()
    if trade:
        # Save to raw history
        st.session_state.trade_history.insert(0, trade)
        if len(st.session_state.trade_history) > 100:
            st.session_state.trade_history.pop()

        # Update per-token rolling buffer (sliding window of 15)
        sym = trade["symbol"]
        if sym not in st.session_state.monitored_tokens:
            st.session_state.monitored_tokens[sym] = []
        
        st.session_state.monitored_tokens[sym].append(trade)
        if len(st.session_state.monitored_tokens[sym]) > 15:
            st.session_state.monitored_tokens[sym].pop(0)

    # Rerun UI loop rapidly to emulate WebSockets
    time.sleep(0.5)
    st.rerun()

# Display Token Security Matrix
st.subheader("📊 Token Analysis Feed")
if st.session_state.monitored_tokens:
    matrix_data = []
    for token, buf in st.session_state.monitored_tokens.items():
        res = analyze_token_buffer(buf)
        matrix_data.append({
            "Token": token,
            "Status": "✅ Clean" if res["is_organic"] else "🚨 MANIPULATED",
            "Dust Ratio": f"{int(res['dust_ratio']*100)}%",
            "Wallet Reuse": f"{int(res['wallet_reuse']*100)}%",
            "Recent Volume (Txns)": len(buf),
            "Flags": ", ".join(res["flags"]) if res["flags"] else "None"
        })
    
    st.dataframe(pd.DataFrame(matrix_data), use_container_width=True)

# Display Raw Live Tape
st.subheader("⚡ Live Transaction Tape")
if st.session_state.trade_history:
    st.dataframe(pd.DataFrame(st.session_state.trade_history), use_container_width=True)
else:
    st.info("Toggle 'Start Live Stream' above to launch real-time monitoring.")
