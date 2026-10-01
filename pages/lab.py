import json
import streamlit as st
from src.receipt_pipeline import FIELDS, analyze_image

st.title("1.0 · 识别实验室")
st.caption("YOLO11 → 字段裁剪 → PaddleOCR → JSON / レシート認識ラボ")
upload = st.file_uploader("上传小票 / Upload receipt", type=["jpg", "jpeg", "png"], key="lab_upload")
if upload:
    try:
        with st.spinner("正在识别小票…"):
            analysis = analyze_image(upload.getvalue(), upload.name)
    except Exception as exc:
        st.error(f"识别失败，请检查图片和模型配置后重试：{exc}")
        st.stop()
    left, right = st.columns(2)
    left.image(analysis["image"], caption="原图")
    right.image(analysis["detection"], caption="YOLO11 检测结果")
    st.subheader("字段裁剪")
    for col, field in zip(st.columns(4), FIELDS):
        with col:
            st.write(field)
            if field in analysis["crops"]:
                crop = analysis["crops"][field]
                st.image(crop["image"])
                st.caption(f"检测置信度：{crop['confidence']:.3f}（不代表 OCR 准确率）")
            else:
                st.warning("未检测到")
    st.subheader("OCR 与结构化结果")
    fields, structured = st.columns(2)
    with fields:
        result = analysis["result"]
        st.write("商户：", result["store_name_candidate"] or "待核对")
        st.write("日期：", result["date_candidate"] or "待核对")
        st.write("合计（日元）：", result["total_amount_candidate"] or "待核对")
        st.text(result["items_text"])
    with structured:
        st.json(analysis["result"])
    st.download_button("下载 JSON", json.dumps(analysis["result"], ensure_ascii=False, indent=2),
                       file_name="receipt_ocr_result.json", mime="application/json")
    st.info("商品明细保留为 OCR 原文。切换至票据管理，可核对并保存本次结果。")
else:
    st.info("上传图片，查看检测、裁剪和 OCR 的完整过程。")
