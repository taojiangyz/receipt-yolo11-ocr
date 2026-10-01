import os
import hashlib
from datetime import date
from pathlib import Path
import streamlit as st
from src.receipt_pipeline import analyze_image
from src.receipt_store import ReceiptStore, candidates, export_csv

store = ReceiptStore(Path(os.getenv("RECEIPT_LIBRARY_DIR", ".receipt_library")) / "receipts.sqlite3")
st.title("2.0 · 票据管理")
st.caption("识别后核对，保存后随时查找。金额单位：日元。数据保存在本机。")
if st.session_state.pop("receipt_saved", False):
    st.success("票据已保存，原始识别结果与修改记录均已保留。")


def editor(values, image, raw, key, *, analysis=None, record=None):
    left, right = st.columns(2)
    with left:
        st.image(image, caption="原始小票")
        with st.expander("查看原始识别结果"):
            st.json(raw)
    with right:
        st.subheader("核对票据信息")
        st.caption("识别结果是候选值，请对照原图。缺失字段可先留空，保存为待核对。")
        with st.form(key):
            updated = {
                "store": st.text_input("商户", value=values["store"]),
                "date": st.text_input("日期（YYYY-MM-DD）", value=values["date"]),
                "amount": st.text_input("合计金额（日元）", value=values["amount"]),
                "items": st.text_area("商品明细（原文，可修改）", value=values["items"]),
                "category": st.text_input("类别", value=values["category"]),
                "status": st.selectbox("核对状态", ["待核对", "已核对"], index=int(values["status"] == "已核对")),
            }
            submitted = st.form_submit_button("保存票据", type="primary")
        if submitted:
            try:
                if record:
                    store.save(updated, receipt_id=record["id"], revision=record["revision"])
                else:
                    store.save(updated, payload=analysis["payload"], filename=analysis["filename"], raw=raw)
                st.session_state["receipt_saved"] = True
                st.rerun()
            except ValueError as exc:
                st.error(str(exc))

mode = st.radio("工作区", ["新增票据", "历史票据"], horizontal=True)
if mode == "新增票据":
    upload = st.file_uploader("上传小票", type=["jpg", "jpeg", "png"], key="manager_upload")
    analysis = st.session_state.get("receipt_analysis")
    if upload:
        duplicate = store.find_digest(upload.getvalue())
        if duplicate:
            st.info("这张图片已经保存。请进入历史票据查看或修改。")
            st.stop()
        if st.button("识别小票", type="primary"):
            try:
                with st.spinner("正在识别…"):
                    analysis = analyze_image(upload.getvalue(), upload.name)
            except Exception as exc:
                st.error(f"识别失败，可重新点击识别重试：{exc}")
                st.stop()
        if not analysis or analysis["digest"] != hashlib.sha256(upload.getvalue()).hexdigest():
            st.info("点击识别小票，完成后可核对保存。")
            st.stop()
    if analysis:
        if store.find_digest(analysis["payload"]):
            st.info("当前识别结果已保存。可上传下一张，或进入历史票据。")
        else:
            st.caption(f"当前图片：{analysis['filename']}（也可从识别实验室带入）")
            editor(candidates(analysis["result"]), analysis["image"], analysis["result"],
                   "new_" + analysis["digest"], analysis=analysis)
    else:
        st.info("上传小票开始，或先在识别实验室完成识别。")
else:
    query = st.text_input("搜索商户、类别或商品")
    status = st.selectbox("状态筛选", ["全部", "待核对", "已核对"])
    start = end = ""
    if st.checkbox("按消费日期筛选"):
        a, b = st.columns(2)
        start = a.date_input("开始日期", value=date.today().replace(day=1)).isoformat()
        end = b.date_input("结束日期", value=date.today()).isoformat()
        if start > end:
            st.error("开始日期不能晚于结束日期")
            st.stop()
    rows = store.list(query, status, start, end)
    st.caption(f"共 {len(rows)} 张票据")
    if rows:
        st.dataframe([{k: v for k, v in row.items() if k != "id"} for row in rows], hide_index=True)
        st.download_button("导出筛选结果 CSV", export_csv(rows), "receipts.csv", "text/csv")
        labels = {r["id"]: f"{r['date'] or '日期待核对'} · {r['store'] or '商户待核对'} · ¥{r['amount'] or '?'} · {r['filename']} · {r['id'][:6]}" for r in rows}
        selected = st.selectbox("打开票据", list(labels), format_func=labels.get)
        record = store.get(selected)
        editor(record["values"], record["image"], record["raw"],
               f"edit_{selected}_{record['revision']}", record=record)
        with st.expander("保存与修改记录"):
            st.json(store.history(selected))
    else:
        st.info("没有符合条件的票据。上传并保存后，会显示在这里。")
