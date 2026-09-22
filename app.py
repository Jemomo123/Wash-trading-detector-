import streamlit as st
import pandas as pd
import io

# ==========================================
# 1. PAGE CONFIG & MOBILE CSS
# ==========================================
st.set_page_config(
    page_title="Wash Trade Detector - Manual & Image Audit",
    page_icon="🛡️",
    layout="wide"
)

st.markdown("""
    <style>
    .block-container { padding-top: 1rem; padding-bottom: 1rem; }
    [data-testid="stMetricValue"] { font-size: 1.5rem !important; }
    h2 { font-size: 1.3rem !important; font-weight: 700; margin-top: 0.5rem; }
    </style>
""", unsafe_allow_html=True)

# State initialization
if "audited_data" not in st.session_state:
    st.session_state.audited_data = {}

if "uploaded_screenshots" not in st.session_state:
    st.session_state.uploaded_screenshots = []

# ==========================================
# 2. SIDEBAR CONFIGURATION & INPUTS
# ==========================================
st.sidebar.header("🌐 Select Network")
input_chain = st.sidebar.selectbox(
    "Network", 
    ["Robinhood Chain", "Solana", "BNB Chain"]
)

st.sidebar.markdown("---")
st.sidebar.header("📥 Transaction Data Input")

input_method = st.sidebar.radio(
    "Input Mode",
    ["Text / CSV Paste", "DexScreener Screenshot"]
)

token_label = st.sidebar.text_input("Token Name / Symbol", value="TEST_TOKEN")

if input_method == "Text / CSV Paste":
    st.sidebar.caption("Paste raw transaction rows or CSV exports from block explorers.")
    uploaded_file = st.sidebar.file_uploader("Upload CSV File", type=["csv"])
    pasted_data = st.sidebar.text_area(
        "Or Paste Table Rows",
        placeholder="trader,usd_val,type\n0xWallet1...,12.50,buy\n0xWallet2...,0.25,sell",
        height=130
    )
    
    if st.sidebar.button("Run Audit on Data", use_container_width=True):
        df_input = None
        try:
            if uploaded_file is not None:
                df_input = pd.read_csv(uploaded_file)
            elif pasted_data.strip():
                df_input = pd.read_csv(io.StringIO(pasted_data.strip()))
            
            if df_input is not None and not df_input.empty:
                df_input.columns = [c.strip().lower() for c in df_input.columns]
                col_map = {}
                for col in df_input.columns:
                    if any(k in col for k in ['trader', 'wallet', 'from', 'account', 'address']):
                        col_map[col] = 'trader'
                    elif any(k in col for k in ['usd', 'value', 'amount', 'price', 'worth']):
                        col_map[col] = 'usd_val'
                    elif any(k in col for k in ['type', 'side', 'action', 'dir']):
                        col_map[col] = 'type'
                
                df_input = df_input.rename(columns=col_map)
                
                if 'trader' not in df_input.columns or 'usd_val' not in df_input.columns:
                    st.sidebar.error("Error: Data must contain columns for trader address and trade USD value.")
                else:
                    if 'type' not in df_input.columns:
                        df_input['type'] = 'unknown'
                    df_input['usd_val'] = pd.to_numeric(df_input['usd_val'].astype(str).str.replace(r'[^0-9.]', '', regex=True), errors='coerce').fillna(0.0)
                    st.session_state.audited_data[f"{input_chain}:{token_label}"] = df_input.to_dict(orient="records")
                    st.sidebar.success(f"Successfully loaded {len(df_input)} transactions!")
            else:
                st.sidebar.warning("Please upload a CSV file or paste transaction rows first.")
        except Exception as e:
            st.sidebar.error(f"Parsing error: {e}")

else:
    st.sidebar.caption("Upload screenshots of the DexScreener live transaction feed for visual inspection and logging.")
    screenshot_file = st.sidebar.file_uploader("Upload DexScreener Screenshot", type=["png", "jpg", "jpeg"])
    
    if screenshot_file is not None:
        st.sidebar.image(screenshot_file, caption="Uploaded DexScreener Feed", use_container_width=True)
        if st.sidebar.button("Save Screenshot to Inspection Log", use_container_width=True):
            st.session_state.uploaded_screenshots.append({
                "chain": input_chain,
                "token": token_label,
                "image": screenshot_file
            })
            st.sidebar.success("Screenshot saved for visual verification audit!")

st.sidebar.markdown("---")
st.sidebar.header("⚙️ Detection Thresholds")

dust_threshold = st.sidebar.number_input(
    "Dust Trade Cutoff ($ USD)", min_value=0.01, max_value=50.0, value=1.0, step=0.25
)
max_dust_ratio = st.sidebar.slider(
    "Max Allowed Dust Ratio (%)", min_value=5, max_value=90, value=25
) / 100.0

max_wallet_reuse = st.sidebar.slider(
    "Max Allowed Wallet Reuse (%)", min_value=5, max_value=90, value=35
) / 100.0

if st.sidebar.button("Clear Audit Data", use_container_width=True):
    st.session_state.audited_data = {}
    st.session_state.uploaded_screenshots = []
    st.rerun()

# ==========================================
# 3. WASH TRADING ENGINE
# ==========================================
def run_wash_audit(trades: list[dict]) -> dict:
    if not trades:
        return {"is_organic": True, "flags": [], "dust_ratio": 0.0, "wallet_reuse": 0.0}

    df = pd.DataFrame(trades)
    total_txns = len(df)
    if total_txns == 0:
        return {"is_organic": True, "flags": [], "dust_ratio": 0.0, "wallet_reuse": 0.0}

    dust_count = len(df[df["usd_val"] < dust_threshold])
    dust_ratio = dust_count / total_txns

    unique_wallets = df["trader"].nunique()
    wallet_reuse = 1.0 - (unique_wallets / total_txns)

    flags = []
    if dust_ratio > max_dust_ratio:
        flags.append(f"DUST_PADDING ({int(dust_ratio*100)}%)")
    if wallet_reuse > max_wallet_reuse:
        flags.append(f"RECYCLED_WALLETS ({unique_wallets} unique / {total_txns} txns)")

    return {
        "is_organic": len(flags) == 0,
        "flags": flags,
        "dust_ratio": dust_ratio,
        "wallet_reuse": wallet_reuse,
        "unique_wallets": unique_wallets,
        "total_txns": total_txns
    }

# ==========================================
# 4. DASHBOARD UI
# ==========================================
st.markdown("## 🛡️ Clean Manual & Visual Wash Trade Auditor")
st.caption("Zero Mock Data • Direct CSV/Text Paste & DexScreener Screenshot Inspection")
st.markdown("---")

if not st.session_state.audited_data and not st.session_state.uploaded_screenshots:
    st.info("👈 **How to begin:** Choose your input mode in the sidebar (Text/CSV or DexScreener Screenshot), upload your records or capture, and run your evaluation.")
else:
    if st.session_state.audited_data:
        st.subheader("📊 Audit Results Summary")
        summary_rows = []
        for key, trades in st.session_state.audited_data.items():
            chain, token = key.split(":", 1)
            analysis = run_wash_audit(trades)
            
            status = "🚨 MANIPULATED" if not analysis["is_organic"] else "🟢 CLEAN / ORGANIC"
            
            summary_rows.append({
                "Chain": chain,
                "Token": token,
                "Audit Status": status,
                "Triggered Flags": ", ".join(analysis["flags"]) if analysis["flags"] else "None",
                "Dust Ratio": f"{int(analysis['dust_ratio']*100)}%",
                "Wallet Reuse": f"{int(analysis['wallet_reuse']*100)}%",
                "Total Txns": analysis["total_txns"]
            })
        
        st.dataframe(pd.DataFrame(summary_rows), use_container_width=True)
        
        st.markdown("---")
        st.subheader("🔍 Transaction Inspection View")
        active_key = st.selectbox("Select dataset to inspect:", list(st.session_state.audited_data.keys()))
        if active_key:
            st.dataframe(pd.DataFrame(st.session_state.audited_data[active_key]), use_container_width=True)

    if st.session_state.uploaded_screenshots:
        st.markdown("---")
        st.subheader("📸 DexScreener Feed Screenshots (Visual Verification)")
        for idx, item in enumerate(st.session_state.uploaded_screenshots):
            st.markdown(f"**Item {idx+1} | Chain:** {item['chain']} | **Token:** {item['token']}")
            st.image(item['image'], use_container_width=True)
