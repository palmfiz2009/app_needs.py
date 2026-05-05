import streamlit as st
import pandas as pd
import google.generativeai as genai
from Bio import Entrez
import datetime
import os
import time
import json
import re
import openai  # 💡 冒頭に移動

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

# --- 3. 解析エンジン（安定化版） ---
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
        response = model.generate_content(core_prompt)
        results_text = response.text
    except Exception as e:
        st.warning("Gemini制限中。GPT-4oへ切り替えます...")

    # 2. GPTで補完または代替（タイムアウト設定付き）
    if HAS_OPENAI and (not results_text or "429" in str(results_text)):
        try:
            res_gpt = client_gpt.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": core_prompt}],
                timeout=30.0  # 💡 30秒でタイムアウトさせて「フリーズ」を防ぐ
            )
            results_text = res_gpt.choices[0].message.content
        except Exception as e:
            st.error(f"GPT解析も失敗しました: {e}")

    return results_text

# --- (以下、load_data, save_data, automated_scoutなどは前回と同じ) ---
# ※ automated_scout内の alliance_analysis 呼び出し部分はそのまま使えます

# --- 7. UI（微調整） ---
tab1, tab2, tab3 = st.tabs(["📊 DB", "📡 自動スキャン", "🧠 AI連合コンサル"])

# (Tab 1, Tab 2 の内容は前回と同様)

with tab3:
    st.subheader("🎓 専門家相談")
    if not HAS_OPENAI:
        st.warning("⚠️ OpenAIのキーが設定されていないため、Geminiのみで動作します。")
    # ...残りのコード

with tab3:
    st.subheader("🎓 専門家相談")
    
    # OpenAIキーの確認メッセージ
    if not HAS_OPENAI:
        st.warning("⚠️ OpenAIのキーが設定されていないため、Geminiのみで動作します。")
        
    # 👇 ここが抜け落ちていました！
    u_input = st.text_input("質問を入力（複数のAIが合議して答えます）:")
    if u_input:
        with st.spinner("AIアライアンスが議論中..."):
            res = alliance_analysis(f"ユーザーの質問: {u_input}")
            st.markdown(res)
