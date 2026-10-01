import streamlit as st
from src.receipt_batch import enqueue, process, save_pending, refresh_saved
from src.receipt_pipeline import analyze_image
from src.receipt_store import candidates

LABELS = {'pending': '等待识别', 'ready': '待保存', 'failed': '识别失败', 'saved': '已保存'}


def render_batch(store, editor):
    st.subheader('批量处理小票')
    st.caption('每批最多 10 张，每张不超过 10 MB。队列仅保留在当前会话；刷新或关闭前请保存结果。')
    queue = st.session_state.setdefault('receipt_batch', {})
    uploads = st.file_uploader('选择多张小票', type=['jpg', 'jpeg', 'png'],
                               accept_multiple_files=True, key='batch_uploads')
    if st.button('加入处理队列', disabled=not uploads):
        try:
            added = enqueue(queue, [(f.name, f.getvalue()) for f in uploads], store)
            st.success(f'已加入 {added} 张，内容相同的图片自动跳过。')
        except ValueError as exc:
            st.error(str(exc))
    refresh_saved(queue, store)
    if not queue:
        st.info('选择图片并加入队列，然后开始批量识别。')
        return
    if st.button('识别等待中的小票', type='primary', disabled=not any(e['status'] == 'pending' for e in queue.values())):
        bar = st.progress(0, text='准备识别…')
        process(queue, analyze_image, store,
                progress=lambda done, total, name: bar.progress(done / total, text=f'{done}/{total} · {name or "处理完成"}'))
    st.dataframe([{'文件': e['filename'], '状态': LABELS[e['status']], '尝试次数': e['attempts'],
                   '说明': e['error'], '图片编号': e['digest'][:8]} for e in queue.values()], hide_index=True)
    for digest, entry in queue.items():
        if entry['status'] == 'failed':
            if st.button(f'重试 {entry["filename"]} · {digest[:8]}', key='retry_' + digest):
                with st.spinner(f'正在重试 {entry["filename"]}…'):
                    process(queue, analyze_image, store, retry_id=digest)
                st.rerun()
    ready = [digest for digest, entry in queue.items() if entry['status'] == 'ready']
    if ready:
        st.caption('可逐张核对保存，也可先全部保存为“待核对”，随后到历史票据中修正。')
        if st.button('将成功结果保存为待核对'):
            count = save_pending(queue, store)
            st.session_state['batch_notice'] = f'本次保存 {count} 张；有错误的结果仍留在队列，可再次保存。'
            st.rerun()
        selected = st.selectbox('选择要核对的小票', ready,
                                format_func=lambda d: f'{queue[d]["filename"]} · {d[:8]}')
        analysis = queue[selected]['analysis']
        editor(candidates(analysis['result']), analysis['image'], analysis['result'],
               'batch_review_' + selected, analysis=analysis)
    if st.session_state.get('batch_notice'):
        st.info(st.session_state.pop('batch_notice'))
    st.caption('清空队列会丢弃未保存的识别结果，已保存的历史票据不受影响。')
    if st.button('清空本次队列'):
        st.session_state['receipt_batch'] = {}
        st.rerun()
