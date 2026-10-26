"""
MediCare — Complete Medical Shop Bill Generator & Inventory App
Built with Python & Streamlit — Styled to match the Clean Card POS Preview UI.
"""

import os
import uuid
from datetime import datetime, date
import pandas as pd
import streamlit as st

# Optional barcode decoding libraries (graceful fallback if not installed)
try:
    from PIL import Image
except ImportError:
    Image = None

try:
    from pyzbar.pyzbar import decode as pyzbar_decode
except Exception:
    pyzbar_decode = None

try:
    import numpy as np
    import cv2
except Exception:
    np = None
    cv2 = None

# -----------------------------------------------------------------------------
# PAGE CONFIGURATION
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="MediCare — Pharmacy Billing & Inventory",
    page_icon="💊",
    layout="wide",
    initial_sidebar_state="collapsed",
)

PRODUCTS_FILE = "products.csv"
SALES_FILE = "sales.csv"
DEFAULT_MIN_STOCK = 10


# -----------------------------------------------------------------------------
# CUSTOM PREVIEW-MATCHING CSS THEME
# -----------------------------------------------------------------------------
def inject_preview_css():
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600;700&family=Plus+Jakarta+Sans:wght@400;500;600;700&display=swap');

        /* Hide default Streamlit chrome & sidebar so Top Bar leads cleanly */
        [data-testid="stSidebar"],
        [data-testid="collapsedControl"],
        header[data-testid="stHeader"],
        #MainMenu,
        footer {
            display: none !important;
            visibility: hidden !important;
        }

        .stApp {
            background-color: #FAFAFA !important;
            color: #111827 !important;
            font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif !important;
        }

        .block-container {
            max-width: 1240px !important;
            padding-top: 0.75rem !important;
            padding-bottom: 3.5rem !important;
            padding-left: 1.5rem !important;
            padding-right: 1.5rem !important;
        }

        /* White rounded-2xl cards matching preview */
        div[data-testid="stVerticalBlockBorderWrapper"] {
            background-color: #FFFFFF !important;
            border: 1px solid #E5E7EB !important;
            border-radius: 16px !important;
            padding: 20px 22px !important;
            box-shadow: 0 1px 2px rgba(0, 0, 0, 0.02) !important;
        }

        /* Clean inputs matching preview */
        div[data-baseweb="input"] > div,
        div[data-baseweb="select"] > div {
            background-color: #F9FAFB !important;
            border: 1px solid #E5E7EB !important;
            border-radius: 10px !important;
            font-size: 13px !important;
            color: #111827 !important;
        }

        div[data-baseweb="input"] input {
            font-family: 'Plus Jakarta Sans', sans-serif !important;
            font-size: 13px !important;
            color: #111827 !important;
        }

        .stTextInput label, .stNumberInput label, .stSelectbox label, .stDateInput label {
            font-size: 12px !important;
            font-weight: 500 !important;
            color: #374151 !important;
        }

        /* Primary Dark Charcoal Buttons (+ Add, New Bill, Generate Bill) */
        div.stButton > button[kind="primary"],
        div.stFormSubmitButton > button[kind="primary"] {
            background-color: #111827 !important;
            color: #FFFFFF !important;
            border: 1px solid #111827 !important;
            border-radius: 10px !important;
            font-family: 'Plus Jakarta Sans', sans-serif !important;
            font-weight: 600 !important;
            font-size: 12.5px !important;
            padding: 0.35rem 0.9rem !important;
            min-height: 36px !important;
            transition: background-color 0.15s ease !important;
        }

        div.stButton > button[kind="primary"]:hover,
        div.stFormSubmitButton > button[kind="primary"]:hover {
            background-color: #1F2937 !important;
            border-color: #1F2937 !important;
        }

        /* Disabled button state matching preview (#D1D5DB muted bar) */
        div.stButton > button:disabled {
            background-color: #D1D5DB !important;
            color: #FFFFFF !important;
            border: 1px solid #D1D5DB !important;
            opacity: 1 !important;
            cursor: not-allowed !important;
        }

        /* Secondary Light Pill Buttons (Category tabs, subtle actions) */
        div.stButton > button[kind="secondary"],
        div.stDownloadButton > button {
            background-color: #F3F4F6 !important;
            color: #374151 !important;
            border: 1px solid #E5E7EB !important;
            border-radius: 10px !important;
            font-family: 'Plus Jakarta Sans', sans-serif !important;
            font-weight: 500 !important;
            font-size: 12.5px !important;
            padding: 0.35rem 0.85rem !important;
            min-height: 36px !important;
        }

        div.stButton > button[kind="secondary"]:hover,
        div.stDownloadButton > button:hover {
            background-color: #E5E7EB !important;
            color: #111827 !important;
        }

        .mono {
            font-family: 'JetBrains Mono', monospace !important;
            font-variant-numeric: tabular-nums !important;
        }

        hr {
            margin: 0.85rem 0 !important;
            border-color: #E5E7EB !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


inject_preview_css()

# -----------------------------------------------------------------------------
# SEED MEDICAL SHOP DATA & CSV PERSISTENCE
# -----------------------------------------------------------------------------


def load_products() -> pd.DataFrame:
    if not os.path.exists(PRODUCTS_FILE):
        df = pd.DataFrame(DEFAULT_PRODUCTS)
        df.to_csv(PRODUCTS_FILE, index=False)
        return df
    try:
        df = pd.read_csv(PRODUCTS_FILE)
        df["price"] = pd.to_numeric(df["price"], errors="coerce").fillna(0.0)
        df["stock"] = pd.to_numeric(df["stock"], errors="coerce").fillna(0).astype(int)
        if "min_stock" not in df.columns:
            df["min_stock"] = DEFAULT_MIN_STOCK
        df["min_stock"] = pd.to_numeric(df["min_stock"], errors="coerce").fillna(DEFAULT_MIN_STOCK).astype(int)
        if "barcode" not in df.columns:
            df["barcode"] = [f"890{i:010d}" for i in range(len(df))]
        df["barcode"] = df["barcode"].astype(str)
        if "sku" not in df.columns:
            df["sku"] = [f"MED-{i+1:03d}" for i in range(len(df))]
        if "batch_number" not in df.columns:
            df["batch_number"] = "B-1001"
        df["expiry_date"] = df["expiry_date"].astype(str)
        return df
    except Exception:
        df = pd.DataFrame(DEFAULT_PRODUCTS)
        df.to_csv(PRODUCTS_FILE, index=False)
        return df


def save_products(df: pd.DataFrame) -> None:
    cols = [
        "id", "name", "sku", "barcode", "category", "batch_number",
        "manufacturer", "schedule", "dosage_form", "price", "stock",
        "min_stock", "expiry_date",
    ]
    existing_cols = [c for c in cols if c in df.columns]
    df[existing_cols].to_csv(PRODUCTS_FILE, index=False)


def load_sales() -> pd.DataFrame:
    if not os.path.exists(SALES_FILE):
        df = pd.DataFrame(DEFAULT_SALES)
        df.to_csv(SALES_FILE, index=False)
        return df
    try:
        df = pd.read_csv(SALES_FILE)
        df["total"] = pd.to_numeric(df["total"], errors="coerce").fillna(0.0)
        df["customer_age"] = pd.to_numeric(df["customer_age"], errors="coerce").fillna(30).astype(int)
        return df
    except Exception:
        df = pd.DataFrame(DEFAULT_SALES)
        df.to_csv(SALES_FILE, index=False)
        return df


def save_sales(df: pd.DataFrame) -> None:
    df.to_csv(SALES_FILE, index=False)


def is_expired_date(exp_str: str, ref_date: date) -> bool:
    try:
        return pd.to_datetime(exp_str).date() < ref_date
    except Exception:
        return False


def decode_camera_barcode(uploaded_file):
    """Attempts to decode 1D/2D barcodes from st.camera_input image frame."""
    if uploaded_file is None:
        return None
    try:
        uploaded_file.seek(0)
        if pyzbar_decode is not None and Image is not None:
            img = Image.open(uploaded_file)
            results = pyzbar_decode(img)
            if results:
                return results[0].data.decode("utf-8")
        if cv2 is not None and np is not None:
            uploaded_file.seek(0)
            file_bytes = np.asarray(bytearray(uploaded_file.read()), dtype=np.uint8)
            frame = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
            if frame is not None:
                if hasattr(cv2, "barcode"):
                    bd = cv2.barcode.BarcodeDetector()
                    retval, decoded_info, _ = bd.detectAndDecode(frame)
                    if retval and decoded_info:
                        for code in decoded_info:
                            if code:
                                return code
                qr = cv2.QRCodeDetector()
                val, _, _ = qr.detectAndDecode(frame)
                if val:
                    return val
    except Exception:
        return None
    return None


# -----------------------------------------------------------------------------
# SESSION STATE
# -----------------------------------------------------------------------------
if "active_tab" not in st.session_state:
    st.session_state.active_tab = "billing"
if "cart" not in st.session_state:
    st.session_state.cart = []
if "selected_category" not in st.session_state:
    st.session_state.selected_category = "All"
if "scanner_open" not in st.session_state:
    st.session_state.scanner_open = False
if "scan_feedback" not in st.session_state:
    st.session_state.scan_feedback = None
if "last_invoice" not in st.session_state:
    st.session_state.last_invoice = None
if "show_rx" not in st.session_state:
    st.session_state.show_rx = False
if "show_add_medicine" not in st.session_state:
    st.session_state.show_add_medicine = False
if "inv_filter" not in st.session_state:
    st.session_state.inv_filter = "all"

today = date.today()
products_df = load_products()
sales_df = load_sales()


def add_product_to_cart(prod_row) -> tuple[bool, str]:
    exp_flag = is_expired_date(str(prod_row["expiry_date"]), today)
    if exp_flag:
        return (
            False,
            f"Cannot dispense '{prod_row['name']}' (Batch {prod_row['batch_number']}): Expired on {prod_row['expiry_date']}.",
        )
    avail = int(prod_row["stock"])
    if avail <= 0:
        return False, f"'{prod_row['name']}' is out of stock."

    prod_id = str(prod_row["id"])
    for item in st.session_state.cart:
        if item["id"] == prod_id:
            if item["quantity"] >= avail:
                return False, f"Maximum available stock ({avail} units) reached for '{prod_row['name']}'."
            item["quantity"] += 1
            item["available_stock"] = avail
            return True, f"Added {prod_row['name']} (Qty: {item['quantity']})"

    st.session_state.cart.append(
        {
            "id": prod_id,
            "name": str(prod_row["name"]),
            "sku": str(prod_row["sku"]),
            "barcode": str(prod_row["barcode"]),
            "batch": str(prod_row["batch_number"]),
            "price": float(prod_row["price"]),
            "quantity": 1,
            "available_stock": avail,
        }
    )
    return True, f"Added {prod_row['name']} · ${float(prod_row['price']):.2f}"


alert_count = sum(
    1
    for _, r in products_df.iterrows()
    if is_expired_date(str(r["expiry_date"]), today) or int(r["stock"]) <= int(r["min_stock"])
)

# -----------------------------------------------------------------------------
# TOP HORIZONTAL NAVIGATION BAR
# -----------------------------------------------------------------------------
nav_cols = st.columns([1.8, 1.4, 1.85, 1.45, 1.25, 1.35], vertical_alignment="center")
with nav_cols[0]:
    st.markdown(
        "<div style='font-size:19px;font-weight:700;letter-spacing:-0.02em;color:#111827;padding:4px 0;'>MediCare</div>",
        unsafe_allow_html=True,
    )
with nav_cols[1]:
    if st.button(
        "🛒 Billing Screen",
        key="nav_billing",
        type="primary" if st.session_state.active_tab == "billing" else "secondary",
        use_container_width=True,
    ):
        st.session_state.active_tab = "billing"
        st.rerun()
with nav_cols[2]:
    inv_label = f"📦 Inventory ({alert_count})" if alert_count > 0 else "📦 Inventory"
    if st.button(
        inv_label,
        key="nav_inventory",
        type="primary" if st.session_state.active_tab == "inventory" else "secondary",
        use_container_width=True,
    ):
        st.session_state.active_tab = "inventory"
        st.rerun()
with nav_cols[3]:
    if st.button(
        "📊 Sales Dashboard",
        key="nav_sales",
        type="primary" if st.session_state.active_tab == "sales" else "secondary",
        use_container_width=True,
    ):
        st.session_state.active_tab = "sales"
        st.rerun()
with nav_cols[4]:
    if st.button(
        "📄 CSV Data",
        key="nav_csv",
        type="primary" if st.session_state.active_tab == "csv" else "secondary",
        use_container_width=True,
    ):
        st.session_state.active_tab = "csv"
        st.rerun()
with nav_cols[5]:
    if st.button("⊕ New Bill", key="nav_new_bill", type="primary", use_container_width=True):
        st.session_state.cart = []
        st.session_state.last_invoice = None
        st.session_state.scan_feedback = None
        st.session_state.active_tab = "billing"
        st.rerun()

st.markdown("<hr style='margin: 0.5rem 0 1.5rem 0; border-color:#E5E7EB;'/>", unsafe_allow_html=True)

# =============================================================================
# TAB 1: BILLING & CHECKOUT SCREEN
# =============================================================================
if st.session_state.active_tab == "billing":
    hdr_left, hdr_right = st.columns([3.2, 1.4], vertical_alignment="center")
    with hdr_left:
        st.markdown(
            """
            <div>
                <h1 style="font-size:26px;font-weight:700;margin:0;padding:0;letter-spacing:-0.02em;color:#111827;">Billing & Checkout</h1>
                <p style="font-size:12.5px;color:#6B7280;margin:4px 0 0 0;">
                    Select medicines or scan barcodes, record customer details, calculate total bill, and update stock automatically
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with hdr_right:
        r_c1, r_c2 = st.columns([1, 1.25], vertical_alignment="center")
        with r_c1:
            st.markdown(
                f"<div class='mono' style='font-size:12px;color:#6B7280;text-align:right;'>Catalog: {len(products_df)} items</div>",
                unsafe_allow_html=True,
            )
        with r_c2:
            scan_btn_label = "✕ Close Scanner" if st.session_state.scanner_open else "📷 Scan Barcode"
            if st.button(scan_btn_label, key="toggle_scanner_hdr", type="primary", use_container_width=True):
                st.session_state.scanner_open = not st.session_state.scanner_open
                st.rerun()

    st.markdown("<hr style='margin: 1rem 0 1.4rem 0; border-color:#E5E7EB;'/>", unsafe_allow_html=True)

    # Device Camera Barcode Scanner Card
    if st.session_state.scanner_open:
        with st.container(border=True):
            st.markdown(
                """
                <div style="margin-bottom:8px;">
                    <span style="font-size:14px;font-weight:700;color:#111827;">📷 Medical Barcode Camera Scanner</span>
                    <span style="font-size:12px;color:#6B7280;margin-left:8px;">· Point device camera at medicine blister/box or scan via EAN-13</span>
                </div>
                """,
                unsafe_allow_html=True,
            )
            cam_col, sim_col = st.columns([1.15, 1.0], gap="large")
            with cam_col:
                cam_img = st.camera_input("Capture Medicine Barcode Frame", key="pharmacy_cam")
                if cam_img is not None:
                    decoded = decode_camera_barcode(cam_img)
                    if decoded:
                        matched = products_df[
                            (products_df["barcode"].astype(str) == decoded.strip())
                            | (products_df["sku"].str.upper() == decoded.strip().upper())
                        ]
                        if not matched.empty:
                            ok, msg = add_product_to_cart(matched.iloc[0])
                            st.session_state.scan_feedback = ("success" if ok else "error", msg)
                        else:
                            st.session_state.scan_feedback = ("error", f"No medicine found for barcode '{decoded}'.")
                    else:
                        st.info("Frame captured. Install `pyzbar` or `opencv-python` for automatic frame decoding, or enter/click barcode on the right.")

            with sim_col:
                st.markdown("<div style='font-size:12.5px;font-weight:600;color:#111827;margin-bottom:6px;'>USB Barcode Gun / Manual EAN Lookup</div>", unsafe_allow_html=True)
                b_in_col, b_btn_col = st.columns([2.2, 1.0], vertical_alignment="bottom")
                with b_in_col:
                    manual_ean = st.text_input("Barcode / SKU", placeholder="e.g. 8901234567890 or PAR-500", label_visibility="collapsed")
                with b_btn_col:
                    if st.button("Lookup & Add", key="manual_ean_btn", type="primary", use_container_width=True):
                        q = manual_ean.strip()
                        if q:
                            matched = products_df[
                                (products_df["barcode"].astype(str) == q)
                                | (products_df["sku"].str.upper() == q.upper())
                            ]
                            if not matched.empty:
                                ok, msg = add_product_to_cart(matched.iloc[0])
                                st.session_state.scan_feedback = ("success" if ok else "error", msg)
                                st.rerun()
                            else:
                                st.session_state.scan_feedback = ("error", f"No medicine found for '{q}'.")
                                st.rerun()

                st.markdown("<div style='font-size:11.5px;font-weight:600;color:#6B7280;margin:12px 0 6px 0;'>Quick-Scan Sample Barcodes (Click to Simulate Scan):</div>", unsafe_allow_html=True)
                sample_rows = products_df.head(6)
                s_cols = st.columns(2)
                for idx, (_, s_row) in enumerate(sample_rows.iterrows()):
                    with s_cols[idx % 2]:
                        short_name = s_row["name"].split("(")[0].strip()[:18]
                        if st.button(f"{short_name} · {str(s_row['barcode'])[-4:]}", key=f"sim_{s_row['id']}", use_container_width=True):
                            ok, msg = add_product_to_cart(s_row)
                            st.session_state.scan_feedback = ("success" if ok else "error", msg)
                            st.rerun()

    if st.session_state.scan_feedback:
        kind, message = st.session_state.scan_feedback
        if kind == "error":
            st.error(message)
        else:
            st.success(message)

    col_left, col_right = st.columns([1.42, 1.0], gap="large")

    # LEFT COLUMN: Customer Details + Select Products
    with col_left:
        with st.container(border=True):
            cd_top1, cd_top2 = st.columns([3, 1.2], vertical_alignment="center")
            with cd_top1:
                st.markdown(
                    "<div style='font-size:14px;font-weight:600;color:#111827;'>👤 Customer Details <span style='font-weight:400;color:#6B7280;font-size:12px;'>· Name, Phone, Age</span></div>",
                    unsafe_allow_html=True,
                )
            with cd_top2:
                if st.button(
                    "Hide Doctor / Rx" if st.session_state.show_rx else "+ Doctor / Rx",
                    key="toggle_rx_btn",
                    use_container_width=True,
                ):
                    st.session_state.show_rx = not st.session_state.show_rx
                    st.rerun()

            c1, c2, c3 = st.columns(3)
            with c1:
                cust_name = st.text_input("Customer Name *", placeholder="e.g. Somesh", key="in_cust_name")
            with c2:
                cust_phone = st.text_input("Phone Number *", placeholder="e.g. 9999999999", key="in_cust_phone")
            with c3:
                cust_age_str = st.text_input("Customer Age *", placeholder="e.g. 20", key="in_cust_age")

            doc_name = ""
            rx_no = ""
            if st.session_state.show_rx:
                rx1, rx2 = st.columns(2)
                with rx1:
                    doc_name = st.text_input("Prescribing Doctor", placeholder="e.g. Dr. Keith Vance", key="in_doc_name")
                with rx2:
                    rx_no = st.text_input("Prescription Ref #", placeholder="e.g. RX-2026-904", key="in_rx_no")

        with st.container(border=True):
            sp_left, sp_right = st.columns([1.3, 1.7], vertical_alignment="center")
            with sp_left:
                st.markdown(
                    "<div style='font-size:14px;font-weight:600;color:#111827;'>🛍 Select Products</div>",
                    unsafe_allow_html=True,
                )
            with sp_right:
                search_query = st.text_input(
                    "Search Products",
                    placeholder="🔍 Search medicine, SKU, or barcode...",
                    label_visibility="collapsed",
                )

            categories = ["All"] + list(dict.fromkeys(products_df["category"].dropna().tolist()))
            cat_cols = st.columns(len(categories))
            for idx, cat in enumerate(categories):
                with cat_cols[idx]:
                    is_active = st.session_state.selected_category == cat
                    if st.button(
                        cat,
                        key=f"cat_pill_{cat}",
                        type="primary" if is_active else "secondary",
                        use_container_width=True,
                    ):
                        st.session_state.selected_category = cat
                        st.rerun()

            st.markdown("<div style='height:4px;'></div>", unsafe_allow_html=True)

            filtered_df = products_df.copy()
            if st.session_state.selected_category != "All":
                filtered_df = filtered_df[filtered_df["category"] == st.session_state.selected_category]
            if search_query.strip():
                q = search_query.strip().lower()
                filtered_df = filtered_df[
                    filtered_df["name"].str.lower().str.contains(q, na=False)
                    | filtered_df["sku"].str.lower().str.contains(q, na=False)
                    | filtered_df["barcode"].astype(str).str.contains(q, na=False)
                    | filtered_df["batch_number"].str.lower().str.contains(q, na=False)
                ]

            if filtered_df.empty:
                st.markdown(
                    "<div style='padding:28px 0;text-align:center;font-size:12.5px;color:#9CA3AF;'>No matching medicines found.</div>",
                    unsafe_allow_html=True,
                )
            else:
                for _, prod in filtered_df.iterrows():
                    expired = is_expired_date(str(prod["expiry_date"]), today)
                    stock_val = int(prod["stock"])
                    min_val = int(prod["min_stock"])
                    low_stock = stock_val <= min_val
                    out_of_stock = stock_val <= 0
                    in_cart_qty = next(
                        (i["quantity"] for i in st.session_state.cart if i["id"] == prod["id"]), 0
                    )

                    row_bg = "#FEF2F2" if expired else "transparent"
                    title_color = "#6B7280" if expired else "#111827"
                    price_color = "#9CA3AF" if expired else "#111827"

                    if out_of_stock:
                        stock_html = "<span style='color:#DC2626;font-weight:600;'>Out of stock</span>"
                    elif low_stock:
                        stock_html = f"<span style='color:#D97706;font-weight:600;'>Stock: {stock_val} units</span>"
                    else:
                        stock_html = f"<span>Stock: {stock_val} units</span>"

                    exp_html = (
                        f"<span style='color:#DC2626;font-weight:600;'>Expired: {prod['expiry_date']}</span>"
                        if expired
                        else f"<span>Exp: {prod['expiry_date']}</span>"
                    )

                    r_info, r_price, r_btn = st.columns([3.7, 0.95, 1.15], vertical_alignment="center")
                    with r_info:
                        st.markdown(
                            f"""
                            <div style="background:{row_bg};padding:8px 10px;border-radius:10px;">
                                <div style="display:flex;align-items:baseline;gap:8px;flex-wrap:wrap;">
                                    <span style="font-size:13px;font-weight:600;color:{title_color};">{prod['name']}</span>
                                    <span class="mono" style="font-size:11px;color:#9CA3AF;">{prod['sku']}</span>
                                </div>
                                <div style="font-size:11.5px;color:#6B7280;margin-top:3px;">
                                    {prod['category']} &nbsp;·&nbsp; Batch {prod['batch_number']} &nbsp;·&nbsp; {stock_html} &nbsp;·&nbsp; {exp_html}
                                </div>
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )
                    with r_price:
                        st.markdown(
                            f"<div class='mono' style='font-size:14px;font-weight:700;color:{price_color};text-align:right;'>${float(prod['price']):.2f}</div>",
                            unsafe_allow_html=True,
                        )
                    with r_btn:
                        btn_text = f"+ Added ({in_cart_qty})" if in_cart_qty > 0 else "+ Add"
                        if st.button(
                            btn_text,
                            key=f"add_btn_{prod['id']}",
                            type="primary",
                            disabled=(expired or out_of_stock),
                            use_container_width=True,
                        ):
                            ok, msg = add_product_to_cart(prod)
                            st.session_state.scan_feedback = ("success" if ok else "error", msg)
                            st.rerun()

                    st.markdown("<hr style='margin:4px 0;border-color:#F3F4F6;'/>", unsafe_allow_html=True)

   
# Current Bill: empty cart or products

if not st.session_state.cart:
    st.markdown(
        """
        <div style="padding:48px 12px;text-align:center;color:#9CA3AF;font-size:12.5px;">
            <div>No items added to the bill yet.</div>
            <div style="font-size:11.5px;">Select items from the catalog on the left.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    subtotal = 0.0
    tax_rate = 5.0
    discount_rate = 0.0
    payment_mode = "Card"

else:
    # Display cart items
    for idx, item in enumerate(list(st.session_state.cart)):
        ic1, ic2, ic3, ic4, ic5 = st.columns(
            [2.4, 0.55, 0.55, 1.0, 0.5],
            vertical_alignment="center",
        )

        with ic1:
            st.markdown(
                f"**{item['name']}**  \n"
                f"${item['price']:.2f} × {item['quantity']} · {item['batch']}"
            )

        with ic2:
            if st.button("-", key=f"dec_{item['id']}", use_container_width=True):
                if item["quantity"] > 1:
                    st.session_state.cart[idx]["quantity"] -= 1
                else:
                    st.session_state.cart.pop(idx)
                st.rerun()

        with ic3:
            if st.button(
                "+",
                key=f"inc_{item['id']}",
                disabled=item["quantity"] >= item["available_stock"],
                use_container_width=True,
            ):
                st.session_state.cart[idx]["quantity"] += 1
                st.rerun()

        with ic4:
            line_total = item["price"] * item["quantity"]
            st.markdown(f"**${line_total:.2f}**")

        with ic5:
            if st.button("✕", key=f"rem_{item['id']}", use_container_width=True):
                st.session_state.cart.pop(idx)
                st.rerun()

    st.markdown("---")

    t_c1, t_c2, t_c3 = st.columns(3)

    with t_c1:
        tax_rate = st.selectbox(
            "Tax (%)", [5.0, 0.0, 12.0, 18.0], index=0, key="sel_tax"
        )

    with t_c2:
        discount_rate = st.selectbox(
            "Discount (%)", [0.0, 5.0, 10.0, 15.0], index=0, key="sel_disc"
        )

    with t_c3:
        payment_mode = st.selectbox(
            "Payment", ["Card", "Cash", "UPI", "Digital"], key="sel_pay"
        )

    subtotal = round(
        sum(i["price"] * i["quantity"] for i in st.session_state.cart),
        2,
    )

# Calculate totals outside the if/else block
discount_amt = round(subtotal * discount_rate / 100, 2)
taxable = max(0.0, subtotal - discount_amt)
tax_amt = round(taxable * tax_rate / 100, 2)
grand_total = round(taxable + tax_amt, 2)

st.markdown(f"Subtotal: ${subtotal:.2f}")
if discount_amt > 0:
    st.markdown(f"Discount: -${discount_amt:.2f}")
st.markdown(f"Tax ({tax_rate:.0f}%): ${tax_amt:.2f}")
st.markdown(f"### Grand Total: ${grand_total:.2f}")


# =============================================================================
# TAB 2: INVENTORY MANAGEMENT SCREEN
# =============================================================================
elif st.session_state.active_tab == "inventory":
    ih1, ih2 = st.columns([3, 1.1], vertical_alignment="center")
    with ih1:
        st.markdown(
            """
            <div>
                <h1 style="font-size:26px;font-weight:700;margin:0;color:#111827;">Inventory Management</h1>
                <p style="font-size:12.5px;color:#6B7280;margin:4px 0 0 0;">
                    Add medicines with prices, stock quantities, barcodes, and expiry dates. Low-stock and expired items are highlighted.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with ih2:
        if st.button(
            "Close Form" if st.session_state.show_add_medicine else "+ Add New Medicine",
            type="primary",
            use_container_width=True,
        ):
            st.session_state.show_add_medicine = not st.session_state.show_add_medicine
            st.rerun()

    st.markdown("<hr style='margin:1rem 0 1.4rem 0;border-color:#E5E7EB;'/>", unsafe_allow_html=True)

    expired_mask = products_df["expiry_date"].apply(lambda d: is_expired_date(str(d), today))
    low_mask = (~expired_mask) & (products_df["stock"] <= products_df["min_stock"])

    k1, k2, k3, k4 = st.columns(4)
    kpis = [
        ("Catalog Medicines", str(len(products_df)), "Total registered drugs", "#FFFFFF", "#E5E7EB", "#111827"),
        ("Total Stock Units", str(int(products_df["stock"].sum())), "Physical strips / units", "#FFFFFF", "#E5E7EB", "#111827"),
        ("Low Stock Alerts", str(int(low_mask.sum())), "Below reorder threshold", "#FFFBEB", "#FDE68A", "#92400E"),
        ("Expired Drugs", str(int(expired_mask.sum())), "Quarantine & do not sell", "#FEF2F2", "#FECACA", "#991B1B"),
    ]
    for col, (title, val, sub, bg, bdr, txt) in zip([k1, k2, k3, k4], kpis):
        with col:
            st.markdown(
                f"""
                <div style="background:{bg};border:1px solid {bdr};border-radius:16px;padding:18px 20px;">
                    <div style="font-size:12px;font-weight:500;color:{txt};">{title}</div>
                    <div class="mono" style="font-size:24px;font-weight:700;color:{txt};margin:4px 0;">{val}</div>
                    <div style="font-size:11px;color:#6B7280;">{sub}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    st.markdown("<div style='height:18px;'></div>", unsafe_allow_html=True)

    if st.session_state.show_add_medicine:
        with st.container(border=True):
            st.markdown("<div style='font-size:14px;font-weight:600;margin-bottom:10px;'>Register New Medicine in Formulary</div>", unsafe_allow_html=True)
            with st.form("new_med_form", clear_on_submit=True):
                fc1, fc2, fc3, fc4 = st.columns(4)
                with fc1:
                    f_name = st.text_input("Medicine Name *", placeholder="e.g. Ibuprofen 400mg")
                    f_price = st.number_input("Unit Price ($) *", min_value=0.10, value=6.50, step=0.50)
                with fc2:
                    f_sku = st.text_input("SKU Code", placeholder="e.g. IBU-400")
                    f_stock = st.number_input("Initial Stock *", min_value=0, value=40, step=1)
                with fc3:
                    f_barcode = st.text_input("Barcode (EAN-13)", value=f"890{uuid.uuid4().int % 10000000000:010d}")
                    f_min = st.number_input("Low Stock Alert ≤", min_value=1, value=10, step=1)
                with fc4:
                    f_cat = st.selectbox("Category", ["Pain Relief", "Antibiotics", "Allergy", "Gastric", "Supplements", "First Aid"])
                    f_exp = st.date_input("Expiry Date *", value=date(today.year + 1, today.month, today.day))

                if st.form_submit_button("Save Medicine to CSV", type="primary"):
                    if not f_name.strip():
                        st.error("Please enter a medicine name.")
                    else:
                        new_row = {
                            "id": f"MED-{uuid.uuid4().hex[:4].upper()}",
                            "name": f_name.strip(),
                            "sku": f_sku.strip() or f"MED-{len(products_df)+1:03d}",
                            "barcode": f_barcode.strip(),
                            "category": f_cat,
                            "batch_number": f"B-{uuid.uuid4().hex[:4].upper()}",
                            "manufacturer": "Cipla Ltd",
                            "schedule": "OTC",
                            "dosage_form": "Strip of 10",
                            "price": float(f_price),
                            "stock": int(f_stock),
                            "min_stock": int(f_min),
                            "expiry_date": str(f_exp),
                        }
                        updated_df = pd.concat([products_df, pd.DataFrame([new_row])], ignore_index=True)
                        save_products(updated_df)
                        st.session_state.show_add_medicine = False
                        st.rerun()

    with st.container(border=True):
        flt1, flt2, flt3, flt_s = st.columns([1, 1, 1, 2.2], vertical_alignment="center")
        with flt1:
            if st.button(f"All ({len(products_df)})", type="primary" if st.session_state.inv_filter == "all" else "secondary", use_container_width=True):
                st.session_state.inv_filter = "all"
                st.rerun()
        with flt2:
            if st.button(f"Low Stock ({int((products_df['stock'] <= products_df['min_stock']).sum())})", type="primary" if st.session_state.inv_filter == "low" else "secondary", use_container_width=True):
                st.session_state.inv_filter = "low"
                st.rerun()
        with flt3:
            if st.button(f"Expired ({int(expired_mask.sum())})", type="primary" if st.session_state.inv_filter == "expired" else "secondary", use_container_width=True):
                st.session_state.inv_filter = "expired"
                st.rerun()
        with flt_s:
            inv_q = st.text_input("Search Inventory", placeholder="🔍 Filter by medicine, barcode, batch...", label_visibility="collapsed")

        st.markdown("<hr style='margin:10px 0;'/>", unsafe_allow_html=True)

        view_df = products_df.copy()
        if st.session_state.inv_filter == "low":
            view_df = view_df[view_df["stock"] <= view_df["min_stock"]]
        elif st.session_state.inv_filter == "expired":
            view_df = view_df[view_df["expiry_date"].apply(lambda d: is_expired_date(str(d), today))]
        if inv_q.strip():
            q = inv_q.strip().lower()
            view_df = view_df[
                view_df["name"].str.lower().str.contains(q, na=False)
                | view_df["barcode"].astype(str).str.contains(q, na=False)
                | view_df["sku"].str.lower().str.contains(q, na=False)
            ]

        for _, row in view_df.iterrows():
            exp = is_expired_date(str(row["expiry_date"]), today)
            low = int(row["stock"]) <= int(row["min_stock"])
            bg = "#FEF2F2" if exp else ("#FFFBEB" if low else "#FFFFFF")
            status_txt = (
                "<span style='color:#DC2626;font-weight:600;'>Expired (Do Not Sell)</span>"
                if exp
                else (
                    f"<span style='color:#D97706;font-weight:600;'>Low Stock (≤ {row['min_stock']})</span>"
                    if low
                    else "<span style='color:#059669;font-weight:500;'>Healthy</span>"
                )
            )

            ic1, ic2, ic3, ic4 = st.columns([3.4, 1.1, 1.3, 1.0], vertical_alignment="center")
            with ic1:
                st.markdown(
                    f"""
                    <div style="background:{bg};padding:8px 12px;border-radius:10px;">
                        <div style="font-size:13px;font-weight:600;color:#111827;">{row['name']} <span class="mono" style="font-size:11px;color:#9CA3AF;">{row['sku']}</span></div>
                        <div class="mono" style="font-size:11px;color:#6B7280;">Barcode: {row['barcode']} · Batch: {row['batch_number']} · Exp: {row['expiry_date']}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            with ic2:
                st.markdown(f"<div style='font-size:12px;'>{status_txt}</div>", unsafe_allow_html=True)
            with ic3:
                st.markdown(
                    f"<div class='mono' style='font-size:13px;font-weight:700;'>${float(row['price']):.2f} &nbsp;·&nbsp; {int(row['stock'])} u</div>",
                    unsafe_allow_html=True,
                )
            with ic4:
                b_minus, b_plus = st.columns(2)
                with b_minus:
                    if st.button("−", key=f"inv_m_{row['id']}", use_container_width=True):
                        idx = products_df[products_df["id"] == row["id"]].index[0]
                        products_df.at[idx, "stock"] = max(0, int(products_df.at[idx, "stock"]) - 1)
                        save_products(products_df)
                        st.rerun()
                with b_plus:
                    if st.button("+", key=f"inv_p_{row['id']}", use_container_width=True):
                        idx = products_df[products_df["id"] == row["id"]].index[0]
                        products_df.at[idx, "stock"] = int(products_df.at[idx, "stock"]) + 1
                        save_products(products_df)
                        st.rerun()
            st.markdown("<hr style='margin:4px 0;border-color:#F3F4F6;'/>", unsafe_allow_html=True)

# =============================================================================
# TAB 3: SALES DASHBOARD SCREEN
# =============================================================================
elif st.session_state.active_tab == "sales":
    st.markdown(
        """
        <div>
            <h1 style="font-size:26px;font-weight:700;margin:0;color:#111827;">Sales Dashboard</h1>
            <p style="font-size:12.5px;color:#6B7280;margin:4px 0 0 0;">
                Total pharmacy revenue, most-dispensed medicine leaderboard, and customer transaction logs
            </p>
        </div>
        <hr style="margin:1rem 0 1.4rem 0;border-color:#E5E7EB;"/>
        """,
        unsafe_allow_html=True,
    )

    total_rev = float(sales_df["total"].sum()) if not sales_df.empty else 0.0
    total_bills = len(sales_df)
    total_units = int(pd.to_numeric(sales_df.get("items_count", 0), errors="coerce").fillna(0).sum()) if not sales_df.empty else 0
    avg_bill = total_rev / total_bills if total_bills > 0 else 0.0

    sk1, sk2, sk3, sk4 = st.columns(4)
    for col, (lbl, val, sub) in zip(
        [sk1, sk2, sk3, sk4],
        [
            ("Total Revenue", f"${total_rev:.2f}", "Cumulative CSV billings"),
            ("Total Bills", str(total_bills), "Completed prescriptions"),
            ("Total Units Sold", str(total_units), "Dispensed strips & bottles"),
            ("Average Bill Value", f"${avg_bill:.2f}", "Mean spend per patient"),
        ],
    ):
        with col:
            st.markdown(
                f"""
                <div style="background:#FFFFFF;border:1px solid #E5E7EB;border-radius:16px;padding:18px 20px;">
                    <div style="font-size:12px;font-weight:500;color:#6B7280;">{lbl}</div>
                    <div class="mono" style="font-size:24px;font-weight:700;color:#111827;margin:4px 0;">{val}</div>
                    <div style="font-size:11px;color:#9CA3AF;">{sub}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    st.markdown("<div style='height:18px;'></div>", unsafe_allow_html=True)

    prod_counts = {}
    for summary in sales_df.get("items_summary", []).dropna():
        for part in str(summary).split(";"):
            part = part.strip()
            if " x" in part:
                name_part, rest = part.rsplit(" x", 1)
                qty_str = rest.split(" ")[0]
                if qty_str.isdigit():
                    prod_counts[name_part.strip()] = prod_counts.get(name_part.strip(), 0) + int(qty_str)

    ranked_products = sorted(prod_counts.items(), key=lambda x: x[1], reverse=True)[:5]

    d_left, d_right = st.columns([1.4, 1.0], gap="large")
    with d_left:
        with st.container(border=True):
            st.markdown("<div style='font-size:14px;font-weight:600;color:#111827;margin-bottom:14px;'>🏆 Most Sold Medicines (Top Dispensed)</div>", unsafe_allow_html=True)
            if not ranked_products:
                st.caption("No medicine sales recorded yet.")
            else:
                max_q = ranked_products[0][1] or 1
                for idx, (m_name, m_qty) in enumerate(ranked_products):
                    pct = int((m_qty / max_q) * 100)
                    bar_color = "#F59E0B" if idx == 0 else "#111827"
                    st.markdown(
                        f"""
                        <div style="margin-bottom:14px;">
                            <div style="display:flex;justify-content:space-between;font-size:12.5px;margin-bottom:5px;">
                                <span style="font-weight:600;color:#111827;">{idx + 1}. {m_name}</span>
                                <span class="mono" style="font-weight:700;color:#111827;">{m_qty} sold</span>
                            </div>
                            <div style="width:100%;height:8px;background:#F3F4F6;border-radius:99px;overflow:hidden;">
                                <div style="width:{pct}%;height:100%;background:{bar_color};border-radius:99px;"></div>
                            </div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

    with d_right:
        with st.container(border=True):
            st.markdown("<div style='font-size:14px;font-weight:600;color:#111827;margin-bottom:14px;'>👥 Customer Age Demographics</div>", unsafe_allow_html=True)
            ages = sales_df["customer_age"] if not sales_df.empty else pd.Series(dtype=int)
            buckets = [
                ("18 – 25 yrs", int((ages <= 25).sum())),
                ("26 – 40 yrs", int(((ages > 25) & (ages <= 40)).sum())),
                ("41 – 60 yrs", int(((ages > 40) & (ages <= 60)).sum())),
                ("60+ yrs", int((ages > 60).sum())),
            ]
            denom = max(1, len(sales_df))
            for b_label, b_cnt in buckets:
                pct = int((b_cnt / denom) * 100)
                st.markdown(
                    f"""
                    <div style="margin-bottom:12px;">
                        <div style="display:flex;justify-content:space-between;font-size:12px;color:#4B5563;margin-bottom:4px;">
                            <span>{b_label}</span>
                            <span class="mono" style="font-weight:600;color:#111827;">{b_cnt} ({pct}%)</span>
                        </div>
                        <div style="width:100%;height:6px;background:#F3F4F6;border-radius:99px;overflow:hidden;">
                            <div style="width:{pct}%;height:100%;background:#374151;border-radius:99px;"></div>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

    with st.container(border=True):
        st.markdown("<div style='font-size:14px;font-weight:600;color:#111827;margin-bottom:10px;'>Recent Sales Transactions (Saved in sales.csv)</div>", unsafe_allow_html=True)
        st.dataframe(sales_df, use_container_width=True, hide_index=True)

# =============================================================================
# TAB 4: LOCAL CSV PERSISTENCE VIEWER & DOWNLOAD
# =============================================================================
elif st.session_state.active_tab == "csv":
    st.markdown(
        """
        <div>
            <h1 style="font-size:26px;font-weight:700;margin:0;color:#111827;">Local CSV Data Storage</h1>
            <p style="font-size:12.5px;color:#6B7280;margin:4px 0 0 0;">
                Every product, stock update, expiry date, and customer bill is saved directly to local CSV files
            </p>
        </div>
        <hr style="margin:1rem 0 1.4rem 0;border-color:#E5E7EB;"/>
        """,
        unsafe_allow_html=True,
    )

    c_prod, c_sales = st.columns(2, gap="large")
    with c_prod:
        with st.container(border=True):
            st.markdown("<div style='font-size:14px;font-weight:600;margin-bottom:8px;'>products.csv</div>", unsafe_allow_html=True)
            st.dataframe(products_df, use_container_width=True, hide_index=True)
            st.download_button(
                "Download products.csv",
                products_df.to_csv(index=False).encode("utf-8"),
                "products.csv",
                "text/csv",
                use_container_width=True,
            )
    with c_sales:
        with st.container(border=True):
            st.markdown("<div style='font-size:14px;font-weight:600;margin-bottom:8px;'>sales.csv</div>", unsafe_allow_html=True)
            st.dataframe(sales_df, use_container_width=True, hide_index=True)
            st.download_button(
                "Download sales.csv",
                sales_df.to_csv(index=False).encode("utf-8"),
                "sales.csv",
                "text/csv",
                use_container_width=True,
            )
