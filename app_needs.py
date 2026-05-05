import streamlit as st
import pandas as pd
import os
from datetime import datetime
from Bio import Entrez
import google.generativeai as genai

# --- 1. アプリ全体の初期設定（一番上に書く必要があります） ---
st.set_page_config(page_title="MedTech Needs Tracker", layout="wide")

# --- 2. API・ファイル設定 ---
# ★メールアドレスとAPIキーを先生のものに書き換えてください
Entrez.email = "your-email@example.com" 
genai.configure(api_key="YOUR_GEMINI_API_KEY")
model = genai.GenerativeModel('gemini-pro')

DATA_FILE = 'medical_needs_data.csv'

# AIからのコピー用セッション状態
if 'draft_need' not in st.session_state:
    st.session_state.draft_need = ""
if 'draft_spec' not in st.session_state:
    st.session_state.draft_spec = ""

# --- 3. 共通関数（データの読み書き・検索・AI解析） ---
def load_data():
    if os.path.exists(DATA_FILE):
        return pd.read_csv(DATA_FILE)
    return pd.DataFrame(columns=['Date', 'Category', 'Medical_Need', 'Engineering_Spec', 'Patent_Info', 'Importance'])

def save_data(df):
    df.to_csv(DATA_FILE, index=False)

def search_pubmed(keyword, max_results=3):
    handle = Entrez.esearch(db="pubmed", term=keyword, retmax=max_results)
    record = Entrez.read(handle)
    handle.close()
    ids = record["IdList"]
    abstracts = []
    for pmid in ids:
        fetch_handle = Entrez.efetch(db="pubmed", id=pmid, rettype="abstract", retmode="text")
        abstract_text = fetch_handle.read()
        fetch_handle.close()
        abstracts.append({"pmid": pmid, "text": abstract_text})
    return abstracts

def extract_needs_with_ai(abstract_dict):
    prompt = f"""
    以下の抄録を読み、医学的ニーズと工学的課題を事実のみ抽出してください。
    絶対に自分の知識で補完せず、テキストにある内容のみを反映させてください。
    論文(PMID: {abstract_dict['pmid']}):
    {abstract_dict['text']}
    """
    response = model.generate_content(prompt)
    return response.text

# --- 4. メイン画面のUI構成 ---
st.title("🏥 医学×工学ニーズ・知財統合プラットフォーム")

# タブで機能を分ける（画面を整理するため）
tab1, tab2 = st.tabs(["📊 データベース & 本登録", "🤖 AIニーズ検索（PubMed）"])

# --- Tab 1: 蓄積データ表示 & 手動登録（編集） ---
with tab1:
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.subheader("📌 現場の知見を登録")
        # AIからの下書きがある場合は、ここに反映される
        with st.form("input_form", clear_on_submit=True):
            category = st.selectbox("カテゴリー", ["泌尿器科", "結石破砕", "腫瘍（UTUC等）", "手術器具", "その他"])
            
            # session_stateを使ってAIの結果を表示
            need = st.text_area("医学的ニーズ（現場の感覚を追記してください）", value=st.session_state.draft_need)
            spec = st.text_area("工学的仕様（数値・物理的構造など）", value=st.session_state.draft_spec)
            
            patent = st.text_input("特許情報・関連技術")
            imp = st.slider("重要度（切実さ）", 1, 5, 3)
            
            if st.form_submit_button("本登録する"):
                new_row = {
                    'Date': datetime.now().strftime("%Y-%m-%d"),
                    'Category': category,
                    'Medical_Need': need,
                    'Engineering_Spec': spec,
                    'Patent_Info': patent,
                    'Importance': imp
                }
                df = load_data()
                df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
                save_data(df)
                # 登録後は下書きをリセット
                st.session_state.draft_need = ""
                st.session_state.draft_spec = ""
                st.success("本登録完了！データが保存されました。")
                st.rerun()

    with col2:
        st.subheader("🔍 蓄積されたニーズ一覧")
        df_display = load_data()
        if not df_display.empty:
            st.dataframe(df_display.sort_values(by='Date', ascending=False), use_container_width=True)
        else:
            st.info("データがまだありません。")

# --- Tab 2: AIによる論文解析 & 下書き生成 ---
with tab2:
    st.subheader("🌐 最新論文からニーズの「種」を探す")
    search_keyword = st.text_input("PubMed検索キーワード（英語）", "Ureteral access sheath suction")
    
    if st.button("AIで検索・解析を実行"):
        if search_keyword:
            with st.spinner("PubMedを検索中..."):
                results = search_pubmed(search_keyword)
                for item in results:
                    with st.expander(f"📄 論文 PMID: {item['pmid']} のAI解析結果"):
                        analysis = extract_needs_with_ai(item)
                        st.write(analysis)
                        
                        # ボタンを押すとTab 1のフォームにデータが飛ぶ
                        if st.button(f"この内容を編集して登録する (PMID:{item['pmid']})"):
                            st.session_state.draft_need = f"【PMID:{item['pmid']}より】\n" + analysis
                            st.session_state.draft_spec = "（ここに先生の工学的知見を追記してください）"
                            st.success("Tab 1 の登録フォームに下書きをコピーしました！")
                        
                        st.caption(f"[PubMedで原文を確認](https://pubmed.ncbi.nlm.nih.gov/{item['pmid']}/)")
        else:
            st.warning("キーワードを入力してください。")

st.markdown("---")
st.caption("Developed for MD-PhD Professional Workflow")
