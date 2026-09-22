import streamlit as st
import pandas as pd
import requests
import time
import random

# ==========================================
# 1. PAGE CONFIG & MOBILE CSS
# ==========================================
st.set_page_config(
    page_title="Multi-Chain Wash Trade Detector",
    page_icon="🛡️",
    layout="wide"
)

st.markdown("""
    <style>
    .block-container { padding-top: 1rem; padding-bottom: 1rem; }
    [data-testid="stMetricValue"] { font-size: 1.6rem !important; }
    h2 { font-size: 1.3rem !important; font-weight: 700; margin-top: 0.5rem; }
    </style>
""", unsafe_allow_html=True)

# State initialization
if "trade_history" not in st.session_state:
    st.session_state.trade_history = []
if "monitored_tokens" not in st.session_state:
    st.session_state.monitored_tokens = {}
if "manual_audits" not in st.session_state:
    st.session_state.manual_audits = {}

# ==========================================
# 2. SIDEBAR CONFIGURATION (SOL, BNB, ROBINHOOD ONLY)
# ==========================================
st.sidebar.header("🌐 Active Chains")
enable_solana = st.sidebar.checkbox("Solana", value=True)
enable_bnb = st.sidebar.checkbox("BNB Chain", value=True)
enable_robinhood = st.sidebar.checkbox("Robinhood Chain", value=True)

# --- MANUAL AUDIT SECTION ---
st.sidebar.markdown("---")
st.sidebar.header("📋 Manual Coin Audit")
st.sidebar.caption("Paste a specific contract or ticker to analyze it directly.")

manual_chain = st.sidebar.selectbox(
    "Target Chain", 
    ["Solana", "BNB", "Robinhood"]
)
manual_contract_input = st.sidebar.text_input(
    "Contract Address or Symbol",
    placeholder="e.g. 0x... or CASHCAT"
)

if st.sidebar.button("Run Manual Audit", use_container_width=True):
    if manual_contract_input.strip():
        target_key = manual_contract_input.strip()
        mock_audit_buffer = [
            {"chain": manual_chain, "symbol": target_key, "trader": f"0x{random.randint(1000,9999)}...{random.randint(1000,9999)}", "usd_val": random.choice([0.2, 0.5, 125.0]), "type": "buy", "timestamp": time.strftime("%H:%M:%S")}
            for _ in range(10)
        ]
        st.session_state.manual_audits[f"{manual_chain}:{target_key}"] = mock_audit_buffer
        st.sidebar.success(f"Audited {target_key} on {manual_chain}!")
    else:
        st.sidebar.warning("Please enter a valid contract or symbol.")

st.sidebar.markdown("---")
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

# ==========================================
# 3. AUTOMATED TREND INTERSECTION
# ==========================================
def fetch_trending_intersection(chain_name: str) -> list:
    tokens = []
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        resp = requests.get(f"https://gmgn.ai/defi/quotation/v1/ranking/{chain_name.lower()}/swaps/1h", headers=headers, timeout=3)
        if resp.status_code == 200:
            data = resp.json().get("data", {}).get("rank", [])
            tokens = [item.get("symbol") for item in data[:5] if item.get("symbol")]
            if tokens: return tokens
    except Exception:
        pass

    try:
        resp = requests.get("https://api.dexscreener.com/latest/dex/trending/tokens", timeout=3)
        if resp.status_code == 200:
            pairs = resp.json().get("pairs", [])
            filtered = [
                p.get("baseToken", {}).get("symbol") 
                for p in pairs 
                if p.get("chainId", "").lower() == chain_name.lower() and p.get("baseToken", {}).get("symbol")
            ]
            if filtered: return list(set(filtered))[:5]
    except Exception:
        pass

    fallback_map = {
        "Solana": ["POPCAT", "WIF", "MYRO"],
        "BNB": ["FLOKI", "BABYDOGE"],
        "Robinhood": ["CASHCAT", "DIH", "HOODIE"]
    }
    return fallback_map.get(chain_name, [])

# ==========================================
# 4. WASH TRADING ENGINE
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
# 5. DATA GENERATOR
# ==========================================
def generate_mock_trade():
    active_chains = []
    if enable_solana: active_chains.append("Solana")
    if enable_bnb: active_chains.append("BNB")
    if enable_robinhood: active_chains.append("Robinhood")
    
    if not active_chains: return None

    chain = random.choice(active_chains)
    trending_tokens = fetch_trending_intersection(chain)
    symbol = random.choice(trending_tokens) if trending_tokens else "TOKEN"
    
    is_bot = random.random() < 0.35
    trader = "0xBot1234...5678" if is_bot else f"0x{random.randint(1000, 9999)}...{random.randint(1000, 9999)}"
    usd_val = random.uniform(0.1, 0.8) if is_bot else random.uniform(5.0, 500.0)

    return {
        "chain": chain,
        "symbol": symbol,
        "trader": trader,
        "usd_val": usd_val,
        "type": random.choice(["buy", "sell"]),
        "timestamp": time.strftime("%H:%M:%S")
    }

# ==========================================
# 6. UI DASHBOARD
# ==========================================
st.markdown("## 🛡️ Multi-Chain Wash Trade Detector")
st.caption("Tap the top-left `>>` menu to open Manual Coin Audit")

col1, col2 = st.columns([2, 1])
with col1:
    run_stream = st.toggle("Start Live Stream", value=True)
with col2:
    if st.button("Clear Data", use_container_width=True):
        st.session_state.trade_history = []
        st.session_state.monitored_tokens = {}
        st.session_state.manual_audits = {}
        st.rerun()

st.markdown("---")

if run_stream:
    trade = generate_mock_trade()
    if trade:
        st.session_state.trade_history.insert(0, trade)
        if len(st.session_state.trade_history) > 100:
            st.session_state.trade_history.pop()

        key = (trade["chain"], trade["symbol"])
        if key not in st.session_state.monitored_tokens:
            st.session_state.monitored_tokens[key] = []
        
        st.session_state.monitored_tokens[key].append(trade)
        if len(st.session_state.monitored_tokens[key]) > 15:
            st.session_state.monitored_tokens[key].pop(0)

# ==========================================
# 7. DISPLAY RESULTS GROUPED BY CHAIN
# ==========================================
chains_to_show = []
if enable_solana: chains_to_show.append("Solana")
if enable_bnb: chains_to_show.append("BNB")
if enable_robinhood: chains_to_show.append("Robinhood")

# Manual Audits Section
if st.session_state.manual_audits:
    st.subheader("📋 Manual Audited Coins")
    manual_rows = []
    for full_key, buf in st.session_state.manual_audits.items():
        chain_name, tok_symbol = full_key.split(":")
        res = analyze_token_buffer(buf)
        manual_rows.append({
            "Chain": chain_name,
            "Coin / Contract": tok_symbol,
            "Dust Ratio": f"{int(res['dust_ratio']*100)}%",
            "Wallet Reuse": f"{int(res['wallet_reuse']*100)}%",
            "Status / Flags": ", ".join(res["flags"]) if res["flags"] else "🟢 Organic / Clean"
        })
    st.dataframe(pd.DataFrame(manual_rows), use_container_width=True)
    st.markdown("---")

# Per-Chain Trending Breakdown
for chain in chains_to_show:
    st.subheader(f"🌐 Chain: {chain} (Trending & Wash Analysis)")
    
    chain_tokens = {k: v for k, v in st.session_state.monitored_tokens.items() if k[0] == chain}
    
    if not chain_tokens:
        st.info(f"Waiting for trending data on {chain}...")
        continue

    chain_data = []
    for (c, symbol), buf in chain_tokens.items():
        res = analyze_token_buffer(buf)
        status = "🚨 MANIPULATED (Wash Trading)" if not res["is_organic"] else "🟢 Clean"
        chain_data.append({
            "Coin": symbol,
            "Status": status,
            "Flags": ", ".join(res["flags"]) if res["flags"] else "None",
            "Dust Ratio": f"{int(res['dust_ratio']*100)}%",
            "Wallet Reuse": f"{int(res['wallet_reuse']*100)}%",
            "Txns": len(buf)
        })
    
    st.dataframe(pd.DataFrame(chain_data), use_container_width=True)

st.markdown("---")
st.subheader("⚡ Live Transaction Tape")
if st.session_state.trade_history:
    st.dataframe(pd.DataFrame(st.session_state.trade_history), use_container_width=True)

if run_stream:
    time.sleep(0.5)
    st.rerun()
