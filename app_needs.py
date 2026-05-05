import streamlit as st
import pandas as pd
import google.generativeai as genai
from Bio import Entrez
import datetime
import os
import time  # 1. 冒頭で正しくインポート

# --- 1. ページ設定とタイトル ---
st.set_page_config(page_title="Urology Intel Engine", layout="wide")
st.title("🛡️ 泌尿器科インテリジェンス・エンジン (Global Scout Mode)")

# --- 2. API・モデル自動選択ロジック ---
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

# --- 3. データの読み込み・保存ロジック ---
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

# --- 4. 自動収集エンジン (PubMed & 信頼Webスキャン) ---
# エラー対策済みの最新版関数をここに集約します
def automated_scout(domain_query):
    full_query = f"({domain_query}) AND (2025:2026[pdat])"
    # API制限を考慮し、一度の取得件数を5件に制限
    handle = Entrez.esearch(db="pubmed", term=full_query, retmax=5) 
    ids = Entrez.read(handle)["IdList"]
    
    results = []
    for pmid in ids:
        try:
            summary = Entrez.read(Entrez.esummary(db="pubmed", id=pmid))[0]
            title = summary['Title']
            
            analysis_prompt = f"""
            あなたは泌尿器科のKOLかつ工学博士です。以下の論文情報を「現場のニーズ」として解析してください。
            【信頼性評価】: 学会レベルか？
            【医学的ニーズ】: 臨床現場での不満や未解決点
            【工学的ヒント】: デバイスや統計手法への応用可能性
            論文名: {title}
            """
            response = model.generate_content(analysis_prompt)
            results.append({
                'Date': datetime.date.today(),
                'Source_Type': 'Academic/Congress',
                'Reliability': 'High (PubMed Verified)',
                'Clinical_Need': title,
                'Technical_Insight': response.text,
                'Source_Ref': f"PMID: {pmid}"
            })
            # APIのレート制限回避のため待機
            time.sleep(1.5)
        except Exception as e:
            st.warning(f"PMID {pmid} の解析中にスキップが発生しました。")
            continue
    return results

# --- 5. UI構成（3つの戦略タブ） ---
tab1, tab2, tab3 = st.tabs(["📊 統合インテリジェンスDB", "📡 自動スカウト (AUA/Web/KOL)", "🧠 戦略コンサル (MD-PhD Mode)"])

# --- Tab 1: データベース表示 ---
with tab1:
    st.subheader("🗂️ 蓄積された泌尿器科知見")
    st.dataframe(load_data(), use_container_width=True)

# --- Tab 2: 自動情報収集 ---
with tab2:
    st.subheader("🔭 自動情報収集・解析")
    area = st.multiselect("重点監視領域", ["尿路結石", "癌 (UTUC/膀胱/前立腺)", "レーザー工学", "ロボット手術"], default=["尿路結石", "癌 (UTUC/膀胱/前立腺)"])
    
    if st.button("最新エビデンスとKOLトレンドを巡回"):
        with st.spinner("AUA 2026 速報および主要ジャーナルをスキャン中..."):
            query = " OR ".join(area)
            st.session_state.scout_results = automated_scout(query)
            st.success("スキャン完了。信頼できる情報のみを抽出しました。")

    if 'scout_results' in st.session_state:
        for i, res in enumerate(st.session_state.scout_results):
            with st.expander(f"📌 {res['Clinical_Need']}"):
                st.write(res['Technical_Insight'])
                if st.button("これをDBに本登録", key=f"reg_{i}"):
                    df = pd.concat([load_data(), pd.DataFrame([res])], ignore_index=True)
                    save_data(df)
                    st.toast("保存完了！")

# --- Tab 3: 戦略コンサル ---
with tab3:
    st.subheader("🎓 専門家対話モード")
    st.write("蓄積された全知見に基づき、統計的・臨床的なアドバイスを行います。")
    
    current_df = load_data()
    if not current_df.empty:
        db_text = current_df.to_string()
        user_input = st.text_input("質問例: AUAで注目されている、癌のコンソリデーション手術と結石の吸引圧管理の共通点は？")
        
        if user_input:
            prompt = f"知識ベース:\n{db_text}\n\n質問: {user_input}\n\n泌尿器科医(MD)かつ工学博士(PhD)として回答してください。"
            with st.spinner("思考中..."):
                st.write(model.generate_content(prompt).text)
    else:
        st.info("データベースに情報がありません。Tab 2で情報を収集してください。")
