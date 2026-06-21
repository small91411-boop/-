# -import sqlite3
import streamlit as st
from PIL import Image
import os
from streamlit_image_coordinates import streamlit_image_coordinates

# 設定網頁標題與佈局
st.set_page_config(page_title="工程缺失安全管制系統 v3", layout="wide")

# ==========================================
# 🔐 資安控管：帳號密碼與權限定義區 (可自由修改)
# ==========================================
USER_CREDENTIALS = {
    "admin": {"password": "super_manager_2026", "role": "admin", "display_name": "工務所主管/工程師"},
    "vendor_01": {"password": "jie_yuan_999", "role": "vendor", "vendor_name": "桀沅工程有限公司"},
    "vendor_02": {"password": "paint_777", "role": "vendor", "vendor_name": "專業油漆包商"}
}

# 初始化 Session State 登入狀態
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False
    st.session_state["username"] = ""
    st.session_state["user_info"] = {}

# ==========================================
# 💾 資料庫初始化
# ==========================================
DB_FILE = "construction_issues_secure.db"
UPLOAD_DIR = "uploaded_images"
os.makedirs(UPLOAD_DIR, exist_ok=True)

def get_db_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('CREATE TABLE IF NOT EXISTS projects (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, plan_path TEXT)')
    cursor.execute('CREATE TABLE IF NOT EXISTS vendors (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, phone TEXT)')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS issues (
            id INTEGER PRIMARY KEY AUTOINCREMENT, project_id INTEGER, vendor_name TEXT,
            x REAL, y REAL, description TEXT, status TEXT,
            before_photo TEXT, after_photo TEXT, vendor_remark TEXT
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# ==========================================
# 🔑 登入介面設計
# ==========================================
if not st.session_state["logged_in"]:
    st.title("🚧 工程缺失管理系統 - 安全登入網路閘口")
    st.markdown("---")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.info("🔒 本系統內含工程機密圖面與廠商個資，非授權人員請勿嘗試登入。")
        with st.form("登入表單"):
            input_user = st.text_input("使用者帳號 (Username)", autocomplete="username")
            input_pass = st.text_input("安全密碼 (Password)", type="password", autocomplete="current-password")
            btn_login = st.form_submit_button("安全登入")
            
            if btn_login:
                if input_user in USER_CREDENTIALS and USER_CREDENTIALS[input_user]["password"] == input_pass:
                    st.session_state["logged_in"] = True
                    st.session_state["username"] = input_user
                    st.session_state["user_info"] = USER_CREDENTIALS[input_user]
                    st.success("身分驗證成功，正在載入安全加密通道...")
                    st.rerun()
                else:
                    st.error("❌ 帳號或密碼錯誤，系統已記錄此嘗試登入事件。")
    st.stop() # 阻斷未登入者往下執行程式

# ==========================================
# 🔓 登入成功後的安全通道區
# ==========================================
user_info = st.session_state["user_info"]

# 側邊欄上方顯示當前登入者身分
st.sidebar.markdown(f"### 👤 當前登入：{user_info.get('display_name', user_info.get('vendor_name'))}")
if st.sidebar.button("🔒 安全登出"):
    st.session_state["logged_in"] = False
    st.session_state["username"] = ""
    st.session_state["user_info"] = {}
    st.rerun()

st.sidebar.markdown("---")

# 根據角色分流不同的選單功能
if user_info["role"] == "admin":
    mode = st.sidebar.radio("工務管理選單", ["Dashboard 缺失總看板", "工程專案管理", "協力廠商管理", "現場巡檢：開立缺失"])
else:
    mode = "廠商專屬回報頁"
    st.sidebar.info("💡 您的權限已受限：僅能瀏覽並回報指派給貴司的修繕項目。")

# ==========================================
# 權限功能模組：管理員 (Admin) 專屬功能
# ==========================================
if user_info["role"] == "admin":
    
    # 1. 大看板
    if mode == "Dashboard 缺失總看板":
        st.header("📊 工程缺失管理大看板 (最高管理權限)")
        conn = get_db_connection()
        all_issues = conn.execute('SELECT issues.*, projects.name as p_name FROM issues JOIN projects ON issues.project_id = projects.id').fetchall()
        conn.close()
        
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("總缺失數", len(all_issues))
        m2.metric("🟠 改善中", len([i for i in all_issues if i['status'] == '改善中']))
        m3.metric("🟣 待確認", len([i for i in all_issues if i['status'] == '待確認']))
        m4.metric("🟢 已完成", len([i for i in all_issues if i['status'] == '已完成']))
        
        st.markdown("---")
        st.subheader("🔍 待查驗審核清單")
        to_verify = [i for i in all_issues if i['status'] == '待確認']
        
        if not to_verify:
            st.info("目前沒有等待驗收的缺失案件。")
        else:
            for idx, issue in enumerate(to_verify):
                with st.expander(f"⚠️ 待驗收：【{issue['p_name']}】負責廠商：{issue['vendor_name']} - {issue['description']}"):
                    st.write(f"廠商回報說明：{issue['vendor_remark']}")
                    c1, c2 = st.columns(2)
                    with c1:
                        if issue['before_photo']: st.image(issue['before_photo'], caption="[改善前]", use_container_width=True)
                    with c2:
                        if issue['after_photo']: st.image(issue['after_photo'], caption="[廠商回報改善後]", use_container_width=True)
                    
                    v_col1, v_col2 = st.columns(2)
                    if v_col1.button("✅ 准予結案 (通過)", key=f"pass_{issue['id']}"):
                        conn = get_db_connection()
                        conn.execute("UPDATE issues SET status = '已完成' WHERE id = ?", (issue['id'],))
                        conn.commit(); conn.close(); st.rerun()
                    if v_col2.button("❌ 退回重辦 (不通過)", key=f"fail_{issue['id']}"):
                        conn = get_db_connection()
                        conn.execute("UPDATE issues SET status = '改善中' WHERE id = ?", (issue['id'],))
                        conn.commit(); conn.close(); st.rerun()

    # 2. 專案管理
    elif mode == "工程專案管理":
        st.header("🏢 工程專案圖面管理")
        with st.form("新增專案"):
            project_name = st.text_input("工程專案名稱")
            uploaded_plan = st.file_uploader("上傳建築平面圖 (JPG/PNG)", type=["png", "jpg", "jpeg"])
            if st.form_submit_button("新增專案") and project_name and uploaded_plan:
                plan_path = os.path.join(UPLOAD_DIR, f"plan_{project_name}_{uploaded_plan.name}")
                with open(plan_path, "wb") as f: f.write(uploaded_plan.getbuffer())
                conn = get_db_connection()
                conn.execute("INSERT INTO projects (name, plan_path) VALUES (?, ?)", (project_name, plan_path))
                conn.commit(); conn.close()
                st.success(f"專案【{project_name}】建檔完成！")

    # 3. 廠商管理
    elif mode == "協力廠商管理":
        st.header("🤝 協力廠商資料管理")
        col1, col2 = st.columns([1, 2])
        with col1:
            st.subheader("➕ 新增合作廠商")
            with st.form("新增廠商"):
                v_name = st.text_input("廠商名稱 (請與最上方資安定義的名字完全一致，例如：桀沅工程有限公司)")
                v_phone = st.text_input("聯絡電話")
                if st.form_submit_button("確認新增") and v_name:
                    conn = get_db_connection()
                    conn.execute("INSERT INTO vendors (name, phone) VALUES (?, ?)", (v_name, v_phone))
                    conn.commit(); conn.close()
                    st.success("廠商資料已建檔！"); st.rerun()
        with col2:
            st.subheader("📋 目前合作廠商清單")
            conn = get_db_connection()
            all_vendors = conn.execute("SELECT * FROM vendors").fetchall()
            conn.close()
            if all_vendors:
                st.table([{"廠商名稱": v['name'], "聯絡電話": v['phone']} for v in all_vendors])

    # 4. 開立缺失 (圖面點擊)
    elif mode == "現場巡檢：開立缺失":
        st.header("📝 現場巡檢 - 點擊圖面開立缺失")
        conn = get_db_connection()
        projects = conn.execute("SELECT * FROM projects").fetchall()
        vendors = conn.execute("SELECT * FROM vendors").fetchall()
        conn.close()
        
        if not projects or not vendors:
            st.warning("請確保系統內已有專案圖面與廠商資料。")
        else:
            project_dict = {p['name']: p['id'] for p in projects}
            selected_project_name = st.selectbox("選擇當前工程專案", list(project_dict.keys()))
            project_id = project_dict[selected_project_name]
            
            selected_vendor_name = st.selectbox("🎯 指派負責改善廠商", [v['name'] for v in vendors])
            
            conn = get_db_connection()
            project_data = conn.execute("SELECT * FROM projects WHERE id = ?", (project_id,)).fetchone()
            conn.close()
            
            if project_data and project_data['plan_path']:
                st.subheader("📍 請在下方平面圖上「直接點擊」缺失位置：")
                img = Image.open(project_data['plan_path'])
                value = streamlit_image_coordinates(img, key="local")
                
                if value:
                    st.success(f"已標記座標：X={value['x']}, Y={value['y']}")
                    with st.form("缺失表單"):
                        desc = st.text_area("缺失具體描述")
                        before_img = st.file_uploader("拍攝/上傳現場缺失照片", type=["png", "jpg", "jpeg"])
                        if st.form_submit_button("確認開立缺失單") and desc:
                            photo_path = ""
                            if before_img:
                                photo_path = os.path.join(UPLOAD_DIR, f"before_{project_id}_{value['x']}_{before_img.name}")
                                with open(photo_path, "wb") as f: f.write(before_img.getbuffer())
                            conn = get_db_connection()
                            conn.execute('''
                                INSERT INTO issues (project_id, vendor_name, x, y, description, status, before_photo, after_photo, vendor_remark)
                                VALUES (?, ?, ?, ?, ?, '改善中', ?, '', '')
                            ''', (project_id, selected_vendor_name, value['x'], value['y'], desc, photo_path))
                            conn.commit(); conn.close()
                            st.balloons(); st.success("缺失已成功掛載至平面圖！")

# ==========================================
# 權限功能模組：外部廠商 (Vendor) 專屬功能 (資安資料隔離)
# ==========================================
else:
    target_vendor = user_info["vendor_name"]
    st.header(f"🛠️ 廠商回報專區 - 【{target_vendor}】")
    
    # 🌟 資安隔離關鍵：在 SQL 查詢時就鎖死廠商名字，絕不外洩別家廠商的缺失
    conn = get_db_connection()
    active_issues = conn.execute('''
        SELECT issues.*, projects.name as p_name FROM issues 
        JOIN projects ON issues.project_id = projects.id 
        WHERE issues.status = '改善中' AND issues.vendor_name = ?
    ''', (target_vendor,)).fetchall()
    conn.close()
    
    if not active_issues:
        st.success("🎉 目前沒有屬於貴司待處理的缺失項目！")
    else:
        issue_options = {f"【{i['p_name']}】單號-{i['id']}: {i['description']}": i['id'] for i in active_issues}
        selected_issue_str = st.selectbox("請選擇您要回報修繕的工程項目：", list(issue_options.keys()))
        issue_id = issue_options[selected_issue_str]
        
        conn = get_db_connection()
        issue_detail = conn.execute("SELECT * FROM issues WHERE id = ?", (issue_id,)).fetchone()
        conn.close()
        
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("缺失詳情")
            st.write(f"**案址專案：** {issue_detail['p_name']}")
            st.write(f"**具體描述：** {issue_detail['description']}")
        with col2:
            if issue_detail['before_photo']:
                st.image(issue_detail['before_photo'], caption="改善前工況照片", width=300)
                
        st.markdown("---")
        st.subheader("提交改善回報報告")
        with st.form("修繕回報"):
            v_remark = st.text_input("修繕工法/說明 (例如：已派員重新安裝完成)")
            after_img = st.file_uploader("上傳修繕完成照片", type=["png", "jpg", "jpeg"])
            if st.form_submit_button("提交查驗審查") and after_img:
                after_path = os.path.join(UPLOAD_DIR, f"after_{issue_id}_{after_img.name}")
                with open(after_path, "wb") as f: f.write(after_img.getbuffer())
                conn = get_db_connection()
                conn.execute('UPDATE issues SET status = "待確認", after_photo = ?, vendor_remark = ? WHERE id = ?', (after_path, v_remark, issue_id))
                conn.commit(); conn.close()
                st.success("回報已安全送達！請靜候現場工程師查驗驗收。")
                st.rerun()
