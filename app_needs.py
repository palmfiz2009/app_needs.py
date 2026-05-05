import streamlit as st
import pandas as pd
import os
from datetime import datetime

# データの保存先ファイル（GitHub Actionsで定期的に叩くことで、ファイルが消えにくくなります）
# 本格的な運用の際は、Googleスプレッドシートやデータベースとの連携が推奨されます
DATA_FILE = 'medical_needs_data.csv'

def load_data():
    if os.path.exists(DATA_FILE):
        return pd.read_csv(DATA_FILE)
    else:
        return pd.DataFrame(columns=['Date', 'Category', 'Medical_Need', 'Engineering_Spec', 'Patent_Info', 'Importance'])

def save_data(df):
    df.to_csv(DATA_FILE, index=False)

# アプリのタイトル
st.set_page_config(page_title="MedTech Needs & IP Tracker", layout="wide")
st.title("🏥 医学×工学ニーズ・知財データベース")
st.markdown("---")

# サイドバー：新規ニーズの入力
with st.sidebar:
    st.header("📌 新規ニーズ登録")
    category = st.selectbox("カテゴリー", ["泌尿器科", "結石破砕", "腫瘍（UTUC等）", "手術器具", "その他"])
    need_text = st.text_area("医学的ニーズ（現場の困りごと）", placeholder="例：吸引時にシースが潰れてしまう...")
    
    st.subheader("⚙️ 工学的翻訳（仕様）")
    spec_text = st.text_area("工学的仕様（数値・構造）", placeholder="例：曲げ剛性 〇〇 N・mm² 以上、外径 〇〇 Fr 以下...")
    
    patent_info = st.text_input("関連特許・先行技術（特許番号など）")
    importance = st.slider("重要度（どれくらい困っているか）", 1, 5, 3)
    
    if st.button("データベースに登録"):
        new_data = {
            'Date': datetime.now().strftime("%Y-%m-%d %H:%M"),
            'Category': category,
            'Medical_Need': need_text,
            'Engineering_Spec': spec_text,
            'Patent_Info': patent_info,
            'Importance': importance
        }
        df = load_data()
        # concatを使ってデータを追加
        df = pd.concat([df, pd.DataFrame([new_data])], ignore_index=True)
        save_data(df)
        st.success("登録完了！")

# メイン画面：登録データの表示と分析
df = load_data()

st.header("🔍 登録ニーズ一覧")

# フィルタリング機能
search_query = st.text_input("キーワード検索", "")
if search_query:
    df = df[df['Medical_Need'].str.contains(search_query) | df['Engineering_Spec'].str.contains(search_query)]

if not df.empty:
    # 重要度でソート
    df = df.sort_values(by='Importance', ascending=False)
    
    # データの表示
    st.dataframe(df, use_container_width=True)
    
    # CSVダウンロードボタン
    csv = df.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="データをCSVでダウンロード",
        data=csv,
        file_name='medical_needs_export.csv',
        mime='text/csv',
    )
else:
    st.info("まだ登録されたニーズはありません。サイドバーから登録してください。")

st.markdown("---")
st.caption("Developed by MD-PhD Professional")
