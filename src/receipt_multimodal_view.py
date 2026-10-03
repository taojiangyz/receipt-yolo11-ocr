"""Explicit UI request; durable request tracking and explicit failed-call retry, suggestions kept separate from edits."""
import io
import streamlit as st
from PIL import Image
from src.receipt_multimodal import VisionConfig, recognize
from src.receipt_quality import REQUIRED


def render_multimodal(store, raw, assessment, *, analysis=None, record=None):
    payload = analysis['payload'] if analysis else record['image']
    attempt = store.get_multimodal_attempt(payload)
    config = None
    config_error = ''
    try:
        config = VisionConfig.from_env()
    except (ValueError, TypeError):
        config_error = '尚未配置可用的视觉模型，请按项目文档在本机设置。'
    retry = bool(attempt and attempt.get('status') == 'failed' and attempt.get('attempt_number', 1) < attempt.get('manual_retry_limit', 3))
    if assessment['needs_multimodal'] and (attempt is None or retry):
        st.caption('AI 可辅助核对店名、日期和总金额。点击后会向已配置的模型发送原图与相关裁剪图，可能产生费用；不自动重试；失败后可手动重试，默认最多三次。')
        if config:
            st.caption('使用模型：' + config.model)
        if config_error:
            st.info(config_error)
        if retry:
            st.warning('上次请求失败，服务端可能已处理或计费。再次发送可能产生额外费用。')
        label = '重试 AI 核对（可能产生费用）' if retry else '让 AI 辅助核对'
        if st.button(label, key='vision_' + (analysis['digest'] if analysis else record['digest']),
                     disabled=config is None):
            metadata = {'model': config.model, 'endpoint': config.endpoint,
                        'target_fields': assessment['target_fields']}
            if store.claim_multimodal_attempt(payload, metadata, retry=retry):
                with st.spinner('AI 正在核对…'):
                    try:
                        image = analysis['image'] if analysis else Image.open(io.BytesIO(payload))
                        crops = analysis.get('crops', {}) if analysis else {}
                        attempt = recognize(raw, image, crops, config)
                    except Exception as exc:
                        attempt = dict(status='failed', attempts=1, suggestions={},
                                       error_type=type(exc).__name__, **metadata)
                    store.finish_multimodal_attempt(payload, attempt)
            else:
                attempt = store.get_multimodal_attempt(payload)
    if not attempt:
        return
    if attempt['status'] == 'completed':
        st.info('AI 建议尚未确认。请对照原图，将需要采用的值填写到下方表单，再保存。')
        for name, suggestion in attempt.get('suggestions', {}).items():
            st.write(f"{REQUIRED.get(name, name)}：{suggestion['value'] or '无法确定'}")
            if suggestion.get('reason'):
                st.caption(suggestion['reason'])
        if attempt.get('rejected_fields'):
            st.warning('部分模型返回值格式无效，未作为建议显示。')
    elif attempt['status'] == 'started':
        st.warning('这张图片已有请求记录，可能仍在处理或曾被中断。为避免重复费用，不会自动重新发送；可以直接人工核对。')
    else:
        st.warning('AI 核对失败，原始 OCR 和人工编辑不受影响。请人工核对；不会自动重复请求。')
    if attempt.get('error_hint'):
        st.caption(attempt['error_hint'])
    if attempt.get('status') == 'failed' and attempt.get('attempt_number', 1) >= attempt.get('manual_retry_limit', 3):
        st.caption('已达到当前请求上限，请先解决配置或网络问题并人工核对。')
    with st.expander('AI 调用记录'):
        st.json(attempt)
