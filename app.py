"""
=========================================================================
🚀 TASKATY PRO V3.1 - Offline Edition (مع دمج Gemini)
=========================================================================
"""

import sqlite3
import pandas as pd
import streamlit as st
import time
import json
import re
from datetime import datetime, date, timedelta
import plotly.express as px
from hijri_converter import Gregorian

# ==========================================
# 1. إعدادات الواجهة (تعمل Offline)
# ==========================================
st.set_page_config(page_title="TASKATY PRO", page_icon="🚀", layout="wide", initial_sidebar_state="expanded")

# ==========================================
# 2. طبقة قاعدة البيانات (SQLite - محلية بالكامل)
# ==========================================
class DatabaseManager:
    def __init__(self, db_name="taskaty_pro.db"):
        self.db_name = db_name
        self.init_db()

    def get_conn(self):
        return sqlite3.connect(self.db_name, check_same_thread=False)

    def init_db(self):
        with self.get_conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    description TEXT,
                    category TEXT,
                    priority TEXT,
                    due_date TEXT,
                    due_time TEXT,
                    status TEXT DEFAULT 'لم تبدأ',
                    completed BOOLEAN DEFAULT 0,
                    deleted BOOLEAN DEFAULT 0,
                    tags TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()

    def add_task(self, title, desc, cat, prio, due_date, due_time, tags=""):
        with self.get_conn() as conn:
            conn.execute(
                "INSERT INTO tasks (title, description, category, priority, due_date, due_time, tags) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (title, desc, cat, prio, due_date, due_time, tags)
            )
            conn.commit()

    def get_active_tasks(self):
        return pd.read_sql("SELECT * FROM tasks WHERE deleted = 0 ORDER BY due_date ASC", self.get_conn())

    def get_deleted_tasks(self):
        return pd.read_sql("SELECT * FROM tasks WHERE deleted = 1", self.get_conn())

    def update_task_status(self, task_id, completed):
        status = 'مكتملة' if completed else 'قيد التنفيذ'
        with self.get_conn() as conn:
            conn.execute("UPDATE tasks SET completed = ?, status = ? WHERE id = ?", (int(completed), status, task_id))
            conn.commit()

    def soft_delete_task(self, task_id):
        with self.get_conn() as conn:
            conn.execute("UPDATE tasks SET deleted = 1 WHERE id = ?", (task_id,))
            conn.commit()

    def restore_task(self, task_id):
        with self.get_conn() as conn:
            conn.execute("UPDATE tasks SET deleted = 0 WHERE id = ?", (task_id,))
            conn.commit()

    def hard_delete_task(self, task_id):
        with self.get_conn() as conn:
            conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
            conn.commit()

    def execute_query(self, query):
        return pd.read_sql(query, self.get_conn())

# ==========================================
# 3. خدمات الأوفلاين (تواريخ وتصميم)
# ==========================================
class AppServices:
    @staticmethod
    def get_hijri(g_date):
        try:
            h = Gregorian(g_date.year, g_date.month, g_date.day).to_hijri()
            return f"{h.day} {h.month_name()} {h.year} هـ"
        except:
            return "خارج النطاق"

    @staticmethod
    def apply_custom_css():
        # استخدام خط افتراضي في حال عدم وجود إنترنت لتحميل خط Cairo
        st.markdown("""
            <style>
            @import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700&display=swap');
            * { font-family: 'Cairo', 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }
            .stApp { direction: rtl; text-align: right; }
            .s-today { border-right: 6px solid #ffc107; background: rgba(255,193,7,0.1); }
            .s-done { border-right: 6px solid #28a745; background: rgba(40,167,69,0.1); opacity: 0.7; }
            .s-late { border-right: 6px solid #6c757d; background: rgba(108,117,125,0.1); }
            .s-prog { border-right: 6px solid #6f42c1; background: rgba(111,66,193,0.1); }
            .task-card { padding: 15px; border-radius: 8px; margin-bottom: 12px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
            .badge { padding: 4px 8px; border-radius: 4px; font-size: 0.8em; font-weight: 600; margin-left: 5px; background: var(--secondary-background-color); }
            .prio-high { color: #dc3545; } .prio-med { color: #fd7e14; } .prio-low { color: #007bff; }
            </style>
        """, unsafe_allow_html=True)

# ==========================================
# 4. تهيئة التطبيق
# ==========================================
db = DatabaseManager()
AppServices.apply_custom_css()
CATEGORIES = ["📚 دراسة", "💼 عمل", "🏠 شخصي", "🏃 صحة", "📅 مواعيد", "🧪 فيزياء وكيمياء", "📐 رياضيات"]

with st.sidebar:
    st.markdown("<h1 style='text-align:center;'>🚀</h1>", unsafe_allow_html=True) # رمز يعمل أوفلاين بدل الصورة
    st.title("TASKATY PRO")
    today = date.today()
    st.write(f"📅 **{today.strftime('%Y-%m-%d')}**")
    st.write(f"🌙 **{AppServices.get_hijri(today)}**")
    st.divider()
    page = st.radio("الرئيسية", ["📋 إدارة المهام", "📊 الإحصائيات", "🍅 مؤقت التركيز", "🧠 المساعد الذكي (Gemini)", "🗑️ سلة المهملات", "⚙️ الإعدادات"])

# ==========================================
# 5. الصفحات
# ==========================================

if page == "📋 إدارة المهام":
    st.header("إدارة المهام المتقدمة")
    
    with st.expander("➕ إضافة مهمة جديدة", expanded=False):
        with st.form("full_task_form", clear_on_submit=True):
            t_title = st.text_input("اسم المهمة (إلزامي):*")
            t_desc = st.text_area("التفاصيل والملاحظات:")
            c1, c2, c3, c4 = st.columns(4)
            t_date = c1.date_input("تاريخ التسليم:", min_value=today, max_value=date(2100, 12, 31))
            t_time = c2.time_input("الوقت:")
            t_cat = c3.selectbox("التصنيف:", CATEGORIES)
            t_prio = c4.selectbox("الأولوية:", ["🔴 عاجلة", "🟠 متوسطة", "🔵 منخفضة"])
            t_tags = st.text_input("علامات (Tags) مفصولة بفاصلة:")
            
            if st.form_submit_button("حفظ في قاعدة البيانات 💾"):
                if t_title:
                    db.add_task(t_title, t_desc, t_cat, t_prio, t_date.strftime("%Y-%m-%d"), t_time.strftime("%H:%M"), t_tags)
                    st.success("تم حفظ المهمة بنجاح!")
                    st.rerun()

    st.divider()
    c_search, c_filter, c_sort = st.columns(3)
    search_q = c_search.text_input("🔍 بحث...")
    f_cat = c_filter.selectbox("تصفية بالتصنيف:", ["الكل"] + CATEGORIES)
    f_status = c_sort.selectbox("الحالة:", ["الكل", "المتبقية", "المكتملة", "المتأخرة"])

    tasks_df = db.get_active_tasks()
    
    if not tasks_df.empty:
        for _, task in tasks_df.iterrows():
            if search_q and search_q not in task["title"]: continue
            if f_cat != "الكل" and task["category"] != f_cat: continue
            if f_status == "المكتملة" and not task["completed"]: continue
            if f_status == "المتبقية" and task["completed"]: continue
            
            due_date = datetime.strptime(task["due_date"], "%Y-%m-%d").date()
            days_left = (due_date - today).days
            
            if f_status == "المتأخرة" and (days_left >= 0 or task["completed"]): continue

            if task["completed"]: css, status = "s-done", "مكتملة 🟢"
            elif days_left < 0: css, status = "s-late", f"متأخرة {abs(days_left)} يوم ⚫"
            elif days_left == 0: css, status = "s-today", "اليوم 🟡"
            else: css, status = "s-prog", f"متبقي {days_left} يوم 🟣"

            prio_color = "prio-high" if "🔴" in task["priority"] else ("prio-med" if "🟠" in task["priority"] else "prio-low")

            st.markdown(f"""
                <div class="task-card {css}">
                    <h4 style="margin:0; text-decoration: {'line-through' if task['completed'] else 'none'};">{task['title']}</h4>
                    <p style="margin:5px 0; font-size:0.9em; color:#555;">{task['description']}</p>
                    <div>
                        <span class="badge">{task['category']}</span>
                        <span class="badge">📅 {task['due_date']} ({AppServices.get_hijri(due_date)})</span>
                        <span class="badge">⏰ {task['due_time']}</span>
                        <span class="badge {prio_color}">{task['priority']}</span>
                        <span class="badge">{status}</span>
                    </div>
                </div>
            """, unsafe_allow_html=True)
            
            b1, b2 = st.columns([1, 11])
            if b1.button("✅" if not task["completed"] else "🔄", key=f"tgl_{task['id']}", help="تغيير الحالة"):
                db.update_task_status(task['id'], not task["completed"])
                st.rerun()
            if b2.button("🗑️", key=f"del_{task['id']}", help="نقل لسلة المهملات"):
                db.soft_delete_task(task['id'])
                st.rerun()
    else:
        st.info("لا توجد مهام مسجلة.")

elif page == "📊 الإحصائيات":
    st.header("الإحصائيات")
    tasks_df = db.get_active_tasks()
    if not tasks_df.empty:
        t_total = len(tasks_df)
        t_done = len(tasks_df[tasks_df["completed"] == 1])
        t_late = len(tasks_df[(tasks_df["completed"] == 0) & (pd.to_datetime(tasks_df["due_date"]).dt.date < today)])
        
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("إجمالي المهام", t_total)
        c2.metric("🟢 المكتملة", t_done)
        c3.metric("🟣 المتبقية", t_total - t_done)
        c4.metric("⚫ المتأخرة", t_late)
        
        col1, col2 = st.columns(2)
        cat_count = tasks_df["category"].value_counts().reset_index()
        cat_count.columns = ["التصنيف", "العدد"]
        fig1 = px.pie(cat_count, values="العدد", names="التصنيف", title="المهام حسب التصنيف")
        col1.plotly_chart(fig1, use_container_width=True)
    else:
        st.info("لا توجد مهام لتحليلها.")

elif page == "🍅 مؤقت التركيز":
    st.header("مؤقت بومودورو للتركيز")
    c1, c2 = st.columns(2)
    work_mins = c1.number_input("دقائق التركيز:", value=50, min_value=1)
    
    if 'timer_running' not in st.session_state: st.session_state.timer_running = False

    col_btn, col_stop = st.columns([1, 10])
    if col_btn.button("▶️ ابدأ"): st.session_state.timer_running = True
    if col_stop.button("⏹️ إيقاف"): st.session_state.timer_running = False
    
    timer_placeholder = st.empty()
    
    if st.session_state.timer_running:
        for i in range(work_mins * 60, -1, -1):
            if not st.session_state.timer_running: break
            mins, secs = divmod(i, 60)
            timer_placeholder.markdown(f"<h1 style='text-align:center; color:#dc3545; font-size:6em;'>{mins:02d}:{secs:02d}</h1>", unsafe_allow_html=True)
            time.sleep(1)
        if st.session_state.timer_running:
            st.success("انتهت الجلسة بامتياز! ☕")
            st.session_state.timer_running = False

# ----------------- صفحة المساعد الذكي (Offline Prompt Generator) -----------------
elif page == "🧠 المساعد الذكي (Gemini)":
    st.header("المساعد الذكي لتقسيم المهام (وضع الأوفلاين 📴)")
    st.write("بما أن البرنامج يعمل محلياً بدون إنترنت، سيقوم المساعد بتجهيز **أمر (Prompt) احترافي ومخصص** لنسخه ولصقه في متصفحك.")
    
    task_input = st.text_area("ما هي المهمة التي تريد تقسيمها؟ (مثلاً: مراجعة الكيمياء العضوية أو حل مسائل دوائر كهربية)", height=100)
    time_input = st.text_input("ما هو الوقت المتاح لديك؟ (مثلاً: 3 أيام، 4 ساعات)")
    
    if st.button("تجهيز الأمر (Prompt) 🪄"):
        if task_input:
            prompt_text = f"""أنا طالب في الصف الثالث الثانوي أدرس الفيزياء والكيمياء والرياضيات.
لدي مهمة كبيرة أريد إنجازها وهي: "{task_input}"
الوقت المتاح لي لإنجازها هو: "{time_input if time_input else 'غير محدد'}".

بناءً على أسلوب بومودورو للتركيز (50 دقيقة تركيز و10 دقائق راحة)، أرجو تقسيم هذه المهمة إلى جدول عمل ومهام فرعية واضحة.
أريد الإجابة في شكل نقاط عملية ومباشرة يمكنني إضافتها فوراً لبرنامج إدارة المهام الخاص بي، مع دمج فترات المراجعة وحل الأسئلة والتدريبات."""
            
            st.success("✅ تم تجهيز الأمر بنجاح! اضغط على علامة النسخ في الزاوية اليمنى للمربع بالأسفل:")
            st.code(prompt_text, language="text")
            
            st.markdown("### الخطوة التالية:")
            st.markdown("""
            1. انسخ الكود من المربع أعلاه.
            2. [🌐 **اضغط هنا لفتح Google Gemini في المتصفح**](https://gemini.google.com/app)
            3. الصق النص هناك واحصل على خطتك لتقوم بإضافتها هنا في المهام.
            """)
        else:
            st.warning("يرجى إدخال المهمة أولاً.")

elif page == "🗑️ سلة المهملات":
    st.header("سلة المهملات")
    deleted_df = db.get_deleted_tasks()
    if not deleted_df.empty:
        for _, task in deleted_df.iterrows():
            st.markdown(f"**{task['title']}**")
            b1, b2 = st.columns([1, 1])
            if b1.button("♻️ استعادة", key=f"res_{task['id']}"):
                db.restore_task(task['id'])
                st.rerun()
            if b2.button("❌ حذف نهائي", key=f"hdel_{task['id']}"):
                db.hard_delete_task(task['id'])
                st.rerun()
            st.divider()
    else:
        st.info("سلة المهملات فارغة.")

elif page == "⚙️ الإعدادات":
    st.header("إدارة البيانات")
    tasks_df = db.execute_query("SELECT * FROM tasks")
    if not tasks_df.empty:
        csv = tasks_df.to_csv(index=False).encode('utf-8')
        st.download_button("📊 تصدير المهام (CSV)", data=csv, file_name='taskaty_database.csv', mime='text/csv')
    else:
        st.write("لا توجد بيانات للتصدير.")
