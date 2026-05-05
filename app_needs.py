import streamlit as st
import pandas as pd
import google.generativeai as genai
from Bio import Entrez
import datetime
import os
import time

# --- 1. ページ設定とタイトル ---
st.set_page_config(page_title="Urology Intel Engine", layout="wide")
st.title("🛡️ 泌尿器科インテリジェンス・エンジン (Global Scout Mode)")

# --- 2. API・モデル自動選択 ---
if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
else:
    st.error("Secretsに GEMINI_API_KEY を設定してください。")

@st.cache_resource
def get_ai_model():
    try:
        available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        target = next((m for m in available_models if "flash" in m), available_models[0])
        return genai.GenerativeModel(target)
    except:
        return genai.GenerativeModel('gemini-1.5-flash')

model = get_ai_model()
DATA_FILE = 'urology_intelligence_db.csv'

# --- 3. データ管理ロジック ---
def load_data():
    columns = ['Date', 'Source_Type', 'Reliability', 'Clinical_Need', 'Technical_Insight', 'Source_Ref']
    if os.path.exists(DATA_FILE):
        df = pd.read_csv(DATA_FILE)
        for col in columns:
            if col not in df.columns: df[col] = "N/A"
        return df[columns]
    return pd.DataFrame(columns=columns)

def save_data(df):
    df.to_csv(DATA_FILE, index=False)

# --- 4. 改良版：一括スカウト関数 ---
def automated_scout(domain_query):
    full_query = f"({domain_query}) AND (2025:2026[pdat])"
    handle = Entrez.esearch(db="pubmed", term=full_query, retmax=5) 
    ids = Entrez.read(handle)["IdList"]
    
    if not ids:
        return []

    # 論文タイトルをリスト化
    paper_list = []
    for pmid in ids:
        summary = Entrez.read(Entrez.esummary(db="pubmed", id=pmid))[0]
        paper_list.append(f"PMID:{pmid} | タイトル: {summary['Title']}")
    
    # 5件まとめてAIに投げる
    batch_prompt = f"""
    あなたは泌尿器科のKOL(MD)かつ工学博士(PhD)です。
    以下の論文リスト（最大5件）を読み、それぞれについて「医学的ニーズ」と「工学的ヒント」を専門的に抽出してください。
    
    {chr(10).join(paper_list)}
    
    回答は以下のJSON形式のリストで返してください（解析できないものは含めないでください）:
    [
      {{"Source_Ref": "PMID:xxxx", "Clinical_Need": "タイトル...", "Technical_Insight": "解析結果..."}}
    ]
    """
    
    results = []
    try:
        # 安全設定を緩和（医学用語による誤作動防止）
        response = model.generate_content(
            batch_prompt,
            safety_settings=[
                {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"}
            ]
        )
        
        # AIの回答をパースして整形
        import json
        import re
        # JSON部分を抽出
        json_match = re.search(r'\[.*\]', response.text, re.DOTALL)
        if json_match:
            raw_results = json.loads(json_match.group())
            for r in raw_results:
                results.append({
                    'Date': datetime.date.today(),
                    'Source_Type': 'Academic/Congress',
                    'Reliability': 'High (PubMed Verified)',
                    'Clinical_Need': r['Clinical_Need'],
                    'Technical_Insight': r['Technical_Insight'],
                    'Source_Ref': r['Source_Ref']
                })
    except Exception as e:
        st.error(f"解析中にエラーが発生しました: {e}")
        
    return results

# --- 5. UI構成 ---
tab1, tab2, tab3 = st.tabs(["📊 統合インテリジェンスDB", "📡 自動スカウト", "🧠 戦略コンサル"])

with tab1:
    st.subheader("🗂️ 蓄積された泌尿器科知見")
    st.dataframe(load_data(), use_container_width=True)

with tab2:
    st.subheader("🔭 自動情報収集・解析")
    area = st.multiselect("重点監視領域", ["尿路結石", "癌 (UTUC/膀胱/前立腺)", "レーザー工学", "ロボット手術"], default=["尿路結石", "癌 (UTUC/膀胱/前立腺)"])
    
    if st.button("最新エビデンスを巡回"):
        with st.spinner("AIがまとめて解析中..."):
            query = " OR ".join(area)
            st.session_state.scout_results = automated_scout(query)
            if st.session_state.scout_results:
                st.success(f"{len(st.session_state.scout_results)} 件の情報を抽出しました。")
            else:
                st.warning("情報を抽出できませんでした。")

    if 'scout_results' in st.session_state:
        for i, res in enumerate(st.session_state.scout_results):
            with st.expander(f"📌 {res['Clinical_Need']}"):
                st.write(res['Technical_Insight'])
                if st.button("これをDBに本登録", key=f"reg_{i}"):
                    df = pd.concat([load_data(), pd.DataFrame([res])], ignore_index=True)
                    save_data(df)
                    st.toast("保存完了！")

with tab3:
    st.subheader("🎓 専門家対話モード")
    current_df = load_data()
    if not current_df.empty:
        db_text = current_df.to_string()
        user_input = st.text_input("質問を入力:")
        if user_input:
            prompt = f"知識ベース:\n{db_text}\n\n質問: {user_input}\n\n泌尿器科医(MD)かつ工学博士(PhD)として回答してください。"
            st.write(model.generate_content(prompt).text)
    else:
        st.info("データがありません。")
