import streamlit as st
import pandas as pd
from Bio import Entrez
import feedparser
import datetime
import urllib.parse

# --- 1. ページ設定 ---
st.set_page_config(page_title="Urology Web Spider", layout="wide")
st.title("🕸️ 泌尿器科ウェブ・スパイダー (特化型検索エンジン)")

# --- 2. 監視対象のデータソース（完全無料のRSSフィード） ---
# ※ここに学会や主要ジャーナルのRSS URLを登録します
SOURCES = {
    "Urology Times": "https://www.urologytimes.com/rss",
    "European Urology (Current Issue)": "https://www.europeanurology.com/current.rss",
    "Journal of Urology": "https://www.auajournals.org/action/showFeed?type=etoc&feed=rss&jc=juro"
}

# --- 3. クローラー関数 ---
@st.cache_data(ttl=3600) # 1時間はキャッシュを保持して高速化
def crawl_web_news():
    news_list = []
    for source_name, url in SOURCES.items():
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:5]: # 各サイト最新5件
                news_list.append({
                    "Date": getattr(entry, 'published', datetime.date.today().strftime("%Y-%m-%d")),
                    "Source": source_name,
                    "Title": entry.title,
                    "Link": entry.link
                })
        except Exception as e:
            pass # エラーが出たサイトはスキップ
    return news_list

@st.cache_data(ttl=3600)
def search_pubmed(query):
    Entrez.email = "spider@example.com"
    full_query = f"({query}) AND (2025:2026[pdat])"
    try:
        handle = Entrez.esearch(db="pubmed", term=full_query, retmax=10, sort="date")
        ids = Entrez.read(handle)["IdList"]
        
        results = []
        for pmid in ids:
            summary = Entrez.read(Entrez.esummary(db="pubmed", id=pmid))[0]
            results.append({
                "Date": summary.get('PubDate', ''),
                "Source": "PubMed",
                "Title": summary.get('Title', ''),
                "Link": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"
            })
        return results
    except:
        return []

# --- 4. UI構成 ---
st.markdown("API課金なし。Web上の最新ジャーナルと論文をクローリングする独自検索エンジンです。")

# 検索インターフェース
search_query = st.text_input("🔍 検索キーワードを入力 (例: UTUC, laser lithotripsy, ureteral access sheath)", "UTUC OR laser lithotripsy")

if st.button("Web全域をスキャン"):
    with st.spinner("クローラーがWeb上を巡回中..."):
        # 1. ニュースサイトのクローリング
        news_data = crawl_web_news()
        
        # 2. PubMedのクローリング
        pubmed_data = search_pubmed(search_query)
        
        # 3. データの結合と検索キーワードでのフィルタリング
        all_data = news_data + pubmed_data
        
        # キーワードが指定されている場合、タイトルにその文字が含まれるか（簡易的な全文検索）
        filtered_results = []
        query_words = search_query.lower().replace(' or ', ' ').replace(' and ', ' ').split()
        
        for item in all_data:
            title_lower = item['Title'].lower()
            # 簡易検索ロジック：キーワードのいずれかが含まれていればヒット
            if any(word in title_lower for word in query_words) or not query_words:
                filtered_results.append(item)
                
        st.session_state.search_results = filtered_results
        st.success(f"スキャン完了。関連情報が {len(filtered_results)} 件見つかりました。")

# 検索結果の表示
if 'search_results' in st.session_state and st.session_state.search_results:
    # データをPandas DataFrameにして綺麗な表にする
    df = pd.DataFrame(st.session_state.search_results)
    
    # URLをクリッカブルなリンクに変換する設定
    st.data_editor(
        df,
        column_config={
            "Link": st.column_config.LinkColumn("Read Article", display_text="Open Link")
        },
        hide_index=True,
        use_container_width=True
    )
