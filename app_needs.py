import streamlit as st
import pandas as pd
from Bio import Entrez
import datetime
import os

# --- 1. ページ設定 ---
st.set_page_config(page_title="Urology Intel Scout", layout="wide")
st.title("🛡️ 泌尿器科インテリジェンス・スカウト (Free Scan Mode)")

# --- 2. データ管理関数 ---
DATA_FILE = 'urology_intelligence_db.csv'

def load_data():
    columns = ['Date', 'Source_Type', 'Reliability', 'Clinical_Need', 'Source_Ref']
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

# --- 3. 無料スカウト関数（PubMed専用） ---
def free_scout(domain_query):
    # Entrezの警告を防ぐためのダミーメール
    Entrez.email = "urology_intel_engine@example.com"
    
    # PubMed検索 (最新のものを5件)
    full_query = f"({domain_query}) AND (2025:2026[pdat])"
    handle = Entrez.esearch(db="pubmed", term=full_query, retmax=5, sort="date")
    ids = Entrez.read(handle)["IdList"]
    
    if not ids: 
        return []

    results = []
    for pmid in ids:
        # 要約（Summary）を取得
        summary = Entrez.read(Entrez.esummary(db="pubmed", id=pmid))[0]
        title = summary.get('Title', 'タイトルなし')
        source = summary.get('Source', '不明なジャーナル')
        pubdate = summary.get('PubDate', '不明な日付')
        
        results.append({
            'PMID': pmid,
            'Title': title,
            'Journal': source,
            'Date': pubdate
        })
        
    return results

# --- 4. UI構成 ---
tab1, tab2 = st.tabs(["📊 保存済み知見", "📡 無料タイトルスキャン"])

with tab1:
    st.subheader("🗂️ 蓄積されたグローバル知見")
    st.dataframe(load_data(), use_container_width=True)

with tab2:
    st.subheader("🔭 領域横断スキャン (API消費ゼロ)")
    
    # 検索キーワードを自由に編集できるように変更
    search_keyword = st.text_input("検索キーワード (例: upper tract urothelial carcinoma OR urolithiasis)", "upper tract urothelial carcinoma OR urolithiasis")
    
    if st.button("最新論文をスキャン"):
        with st.spinner("PubMedを検索中..."):
            st.session_state.scan_results = free_scout(search_keyword)
            if st.session_state.scan_results:
                st.success(f"{len(st.session_state.scan_results)}件の最新論文を見つけました。")
            else:
                st.warning("論文が見つかりませんでした。キーワードを変えてみてください。")

    if 'scan_results' in st.session_state:
        for i, res in enumerate(st.session_state.scan_results):
            with st.expander(f"📄 {res['Title']}"):
                st.write(f"**ジャーナル:** {res['Journal']}")
                st.write(f"**発行日:** {res['Date']}")
                st.write(f"**PMID:** {res['PMID']}")
                # PubMedへのリンクを生成
                st.markdown(f"[PubMedで抄録を読む (PMID: {res['PMID']})](https://pubmed.ncbi.nlm.nih.gov/{res['PMID']}/)")
                
                if st.button("このタイトルをDBに保存", key=f"save_{i}"):
                    new_entry = {
                        'Date': datetime.date.today(),
                        'Source_Type': 'PubMed Scan',
                        'Reliability': 'High',
                        'Clinical_Need': res['Title'],
                        'Source_Ref': f"PMID: {res['PMID']}"
                    }
                    df = pd.concat([load_data(), pd.DataFrame([new_entry])], ignore_index=True)
                    save_data(df)
                    st.toast("保存完了！")
