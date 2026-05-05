import streamlit as st
import pandas as pd
import google.generativeai as genai
from Bio import Entrez
import datetime

# --- 1. ページ設定とAPI準備 ---
st.set_page_config(page_title="Urology Intel & IP Analyzer", layout="wide")
st.title("🎯 泌尿器科インテリジェンス ＆ 知財アナライザー")

# Gemini APIの初期化（最も安定している 'gemini-pro' に変更）
if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    # 💡 確実につながる標準モデルに変更
    model = genai.GenerativeModel('gemini-pro')
else:
    st.error("Gemini API Key が設定されていません。")

# --- 2. スナイパー検索関数 ---
SNIPER_QUERIES = {
    "【Project SUI】 吸引機能付き尿管アクセスシース": 
        '("ureteral access sheath"[Title/Abstract] AND (suction OR vacuum OR "negative pressure"))',
    "【癌・腫瘍】 UTUC の最新外科治療": 
        '("upper tract urothelial carcinoma"[Title/Abstract] OR UTUC[Title/Abstract]) AND (surgery OR consolidative OR nephroureterectomy)',
    "【レーザー工学】 Revolix HTL等レーザー砕石術": 
        '(lithotripsy[Title/Abstract]) AND (thulium OR holmium OR "Revolix" OR "super thulium")',
    "【統計手法】 泌尿器科におけるROC分析 / PSM": 
        '("urology"[Journal] OR "european urology"[Journal]) AND ("propensity score" OR "ROC")'
}

@st.cache_data(ttl=3600)
def pubmed_sniper(query_key, max_results=5):
    Entrez.email = "sniper_ip@example.com"
    base_query = SNIPER_QUERIES[query_key]
    full_query = f"({base_query}) AND (2025:2026[pdat])"
    
    try:
        handle = Entrez.esearch(db="pubmed", term=full_query, retmax=max_results, sort="date")
        ids = Entrez.read(handle)["IdList"]
        if not ids: return []

        results = []
        for pmid in ids:
            summary = Entrez.read(Entrez.esummary(db="pubmed", id=pmid))[0]
            
            # Abstract取得
            fetch_handle = Entrez.efetch(db="pubmed", id=pmid, retmode="xml")
            fetch_records = Entrez.read(fetch_handle)
            abstract_text = "Abstract not available."
            try:
                article = fetch_records['PubmedArticle'][0]['MedlineCitation']['Article']
                if 'Abstract' in article and 'AbstractText' in article['Abstract']:
                    abstract_text = " ".join([str(text) for text in article['Abstract']['AbstractText']])
            except: pass

            results.append({
                "Date": summary.get('PubDate', 'N/A'),
                "Title": summary.get('Title', 'N/A'),
                "Abstract": abstract_text,
                "PMID": pmid
            })
        return results
    except Exception as e:
        st.error(f"PubMed検索エラー: {e}")
        return []

# --- 3. 知財・アンメットニーズ抽出エンジン（Gemini） ---
def analyze_unmet_needs(abstracts_text, theme):
    prompt = f"""
    あなたは泌尿器科医(MD)かつ工学博士(PhD)の知財戦略コンサルタントです。
    以下の最新論文(Abstract)群を読み込み、テーマ「{theme}」に関する事業化・特許化のためのインテリジェンスを抽出してください。

    【論文データ】
    {abstracts_text}

    以下の3項目を、専門的かつ具体的に日本語で出力してください。
    1. 臨床的ペインポイント (MD視点：現場でまだ解決されていない課題)
    2. 工学的ボトルネック (PhD視点：なぜ他社はそれを解決できていないのか)
    3. 商業化・特許の「ホワイトスペース」 (知財戦略：どのような構造やメソッドで特許を押さえるべきか、キラーフレーズは何か)
    """
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"Gemini解析エラー: {e}"

# --- 4. UI構成 ---
tab1, tab2 = st.tabs(["🎯 PubMed スナイパー検索", "🧠 知財・アンメットニーズ抽出"])

with tab1:
    st.markdown("ノイズを排除し、研究テーマに直結するPubMedの抄録（Abstract）を取得します。")
    selected_theme = st.selectbox("検索ターゲットを選択", list(SNIPER_QUERIES.keys()))
    
    if st.button("狙撃開始 (PubMed検索)"):
        with st.spinner("PubMedからデータ抽出中..."):
            st.session_state.sniper_data = pubmed_sniper(selected_theme)
            if st.session_state.sniper_data:
                st.success(f"{len(st.session_state.sniper_data)} 件のAbstractを取得しました！「🧠 知財・アンメットニーズ抽出」タブに進んでください。")
            else:
                st.warning("データが見つかりませんでした。")

    if 'sniper_data' in st.session_state:
        for res in st.session_state.sniper_data:
            with st.expander(f"📄 {res['Title']} (PMID: {res['PMID']})"):
                st.write(res['Abstract'])

with tab2:
    st.markdown("Tab 1で取得したAbstract群をGeminiが一括解析し、**特許のホワイトスペース**を抽出します。")
    
    if 'sniper_data' in st.session_state and st.session_state.sniper_data:
        if st.button("✨ 取得したデータからアンメットニーズを抽出"):
            with st.spinner("MD-PhD視点で知財戦略を構築中..."):
                # 取得したすべてのAbstractを1つのテキストに結合
                combined_abstracts = "\n\n".join([f"Title: {d['Title']}\nAbstract: {d['Abstract']}" for d in st.session_state.sniper_data])
                
                # Geminiに解析させる
                analysis_result = analyze_unmet_needs(combined_abstracts, selected_theme)
                
                st.markdown("### 💡 事業化インテリジェンス・レポート")
                st.write(analysis_result)
    else:
        st.info("まずは「🎯 PubMed スナイパー検索」タブで論文データを取得してください。")
