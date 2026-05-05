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

# --- Tab 2: Web知識の「ざっと」収集 ---
with tab2:
    st.subheader("🌐 最新知見のバルク収集")
    search_q = st.text_input("検索キーワード（例: Ureteral access sheath suction camera）")
    if st.button("最新論文・技術トレンドを解析"):
        with st.spinner("AIがPubMedと最新トレンドを解析中..."):
            collected_info = fetch_and_analyze(search_q)
            for info in collected_info:
                st.info(f"**{info['Medical_Need']}**")
                st.write(info['Engineering_Spec'])
                if st.button(f"これを保存: {info['Source'][:10]}", key=info['Source']):
                    df = pd.concat([load_data(), pd.DataFrame([info])], ignore_index=True)
                    save_data(df)
                    st.toast("保存しました！")

# --- Tab 3: AI知財コンサル（ぱっと引き出す） ---
with tab3:
    st.subheader("🤖 AI知財壁打ちモード")
    st.write("これまでに蓄積したデータに基づいて、AIが開発のアドバイスをします。")
    
    knowledge_base = load_data().to_string()
    user_q = st.text_input("質問例：ワイヤー屈曲固定のアイデアについて、過去のメモと似た論文はあった？")
    
    if user_q:
        consult_prompt = f"""
        あなたは医療機器開発の弁理士かつ工学博士です。
        以下の知識ベースを元に、ユーザーの質問に答えてください。
        
        【知識ベース】
        {knowledge_base}
        
        【質問】
        {user_q}
        """
        with st.spinner("思考中..."):
            answer = model.generate_content(consult_prompt)
            st.markdown(f"### AIのアドバイス\n{answer.text}")
