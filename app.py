import streamlit as st
import pandas as pd
import time
import random

# Page config optimized for mobile views
st.set_page_config(
    page_title="Wash-Trading Detector",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom CSS for compact mobile display
st.markdown("""
    <style>
    /* Reduce top padding on mobile */
    .block-container {
        padding-top: 1.5rem;
        padding-bottom: 1.5rem;
    }
    /* Compact metric card styling */
    [data-testid="stMetricValue"] {
        font-size: 1.8rem !important;
    }
    /* Adjust main header size */
    h2, h3 {
        margin-top: -0.5rem;
    }
    </style>
""", unsafe_allow_html=True)

# Title section
st.markdown("## 🛡️ Multi-Chain Wash-Trading Detector")
st.caption("Live streaming analytics for Solana, BNB Chain, and EVM/Robinhood Chain")

st.divider()

# Controls section
st.subheader("Stream Controls")
col_ctrl1, col_ctrl2 = st.columns([2, 1])

with col_ctrl1:
    is_live = st.toggle("Start Live Stream", value=True)

with col_ctrl2:
    if st.button("Clear History", use_container_width=True):
        st.session_state['trade_buffer'] = []
        st.experimental_rerun()

st.divider()

# Buffer Metrics Section
st.subheader("Live Buffer Metrics")

# Use st.columns with small gap to prevent awkward vertical stacking on mobile
m_col1, m_col2, m_col3 = st.columns(3, gap="small")

# Placeholder metric values (replace with your live buffer variables)
total_trades = st.session_state.get("total_trades", 100)
active_pairs = st.session_state.get("active_pairs", 7)
flagged_pairs = st.session_state.get("flagged_pairs", 5)

with m_col1:
    st.metric(label="Total Trades", value=total_trades)

with m_col2:
    st.metric(label="Active Pairs", value=active_pairs)

with m_col3:
    st.metric(label="Flagged Pairs", value=flagged_pairs)

st.divider()

# Main Stream Table / Alert Feeds
if is_live:
    st.info("⚡ Live stream active and monitoring sliding buffer...")
else:
    st.warning("⏸️ Stream paused.")
