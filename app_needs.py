import streamlit as st
import pandas as pd
from Bio import Entrez
import datetime

# --- 1. ページ設定 ---
st.set_page_config(page_title="Urology Intel Sniper", layout="wide")
st.title("🎯 泌尿器科インテリジェンス・スナイパー (Precision Mode)")

# --- 2. 高度な検索式（Sniper Queries） ---
# ※ノイズを排除し、Coreな論文だけを狙い撃ちする検索式
SNIPER_QUERIES = {
    "【Project SUI】 吸引機能付き尿管アクセスシース": 
        '("ureteral access sheath"[Title/Abstract] AND (suction OR vacuum OR "negative pressure"))',
    
    "【癌・腫瘍】 UTUC (上部尿路尿路上皮癌) の最新外科治療": 
        '("upper tract urothelial carcinoma"[Title/Abstract] OR UTUC[Title/Abstract]) AND (surgery OR consolidative OR nephroureterectomy)',
    
    "【レーザー工学】 ツリウム/ホルミウムレーザー砕石術": 
        '(lithotripsy[Title/Abstract]) AND (thulium OR holmium OR "Revolix" OR "super thulium")',
    
    "【統計手法】 泌尿器科におけるROC分析 / PSM": 
        '("urology"[Journal] OR "european urology"[Journal]) AND ("propensity score" OR "ROC")'
}

# --- 3. スナイパー検索関数 ---
@st.cache_data(ttl=3600)
def pubmed_sniper(query_key, max_results=10):
    Entrez.email = "sniper@example.com"
    base_query = SNIPER_QUERIES[query_key]
    
    # 2025年以降の論文に限定してさらに絞り込む
    full_query = f"({base_query}) AND (2025:2026[pdat])"
    
    try:
        handle = Entrez.esearch(db="pubmed", term=full_query, retmax=max_results, sort="date")
        ids = Entrez.read(handle)["IdList"]
        
        if not ids:
            return []

        results = []
        for pmid in ids:
            summary = Entrez.read(Entrez.esummary(db="pubmed", id=pmid))[0]
            
            # Abstract（抄録）を取得するための追加リクエスト
            fetch_handle = Entrez.efetch(db="pubmed", id=pmid, retmode="xml")
            fetch_records = Entrez.read(fetch_handle)
            abstract_text = "Abstract not available."
            
            try:
                article = fetch_records['PubmedArticle'][0]['MedlineCitation']['Article']
                if 'Abstract' in article and 'AbstractText' in article['Abstract']:
                    # Abstractが複数段落に分かれている場合を結合
                    abstract_text = " ".join([str(text) for text in article['Abstract']['AbstractText']])
            except:
                pass

            results.append({
                "Date": summary.get('PubDate', 'N/A'),
                "Journal": summary.get('Source', 'N/A'),
                "Title": summary.get('Title', 'N/A'),
                "Abstract": abstract_text,
                "PMID": pmid,
                "Link": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"
            })
        return results
    except Exception as e:
        st.error(f"PubMed検索中にエラーが発生しました: {e}")
        return []

# --- 4. UI構成 ---
st.markdown("API課金ゼロ。ノイズを排除し、研究テーマに直結するPubMed論文のAbstract（抄録）まで直接狙い撃ちします。")

selected_theme = st.selectbox("🎯 ターゲット領域を選択", list(SNIPER_QUERIES.keys()))
fetch_count = st.slider("取得件数", min_value=5, max_value=20, value=5)

if st.button("狙撃開始 (PubMed検索)"):
    with st.spinner("PubMedから高精度データを抽出中..."):
        st.session_state.sniper_results = pubmed_sniper(selected_theme, fetch_count)
        
        if st.session_state.sniper_results:
            st.success(f"標的を {len(st.session_state.sniper_results)} 件捕捉しました。")
        else:
            st.warning("指定の条件で2025年以降の最新論文は見つかりませんでした。")

# 結果の表示
if 'sniper_results' in st.session_state and st.session_state.sniper_results:
    for i, res in enumerate(st.session_state.sniper_results):
        with st.container():
            st.markdown(f"### {res['Title']}")
            col1, col2 = st.columns([3, 1])
            with col1:
                st.caption(f"**Journal:** {res['Journal']} | **Date:** {res['Date']} | **PMID:** {res['PMID']}")
            with col2:
                st.markdown(f"[🔗 PubMedで開く]({res['Link']})")
            
            # Abstractをデフォルトで表示する（展開ボックス）
            with st.expander("📝 抄録 (Abstract) を読む", expanded=False):
                st.write(res['Abstract'])
            st.divider()
