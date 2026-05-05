import streamlit as st
import pandas as pd
import google.generativeai as genai
from Bio import Entrez
import datetime
import os
import time
import json
import re

# --- 1. ページ設定 ---
st.set_page_config(page_title="Urology AI Alliance", layout="wide")
st.title("🛡️ 泌尿器科インテリジェンス・アライアンス (Full Autonomous Mode)")

# --- 2. 各AIの設定 ---
if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
else:
    st.error("Secretsに GEMINI_API_KEY を設定してください。")

HAS_OPENAI = "OPENAI_API_KEY" in st.secrets

@st.cache_resource
def get_gemini_model():
    return genai.GenerativeModel('gemini-1.5-flash')

model_gemini = get_gemini_model()
DATA_FILE = 'urology_intelligence_db.csv'

# --- 3. 解析エンジン：自律アライアンス・ロジック ---
def alliance_analysis(title_list_str):
    """
    複数のAIを裏側で連動させ、医学・工学・KOL予測を統合した最終回答を生成する
    """
    # 共通の分析指示（MD-PhD視点）
    core_prompt = f"""
    あなたは泌尿器科医(MD)かつ工学博士(PhD)の最高顧問です。
    以下の論文リストに対し、2つの視点（医学的ニーズ・工学的解決）から多角的に分析してください。
    
    対象リスト:
    {title_list_str}
    
    【出力形式】
    以下のJSON配列のみを返してください。
    [
      {{
        "Source_Ref": "PMID:xxxx",
        "Clinical_Need": "タイトル...",
        "Technical_Insight": "【医学的インパクト】と【工学的スペック案】、そして【KOLの反応予測】を統合した詳細な解析"
      }}
    ]
    """

    results_text = ""
    
    # 1. 第一フェーズ：Geminiによる「広角」解析
    try:
        response = model_gemini.generate_content(core_prompt)
        results_text = response.text
    except Exception as e:
        st.warning(f"Geminiが制限中のため、GPT-4oが単独で解析を継続します。")
        
    # 2. 第二フェーズ：GPT-4oによる「深層」検証と統合（キーがある場合）
    if HAS_OPENAI:
        import openai
        client = openai.OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
        try:
            # Geminiの結果がある場合は、それを踏まえてGPTがさらにブラッシュアップする
            refinement_prompt = f"以下の解析案を、さらに工学的・特許的な視点（ROC分析の妥当性、Revolix HTLとの差別化、デバイスのFr径など）で磨き上げてください。\n\n解析案:\n{results_text if results_text else core_prompt}"
            
            res_gpt = client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": refinement_prompt}]
            )
            results_text = res_gpt.choices[0].message.content
        except Exception as e:
            st.error(f"GPT解析中にエラー: {e}")

    return results_text

# --- 4. データ管理 ---
def load_data():
    columns = ['Date', 'Source_Type', 'Reliability', 'Clinical_Need', 'Technical_Insight', 'Source_Ref']
    if os.path.exists(DATA_FILE):
        df = pd.read_csv(DATA_FILE)
        return df.reindex(columns=columns).fillna("N/A")
    return pd.DataFrame(columns=columns)

def save_data(df):
    df.to_csv(DATA_FILE, index=False)

# --- 5. スカウト関数 ---
def automated_scout(domain_query):
    # PubMed検索
    full_query = f"({domain_query}) AND (2025:2026[pdat])"
    handle = Entrez.esearch(db="pubmed", term=full_query, retmax=5)
    ids = Entrez.read(handle)["IdList"]
    if not ids: return []

    paper_list = []
    for pmid in ids:
        summary = Entrez.read(Entrez.esummary(db="pubmed", id=pmid))[0]
        paper_list.append(f"PMID:{pmid} | {summary['Title']}")
    
    # アライアンス解析実行
    response_text = alliance_analysis("\n".join(paper_list))
    
    final_results = []
    if response_text:
        json_match = re.search(r'\[.*\]', response_text, re.DOTALL)
        if json_match:
            try:
                raw_json = json.loads(json_match.group())
                for r in raw_json:
                    final_results.append({
                        'Date': datetime.date.today(),
                        'Source_Type': 'Alliance Intelligence',
                        'Reliability': 'High (Gemini+GPT)',
                        'Clinical_Need': r['Clinical_Need'],
                        'Technical_Insight': r['Technical_Insight'],
                        'Source_Ref': r['Source_Ref']
                    })
            except: pass
    return final_results

# --- 6. UI ---
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

    if 'alliance_results' in st.session_state:
        for i, res in enumerate(st.session_state.alliance_results):
            with st.expander(f"📌 {res['Clinical_Need']}"):
                st.write(res['Technical_Insight'])
                if st.button("知財として登録", key=f"reg_{i}"):
                    df = pd.concat([load_data(), pd.DataFrame([res])], ignore_index=True)
                    save_data(df)
                    st.toast("保存完了！")

with tab3:
    st.subheader("🎓 AI連合への直接相談 (MD-PhD)")
    u_input = st.text_input("質問を入力（複数のAIが合議して答えます）:")
    if u_input:
        with st.spinner("AIアライアンスが議論中..."):
            res = alliance_analysis(f"ユーザーの質問: {u_input}")
            st.markdown(res)
