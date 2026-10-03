"""Local receipt library. Original image/OCR and audit changes share a transaction."""
import csv
import hashlib
import io
import json
import re
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import date, datetime, timezone
from pathlib import Path

FIELDS = ("store", "date", "amount", "items", "category", "status")
from src.receipt_items import parse_items, normalize_items

STATUSES = ("待核对", "已核对")


def validate(values):
    errors = []
    if values.get("status") not in STATUSES:
        errors.append("状态无效")
    if values.get("date"):
        try:
            if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", values["date"]):
                raise ValueError
            date.fromisoformat(values["date"])
        except ValueError:
            errors.append("日期必须是有效的 YYYY-MM-DD")
    if values.get("amount") and not re.fullmatch(r"[0-9]{1,9}", values["amount"]):
        errors.append("金额应为非负整数日元，不含逗号或货币符号")
    if values.get("status") == "已核对":
        for field, label in (("store", "商户"), ("date", "日期"), ("amount", "金额")):
            if not values.get(field, "").strip():
                errors.append(f"已核对票据必须填写{label}")
    return errors


def candidates(raw):
    return dict(store=raw.get("store_name_candidate", ""), date=raw.get("date_candidate", ""),
                amount=raw.get("total_amount_candidate", ""), items=raw.get("items_text", ""),
                category="未分类", status="待核对", line_items=parse_items(raw.get("items_text", ""))["rows"])


class ReceiptStore:
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connection() as db:
            db.executescript('''
                CREATE TABLE IF NOT EXISTS receipts (
                    id TEXT PRIMARY KEY, digest TEXT UNIQUE NOT NULL,
                    filename TEXT NOT NULL, image BLOB NOT NULL, raw_json TEXT NOT NULL,
                    values_json TEXT NOT NULL, revision INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT NOT NULL, updated_at TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS multimodal_attempts (
                    digest TEXT PRIMARY KEY, result_json TEXT NOT NULL,
                    created_at TEXT NOT NULL, updated_at TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS changes (
                    id INTEGER PRIMARY KEY, receipt_id TEXT NOT NULL,
                    before_json TEXT, after_json TEXT NOT NULL, changed_at TEXT NOT NULL,
                    FOREIGN KEY(receipt_id) REFERENCES receipts(id));
            ''')

    @contextmanager
    def connection(self):
        db = sqlite3.connect(self.path, timeout=15)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys=ON")
        try:
            with db:
                yield db
        finally:
            db.close()

    def get_multimodal_attempt(self, payload):
        digest = hashlib.sha256(payload).hexdigest()
        with self.connection() as db:
            row = db.execute("SELECT result_json FROM multimodal_attempts WHERE digest=?", (digest,)).fetchone()
        return json.loads(row["result_json"]) if row else None

    def claim_multimodal_attempt(self, payload, metadata):
        """Reserve before sending; UNIQUE digest prevents duplicate calls across reruns/restarts."""
        digest = hashlib.sha256(payload).hexdigest()
        now = datetime.now(timezone.utc).isoformat()
        initial = dict(metadata, status="started", attempts=1, suggestions={})
        with self.connection() as db:
            inserted = db.execute("INSERT OR IGNORE INTO multimodal_attempts VALUES (?,?,?,?)",
                                  (digest, json.dumps(initial, ensure_ascii=False), now, now))
        return inserted.rowcount == 1

    def finish_multimodal_attempt(self, payload, result):
        digest = hashlib.sha256(payload).hexdigest()
        now = datetime.now(timezone.utc).isoformat()
        with self.connection() as db:
            db.execute("UPDATE multimodal_attempts SET result_json=?,updated_at=? WHERE digest=?",
                       (json.dumps(result, ensure_ascii=False), now, digest))

    def find_digest(self, payload):
        with self.connection() as db:
            row = db.execute("SELECT id FROM receipts WHERE digest=?",
                             (hashlib.sha256(payload).hexdigest(),)).fetchone()
        return row["id"] if row else None

    def save(self, values, *, payload=None, filename="", raw=None, receipt_id=None, revision=None):
        line_items = normalize_items(values.get("line_items", []))
        values = {field: str(values.get(field, "")).strip() for field in FIELDS}
        values["line_items"] = line_items
        errors = validate(values)
        if errors:
            raise ValueError("；".join(errors))
        encoded = json.dumps(values, ensure_ascii=False)
        now = datetime.now(timezone.utc).isoformat()
        with self.connection() as db:
            before = None
            if receipt_id:
                row = db.execute("SELECT * FROM receipts WHERE id=?", (receipt_id,)).fetchone()
                if not row or row["revision"] != revision:
                    raise ValueError("票据已被其他页面更新，请重新打开后再保存")
                before = row["values_json"]
                changed = db.execute("UPDATE receipts SET values_json=?, updated_at=?, revision=revision+1 "
                                     "WHERE id=? AND revision=?", (encoded, now, receipt_id, revision))
                if changed.rowcount != 1:
                    raise ValueError("票据已更新，请重新打开")
            else:
                if not payload or raw is None:
                    raise ValueError("缺少原始图片或识别结果")
                receipt_id = uuid.uuid4().hex
                try:
                    db.execute("INSERT INTO receipts VALUES (?,?,?,?,?,?,1,?,?)",
                               (receipt_id, hashlib.sha256(payload).hexdigest(), Path(filename).name,
                                payload, json.dumps(raw, ensure_ascii=False), encoded, now, now))
                except sqlite3.IntegrityError as exc:
                    raise ValueError("这张图片已经保存，请在历史票据中打开修改") from exc
            db.execute("INSERT INTO changes(receipt_id,before_json,after_json,changed_at) VALUES (?,?,?,?)",
                       (receipt_id, before, encoded, now))
        return receipt_id

    def get(self, receipt_id):
        with self.connection() as db:
            row = db.execute("SELECT * FROM receipts WHERE id=?", (receipt_id,)).fetchone()
        if row is None:
            raise ValueError("票据不存在")
        result = dict(row)
        result["values"] = json.loads(result.pop("values_json"))
        result["raw"] = json.loads(result.pop("raw_json"))
        return result

    def list(self, query="", status="全部", start="", end=""):
        with self.connection() as db:
            rows = db.execute("SELECT id,filename,values_json,updated_at FROM receipts ORDER BY updated_at DESC").fetchall()
        result = []
        for row in rows:
            values = json.loads(row["values_json"])
            if query.casefold() not in (values["store"] + " " + values["items"] + " " + values["category"]).casefold():
                continue
            if status != "全部" and values["status"] != status:
                continue
            if start and (not values["date"] or values["date"] < start):
                continue
            if end and (not values["date"] or values["date"] > end):
                continue
            result.append(dict(id=row["id"], filename=row["filename"], **values, updated_at=row["updated_at"]))
        return result

    def history(self, receipt_id):
        with self.connection() as db:
            rows = db.execute("SELECT before_json,after_json,changed_at FROM changes WHERE receipt_id=? ORDER BY id DESC",
                              (receipt_id,)).fetchall()
        return [dict(before=json.loads(r["before_json"]) if r["before_json"] else None,
                     after=json.loads(r["after_json"]), changed_at=r["changed_at"]) for r in rows]


def export_csv(rows):
    output = io.StringIO(newline="")
    fields = ("id", "filename", *FIELDS, "line_items", "updated_at")
    writer = csv.DictWriter(output, fieldnames=fields)
    writer.writeheader()
    for row in rows:
        row = dict(row, line_items=json.dumps(row.get("line_items", []), ensure_ascii=False))
        # Avoid interpreting untrusted OCR text as a spreadsheet formula.
        safe = {key: ("'" + str(row.get(key, "")) if str(row.get(key, "")).lstrip().startswith(("=", "+", "-", "@"))
                      or str(row.get(key, "")).startswith(("\t", "\r", "\n")) else row.get(key, "")) for key in fields}
        writer.writerow(safe)
    return output.getvalue().encode("utf-8-sig")


def export_items_csv(rows):
    """One reviewed/candidate item per row, linked to the receipt's review status."""
    output = io.StringIO(newline="")
    fields = ("receipt_id", "store", "date", "status", "name", "line_total")
    writer = csv.DictWriter(output, fieldnames=fields)
    writer.writeheader()
    for receipt in rows:
        for item in receipt.get("line_items", []):
            row = dict(receipt_id=receipt["id"], store=receipt["store"], date=receipt["date"],
                       status=receipt["status"], **item)
            for field in fields:
                value = str(row.get(field, ""))
                row[field] = "'" + value if value.lstrip().startswith(("=", "+", "-", "@")) or value.startswith(("\t", "\r", "\n")) else value
            writer.writerow(row)
    return output.getvalue().encode("utf-8-sig")
