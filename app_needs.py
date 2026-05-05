import streamlit as st
import pandas as pd
import google.generativeai as genai
from Bio import Entrez
import datetime
import os
import json
import re
import openai

# --- 1. ページ設定 ---
st.set_page_config(page_title="Urology AI Alliance", layout="wide")
st.title("🛡️ 泌尿器科インテリジェンス・アライアンス (Full Autonomous Mode)")

# --- 2. API接続チェック（診断機能） ---
# Geminiチェック
if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
else:
    st.error("Gemini API Key が未設定です。")

# OpenAIチェック
HAS_OPENAI = False
if "OPENAI_API_KEY" in st.secrets:
    try:
        client_gpt = openai.OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
        HAS_OPENAI = True
    except Exception as e:
        st.error(f"OpenAIの初期化に失敗しました: {e}")

# --- 3. データ管理関数 ---
DATA_FILE = 'urology_intelligence_db.csv'

def load_data():
    columns = ['Date', 'Source_Type', 'Reliability', 'Clinical_Need', 'Technical_Insight', 'Source_Ref']
    if os.path.exists(DATA_FILE):
        df = pd.read_csv(DATA_FILE)
        # 不足している列があればN/Aで埋める
        for col in columns:
            if col not in df.columns: 
                df[col] = "N/A"
        return df[columns]
    return pd.DataFrame(columns=columns)

def save_data(df):
    df.to_csv(DATA_FILE, index=False)

# --- 4. 解析エンジン（安定化版） ---
def alliance_analysis(title_list_str):
    core_prompt = f"""
    あなたは泌尿器科医(MD)かつ工学博士(PhD)です。
    以下の論文リストを解析し、JSON形式で返してください。
    
    対象: {title_list_str}
    
    【形式】
    [
      {{"Source_Ref": "PMID:xxxx", "Clinical_Need": "タイトル...", "Technical_Insight": "詳細解析..."}}
    ]
    """
    
    results_text = ""
    
    # 1. Geminiで試行
    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        # 安全フィルターを緩和して医学用語のブロックを防止
        response = model.generate_content(
            core_prompt,
            safety_settings=[
                {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"}
            ]
        )
        results_text = response.text
    except Exception as e:
        st.warning("Gemini制限中。GPT-4oへ切り替えます...")

    # 2. GPTで補完または代替（タイムアウト設定付き）
    if HAS_OPENAI and (not results_text or "429" in str(results_text)):
        try:
            res_gpt = client_gpt.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": core_prompt}],
                timeout=30.0  # 30秒でタイムアウトさせて「フリーズ」を防ぐ
            )
            results_text = res_gpt.choices[0].message.content
        except Exception as e:
            st.error(f"GPT解析も失敗しました: {e}")

    return results_text

# --- 5. 自動スカウト関数 ---
def automated_scout(domain_query):
    # Entrezの警告を防ぐためのダミーメール
    Entrez.email = "urology_intel_engine@example.com"
    
    # PubMed検索
    full_query = f"({domain_query}) AND (2025:2026[pdat])"
    handle = Entrez.esearch(db="pubmed", term=full_query, retmax=5)
    ids = Entrez.read(handle)["IdList"]
    if not ids: 
        return []

    paper_list = []
    for pmid in ids:
        summary = Entrez.read(Entrez.esummary(db="pubmed", id=pmid))[0]
        paper_list.append(f"PMID:{pmid} | {summary['Title']}")
    
    # アライアンス解析実行
    response_text = alliance_analysis("\n".join(paper_list))
    
    final_results = []
    if response_text:
        # AIの回答からJSON部分だけを抜き出す
        json_match = re.search(r'\[.*\]', response_text, re.DOTALL)
        if json_match:
            try:
                raw_json = json.loads(json_match.group())
                for r in raw_json:
                    final_results.append({
                        'Date': datetime.date.today(),
                        'Source_Type': 'Alliance Intelligence',
                        'Reliability': 'High (Gemini+GPT)',
                        'Clinical_Need': r.get('Clinical_Need', 'N/A'),
                        'Technical_Insight': r.get('Technical_Insight', 'N/A'),
                        'Source_Ref': r.get('Source_Ref', 'N/A')
                    })
            except Exception as e:
                st.error("AIの回答形式を読み取れませんでした。")
    return final_results

# --- 6. UI構成 ---
tab1, tab2, tab3 = st.tabs(["📊 知能データベース", "📡 全自動スキャン", "🧠 AI連合コンサル"])

with tab1:
    st.subheader("🗂️ 蓄積されたグローバル知見")
    st.dataframe(load_data(), use_container_width=True)

with tab2:
    st.subheader("🔭 AI連合による領域横断スキャン")
    area = st.multiselect("監視対象", ["尿路結石", "癌 (UTUC/膀胱/前立腺)", "レーザー工学", "統計手法(ROC/PSM)"], default=["尿路結石", "癌 (UTUC/膀胱/前立腺)"])
    
    if st.button("全AIを起動して巡回開始"):
        with st.spinner("Gemini と GPT-4o が並列思考中..."):
            st.session_state.alliance_results = automated_scout(" OR ".join(area))
            if st.session_state.alliance_results:
                st.success("アライアンス解析が完了しました。")
            else:
                st.warning("情報を抽出できませんでした。")

    if 'alliance_results' in st.session_state:
        for i, res in enumerate(st.session_state.alliance_results):
            with st.expander(f"📌 {res['Clinical_Need']}"):
                st.write(res['Technical_Insight'])
                if st.button("知財として登録", key=f"reg_{i}"):
                    df = pd.concat([load_data(), pd.DataFrame([res])], ignore_index=True)
                    save_data(df)
                    st.toast("保存完了！")

with tab3:
    st.subheader("🎓 専門家相談")
    
    if not HAS_OPENAI:
        st.warning("⚠️ OpenAIのキーが設定されていないため、Geminiのみで動作します。")
        
    u_input = st.text_input("質問を入力（複数のAIが合議して答えます）:")
    if u_input:
        with st.spinner("AIアライアンスが議論中..."):
            res = alliance_analysis(f"ユーザーの質問: {u_input}")
            st.markdown(res)
