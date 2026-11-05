import streamlit as st
import pandas as pd
import json
import sqlite3
import requests
import base64
from gtts import gTTS
import os
import tempfile

# --- 1. KONFIGURASI DATABASE ---
def init_db():
    conn = sqlite3.connect('kamus_vocab.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS vocab (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            kata TEXT UNIQUE,
            type TEXT,
            translation TEXT,
            v1 TEXT,
            v2 TEXT,
            v3 TEXT
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# --- 2. FUNGSI HELPER DB ---
def save_to_db(entry):
    conn = sqlite3.connect('kamus_vocab.db')
    c = conn.cursor()
    try:
        c.execute('''
            INSERT OR REPLACE INTO vocab (kata, type, translation, v1, v2, v3) 
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (entry['Kata'], entry['Type'], entry['Terjemahan'], entry['Verb 1'], entry['Verb 2'], entry['Verb 3']))
        conn.commit()
        return True
    except Exception as e:
        st.error(f"Gagal menyimpan ke database: {e}")
        return False
    finally:
        conn.close()

def get_all_vocab():
    conn = sqlite3.connect('kamus_vocab.db')
    df = pd.read_sql_query("SELECT id, kata as Kata, type as Type, translation as Terjemahan, v1 as 'Verb 1', v2 as 'Verb 2', v3 as 'Verb 3' FROM vocab ORDER BY id DESC", conn)
    conn.close()
    return df

def delete_vocab_by_id(vocab_id):
    conn = sqlite3.connect('kamus_vocab.db')
    c = conn.cursor()
    try:
        c.execute("DELETE FROM vocab WHERE id = ?", (vocab_id,))
        conn.commit()
        return True
    except Exception as e:
        st.error(f"Gagal menghapus data: {e}")
        return False
    finally:
        conn.close()

# --- 3. KONFIGURASI AI DEEPSEEK ---
class DeepSeekClient:
    def __init__(self, api_key):
        self.api_key = api_key
        self.base_url = "https://api.deepseek.com/v1/chat/completions"
        
    def generate_content(self, prompt):
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": "deepseek-chat",
            "messages": [
                {"role": "system", "content": "You are a helpful English vocabulary assistant. Always respond in Indonesian."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.3,
            "max_tokens": 200
        }
        
        try:
            response = requests.post(self.base_url, headers=headers, json=payload)
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"]
        except requests.exceptions.RequestException as e:
            st.error(f"Error menghubungi DeepSeek API: {e}")
            return None

# --- 4. FUNGSI AUDIO ---
def text_to_speech(text):
    """Mengubah teks menjadi audio"""
    try:
        tts = gTTS(text=text, lang='en', slow=False)
        with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as fp:
            tts.save(fp.name)
            audio_file = fp.name
        
        # Baca file audio
        with open(audio_file, 'rb') as f:
            audio_bytes = f.read()
            audio_base64 = base64.b64encode(audio_bytes).decode()
        
        # Hapus file temporary
        os.unlink(audio_file)
        
        # Buat HTML audio player
        audio_html = f'''
            <audio controls style="width: 100%; height: 35px;">
                <source src="data:audio/mp3;base64,{audio_base64}" type="audio/mp3">
                Your browser does not support the audio element.
            </audio>
        '''
        return audio_html
    except Exception as e:
        st.error(f"Error membuat audio: {e}")
        return None

# --- 5. TAMPILAN UI ---
st.set_page_config(page_title="Kamus AI dengan DeepSeek", layout="wide")
st.title("🤖 Kamus Kosakata Pintar (DeepSeek Powered)")

# --- 5a. AMBIL API KEY DARI SECRETS (AMAN) ---
try:
    DEEPSEEK_API_KEY = st.secrets["DEEPSEEK_API_KEY"]
except (KeyError, FileNotFoundError):
    st.error("⚠️ API Key DeepSeek belum dikonfigurasi. Silakan atur `DEEPSEEK_API_KEY` di Secrets Streamlit Cloud (atau `.streamlit/secrets.toml` saat lokal).")
    st.stop()

# Inisialisasi client DeepSeek
deepseek_client = DeepSeekClient(DEEPSEEK_API_KEY)

# Custom CSS untuk tampilan lebih baik
st.markdown("""
    <style>
    /* Styling untuk container vocabulary */
    .vocab-container {
        background-color: #f8f9fa;
        border-radius: 10px;
        padding: 8px 15px;
        margin-bottom: 8px;
        border: 1px solid #e0e0e0;
        transition: all 0.3s ease;
    }
    .vocab-container:hover {
        background-color: #f0f2f6;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    }
    
    /* Text styling */
    .kata-text {
        font-weight: bold;
        font-size: 16px;
        color: #1f2937;
    }
    .type-text {
        font-size: 14px;
        color: #6b7280;
        background-color: #e5e7eb;
        padding: 2px 10px;
        border-radius: 12px;
        display: inline-block;
    }
    .terjemahan-text {
        font-size: 15px;
        color: #374151;
    }
    .verb-text {
        font-size: 14px;
        color: #4b5563;
        font-family: monospace;
    }
    
    /* Button styling */
    .stButton button {
        border-radius: 6px;
        transition: all 0.3s ease;
        font-size: 13px !important;
        padding: 4px 12px !important;
        height: auto !important;
        width: 100% !important;
    }
    .stButton button:hover {
        transform: scale(1.05);
    }
    
    /* Delete button styling */
    .delete-btn {
        background-color: #ef4444 !important;
        color: white !important;
    }
    .delete-btn:hover {
        background-color: #dc2626 !important;
    }
    
    /* Audio player styling */
    audio {
        border-radius: 30px;
        background-color: #f3f4f6;
        width: 100%;
    }
    
    /* Garis pemisah antar kolom */
    .col-divider {
        border-right: 2px solid #e5e7eb;
        padding-right: 10px;
    }
    
    /* Header kolom dengan garis */
    .header-col {
        border-right: 2px solid #d1d5db;
        padding-right: 10px;
        font-weight: bold;
    }
    .header-col:last-child {
        border-right: none;
    }
    
    /* Style untuk baris data */
    .data-row {
        display: flex;
        align-items: center;
        padding: 5px 0;
    }
    .data-col {
        border-right: 2px solid #e5e7eb;
        padding-right: 10px;
        padding-left: 5px;
        min-height: 40px;
        display: flex;
        align-items: center;
    }
    .data-col:last-child {
        border-right: none;
    }
    </style>
""", unsafe_allow_html=True)

def get_vocab_info(word):
    prompt = f"""
    Berikan informasi untuk kata bahasa Inggris: "{word}".
    Berikan HANYA JSON tanpa teks tambahan.
    Struktur JSON: {{"type": "noun/verb/etc", "translation": "...", "v1": "-", "v2": "-", "v3": "-"}}.
    Isi v1, v2, v3 dengan "-" jika bukan verb.
    """
    try:
        response = deepseek_client.generate_content(prompt)
        if response:
            clean_text = response.replace('```json', '').replace('```', '').strip()
            return json.loads(clean_text)
        return None
    except Exception as e:
        st.error(f"DeepSeek gagal memberikan data. Detail error: {e}")
        return None

# --- 6. FORM INPUT ---
with st.form("input_form", clear_on_submit=True):
    col1, col2, col3 = st.columns([3, 1, 1])
    with col1:
        kata = st.text_input("Masukkan kata bahasa Inggris:", placeholder="Contoh: beautiful, run, happiness")
    with col2:
        st.write("")  # Spacing
        st.write("")  # Spacing
        submit = st.form_submit_button("📚 Tambahkan", use_container_width=True)

    if submit and kata:
        with st.spinner(f"DeepSeek sedang mencari arti untuk '{kata}'..."):
            info = get_vocab_info(kata)
            if info:
                entry = {
                    "Kata": kata.lower(),
                    "Type": info.get("type", "-"),
                    "Terjemahan": info.get("translation", "-"),
                    "Verb 1": info.get("v1", "-"),
                    "Verb 2": info.get("v2", "-"),
                    "Verb 3": info.get("v3", "-")
                }
                if save_to_db(entry):
                    st.success(f"✅ Data '{kata}' berhasil disimpan!")
                    st.balloons()
                else:
                    st.error("❌ Gagal menyimpan data!")
            else:
                st.error("❌ Gagal mendapatkan respons valid dari DeepSeek. Coba lagi nanti.")

# --- 7. MENAMPILKAN DATA ---
st.subheader("📖 Daftar Kosakata Anda")
st.markdown("---")

# Ambil data dari database
df = get_all_vocab()

if not df.empty:
    # Header kolom (8 kolom)
    header_cols = st.columns([1.5, 0.8, 1.5, 0.8, 0.8, 0.8, 1.5, 0.8])
    with header_cols[0]:
        st.markdown("**📝 Kata**")
    with header_cols[1]:
        st.markdown("**📌 Tipe**")
    with header_cols[2]:
        st.markdown("**🌐 Terjemahan**")
    with header_cols[3]:
        st.markdown("**V1**")
    with header_cols[4]:
        st.markdown("**V2**")
    with header_cols[5]:
        st.markdown("**V3**")
    with header_cols[6]:
        st.markdown("**🔊 Audio**")
    with header_cols[7]:
        st.markdown("**🗑️ Aksi**")
    
    st.markdown("---")
    
    # Loop data dengan container per baris
    for idx, row in df.iterrows():
        with st.container():
            # Buat kolom dengan proporsi yang sama (8 kolom)
            cols = st.columns([1.5, 0.8, 1.5, 0.8, 0.8, 0.8, 1.5, 0.8])
            
            # Kolom 1: Kata
            with cols[0]:
                st.markdown(f'<span class="kata-text">{row["Kata"].capitalize()}</span>', unsafe_allow_html=True)
            
            # Kolom 2: Type
            with cols[1]:
                st.markdown(f'<span class="type-text">{row["Type"]}</span>', unsafe_allow_html=True)
            
            # Kolom 3: Terjemahan
            with cols[2]:
                st.markdown(f'<span class="terjemahan-text">{row["Terjemahan"]}</span>', unsafe_allow_html=True)
            
            # Kolom 4: Verb 1
            with cols[3]:
                if row["Verb 1"] != "-":
                    st.markdown(f'<span class="verb-text">{row["Verb 1"]}</span>', unsafe_allow_html=True)
                else:
                    st.write("-")
            
            # Kolom 5: Verb 2
            with cols[4]:
                if row["Verb 2"] != "-":
                    st.markdown(f'<span class="verb-text">{row["Verb 2"]}</span>', unsafe_allow_html=True)
                else:
                    st.write("-")
            
            # Kolom 6: Verb 3
            with cols[5]:
                if row["Verb 3"] != "-":
                    st.markdown(f'<span class="verb-text">{row["Verb 3"]}</span>', unsafe_allow_html=True)
                else:
                    st.write("-")
            
            # Kolom 7: Audio
            with cols[6]:
                audio_html = text_to_speech(row["Kata"])
                if audio_html:
                    st.markdown(audio_html, unsafe_allow_html=True)
                else:
                    st.write("⚠️ Audio tidak tersedia")
            
            # Kolom 8: Delete Button
            with cols[7]:
                if st.button("🗑️", key=f"delete_{row['id']}", use_container_width=True):
                    if delete_vocab_by_id(row['id']):
                        st.success(f"✅ '{row['Kata']}' berhasil dihapus!")
                        st.rerun()
                    else:
                        st.error("❌ Gagal menghapus data!")
            
            # Garis pemisah antar item
            st.markdown("---")

else:
    st.info("ℹ️ Belum ada kosakata yang disimpan. Tambahkan kata baru di atas!")

# --- 8. SIDEBAR ---
with st.sidebar:
    st.header("📊 Statistik")
    total_words = len(df) if not df.empty else 0
    st.metric("Total Kosakata", total_words)
    
    if not df.empty:
        st.markdown("---")
        st.subheader("📈 Distribusi Jenis Kata")
        type_counts = df['Type'].value_counts()
        for type_name, count in type_counts.items():
            percentage = (count / total_words) * 100
            st.progress(percentage / 100)
            st.caption(f"**{type_name}**: {count} kata ({percentage:.1f}%)")
        
        st.markdown("---")
        st.subheader("🔤 Kata Terbaru")
        latest_words = df.head(5)['Kata'].tolist()
        for word in latest_words:
            st.write(f"• {word.capitalize()}")
    
    st.markdown("---")
    st.caption("💡 **Tips Penggunaan:**")
    st.caption("• Klik play pada audio untuk mendengar pengucapan")
    st.caption("• 🗑️ Hapus kata yang tidak diperlukan")
    st.caption("• Data tersimpan di database SQLite")