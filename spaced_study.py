import streamlit as st
import datetime
import json
import hashlib
import os
from google import genai

# ==========================================
# 1. VERİTABANI VE ŞİFRELEME FONKSİYONLARI
# ==========================================
USERS_DB_FILE = "users_db.json"

def make_hash(password):
    return hashlib.sha256(password.encode('utf-8')).hexdigest()

def check_hash(password, hashed_text):
    return make_hash(password) == hashed_text

def load_users_db():
    if os.path.exists(USERS_DB_FILE):
        try:
            with open(USERS_DB_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError:
            return {}
    return {}

def save_users_db(data):
    with open(USERS_DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# ==========================================
# 2. GEMINI YAPAY ZEKA ENTEGRASYONU
# ==========================================
def get_ai_tutor_response(prompt_text):
    """Gemini API kullanarak yapay zeka yanıtı üretir."""
    api_key = st.secrets.get("GEMINI_API_KEY") or os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return "⚠️ Gemini API Anahtarı bulunamadı! Lütfen Streamlit Secrets ayarlarına GEMINI_API_KEY ekleyin."
    
    try:
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model="gemini-3.8-flash",
            contents=prompt_text,
        )
        return response.text
    except Exception as e:
        return f"Yapay zeka ile iletişim kurulurken bir hata oluştu: {str(e)}"

# ==========================================
# 3. SAYFA AYARLARI VE OTURUM KONTROLÜ
# ==========================================
st.set_page_config(
    page_title="Akıllı Tekrar & AI Çalışma Takvimi",
    page_icon="📚",
    layout="wide"
)

db = load_users_db()

if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False
if "username" not in st.session_state:
    st.session_state["username"] = ""
if "selected_study_topic" not in st.session_state:
    st.session_state["selected_study_topic"] = ""

# ==========================================
# 4. GİRİŞ VE KAYIT EKRANI
# ==========================================
if not st.session_state["logged_in"]:
    st.title("📚 Akıllı Ders Çalışma Takvimi")
    st.subheader("Giriş Yap veya Kayıt Ol")

    tab_login, tab_register = st.tabs(["🔑 Giriş Yap", "📝 Kayıt Ol"])

    with tab_login:
        login_user = st.text_input("Kullanıcı Adı", key="login_user")
        login_pass = st.text_input("Şifre", type="password", key="login_pass")
        
        if st.button("Giriş Yap"):
            if login_user in db and check_hash(login_pass, db[login_user]["password"]):
                st.session_state["logged_in"] = True
                st.session_state["username"] = login_user
                st.success(f"Hoş geldin, {login_user}!")
                st.rerun()
            else:
                st.error("Kullanıcı adı veya şifre hatalı!")

    with tab_register:
        reg_user = st.text_input("Yeni Kullanıcı Adı", key="reg_user")
        reg_pass = st.text_input("Yeni Şifre", type="password", key="reg_pass")
        
        if st.button("Hesap Oluştur"):
            if reg_user in db:
                st.warning("Bu kullanıcı adı zaten kullanılıyor!")
            elif reg_user and reg_pass:
                db[reg_user] = {
                    "password": make_hash(reg_pass),
                    "topics": []
                }
                save_users_db(db)
                st.success("Hesabınız başarıyla oluşturuldu! Şimdi Giriş Yap sekmesinden giriş yapabilirsiniz.")
            else:
                st.warning("Lütfen hem kullanıcı adı hem de şifre giriniz.")

# ==========================================
# 5. GİRİŞ YAPILMIŞ ANA UYGULAMA EKRANI
# ==========================================
else:
    current_user = st.session_state["username"]
    user_data = db[current_user]
    topics = user_data["topics"]
    today_str = datetime.date.today().isoformat()

    col_title, col_logout = st.columns([4, 1])
    with col_title:
        st.title("📚 Aralıklı Tekrar & AI Destekli Çalışma Paneli")
        st.caption(f"Aktif Öğrenci Hesabı: **{current_user}** | Ebbinghaus Unutma Eğrisi")
    with col_logout:
        st.write("")
        if st.button("🚪 Çıkış Yap"):
            st.session_state["logged_in"] = False
            st.session_state["username"] = ""
            st.rerun()

    st.divider()

    # YAN PANEL: DERS EKLEME
    st.sidebar.header("➕ Yeni Konu Çalışması Ekle")

    with st.sidebar.form("add_topic_form"):
        course_name = st.selectbox("Ders Seçin:", ["Matematik", "Fizik", "Kimya", "Biyoloji", "Türkçe", "Tarih", "Coğrafya"])
        topic_title = st.text_input("Konu Adı:", placeholder="Örn: Türev Alma Kuralları")
        difficulty = st.select_slider(
            "Konu Zorluk / Anlama Düzeyi:",
            options=["Zor (Çok Unutulabilir)", "Orta (Normal)", "Kolay (İyi Anlaşıldı)"]
        )
        submitted = st.form_submit_button("Çalışmayı Kaydet")

    if submitted and topic_title:
        interval = 1 if "Zor" in difficulty else (3 if "Orta" in difficulty else 5)
        next_review = datetime.date.today() + datetime.timedelta(days=interval)
        
        new_entry = {
            "id": len(topics) + 1,
            "course": course_name,
            "topic": topic_title,
            "added_date": today_str,
            "last_review": today_str,
            "next_review": next_review.isoformat(),
            "interval_days": interval,
            "review_count": 0,
            "difficulty": difficulty
        }
        
        topics.append(new_entry)
        save_users_db(db)
        st.sidebar.success(f"'{topic_title}' hesabınıza kaydedildi!")
        st.rerun()

    due_topics = [t for t in topics if t["next_review"] <= today_str]
    upcoming_topics = [t for t in topics if t["next_review"] > today_str]

    m1, m2, m3 = st.columns(3)
    m1.metric("Toplam Takip Edilen Konu", len(topics))
    m2.metric("⚠️ Bugün Tekrar Edilecekler", len(due_topics), delta_color="inverse")
    m3.metric("✅ İleriki Tarihli Tekrarlar", len(upcoming_topics))

    st.divider()

    # TEKRAR LİSTESİ VE AI ÖĞRETMEN SEKMELERİ
    tab1, tab2, tab3 = st.tabs(["🔔 Bugünün Tekrar Görevleri", "🤖 AI Özel Öğretmen", "📋 Tüm Çalışma Geçmişi"])

    with tab1:
        st.subheader("🔔 Bugün Tamamlanması Gereken Tekrarlar")
        if not due_topics:
            st.info("🎉 Harika! Bugün tekrar etmen gereken hiçbir konu kalmadı.")
        else:
            for item in due_topics:
                with st.expander(f"📌 [{item['course']}] - {item['topic']} (Son Tekrar: {item['last_review']})", expanded=True):
                    st.write(f"**Ekleme Tarihi:** {item['added_date']} | **Tekrar Sayısı:** {item['review_count']}")
                    st.write(f"**Son Değerlendirme:** {item['difficulty']}")
                    
                    b1, b2, b3, b4 = st.columns(4)
                    if b1.button("🔴 Zorlandım (1 Gün)", key=f"hard_{item['id']}"):
                        item['interval_days'] = 1
                        item['next_review'] = (datetime.date.today() + datetime.timedelta(days=1)).isoformat()
                        item['last_review'] = today_str
                        item['review_count'] += 1
                        item['difficulty'] = "Zor (Çok Unutulabilir)"
                        save_users_db(db)
                        st.rerun()
                        
                    if b2.button("🟡 Normaldi (3 Gün)", key=f"mid_{item['id']}"):
                        item['interval_days'] = int(item['interval_days'] * 1.8) + 2
                        item['next_review'] = (datetime.date.today() + datetime.timedelta(days=item['interval_days'])).isoformat()
                        item['last_review'] = today_str
                        item['review_count'] += 1
                        item['difficulty'] = "Orta (Normal)"
                        save_users_db(db)
                        st.rerun()

                    if b3.button("🟢 Çok Kolaydı (7 Gün)", key=f"easy_{item['id']}"):
                        item['interval_days'] = int(item['interval_days'] * 2.5) + 5
                        item['next_review'] = (datetime.date.today() + datetime.timedelta(days=item['interval_days'])).isoformat()
                        item['last_review'] = today_str
                        item['review_count'] += 1
                        item['difficulty'] = "Kolay (İyi Anlaşıldı)"
                        save_users_db(db)
                        st.rerun()

                    if b4.button("🤖 AI ile Konuyu Çalış", key=f"ai_study_{item['id']}"):
                        st.session_state["selected_study_topic"] = f"{item['course']} - {item['topic']}"
                        st.rerun()

    with tab2:
        st.subheader("🤖 Yapay Zeka (Gemini) Özel Öğretmeni")
        st.write("Zorlandığın konuyu seç veya yaz; yapay zeka sana konunun özünü anlatsın, kritik püf noktaları versin ve kendini test etmen için pratik sorular sorsun.")

        default_topic = st.session_state.get("selected_study_topic", "")
        study_input = st.text_input("Çalışmak İstediğin Ders / Konu:", value=default_topic, placeholder="Örn: Matematik - Türev Alma Kuralları")

        study_mode = st.radio(
            "Nasıl Bir Destek İstersin?",
            ["💡 Konu Özeti ve Püf Noktalar", "❓ Örnek Soru ve Çözümleri", "🎯 Hızlı Kavrama Testi (3 Soru)"],
            horizontal=True
        )

        if st.button("🚀 Yapay Zeka ile Çalışmayı Başlat"):
            if study_input:
                with st.spinner("Yapay zeka öğretmenin özel ders notunu hazırlıyor..."):
                    prompt = f"""
                    Sen lise öğrencilerine ders anlatan çok samimi, motive edici ve harika bir özel öğretmensin.
                    Öğrenci senden şu konu hakkında destek istiyor: '{study_input}'.
                    İstenen mod: '{study_mode}'.

                    Lütfen cevabında:
                    - Gereksiz uzun anlatımlardan kaçın.
                    - Formül veya mantığı anlaşılır biçimde açıkla.
                    - Öğrencinin aklında kalacak pratik bir ipucu ver.
                    - Samimi ve cesaret verici bir dil kullan.
                    """
                    ai_response = get_ai_tutor_response(prompt)
                    st.markdown("---")
                    st.markdown(ai_response)
            else:
                st.warning("Lütfen önce çalışmak istediğin bir konu girin!")

    with tab3:
        st.subheader("📋 Tüm Konular ve Gelecek Tekrar Tarihleri")
        if topics:
            table_data = [{
                "Ders": t["course"],
                "Konu": t["topic"],
                "Son Tekrar": t["last_review"],
                "Gelecek Tekrar": t["next_review"],
                "Tekrar Sayısı": t["review_count"],
                "Durum": "⚠️ BUGÜN!" if t["next_review"] <= today_str else "⏳ Beklemede"
            } for t in topics]
            st.dataframe(table_data, use_container_width=True)
        else:
            st.write("Henüz bu hesaba eklenmiş bir konu bulunmuyor.")
