import streamlit as st
import pandas as pd
import google.generativeai as genai
from Bio import Entrez
import datetime
import os
import time
import json
import re

# --- 1. ページ設定とタイトル ---
st.set_page_config(page_title="Urology Intel Engine v4", layout="wide")
st.title("🛡️ 泌尿器科インテリジェンス・エンジン (Hybrid AI Mode)")

# --- 2. 各AIの設定 ---
# Geminiの設定
if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
else:
    st.error("Secretsに GEMINI_API_KEY を設定してください。")

# OpenAIの設定（予備）
HAS_OPENAI = "OPENAI_API_KEY" in st.secrets

@st.cache_resource
def get_gemini_model():
    try:
        available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        target = next((m for m in available_models if "flash" in m), available_models[0])
        return genai.GenerativeModel(target)
    except:
        return genai.GenerativeModel('gemini-1.5-flash')

model_gemini = get_gemini_model()
DATA_FILE = 'urology_intelligence_db.csv'

# --- 3. バックアップ用GPT関数 ---
def ask_gpt(prompt):
    import openai
    client = openai.OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content

# --- 4. 統合解析ロジック（Gemini優先、失敗時にGPTへ） ---
def dual_ai_generate(prompt):
    try:
        # 第一選択：Gemini
        response = model_gemini.generate_content(
            prompt,
            safety_settings=[
                {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"}
            ]
        )
        return response.text
    except Exception as e:
        if HAS_OPENAI:
            st.warning("Geminiの制限により、GPT-4oで代替解析を開始します...")
            return ask_gpt(prompt)
        else:
            st.error(f"解析エラーが発生しました。予備のAPIキーが設定されていません: {e}")
            return None

# --- 5. データ管理 ---
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

# --- 6. スカウト関数 ---
def automated_scout(domain_query):
    full_query = f"({domain_query}) AND (2025:2026[pdat])"
    handle = Entrez.esearch(db="pubmed", term=full_query, retmax=5) 
    ids = Entrez.read(handle)["IdList"]
    
    if not ids: return []

    paper_list = []
    for pmid in ids:
        summary = Entrez.read(Entrez.esummary(db="pubmed", id=pmid))[0]
        paper_list.append(f"PMID:{pmid} | タイトル: {summary['Title']}")
    
    batch_prompt = f"""
    あなたは泌尿器科のKOL(MD)かつ工学博士(PhD)です。
    以下の論文リスト（最大5件）を解析し、JSON形式のリストで返してください:
    [
      {{"Source_Ref": "PMID:xxxx", "Clinical_Need": "タイトル...", "Technical_Insight": "解析結果..."}}
    ]
    リスト:
    {chr(10).join(paper_list)}
    """
    
    results = []
    response_text = dual_ai_generate(batch_prompt)
    
    if response_text:
        json_match = re.search(r'\[.*\]', response_text, re.DOTALL)
        if json_match:
            try:
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
            except:
                st.error("AIの回答形式を読み取れませんでした。")
    return results

# --- 7. UI構成 ---
tab1, tab2, tab3 = st.tabs(["📊 インテリジェンスDB", "📡 自動スカウト", "🧠 戦略コンサル"])

with tab1:
    st.subheader("🗂️ 蓄積された知見")
    st.dataframe(load_data(), use_container_width=True)

with tab2:
    st.subheader("🔭 領域横断スキャン")
    area = st.multiselect("重点監視", ["尿路結石", "癌 (UTUC/膀胱/前立腺)", "レーザー工学", "ロボット手術"], default=["尿路結石", "癌 (UTUC/膀胱/前立腺)"])
    
    if st.button("最新エビデンスを巡回"):
        with st.spinner("AIが解析中..."):
            st.session_state.scout_results = automated_scout(" OR ".join(area))
            if st.session_state.scout_results:
                st.success("抽出完了")

    if 'scout_results' in st.session_state:
        for i, res in enumerate(st.session_state.scout_results):
            with st.expander(f"📌 {res['Clinical_Need']}"):
                st.write(res['Technical_Insight'])
                if st.button("本登録", key=f"reg_{i}"):
                    df = pd.concat([load_data(), pd.DataFrame([res])], ignore_index=True)
                    save_data(df)
                    st.toast("保存しました")

with tab3:
    st.subheader("🎓 戦略相談 (MD-PhD)")
    current_df = load_data()
    user_input = st.text_input("質問を入力:")
    if user_input:
        context = current_df.to_string() if not current_df.empty else "データなし"
        prompt = f"知識ベース:\n{context}\n\n質問: {user_input}\n\n泌尿器科医(MD)かつ工学博士(PhD)として回答してください。"
        st.write(dual_ai_generate(prompt))
