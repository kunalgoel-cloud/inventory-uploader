import streamlit as st
import pandas as pd
import io
from datetime import date

# ── Page config ──────────────────────────────────────────────
st.set_page_config(
    page_title="Inventory Uploader — MamaNourish",
    page_icon="📦",
    layout="wide"
)

# ── Column mapping (WMS CSV → Zoho Analytics table) ──────────
COLUMN_MAP = {
    "Warehouse"              : "Warehouse",
    "Barcode"                : "Barcode",
    "SKU"                    : "SKU",
    "Title"                  : "Title",
    "Brand"                  : "Brand",
    "MRP"                    : "MRP",
    "Total Stock"            : "Total_Stock",
    "Mfg Date"               : "Mfg_Date",
    "Exp Date"               : "Exp_Date",
    "Batch No"               : "Batch_No",
    "Left Days"              : "Left_Days",
    "Shelf Life"             : "Shelf_Life_Raw",
    "Stock Last Updated Date": "Stock_Last_Updated",
    "Bin"                    : "Bin",
}

# ── CSS ───────────────────────────────────────────────────────
st.markdown("""
<style>
    .block-container { padding-top: 2rem; }
    .stTabs [data-baseweb="tab-list"] { gap: 16px; }
    .stTabs [data-baseweb="tab"] {
        font-size: 16px;
        font-weight: 600;
        padding: 8px 24px;
        border-radius: 8px 8px 0 0;
    }
    div[data-testid="stDownloadButton"] button {
        width: 100%;
        padding: 12px;
        font-size: 15px;
        font-weight: 700;
    }
</style>
""", unsafe_allow_html=True)

# ── Header ────────────────────────────────────────────────────
st.title("📦 Inventory Uploader")
st.caption("MamaNourish — Process WMS snapshots for Zoho Analytics import")
st.divider()


# ── Core processing function ──────────────────────────────────
def process_csv(uploaded_file, channel, snapshot_date):
    df = pd.read_csv(uploaded_file, thousands=",", dtype=str)

    # Keep only mapped columns that exist
    present = {k: v for k, v in COLUMN_MAP.items() if k in df.columns}
    missing = [k for k in COLUMN_MAP if k not in df.columns]

    df = df[list(present.keys())].rename(columns=present)

    # Clean MRP — remove commas
    if "MRP" in df.columns:
        df["MRP"] = df["MRP"].str.replace(",", "", regex=False)

    # Parse Shelf_Life_Raw → clean numeric Shelf_Life_Pct
    # Handles bad values like "MfgDate is greater Than ExpDate"
    def parse_shelf_life(val):
        try:
            return float(str(val).replace("%", "").strip())
        except:
            return 0.0

    if "Shelf_Life_Raw" in df.columns:
        df["Shelf_Life_Pct"] = df["Shelf_Life_Raw"].apply(parse_shelf_life)

    # Add metadata columns
    df["Snapshot_Date"] = snapshot_date.strftime("%Y-%m-%d")
    df["Channel"]       = channel

    return df, missing


def render_uploader(channel, accent_color):
    col1, col2 = st.columns([1, 1])

    with col1:
        snapshot_date = st.date_input(
            "📅 Snapshot Date",
            value=date.today(),
            key=f"date_{channel}"
        )

    with col2:
        uploaded_file = st.file_uploader(
            "📂 WMS CSV File",
            type=["csv"],
            key=f"file_{channel}"
        )

    if uploaded_file:
        try:
            df, missing = process_csv(uploaded_file, channel, snapshot_date)

            st.success(f"✅ {len(df):,} rows processed · {len(df.columns)} columns · Channel = {channel} · Date = {snapshot_date}")

            if missing:
                st.warning(f"⚠️ Columns not found in CSV (skipped): {', '.join(missing)}")

            with st.expander("Preview first 10 rows"):
                st.dataframe(df.head(10), use_container_width=True)

            # Download button
            csv_bytes = df.to_csv(index=False).encode("utf-8")
            filename  = f"inventory_{channel.lower()}_{snapshot_date}.csv"

            st.download_button(
                label=f"⬇️ Download Processed CSV ({channel})",
                data=csv_bytes,
                file_name=filename,
                mime="text/csv",
                key=f"dl_{channel}"
            )

            st.info(
                "**Next step:** Go to Zoho Analytics → Inventory_Snapshots table → "
                "**Import Data** → upload this file → columns will auto-map → Import ✓"
            )

        except Exception as e:
            st.error(f"❌ Error processing file: {e}")
    else:
        st.markdown(
            f"""
            <div style='border: 2px dashed {accent_color}; border-radius: 12px;
                        padding: 32px; text-align: center; color: #888; margin-top: 8px;'>
                Upload a CSV file above to get started
            </div>
            """,
            unsafe_allow_html=True
        )


# ── Two tabs: B2B and B2C ────────────────────────────────────
tab_b2b, tab_b2c = st.tabs(["🔵  B2B Upload", "🟠  B2C Upload"])

with tab_b2b:
    st.subheader("B2B Warehouse Export")
    render_uploader("B2B", "#3498db")

with tab_b2c:
    st.subheader("B2C Warehouse Export")
    render_uploader("B2C", "#e67e22")

# ── Footer ───────────────────────────────────────────────────
st.divider()
st.caption("Data is processed locally in your browser session — nothing is stored or transmitted.")
