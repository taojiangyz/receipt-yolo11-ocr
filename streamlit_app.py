import streamlit as st

st.set_page_config(page_title="Receipt Intelligence", page_icon="🧾", layout="wide")
st.navigation([
    st.Page("pages/lab.py", title="1.0 · 识别实验室", icon="🔬"),
    st.Page("pages/manager.py", title="2.0 · 票据管理", icon="🧾", default=True),
]).run()
