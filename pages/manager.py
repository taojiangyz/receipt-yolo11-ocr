import os
import hashlib
import pandas as pd
from src.receipt_quality import assess_receipt
from src.receipt_items import parse_items, normalize_items, reconcile
from datetime import date
from pathlib import Path
import streamlit as st
from src.receipt_pipeline import analyze_image
from src.receipt_store import ReceiptStore, candidates, export_csv, export_items_csv

store = ReceiptStore(Path(os.getenv("RECEIPT_LIBRARY_DIR", ".receipt_library")) / "receipts.sqlite3")
st.title("2.0 · 票据管理")
st.caption("识别后核对，保存后随时查找。金额单位：日元。数据保存在本机。")
if st.session_state.pop("receipt_saved", False):
    st.success("票据已保存，原始识别结果与修改记录均已保留。")
    comparison = st.session_state.pop("receipt_comparison", None)
    if comparison:
        st.warning(comparison["message"]) if comparison["state"] == "difference" else st.info(comparison["message"])


def editor(values, image, raw, key, *, analysis=None, record=None):
    left, right = st.columns(2)
    with left:
        st.image(image, caption="原始小票")
        with st.expander("查看原始识别结果"):
            st.json(raw)
    with right:
        st.subheader("核对票据信息")
        assessment = assess_receipt(raw, detected_fields=raw.get("evidence", {}).get("detected_fields"))
        with st.expander("识别质量检查", expanded=assessment["needs_multimodal"]):
            if assessment["needs_multimodal"]:
                st.warning("核心字段需要核对，可使用下方 AI 辅助核对。")
            elif assessment["route"] == "retake":
                st.warning("建议重拍或人工核对")
            else:
                st.info("未触发自动补救条件，仍需核对。")
            for reason in assessment["reasons"]:
                st.write("• " + reason["message"])
            for advisory in assessment["advisories"]:
                st.caption(advisory["message"])
            st.caption("当前规则只对店名、日期、总金额判断补救；商品明细仅提示。基于原始 OCR 重新检查，历史报告保持不变。")
        from src.receipt_multimodal_view import render_multimodal
        render_multimodal(store, raw, assessment, analysis=analysis, record=record)
        st.caption("识别结果是候选值，请对照原图。缺失字段可先留空，保存为待核对。")
        parsed = parse_items(values["items"])
        if parsed["unmatched"]:
            st.warning("部分文字无法可靠配对为商品与金额，请对照原图补充。税额和折扣不会自动计入商品行。")
            with st.expander("未自动配对的文字"):
                st.text("\n".join(parsed["unmatched"]))
        initial_rows = values.get("line_items", parsed["rows"])
        with st.form(key):
            updated = {
                "store": st.text_input("商户", value=values["store"]),
                "date": st.text_input("日期（YYYY-MM-DD）", value=values["date"]),
                "amount": st.text_input("合计金额（日元）", value=values["amount"]),
                "items": st.text_area("商品明细（原文，可修改）", value=values["items"]),
                "category": st.text_input("类别", value=values["category"]),
                "status": st.selectbox("核对状态", ["待核对", "已核对"], index=int(values["status"] == "已核对")),
            }
            st.caption("商品行金额是该行总价，不是单价。候选行需人工核对；可增删行，不推测数量或税率。")
            table = st.data_editor(
                pd.DataFrame(initial_rows, columns=["name", "line_total"], dtype=str),
                num_rows="dynamic", hide_index=True, key=key + "_items",
                column_config={
                    "name": st.column_config.TextColumn("商品名称"),
                    "line_total": st.column_config.TextColumn("行金额（日元）"),
                },
            )
            submitted = st.form_submit_button("保存票据", type="primary")
        if submitted:
            try:
                updated["line_items"] = normalize_items(table.fillna("").to_dict("records"))
                if record:
                    store.save(updated, receipt_id=record["id"], revision=record["revision"])
                else:
                    store.save(updated, payload=analysis["payload"], filename=analysis["filename"], raw=raw)
                st.session_state["receipt_comparison"] = reconcile(updated["line_items"], updated["amount"])
                st.session_state["receipt_saved"] = True
                st.rerun()
            except ValueError as exc:
                st.error(str(exc))
        comparison = reconcile(initial_rows, values["amount"])
        if comparison["state"] == "difference":
            st.warning(comparison["message"])
        else:
            st.info(comparison["message"])
        st.caption("上方比较基于已保存值／初始候选值，修改后保存即可更新。金额一致不代表识别正确。")

mode = st.radio("工作区", ["新增票据", "批量处理", "历史票据"], horizontal=True)
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
elif mode == "批量处理":
    from src.receipt_batch_view import render_batch
    render_batch(store, editor)
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
        st.dataframe([{k: v for k, v in row.items() if k not in ("id", "line_items")} for row in rows], hide_index=True)
        st.download_button("导出筛选结果 CSV", export_csv(rows), "receipts.csv", "text/csv")
        st.download_button("导出商品明细 CSV", export_items_csv(rows), "receipt_items.csv", "text/csv")
        labels = {r["id"]: f"{r['date'] or '日期待核对'} · {r['store'] or '商户待核对'} · ¥{r['amount'] or '?'} · {r['filename']} · {r['id'][:6]}" for r in rows}
        selected = st.selectbox("打开票据", list(labels), format_func=labels.get)
        record = store.get(selected)
        editor(record["values"], record["image"], record["raw"],
               f"edit_{selected}_{record['revision']}", record=record)
        with st.expander("保存与修改记录"):
            st.json(store.history(selected))
    else:
        st.info("没有符合条件的票据。上传并保存后，会显示在这里。")
