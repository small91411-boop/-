import streamlit as st
from PIL import Image
import os
import pandas as pd
from streamlit_image_coordinates import streamlit_image_coordinates

# 設定網頁標題與佈局
st.set_page_config(page_title="工程缺失安全管制系統 v4", layout="wide")

# ==========================================
# 🔐 資安控管：帳號密碼與權限定義區
# ==========================================
USER_CREDENTIALS = {
    "admin": {"password": "super_manager_2026", "role": "admin", "display_name": "工務所主管/工程師"},
    "vendor_01": {"password": "jie_yuan_999", "role": "vendor", "vendor_name": "桀沅工程有限公司"},
    "vendor_02": {"password": "paint_777", "role": "vendor", "vendor_name": "專業油漆包商"}
}

# 🔗 雲端資料庫串接：請將下方引號內替換為您複製的 Google 試算表連結
GOOGLE_SHEET_URL = "https://docs.google.com/spreadsheets/d/1Vcu1S4L500DbBuHAyjxNrRvoui-ovx1WEBjyg6ABogY/edit?usp=sharing"

# 初始化 Session State 登入狀態
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False
    st.session_state["username"] = ""
    st.session_state["user_info"] = {}

UPLOAD_DIR = "uploaded_images"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# ==========================================
# 📊 雲端資料庫讀寫函式 (維持選單運作)
# ==========================================
def get_cloud_data(sheet_name, columns):
    """安全讀取雲端特定工作表資料"""
    try:
        # 將連結轉換為 CSV 下載格式並指定工作表
        base_url = GOOGLE_SHEET_URL.split("/edit")[0]
        csv_url = f"{base_url}/gviz/tq?tqx=out:csv&sheet={sheet_name}"
        df = pd.read_csv(csv_url)
        # 確保必要的欄位都存在
        for col in columns:
            if col not in df.columns:
                df[col] = ""
        return df[columns]
    except:
        return pd.DataFrame(columns=columns)

# 初始化/讀取雲端資料
if st.session_state["logged_in"]:
    if "df_projects" not in st.session_state:
        st.session_state["df_projects"] = get_cloud_data("projects", ["id", "name", "plan_path"])
    if "df_vendors" not in st.session_state:
        st.session_state["df_vendors"] = get_cloud_data("vendors", ["id", "name", "phone"])
    if "df_issues" not in st.session_state:
        st.session_state["df_issues"] = get_cloud_data("issues", [
            "id", "project_id", "vendor_name", "x", "y", 
            "description", "status", "before_photo", "after_photo", "vendor_remark"
        ])

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
# 🔓 登入成功後的安全通道區（選單功能全回復）
# ==========================================
user_info = st.session_state["user_info"]

st.sidebar.markdown(f"### 👤 當前登入：{user_info.get('display_name', user_info.get('vendor_name'))}")
if st.sidebar.button("🔒 安全登出"):
    st.session_state["logged_in"] = False
    st.session_state["username"] = ""
    st.session_state.clear()
    st.rerun()

st.sidebar.markdown("---")

# 權限分流選單 (完全還原五大模組)
if user_info["role"] == "admin":
    mode = st.sidebar.radio("工務管理選單", [
        "Dashboard 缺失總看板", 
        "🏢 工程專案管理", 
        "🤝 協力廠商管理", 
        "現場巡檢：開立缺失"
    ])
else:
    mode = "廠商專屬回報頁"
    st.sidebar.info("💡 您的權限已受限：僅能瀏覽並回報指派給貴司的修繕項目。")

# --- 1. Dashboard 缺失總看板 ---
if mode == "Dashboard 缺失總看板" and user_info["role"] == "admin":
    st.header("📊 工程缺失管理大看板 (最高管理權限)")
    df_i = st.session_state["df_issues"]
    df_p = st.session_state["df_projects"]
    
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("總缺失數", len(df_i))
    m2.metric("🟠 改善中", len(df_i[df_i['status'] == '改善中']))
    m3.metric("🟣 待確認", len(df_i[df_i['status'] == '待確認']))
    m4.metric("🟢 已完成", len(df_i[df_i['status'] == '已完成']))
    
    st.markdown("---")
    st.subheader("🔍 待查驗審核清單")
    to_verify = df_i[df_i['status'] == '待確認']
    
    if to_verify.empty:
        st.info("目前沒有等待驗收的缺失案件。")
    else:
        for idx, row in to_verify.iterrows():
            p_name = df_p[df_p['id'] == row['project_id']]['name'].values
            p_name_str = p_name[0] if len(p_name) > 0 else "未知專案"
            with st.expander(f"⚠️ 待驗收：【{p_name_str}】負責廠商：{row['vendor_name']} - {row['description']}"):
                st.write(f"廠商回報說明：{row['vendor_remark']}")
                c1, c2 = st.columns(2)
                with c1:
                    if row['before_photo']: st.image(row['before_photo'], caption="[改善前]", width=300)
                with c2:
                    if row['after_photo']: st.image(row['after_photo'], caption="[廠商回報改善後]", width=300)
                
                v_col1, v_col2 = st.columns(2)
                if v_col1.button("✅ 准予結案 (通過)", key=f"pass_{row['id']}"):
                    st.session_state["df_issues"].loc[st.session_state["df_issues"]['id'] == row['id'], 'status'] = '已完成'
                    st.success("已更新為結案狀態，請記得手動更新雲端試算表存檔。")
                    st.rerun()
                if v_col2.button("❌ 退回重辦 (不通過)", key=f"fail_{row['id']}"):
                    st.session_state["df_issues"].loc[st.session_state["df_issues"]['id'] == row['id'], 'status'] = '改善中'
                    st.rerun()

# --- 2. 工程專案管理 (回復) ---
elif mode == "🏢 工程專案管理" and user_info["role"] == "admin":
    st.header("🏢 工程專案圖面管理")
    with st.form("新增專案"):
        project_name = st.text_input("工程專案名稱")
        uploaded_plan = st.file_uploader("上傳建築平面圖 (JPG/PNG)", type=["png", "jpg", "jpeg"])
        if st.form_submit_button("確認新增專案") and project_name and uploaded_plan:
            plan_path = os.path.join(UPLOAD_DIR, f"plan_{project_name}_{uploaded_plan.name}")
            with open(plan_path, "wb") as f: f.write(uploaded_plan.getbuffer())
            
            new_id = len(st.session_state["df_projects"]) + 1
            new_row = {"id": new_id, "name": project_name, "plan_path": plan_path}
            st.session_state["df_projects"] = pd.concat([st.session_state["df_projects"], pd.DataFrame([new_row])], ignore_index=True)
            st.success(f"專案【{project_name}】已成功在本機記憶體建檔！")
            st.info("💡 提示：請定時點擊側邊欄匯出按份，或將數據貼回您的 Google Sheet 的 projects 分頁中。")
            st.rerun()
            
    st.subheader("📋 目前已登錄之工程專案")
    st.dataframe(st.session_state["df_projects"], use_container_width=True)

# --- 3. 協力廠商管理 (回復) ---
elif mode == "🤝 協力廠商管理" and user_info["role"] == "admin":
    st.header("🤝 協力廠商資料管理")
    col1, col2 = st.columns([1, 2])
    with col1:
        st.subheader("➕ 新增合作廠商")
        with st.form("新增廠商"):
            v_name = st.text_input("廠商名稱 (請與程式碼內的資安名稱一致)")
            v_phone = st.text_input("聯絡電話")
            if st.form_submit_button("確認新增"):
                new_id = len(st.session_state["df_vendors"]) + 1
                new_row = {"id": new_id, "name": v_name, "phone": v_phone}
                st.session_state["df_vendors"] = pd.concat([st.session_state["df_vendors"], pd.DataFrame([new_row])], ignore_index=True)
                st.success("廠商資料已建檔！")
                st.rerun()
    with col2:
        st.subheader("📋 目前合作廠商清單")
        st.dataframe(st.session_state["df_vendors"], use_container_width=True)

# --- 4. 現場巡檢：開立缺失 ---
elif mode == "現場巡檢：開立缺失" and user_info["role"] == "admin":
    st.header("📝 現場巡檢 - 點擊圖面開立缺失")
    df_p = st.session_state["df_projects"]
    df_v = st.session_state["df_vendors"]
    
    if df_p.empty:
        st.warning("請先前往『🏢 工程專案管理』上傳並建立專案平面圖面。")
    else:
        project_dict = {row['name']: row['id'] for _, row in df_p.iterrows()}
        selected_project_name = st.selectbox("選擇當前工程專案", list(project_dict.keys()))
        project_id = project_dict[selected_project_name]
        
        # 整合動態與靜態廠商清單
        vendor_options = list(USER_CREDENTIALS.keys())
        if not df_v.empty:
            vendor_options = list(set(vendor_options + df_v['name'].tolist()))
            
        selected_vendor_name = st.selectbox("🎯 指派負責改善廠商", vendor_options)
        
        project_data = df_p[df_p['id'] == project_id].iloc[0]
        
        if os.path.exists(project_data['plan_path']):
            img = Image.open(project_data['plan_path'])
            st.subheader("📍 請在下方平面圖上「直接點擊」缺失位置：")
            value = streamlit_image_coordinates(img, key="v4_map")
            
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
                        
                        new_id = len(st.session_state["df_issues"]) + 1
                        new_row = {
                            "id": new_id, "project_id": project_id, "vendor_name": selected_vendor_name,
                            "x": value['x'], "y": value['y'], "description": desc, "status": "改善中",
                            "before_photo": photo_path, "after_photo": "", "vendor_remark": ""
                        }
                        st.session_state["df_issues"] = pd.concat([st.session_state["df_issues"], pd.DataFrame([new_row])], ignore_index=True)
                        st.balloons(); st.success("缺失已成功掛載至平面圖！")
                        st.rerun()
        else:
            st.error("找不到專案底圖檔案，請重新至專案管理上傳。")

# --- 5. 廠商專屬回報頁 ---
elif mode == "廠商專屬回報頁":
    target_vendor = user_info.get("vendor_name", st.session_state["username"])
    st.header(f"🛠️ 廠商回報專區 - 【{target_vendor}】")
    
    df_i = st.session_state["df_issues"]
    vendor_issues = df_i[(df_i['vendor_name'] == target_vendor) & (df_i['status'] == '改善中')]
    
    if vendor_issues.empty:
        st.success("🎉 目前沒有屬於貴司待處理的缺失項目！")
    else:
        issue_options = {f"單號-{row['id']}: {row['description']}": row['id'] for _, row in vendor_issues.iterrows()}
        selected_issue_str = st.selectbox("請選擇您要回報修繕的工程項目：", list(issue_options.keys()))
        selected_id = issue_options[selected_issue_str]
        
        issue_detail = df_i[df_i['id'] == selected_id].iloc[0]
        
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("缺失詳情")
            st.write(f"**具體描述：** {issue_detail['description']}")
        with col2:
            if issue_detail['before_photo'] and os.path.exists(issue_detail['before_photo']):
                st.image(issue_detail['before_photo'], caption="改善前工況照片", width=250)
                
        st.markdown("---")
        with st.form("修繕回報"):
            v_remark = st.text_input("修繕工法/說明", value="已派員重新處理完成。")
            after_img = st.file_uploader("上傳修繕完成照片", type=["png", "jpg", "jpeg"])
            if st.form_submit_button("提交查驗審查") and after_img:
                after_path = os.path.join(UPLOAD_DIR, f"after_{selected_id}_{after_img.name}")
                with open(after_path, "wb") as f: f.write(after_img.getbuffer())
                
                st.session_state["df_issues"].loc[st.session_state["df_issues"]['id'] == selected_id, 'status'] = '待確認'
                st.session_state["df_issues"].loc[st.session_state["df_issues"]['id'] == selected_id, 'after_photo'] = after_path
                st.session_state["df_issues"].loc[st.session_state["df_issues"]['id'] == selected_id, 'vendor_remark'] = v_remark
                st.success("回報已送達！請靜候現場工程師進行查驗。")
                st.rerun()

# 頁尾提供管理者一鍵下載備份，以應對雲端重置
if user_info["role"] == "admin":
    st.sidebar.markdown("---")
    st.sidebar.markdown("💾 **最高管理員備份專區**")
    if st.sidebar.button("📥 下載最新數據備份檔案"):
        st.info("請至右側畫面下載備份檔案")
        st.header("📥 導出當前全系統數據")
        c1, c2, c3 = st.columns(3)
        c1.download_button("下載專案清單 (CSV)", st.session_state["df_projects"].to_csv(index=False).encode('utf-8-sig'), "projects.csv", "text/csv")
        c2.download_button("下載廠商清單 (CSV)", st.session_state["df_vendors"].to_csv(index=False).encode('utf-8-sig'), "vendors.csv", "text/csv")
        c3.download_button("下載缺失紀錄 (CSV)", st.session_state["df_issues"].to_csv(index=False).encode('utf-8-sig'), "issues.csv", "text/csv")
