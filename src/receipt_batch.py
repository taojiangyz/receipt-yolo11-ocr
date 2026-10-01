"""Session-local sequential batch processing, with per-image retry and deduplication."""
import hashlib

MAX_FILES = 10
MAX_FILE_BYTES = 10 * 1024 * 1024


def enqueue(queue, files, store):
    """Validate the whole addition before mutating the queue."""
    additions = {}
    for filename, payload in files:
        if not payload or len(payload) > MAX_FILE_BYTES:
            raise ValueError(f'{filename}：图片为空或超过 10 MB，请压缩后上传')
        digest = hashlib.sha256(payload).hexdigest()
        if digest not in queue and digest not in additions:
            saved_id = store.find_digest(payload)
            additions[digest] = dict(digest=digest, filename=filename, payload=payload,
                                     status='saved' if saved_id else 'pending',
                                     saved_id=saved_id, analysis=None, attempts=0, error='')
    if len(queue) + len(additions) > MAX_FILES:
        raise ValueError('每批最多 10 张不同图片，请先保存当前结果，再清空队列后上传下一批')
    queue.update(additions)
    return len(additions)


def process(queue, analyze, store, *, retry_id=None, progress=None):
    targets = [entry for digest, entry in queue.items()
               if (digest == retry_id and entry['status'] == 'failed')
               or (retry_id is None and entry['status'] == 'pending')]
    for i, entry in enumerate(targets):
        if progress:
            progress(i, len(targets), entry['filename'])
        try:
            existing = store.find_digest(entry['payload'])
            if existing:
                entry.update(status='saved', saved_id=existing, error='')
                continue
            entry['attempts'] += 1
            analysis = analyze(entry['payload'], entry['filename'])
            entry.update(status='ready', analysis=analysis, error='')
        except Exception as exc:
            entry.update(status='failed', error=str(exc))
    if progress and targets:
        progress(len(targets), len(targets), '')


def save_pending(queue, store):
    from src.receipt_store import candidates
    saved = 0
    for entry in queue.values():
        if entry['status'] != 'ready':
            continue
        try:
            existing = store.find_digest(entry['payload'])
            if existing:
                entry.update(status='saved', saved_id=existing, error='')
                continue
            raw = entry['analysis']['result']
            receipt_id = store.save(candidates(raw), payload=entry['payload'], filename=entry['filename'], raw=raw)
            entry.update(status='saved', saved_id=receipt_id, error='')
            saved += 1
        except Exception as exc:
            # A storage error must not discard a successful recognition or rerun OCR.
            entry['error'] = f'保存失败：{exc}'
    return saved


def refresh_saved(queue, store):
    for entry in queue.values():
        if entry['status'] == 'ready':
            existing = store.find_digest(entry['payload'])
            if existing:
                entry.update(status='saved', saved_id=existing, error='')
