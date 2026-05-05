import streamlit as st
import pandas as pd
import google.generativeai as genai
from Bio import Entrez
import datetime
import os

# --- 1. ページ設定 ---
st.set_page_config(page_title="MedTech IP-Engine", layout="wide")
st.title("🚀 医学×工学 知財統合プラットフォーム (v2.0)")

# --- 2. API・モデル自動選択設定 ---
Entrez.email = "t-yoshida@kmu.ac.jp" 

if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
else:
    st.error("Secretsに GEMINI_API_KEY を設定してください。")

@st.cache_resource
def get_ai_model():
    try:
        # 稼働中の最新モデルを自動検知
        available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        target = next((m for m in available_models if "flash" in m), available_models[0])
        return genai.GenerativeModel(target)
    except:
        return genai.GenerativeModel('gemini-1.5-flash')

model = get_ai_model()
DATA_FILE = 'medical_needs_data.csv'

# --- 3. データ管理関数 ---
def load_data():
    if os.path.exists(DATA_FILE):
        return pd.read_csv(DATA_FILE)
    return pd.DataFrame(columns=['Date', 'Category', 'Medical_Need', 'Engineering_Spec', 'Source'])

def save_data(df):
    df.to_csv(DATA_FILE, index=False)

# --- 4. 知識収集ロジック (PubMed + AI) ---
def fetch_and_analyze(query):
    handle = Entrez.esearch(db="pubmed", term=query, retmax=5)
    record = Entrez.read(handle)
    ids = record["IdList"]
    
    results = []
    for pmid in ids:
        summary_handle = Entrez.esummary(db="pubmed", id=pmid)
        summary = Entrez.read(summary_handle)
        title = summary[0]['Title']
        
        # AIによる「工学的課題」の抽出
        prompt = f"""
        以下の論文タイトルから、泌尿器科デバイス開発（特に吸引・屈曲・カメラ統合）に関する
        1.未解決の医学的ニーズ 2.必要な工学的仕様 を専門的に抽出してください。
        論文名: {title}
        """
        response = model.generate_content(prompt)
        results.append({
            'Date': datetime.date.today(),
            'Category': 'AI収集(PubMed)',
            'Medical_Need': title,
            'Engineering_Spec': response.text,
            'Source': f"PMID: {pmid}"
        })
    return results

# --- 5. UI（タブ構成） ---
tab1, tab2, tab3 = st.tabs(["基本データベース", "Web・論文インテリジェンス", "AI知財コンサル"])

# --- Tab 1: 現場の知見を登録 ---
with tab1:
    col1, col2 = st.columns([1, 2])
    with col1:
        st.subheader("📌 現場の気づきを登録")
        cat = st.selectbox("カテゴリー", ["泌尿器科", "手術支援ロボット", "内視鏡装置", "その他"])
        need = st.text_area("医学的ニーズ（ボヤキ・不満）")
        spec = st.text_area("工学的仕様（アイデア・数値）")
        if st.button("データベースに本登録"):
            new_data = pd.DataFrame([[datetime.date.today(), cat, need, spec, "Manual"]], 
                                    columns=load_data().columns)
            df = pd.concat([load_data(), new_data], ignore_index=True)
            save_data(df)
            st.success("登録完了！")
    
    with col2:
        st.subheader("🔍 蓄積されたニーズ一覧")
        st.dataframe(load_data(), use_container_width=True)

# --- 修正版：Tab 2 (Web知識の収集) ---
with tab2:
    st.subheader("🌐 最新知見のバルク収集")
    search_q = st.text_input("検索キーワード", value="Ureteral access sheath suction")
    
    # 検索結果を保持するための「記憶スペース」を準備
    if 'search_results' not in st.session_state:
        st.session_state.search_results = []

    if st.button("最新論文・技術トレンドを解析"):
        with st.spinner("AIが解析中..."):
            # 検索結果を「記憶スペース」に保存
            st.session_state.search_results = fetch_and_analyze(search_q)

    # 記憶スペースにデータがある場合のみ表示
    if st.session_state.search_results:
        for i, info in enumerate(st.session_state.search_results):
            with st.container():
                st.info(f"**{info['Medical_Need']}**")
                st.write(info['Engineering_Spec'])
                
                # keyに番号(i)を振ることで、ボタンの押し間違いを防ぐ
                if st.button(f"これを保存する", key=f"save_{i}"):
                    current_df = load_data()
                    # 重複チェック（同じ論文を何度も保存しない）
                    if not (current_df['Source'] == info['Source']).any():
                        new_df = pd.concat([current_df, pd.DataFrame([info])], ignore_index=True)
                        save_data(new_df)
                        st.success(f"「{info['Source']}」をデータベースに保存しました！")
                    else:
                        st.warning("この情報はすでに保存されています。")
                st.divider()

# --- 修正版：Tab 3 (AI知財コンサル) ---
with tab3:
    st.subheader("🤖 AI知財壁打ちモード")
    
    # データベースの最新状態を反映させる
    df_for_consult = load_data()
    
    if df_for_consult.empty:
        st.warning("データベースが空です。Tab 1 か Tab 2 で情報を蓄積してください。")
    else:
        st.write(f"現在、{len(df_for_consult)} 件の知見に基づいたアドバイスが可能です。")
        knowledge_base = df_for_consult.to_string()
        
        user_q = st.text_input("質問例：Project SUIの屈曲固定について、過去のデータから課題を教えて")
        
        if user_q:
            consult_prompt = f"以下の知識ベースを元に回答してください。\n\n{knowledge_base}\n\n質問：{user_q}"
            with st.spinner("思考中..."):
                answer = model.generate_content(consult_prompt)
                st.markdown(f"### AIのアドバイス\n{answer.text}")
