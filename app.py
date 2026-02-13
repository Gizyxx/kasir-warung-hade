import streamlit as st
import pandas as pd
import sqlite3
import base64
import io
from datetime import datetime

# =====================================================
# 1. KONFIGURASI HALAMAN
# =====================================================
st.set_page_config(page_title="Warung HADE POS", page_icon="🏪", layout="centered")

# =====================================================
# 2. CSS CUSTOM (TEMA NAVY + STRUK ANTI-ERROR)
# =====================================================
st.markdown("""
<style>
    /* IMPORT FONT */
    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;600&display=swap');

    /* BACKGROUND UTAMA GELAP (NAVY) */
    .stApp {
        background-color: #0b1120;
        color: #e2e8f0;
        font-family: 'Poppins', sans-serif;
    }
    
    /* INPUT STYLE */
    .stTextInput input, .stNumberInput input {
        background-color: #1e293b;
        color: white;
        border: 1px solid #334155;
        border-radius: 6px;
    }
    .stTextInput input:focus, .stNumberInput input:focus {
        border-color: #3b82f6;
    }

    /* TOMBOL STYLE */
    div.stButton > button {
        width: 100%;
        border-radius: 6px;
        font-weight: 600;
    }

    /* TOMBOL CETAK (HIJAU) */
    .btn-cetak {
        display: block; width: 100%; 
        background-color: #22c55e; 
        color: white !important;
        text-align: center; padding: 12px 0; border-radius: 8px;
        font-weight: bold; font-size: 16px; text-decoration: none; 
        margin-top: 15px;
        box-shadow: 0 4px 10px rgba(34, 197, 94, 0.3);
        transition: transform 0.2s;
    }
    .btn-cetak:active { transform: scale(0.98); }

    /* WADAH STRUK VISUAL (FIX: BACKGROUND PUTIH) */
    .struk-container {
        background-color: white !important;
        color: black !important;
        padding: 25px;
        width: 100%;
        max-width: 380px;
        margin: 0 auto;
        font-family: 'Courier New', monospace;
        border: 1px solid #ccc;
        box-shadow: 0 0 20px rgba(0,0,0,0.5);
    }
    
    /* SEMBUNYIKAN HEADER BAWAAN */
    header {visibility: hidden;}
    footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# =====================================================
# 3. DATABASE & HELPER
# =====================================================
@st.cache_resource
def init_db():
    # Gunakan nama DB baru untuk menghindari konflik skema lama
    conn = sqlite3.connect("warung_hade_v_fix.db", check_same_thread=False)
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS transaksi (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                waktu TEXT, total_belanja INTEGER, bayar INTEGER, kembali INTEGER)""")
    c.execute("""CREATE TABLE IF NOT EXISTS detail_transaksi (
                id INTEGER PRIMARY KEY AUTOINCREMENT, id_transaksi INTEGER,
                nama_barang TEXT, harga INTEGER, qty INTEGER, subtotal INTEGER)""")
    conn.commit()
    return conn

conn = init_db()

# FUNGSI FORMAT RUPIAH (SAFE MODE)
def format_rupiah(x):
    if x is None: return "Rp 0"
    if isinstance(x, bytes): return "Rp Error (Reset Data)" # Deteksi data rusak
    try:
        return f"Rp {float(x):,.0f}".replace(",", ".")
    except:
        return f"Rp {x}"

# =====================================================
# 4. LOGIKA UTAMA
# =====================================================
if "keranjang" not in st.session_state: st.session_state.keranjang = []
if "last_trx" not in st.session_state: st.session_state.last_trx = None

with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/2897/2897785.png", width=80)
    st.markdown("### POS SYSTEM")
    menu = st.radio("Menu", ["🛒 Kasir", "📜 Riwayat", "🧪 Test Printer"], label_visibility="collapsed")
    st.divider()
    st.info("Tips: Jika Laporan error 'bytes', klik tombol Hapus Data di menu Riwayat.")

# =====================================================
# MENU: KASIR
# =====================================================
if menu == "🛒 Kasir":
    st.markdown("""
    <div style="background: linear-gradient(90deg, #0f172a, #1e293b); padding: 20px; border-radius: 12px; text-align: center; border-bottom: 3px solid #3b82f6; margin-bottom: 20px;">
        <h2 style="margin:0; color:white;">🏪 WARUNG HADE</h2>
        <p style="margin:0; color:#94a3b8;">Sistem Kasir Digital Terintegrasi</p>
    </div>
    """, unsafe_allow_html=True)

    # --- INPUT ---
    st.markdown("##### 📦 Input Barang")
    c1, c2 = st.columns([3, 2])
    with c1: nama = st.text_input("Nama Barang", placeholder="Cth: Kopi Hitam", key="nama")
    with c2: harga = st.number_input("Harga (Rp)", min_value=0, step=500, key="harga")

    c3, c4 = st.columns([1, 2])
    with c3: qty = st.number_input("Jml", min_value=1, value=1, key="qty")
    with c4:
        st.markdown("<div style='height: 29px'></div>", unsafe_allow_html=True)
        if st.button("➕ Tambah Ke Keranjang", type="primary"):
            if nama and harga > 0:
                # KONVERSI KE INT MURNI (PENTING AGAR TIDAK ERROR BYTES)
                subtotal = int(harga) * int(qty)
                st.session_state.keranjang.append({
                    "Nama": nama, "Harga": int(harga), "Qty": int(qty), "Subtotal": subtotal
                })
                st.rerun()
            else:
                st.toast("Isi nama dan harga!", icon="⚠️")

    # --- TABEL ---
    if st.session_state.keranjang:
        st.divider()
        c_h1, c_h2 = st.columns([4,1])
        c_h1.markdown("##### 🛒 Daftar Belanja")
        if c_h2.button("Reset", type="secondary"):
            st.session_state.keranjang = []
            st.rerun()

        df = pd.DataFrame(st.session_state.keranjang)
        st.dataframe(df, use_container_width=True, hide_index=True,
                     column_config={"Harga": st.column_config.NumberColumn(format="Rp %d"),
                                    "Subtotal": st.column_config.NumberColumn(format="Rp %d")})

        total = int(df["Subtotal"].sum()) # Pastikan INT

        # --- BAYAR ---
        st.markdown("---")
        col_tot, col_bayar = st.columns([1,1])
        with col_tot:
            st.markdown("Total Tagihan")
            st.markdown(f"<h2 style='color:#3b82f6; margin:0;'>{format_rupiah(total)}</h2>", unsafe_allow_html=True)
        with col_bayar:
            bayar = st.number_input("Uang Diterima", min_value=0, step=1000)
            kembali = int(bayar) - total
            if bayar > 0:
                color = "#22c55e" if kembali >= 0 else "#ef4444"
                txt = "KEMBALI" if kembali >= 0 else "KURANG"
                st.markdown(f"<h4 style='color:{color}; margin-top:10px;'>{txt}: {format_rupiah(abs(kembali))}</h4>", unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("✅ PROSES PEMBAYARAN", type="primary"):
            if bayar >= total:
                # SIMPAN KE DB (PASTIKAN TIPE DATA NATIVE PYTHON)
                waktu = datetime.now().strftime("%d/%m/%Y %H:%M")
                c = conn.cursor()
                c.execute("INSERT INTO transaksi (waktu,total_belanja,bayar,kembali) VALUES (?,?,?,?)", 
                          (waktu, int(total), int(bayar), int(kembali)))
                trx_id = c.lastrowid
                
                for item in st.session_state.keranjang:
                    c.execute("INSERT INTO detail_transaksi (id_transaksi,nama_barang,harga,qty,subtotal) VALUES (?,?,?,?,?)", 
                              (trx_id, item["Nama"], int(item["Harga"]), int(item["Qty"]), int(item["Subtotal"])))
                conn.commit()
                
                st.session_state.last_trx = {
                    "waktu": waktu, "items": st.session_state.keranjang.copy(),
                    "total": total, "bayar": bayar, "kembali": kembali
                }
                st.session_state.keranjang = []
                st.rerun()
            else:
                st.error("Uang kurang!")

    # --- STRUK VISUAL ---
    if st.session_state.last_trx:
        trx = st.session_state.last_trx
        st.divider()
        st.success("✅ Transaksi Berhasil!")

        # HTML STRUK DI RAKIT TANPA SPASI DI AWAL BARIS (MENGHINDARI ERROR TAMPILAN KODE)
        rows_html = ""
        for item in trx['items']:
            rows_html += f"<tr><td style='padding-top:5px; border-bottom:1px dashed #ddd;'>{item['Nama']}<br><small style='color:#555;'>{item['Qty']} x {format_rupiah(item['Harga'])}</small></td><td style='text-align:right; vertical-align:bottom; border-bottom:1px dashed #ddd;'>{format_rupiah(item['Subtotal'])}</td></tr>"
        
        # Container HTML
        struk_html = f"""<div class="struk-container"><div style="text-align:center; padding-bottom:10px; border-bottom:2px dashed #000; margin-bottom:10px;"><h3 style="margin:0; font-weight:800; color:black;">WARUNG HADE</h3><p style="margin:0; font-size:12px; color:#333;">Tanjung Pinang</p><p style="margin:0; font-size:12px; color:#333;">{trx['waktu']}</p></div><table style="width:100%; border-collapse:collapse; font-size:13px; color:black;">{rows_html}</table><div style="margin-top:10px; padding-top:10px; border-top:2px dashed #000;"><div style="display:flex; justify-content:space-between; font-weight:bold; color:black;"><span>TOTAL</span><span>{format_rupiah(trx['total'])}</span></div><div style="display:flex; justify-content:space-between; font-size:13px; color:black;"><span>BAYAR</span><span>{format_rupiah(trx['bayar'])}</span></div><div style="display:flex; justify-content:space-between; font-size:13px; color:black;"><span>KEMBALI</span><span>{format_rupiah(trx['kembali'])}</span></div></div><div style="text-align:center; margin-top:15px; font-size:12px; color:black;">*** TERIMA KASIH ***</div></div>"""
        
        st.markdown(struk_html, unsafe_allow_html=True)
        
        # RAWBT PRINT LINK
        raw_text = f"\x1b\x40\x1b\x61\x01WARUNG HADE\n{trx['waktu']}\n--------------------------------\n\x1b\x61\x00"
        for item in trx["items"]:
            raw_text += f"{item['Nama']}\n{item['Qty']} x {item['Harga']:,} = {item['Subtotal']:,}\n"
        raw_text += f"--------------------------------\nTOTAL   : {trx['total']:,}\nBAYAR   : {trx['bayar']:,}\nKEMBALI : {trx['kembali']:,}\n--------------------------------\n\x1b\x61\x01Terima Kasih\n\n\n"
        b64_print = base64.b64encode(raw_text.encode()).decode()
        
        col_btn1, col_btn2 = st.columns(2)
        with col_btn1:
            st.markdown('<div style="margin-top: 15px;"></div>', unsafe_allow_html=True)
            if st.button("🏠 Transaksi Baru", use_container_width=True):
                st.session_state.last_trx = None
                st.rerun()
        with col_btn2:
            st.markdown(f'<a href="rawbt:base64,{b64_print}" class="btn-cetak">🖨️ CETAK SEKARANG</a>', unsafe_allow_html=True)

# =====================================================
# MENU: RIWAYAT
# =====================================================
elif menu == "📜 Riwayat":
    st.markdown("## 📜 Laporan Transaksi")
    
    # LOAD DATA DENGAN ERROR HANDLING
    try:
        df = pd.read_sql_query("SELECT * FROM transaksi ORDER BY id DESC", conn)
    except:
        st.error("Gagal membaca database.")
        df = pd.DataFrame()

    if not df.empty:
        # HANDLING DATA RUSAK (BYTES)
        try:
            total_omzet = df["total_belanja"].sum()
        except:
            total_omzet = 0 # Fallback jika data rusak

        col1, col2 = st.columns(2)
        col1.metric("Total Transaksi", f"{len(df)} Bon")
        col2.metric("Total Omzet", format_rupiah(total_omzet))

        st.dataframe(df, use_container_width=True, hide_index=True)
        
        # Download Excel
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
            df.to_excel(writer, index=False)
        st.download_button("📥 Download Excel", buffer.getvalue(), "Laporan.xlsx", "application/vnd.ms-excel")
        
        st.markdown("---")
        with st.expander("🔴 Zona Bahaya (Reset Database)"):
            st.warning("Klik tombol di bawah jika Laporan error atau muncul kode aneh.")
            if st.button("Hapus SEMUA Riwayat", type="primary"):
                conn.execute("DELETE FROM transaksi")
                conn.execute("DELETE FROM detail_transaksi")
                conn.commit()
                st.success("Database berhasil di-reset!")
                st.rerun()
    else:
        st.info("Belum ada data transaksi.")

# =====================================================
# MENU: TEST PRINTER
# =====================================================
elif menu == "🧪 Test Printer":
    st.markdown("## 🖨️ Test Printer")
    raw = "\x1b\x40\x1b\x61\x01TEST PRINTER\nWARUNG HADE\n\nBERHASIL!\n\n\n"
    b64_dummy = base64.b64encode(raw.encode()).decode()
    st.markdown(f'<a href="rawbt:base64,{b64_dummy}" class="btn-cetak">🖨️ KLIK UNTUK TEST</a>', unsafe_allow_html=True)