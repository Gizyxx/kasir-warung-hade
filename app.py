import streamlit as st
import pandas as pd
import sqlite3
import base64
import io
from datetime import datetime

# =====================================================
# KONFIGURASI
# =====================================================
st.set_page_config(page_title="Warung HADE POS", page_icon="🏪", layout="centered")

# =====================================================
# DATABASE
# =====================================================
@st.cache_resource
def init_db():
    conn = sqlite3.connect("warung_hade_navy.db", check_same_thread=False)
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS transaksi (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            waktu TEXT,
            total_belanja INTEGER,
            bayar INTEGER,
            kembali INTEGER
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS detail_transaksi (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            id_transaksi INTEGER,
            nama_barang TEXT,
            harga INTEGER,
            qty INTEGER,
            subtotal INTEGER
        )
    """)

    conn.commit()
    return conn

conn = init_db()

# =====================================================
# HELPER
# =====================================================
def format_rupiah(x):
    return f"Rp {x:,.0f}".replace(",", ".")

# =====================================================
# SESSION
# =====================================================
if "keranjang" not in st.session_state:
    st.session_state.keranjang = []

if "last_trx" not in st.session_state:
    st.session_state.last_trx = None

# =====================================================
# SIDEBAR NAVIGASI
# =====================================================
menu = st.sidebar.radio("Menu", ["🛒 Kasir", "📜 Riwayat", "🧪 Test Printer"])

# =====================================================
# ================= KASIR =============================
# =====================================================
if menu == "🛒 Kasir":

    st.markdown("## 🏪 WARUNG HADE")
    st.caption("Sistem Kasir Digital")

    # ================= INPUT =================
    with st.container():
        col1, col2 = st.columns([3,2])
        with col1:
            nama = st.text_input("Nama Barang")
        with col2:
            harga = st.number_input("Harga (Rp)", min_value=0, step=500)

        col3, col4 = st.columns([2,3])
        with col3:
            qty = st.number_input("Jumlah", min_value=1, value=1)
        with col4:
            if st.button("➕ Tambah", use_container_width=True):
                if nama and harga > 0:
                    subtotal = harga * qty
                    st.session_state.keranjang.append({
                        "Nama": nama,
                        "Harga": harga,
                        "Qty": qty,
                        "Subtotal": subtotal
                    })
                    st.rerun()
                else:
                    st.error("Isi nama & harga dulu!")

    # ================= KERANJANG =================
    if st.session_state.keranjang:

        st.divider()
        df = pd.DataFrame(st.session_state.keranjang)

        st.dataframe(df, use_container_width=True, hide_index=True)

        total = df["Subtotal"].sum()

        colA, colB = st.columns(2)

        with colA:
            st.markdown(f"### Total: {format_rupiah(total)}")

        with colB:
            bayar = st.number_input("Uang Diterima", min_value=0, step=1000)
            kembali = bayar - total

            if bayar > 0:
                warna = "green" if kembali >= 0 else "red"
                st.markdown(
                    f"<div style='color:{warna};font-weight:bold;'>"
                    f"{'Kembali' if kembali>=0 else 'Kurang'}: {format_rupiah(abs(kembali))}"
                    "</div>",
                    unsafe_allow_html=True
                )

        if st.button("✅ Proses Bayar", use_container_width=True):
            if bayar >= total:

                waktu = datetime.now().strftime("%d/%m/%Y %H:%M")

                c = conn.cursor()
                c.execute("INSERT INTO transaksi (waktu,total_belanja,bayar,kembali) VALUES (?,?,?,?)",
                          (waktu,total,bayar,kembali))
                trx_id = c.lastrowid

                for item in st.session_state.keranjang:
                    c.execute("INSERT INTO detail_transaksi (id_transaksi,nama_barang,harga,qty,subtotal) VALUES (?,?,?,?,?)",
                              (trx_id,item["Nama"],item["Harga"],item["Qty"],item["Subtotal"]))

                conn.commit()

                # SIMPAN UNTUK STRUK
                st.session_state.last_trx = {
                    "waktu": waktu,
                    "items": st.session_state.keranjang.copy(),
                    "total": total,
                    "bayar": bayar,
                    "kembali": kembali
                }

                st.session_state.keranjang = []
                st.success("Transaksi berhasil disimpan!")

                st.rerun()
            else:
                st.error("Uang kurang!")

    # ================= STRUK =================
    if st.session_state.last_trx:

        st.divider()
        st.markdown("### 🧾 STRUK TRANSAKSI")

        trx = st.session_state.last_trx

        st.write(f"Tanggal : {trx['waktu']}")
        st.write("--------------------------------")

        for item in trx["items"]:
            st.write(f"{item['Nama']} x{item['Qty']} = {format_rupiah(item['Subtotal'])}")

        st.write("--------------------------------")
        st.write(f"Total   : {format_rupiah(trx['total'])}")
        st.write(f"Bayar   : {format_rupiah(trx['bayar'])}")
        st.write(f"Kembali : {format_rupiah(trx['kembali'])}")

        if st.button("Tutup Struk"):
            st.session_state.last_trx = None
            st.rerun()

# =====================================================
# ================= RIWAYAT ===========================
# =====================================================
elif menu == "📜 Riwayat":

    st.markdown("## 📜 Riwayat Transaksi")

    df = pd.read_sql_query("SELECT * FROM transaksi ORDER BY id DESC", conn)

    if not df.empty:

        total_omzet = df["total_belanja"].sum()

        col1, col2 = st.columns(2)
        col1.metric("Jumlah Transaksi", len(df))
        col2.metric("Total Omzet", format_rupiah(total_omzet))

        st.dataframe(df, use_container_width=True, hide_index=True)

        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
            df.to_excel(writer, index=False)

        st.download_button("📥 Download Excel",
                           buffer.getvalue(),
                           "Laporan_Warung_Hade.xlsx",
                           "application/vnd.ms-excel")
    else:
        st.info("Belum ada transaksi.")

# =====================================================
# ================= TEST PRINTER ======================
# =====================================================
elif menu == "🧪 Test Printer":

    st.markdown("## 🖨️ Test Cetak Printer")

    if st.button("🖨️ Test Print Struk Dummy", use_container_width=True):

        raw_text = "\x1b\x40\x1b\x61\x01WARUNG HADE\n"
        raw_text += "TEST PRINT\n"
        raw_text += "----------------------\n"
        raw_text += "Item Test\n1 x 1000 = 1000\n"
        raw_text += "----------------------\n"
        raw_text += "TOTAL : 1000\n"
        raw_text += "----------------------\n"
        raw_text += "Terima Kasih\n\n\n"

        b64 = base64.b64encode(raw_text.encode()).decode()
        href = f"rawbt:base64,{b64}"

        st.markdown(
            f'<a href="{href}" style="display:block;text-align:center;background:#2ecc71;padding:12px;border-radius:8px;color:white;font-weight:bold;text-decoration:none;">Klik Untuk Print via RawBT</a>',
            unsafe_allow_html=True
        )
