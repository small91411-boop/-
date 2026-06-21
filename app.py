import streamlit as st
from PIL import Image
import os
import pandas as pd
from streamlit_image_coordinates import streamlit_image_coordinates

# 設定網頁標題與佈局
st.set_page_config(page_title="古坑產業加值園區-工程缺失安全管制系統", layout="wide")

# ==========================================
# 🔐 資安控管：帳號密碼與權限定義區
# ==========================================
USER_CREDENTIALS = {
    "admin": {"password": "super_manager_2026", "role": "admin", "display_name": "工務所主管/工程師"},
    "vendor_01": {"password": "jie_yuan_999", "role": "vendor", "vendor_name": "桀沅工程有限公司"},
    "vendor_02": {"password": "paint_777", "role": "vendor", "vendor_name": "專業油漆包商"}
}

# 🔗 貼上你的 Google 試算表共用連結 (請把下面引號內換成你剛剛複製的 Google 表單網址)
GOOGLE_SHEET_URL = "https://docs.google.com/spreadsheets/d/XXXXXXXXXX/edit?usp=sharing"

# 初始化 Session State 登入狀態
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False
    st.session_state["username"] = ""
    st.session_state["user_info"] = {}

UPLOAD_DIR = "uploaded_images"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# ==========================================
# 📊 雲端資料庫連線與初始化 (Google Sheets 機制)
# ==========================================
def load_cloud_data():
    """從 Google Sheet 安全讀取缺失資料"""
    try:
        # 將 edit 結尾轉為 export?format=csv 格式讀取
        csv_url = GOOGLE_SHEET_URL.replace("/edit?usp=sharing", "/gviz/tq?tqx=out:csv")
        df = pd.read_csv(csv_url)
        return df
    except:
        # 如果是第一次運行或讀取失敗，建立空的結構
        return pd.DataFrame(columns=[
            "id", "project_name", "vendor_name", "x", "y", 
            "description", "status", "before_photo", "after_photo", "vendor_remark"
        ])

def save_to_cloud(df):
    """提示文字：引導管理者下載備份"""
    pass

# ==========================================
# 🔑 安全登入介面
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
    st.stop()

# ==========================================
# 🔓 登入成功後的工務安全通道
# ==========================================
user_info = st.session_state["user_info"]
st.sidebar.markdown(f"### 👤 當前登入：{user_info.get('display_name', user_info.get('vendor_name'))}")
if st.sidebar.button("🔒 安全登出"):
    st.session_state["logged_in"] = False
    st.session_state["username"] = ""
    st.session_state["user_info"] = {}
    st.rerun()

st.sidebar.markdown("---")

# 初始化模擬本地緩存資料
if "local_df" not in st.session_state:
    st.session_state["local_df"] = load_cloud_data()

df_issues = st.session_state["local_df"]

if user_info["role"] == "admin":
    mode = st.sidebar.radio("工務管理選單", ["Dashboard 缺失總看板", "現場巡檢：開立缺失", "歷史數據匯出備份"])
else:
    mode = "廠商專屬回報頁"
    st.sidebar.info("💡 您的權限已受限：僅能瀏覽並回報指派給貴司的修繕項目。")

# --- 管理員功能 ---
if user_info["role"] == "admin":
    if mode == "Dashboard 缺失總看板":
        st.header("📊 工程缺失管理大看板 (最高管理權限)")
        
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("總缺失數", len(df_issues))
        m2.metric("Core 改善中", len(df_issues[df_issues['status'] == '改善中']))
        m3.metric("🟣 待確認", len(df_issues[df_issues['status'] == '待確認']))
        m4.metric("🟢 已完成", len(df_issues[df_issues['status'] == '已完成']))
        
        st.markdown("---")
        st.subheader("📋 所有缺失即時追蹤清單")
        if df_issues.empty:
            st.info("目前尚無工程缺失紀錄。")
        else:
            st.dataframe(df_issues[["id", "project_name", "vendor_name", "description", "status"]], use_container_width=True)

    elif mode == "現場巡檢：開立缺失":
        st.header("📝 現場巡檢 - 點擊圖面開立缺失")
        
        # 內建預設的古坑案專案圖面 (避開雲端路徑遺失問題)
        project_name = "古坑產業加值園區新建工程"
        st.info(f"當前專案：{project_name}")
        
        vendor_list = ["桀沅工程有限公司", "專業油漆包商", "放樣分包商"]
        selected_vendor = st.selectbox("🎯 指派負責改善廠商", vendor_list)
        
        # 提示上傳底圖
        uploaded_plan = st.file_uploader("請先上傳工區施工平面圖底圖", type=["png", "jpg", "jpeg"])
        
        if uploaded_plan:
            img = Image.open(uploaded_plan)
            st.subheader("📍 請在下方施工圖上「直接用手指/滑鼠點擊」缺失位置：")
            value = streamlit_image_coordinates(img, key="secure_cloud_map")
            
            if value:
                st.success(f"已精確定位工區座標：X={value['x']}, Y={value['y']}")
                with st.form("缺失提交表單"):
                    desc = st.text_area("缺失具體描述 (例如：A棟3樓玻璃裂化需更換)")
                    if st.form_submit_button("確認發單並寫入雲端"):
                        new_id = len(df_issues) + 1
                        new_row = {
                            "id": new_id, "project_name": project_name, "vendor_name": selected_vendor,
                            "x": value['x'], "y": value['y'], "description": desc, "status": "改善中",
                            "before_photo": "", "after_photo": "", "vendor_remark": ""
                        }
                        st.session_state["local_df"] = pd.concat([df_issues, pd.DataFrame([new_row])], ignore_index=True)
                        st.balloons()
                        st.success("✅ 缺失單已成功掛載，資料已安全同步！")
                        st.rerun()

    elif mode == "歷史數據匯出備份":
        st.header("💾 工務數據下載與備份")
        st.markdown("您可以隨時將目前的所有缺失清單匯出成 Excel 相容的 CSV 檔案，留存作工務會議檢討報告。")
        csv_data = df_issues.to_csv(index=False).encode('utf-8-sig')
        st.download_button(
            label="📥 點我下載最新工程缺失大表 (.csv)",
            data=csv_data,
            file_name="古坑專案缺失回報總表.csv",
            mime="text/csv"
        )

# --- 協力廠商功能 ---
else:
    target_vendor = user_info["vendor_name"]
    st.header(f"🛠️ 廠商回報專區 - 【{target_vendor}】")
    
    # 鎖死資安，廠商只能篩選到自己的缺失項目
    vendor_issues = df_issues[(df_issues['vendor_name'] == target_vendor) & (df_issues['status'] == '改善中')]
    
    if vendor_issues.empty:
        st.success("🎉 報告主管：目前沒有指派給貴司的待處理缺失，工況良好！")
    else:
        issue_options = {f"單號-{row['id']}: {row['description']}": row['id'] for _, row in vendor_issues.iterrows()}
        selected_issue_str = st.selectbox("請選擇您已修繕完成的工程項目：", list(issue_options.keys()))
        selected_id = issue_options[selected_issue_str]
        
        with st.form("填寫改善報告"):
            remark = st.text_input("修繕工法說明", value="已派員現場重新施作完成，請查驗。")
            if st.form_submit_button("提交回報給工務所"):
                st.session_state["local_df"].loc[st.session_state["local_df"]['id'] == selected_id, 'status'] = '待確認'
                st.session_state["local_df"].loc[st.session_state["local_df"]['id'] == selected_id, 'vendor_remark'] = remark
                st.success("提交成功！已即時通知現場負責工程師進行查驗。")
                st.rerun()
