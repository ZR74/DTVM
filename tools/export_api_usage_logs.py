#!/usr/bin/env python3

from __future__ import annotations

import argparse
import csv
import json
import zipfile
from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from xml.sax.saxutils import escape
from zoneinfo import ZoneInfo


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_DIR = REPO_ROOT / "data" / "api_usage_exports"
LOCAL_TZ = ZoneInfo("Asia/Shanghai")

DETAIL_FIELDS = [
    "tool",
    "local_date",
    "local_time",
    "utc_timestamp",
    "session_id",
    "request_id",
    "model_provider",
    "model",
    "cwd",
    "input_tokens",
    "cached_input_tokens",
    "cache_creation_input_tokens",
    "cache_read_input_tokens",
    "output_tokens",
    "reasoning_output_tokens",
    "total_tokens",
    "source_file",
]

CODEX_SESSION_FIELDS = [
    "tool",
    "session_id",
    "first_local_date",
    "first_local_time",
    "last_local_date",
    "last_local_time",
    "first_utc_timestamp",
    "last_utc_timestamp",
    "model_provider",
    "model",
    "cwd",
    "originator",
    "source",
    "cli_version",
    "usage_record_count",
    "max_total_input_tokens",
    "max_total_cached_input_tokens",
    "max_total_output_tokens",
    "max_total_reasoning_output_tokens",
    "max_total_tokens",
    "source_file",
]


@dataclass
class ExportSummary:
    claude_requests: int = 0
    codex_usage_records: int = 0
    claude_total_tokens: int = 0
    codex_total_tokens: int = 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export Codex and Claude Code API usage metadata from local JSONL logs."
    )
    parser.add_argument("--start-date", default="2026-02-06")
    parser.add_argument("--end-date", default="2026-04-01")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    return parser.parse_args()


def parse_utc_timestamp(value: str | None) -> datetime | None:
    if not value:
        return None
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    dt = datetime.fromisoformat(text)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def within_local_date_range(utc_dt: datetime, start_local: datetime, end_local: datetime) -> bool:
    local_dt = utc_dt.astimezone(LOCAL_TZ)
    return start_local <= local_dt <= end_local


def fmt_local_date_time(utc_dt: datetime) -> tuple[str, str]:
    local_dt = utc_dt.astimezone(LOCAL_TZ)
    return local_dt.strftime("%Y-%m-%d"), local_dt.strftime("%H:%M:%S")


def utc_iso_z(utc_dt: datetime) -> str:
    return utc_dt.astimezone(UTC).isoformat().replace("+00:00", "Z")


def iter_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8", errors="replace") as handle:
        for raw_line in handle:
            line = raw_line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return rows


def token_int(value: Any) -> int:
    if value in (None, ""):
        return 0
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def blank_if_zero(value: int) -> str:
    return "" if value == 0 else str(value)


def write_csv(path: Path, rows: list[dict[str, str]], fieldnames: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def column_letter(index: int) -> str:
    out = ""
    while index > 0:
        index, rem = divmod(index - 1, 26)
        out = chr(65 + rem) + out
    return out


def excel_cell(value: Any) -> str:
    if value is None:
        return ""
    text = str(value)
    if text == "":
        return ""
    return f'<c t="inlineStr"><is><t>{escape(text)}</t></is></c>'


def make_sheet_xml(rows: list[list[Any]]) -> str:
    sheet_rows: list[str] = []
    for row_index, row in enumerate(rows, start=1):
        cells: list[str] = []
        for col_index, value in enumerate(row, start=1):
            cell_ref = f"{column_letter(col_index)}{row_index}"
            cell = excel_cell(value)
            if cell:
                cells.append(cell.replace("<c ", f'<c r="{cell_ref}" ', 1))
        sheet_rows.append(f'<row r="{row_index}">{"".join(cells)}</row>')
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        f"<sheetData>{''.join(sheet_rows)}</sheetData>"
        "</worksheet>"
    )


def write_xlsx(path: Path, sheets: list[tuple[str, list[dict[str, str]], list[str]]]) -> None:
    workbook_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        "<sheets>"
        + "".join(
            f'<sheet name="{escape(name)}" sheetId="{idx}" r:id="rId{idx}"/>'
            for idx, (name, _, _) in enumerate(sheets, start=1)
        )
        + "</sheets></workbook>"
    )
    workbook_rels_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        + "".join(
            (
                f'<Relationship Id="rId{idx}" '
                'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" '
                f'Target="worksheets/sheet{idx}.xml"/>'
            )
            for idx, _ in enumerate(sheets, start=1)
        )
        + "</Relationships>"
    )
    root_rels_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" '
        'Target="xl/workbook.xml"/>'
        "</Relationships>"
    )
    content_types_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/xl/workbook.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
        + "".join(
            f'<Override PartName="/xl/worksheets/sheet{idx}.xml" '
            'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
            for idx, _ in enumerate(sheets, start=1)
        )
        + "</Types>"
    )

    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", content_types_xml)
        zf.writestr("_rels/.rels", root_rels_xml)
        zf.writestr("xl/workbook.xml", workbook_xml)
        zf.writestr("xl/_rels/workbook.xml.rels", workbook_rels_xml)
        for idx, (_, rows, fieldnames) in enumerate(sheets, start=1):
            data = [fieldnames] + [[row.get(field, "") for field in fieldnames] for row in rows]
            zf.writestr(f"xl/worksheets/sheet{idx}.xml", make_sheet_xml(data))


def discover_codex_files() -> list[Path]:
    files = sorted(Path.home().joinpath(".codex", "sessions").glob("**/*.jsonl"))
    files.extend(sorted(Path.home().joinpath(".codex", "archived_sessions").glob("*.jsonl")))
    return files


def discover_claude_files() -> list[Path]:
    return sorted(Path.home().joinpath(".claude", "projects").glob("**/*.jsonl"))


def extract_codex_rows(
    start_local: datetime, end_local: datetime
) -> tuple[list[dict[str, str]], list[dict[str, str]], ExportSummary]:
    detail_rows: list[dict[str, str]] = []
    session_rows: list[dict[str, str]] = []
    session_acc: dict[str, dict[str, Any]] = defaultdict(dict)
    summary = ExportSummary()

    for path in discover_codex_files():
        session_meta: dict[str, Any] = {}
        current_model = ""
        for record in iter_jsonl(path):
            rec_type = record.get("type")
            payload = record.get("payload") or {}
            if rec_type == "session_meta":
                session_meta = payload
                continue
            if rec_type == "turn_context":
                current_model = str(payload.get("model") or current_model or "")
                continue
            if rec_type != "event_msg" or payload.get("type") != "token_count":
                continue
            info = payload.get("info") or {}
            last_usage = info.get("last_token_usage") or {}
            total_usage = info.get("total_token_usage") or {}
            utc_dt = parse_utc_timestamp(record.get("timestamp"))
            if utc_dt is None or not within_local_date_range(utc_dt, start_local, end_local):
                continue

            input_tokens = token_int(last_usage.get("input_tokens"))
            cached_input_tokens = token_int(last_usage.get("cached_input_tokens"))
            output_tokens = token_int(last_usage.get("output_tokens"))
            reasoning_output_tokens = token_int(last_usage.get("reasoning_output_tokens"))
            total_tokens = token_int(last_usage.get("total_tokens"))
            local_date, local_time = fmt_local_date_time(utc_dt)
            session_id = str(session_meta.get("id") or "")

            detail_rows.append(
                {
                    "tool": "codex",
                    "local_date": local_date,
                    "local_time": local_time,
                    "utc_timestamp": utc_iso_z(utc_dt),
                    "session_id": session_id,
                    "request_id": "",
                    "model_provider": str(session_meta.get("model_provider") or ""),
                    "model": current_model,
                    "cwd": str(session_meta.get("cwd") or ""),
                    "input_tokens": str(input_tokens),
                    "cached_input_tokens": str(cached_input_tokens),
                    "cache_creation_input_tokens": "",
                    "cache_read_input_tokens": "",
                    "output_tokens": str(output_tokens),
                    "reasoning_output_tokens": str(reasoning_output_tokens),
                    "total_tokens": str(total_tokens),
                    "source_file": str(path),
                }
            )
            summary.codex_usage_records += 1
            summary.codex_total_tokens += total_tokens

            acc = session_acc.setdefault(
                session_id or str(path),
                {
                    "tool": "codex",
                    "session_id": session_id,
                    "model_provider": str(session_meta.get("model_provider") or ""),
                    "model": current_model,
                    "cwd": str(session_meta.get("cwd") or ""),
                    "originator": str(session_meta.get("originator") or ""),
                    "source": str(session_meta.get("source") or ""),
                    "cli_version": str(session_meta.get("cli_version") or ""),
                    "usage_record_count": 0,
                    "max_total_input_tokens": 0,
                    "max_total_cached_input_tokens": 0,
                    "max_total_output_tokens": 0,
                    "max_total_reasoning_output_tokens": 0,
                    "max_total_tokens": 0,
                    "source_file": str(path),
                    "first_dt": utc_dt,
                    "last_dt": utc_dt,
                },
            )
            acc["usage_record_count"] += 1
            acc["model"] = acc["model"] or current_model
            acc["first_dt"] = min(acc["first_dt"], utc_dt)
            acc["last_dt"] = max(acc["last_dt"], utc_dt)
            acc["max_total_input_tokens"] = max(
                acc["max_total_input_tokens"], token_int(total_usage.get("input_tokens"))
            )
            acc["max_total_cached_input_tokens"] = max(
                acc["max_total_cached_input_tokens"],
                token_int(total_usage.get("cached_input_tokens")),
            )
            acc["max_total_output_tokens"] = max(
                acc["max_total_output_tokens"], token_int(total_usage.get("output_tokens"))
            )
            acc["max_total_reasoning_output_tokens"] = max(
                acc["max_total_reasoning_output_tokens"],
                token_int(total_usage.get("reasoning_output_tokens")),
            )
            acc["max_total_tokens"] = max(
                acc["max_total_tokens"], token_int(total_usage.get("total_tokens"))
            )

    for acc in session_acc.values():
        first_date, first_time = fmt_local_date_time(acc["first_dt"])
        last_date, last_time = fmt_local_date_time(acc["last_dt"])
        session_rows.append(
            {
                "tool": "codex",
                "session_id": acc["session_id"],
                "first_local_date": first_date,
                "first_local_time": first_time,
                "last_local_date": last_date,
                "last_local_time": last_time,
                "first_utc_timestamp": utc_iso_z(acc["first_dt"]),
                "last_utc_timestamp": utc_iso_z(acc["last_dt"]),
                "model_provider": acc["model_provider"],
                "model": acc["model"],
                "cwd": acc["cwd"],
                "originator": acc["originator"],
                "source": acc["source"],
                "cli_version": acc["cli_version"],
                "usage_record_count": str(acc["usage_record_count"]),
                "max_total_input_tokens": str(acc["max_total_input_tokens"]),
                "max_total_cached_input_tokens": str(acc["max_total_cached_input_tokens"]),
                "max_total_output_tokens": str(acc["max_total_output_tokens"]),
                "max_total_reasoning_output_tokens": str(acc["max_total_reasoning_output_tokens"]),
                "max_total_tokens": str(acc["max_total_tokens"]),
                "source_file": acc["source_file"],
            }
        )

    detail_rows.sort(key=lambda row: (row["utc_timestamp"], row["tool"], row["session_id"]))
    session_rows.sort(key=lambda row: (row["first_utc_timestamp"], row["session_id"]))
    return detail_rows, session_rows, summary


def extract_claude_rows(
    start_local: datetime, end_local: datetime
) -> tuple[list[dict[str, str]], ExportSummary]:
    detail_rows: list[dict[str, str]] = []
    seen_request_ids: set[tuple[str, str]] = set()
    summary = ExportSummary()

    for path in discover_claude_files():
        for record in iter_jsonl(path):
            if record.get("type") != "assistant":
                continue
            message = record.get("message")
            if not isinstance(message, dict):
                continue
            usage = message.get("usage")
            if not isinstance(usage, dict):
                continue
            utc_dt = parse_utc_timestamp(record.get("timestamp"))
            if utc_dt is None or not within_local_date_range(utc_dt, start_local, end_local):
                continue

            request_id = str(
                record.get("requestId")
                or message.get("requestId")
                or message.get("id")
                or record.get("uuid")
                or ""
            )
            session_id = str(record.get("sessionId") or "")
            dedupe_key = (session_id, request_id)
            if dedupe_key in seen_request_ids:
                continue
            seen_request_ids.add(dedupe_key)

            input_tokens = token_int(usage.get("input_tokens"))
            cache_creation_input_tokens = token_int(usage.get("cache_creation_input_tokens"))
            cache_read_input_tokens = token_int(usage.get("cache_read_input_tokens"))
            output_tokens = token_int(usage.get("output_tokens"))
            total_tokens = (
                input_tokens + cache_creation_input_tokens + cache_read_input_tokens + output_tokens
            )
            local_date, local_time = fmt_local_date_time(utc_dt)

            detail_rows.append(
                {
                    "tool": "claude",
                    "local_date": local_date,
                    "local_time": local_time,
                    "utc_timestamp": utc_iso_z(utc_dt),
                    "session_id": session_id,
                    "request_id": request_id,
                    "model_provider": "anthropic",
                    "model": str(message.get("model") or ""),
                    "cwd": str(record.get("cwd") or ""),
                    "input_tokens": str(input_tokens),
                    "cached_input_tokens": blank_if_zero(
                        cache_creation_input_tokens + cache_read_input_tokens
                    ),
                    "cache_creation_input_tokens": str(cache_creation_input_tokens),
                    "cache_read_input_tokens": str(cache_read_input_tokens),
                    "output_tokens": str(output_tokens),
                    "reasoning_output_tokens": "",
                    "total_tokens": str(total_tokens),
                    "source_file": str(path),
                }
            )
            summary.claude_requests += 1
            summary.claude_total_tokens += total_tokens

    detail_rows.sort(key=lambda row: (row["utc_timestamp"], row["tool"], row["session_id"]))
    return detail_rows, summary


def verify_csv(path: Path) -> tuple[int, list[str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.reader(handle)
        rows = list(reader)
    line_count = len(rows)
    header = rows[0] if rows else []
    return line_count, header


def verify_xlsx(path: Path) -> bool:
    if not path.exists():
        return False
    with zipfile.ZipFile(path) as zf:
        return "xl/worksheets/sheet1.xml" in set(zf.namelist())


def main() -> int:
    args = parse_args()
    start_local = datetime.fromisoformat(args.start_date).replace(
        hour=0, minute=0, second=0, microsecond=0, tzinfo=LOCAL_TZ
    )
    end_local = datetime.fromisoformat(args.end_date).replace(
        hour=23, minute=59, second=59, microsecond=999999, tzinfo=LOCAL_TZ
    )

    args.output_dir.mkdir(parents=True, exist_ok=True)
    stamp = f"{args.start_date}_to_{args.end_date}"
    detail_csv = args.output_dir / f"api_usage_detail_{stamp}.csv"
    codex_session_csv = args.output_dir / f"api_usage_codex_sessions_{stamp}.csv"
    detail_xlsx = args.output_dir / f"api_usage_detail_{stamp}.xlsx"

    codex_detail_rows, codex_session_rows, codex_summary = extract_codex_rows(
        start_local, end_local
    )
    claude_rows, claude_summary = extract_claude_rows(start_local, end_local)
    all_rows = sorted(
        codex_detail_rows + claude_rows,
        key=lambda row: (row["utc_timestamp"], row["tool"], row["session_id"], row["request_id"]),
    )

    write_csv(detail_csv, all_rows, DETAIL_FIELDS)
    write_csv(codex_session_csv, codex_session_rows, CODEX_SESSION_FIELDS)
    write_xlsx(
        detail_xlsx,
        [
            ("detail", all_rows, DETAIL_FIELDS),
            ("codex_sessions", codex_session_rows, CODEX_SESSION_FIELDS),
        ],
    )

    detail_line_count, detail_header = verify_csv(detail_csv)
    session_line_count, session_header = verify_csv(codex_session_csv)
    xlsx_ok = verify_xlsx(detail_xlsx)

    print(
        json.dumps(
            {
                "date_range_local": {
                    "start": start_local.isoformat(),
                    "end": end_local.isoformat(),
                },
                "files": {
                    "detail_csv": str(detail_csv),
                    "codex_session_csv": str(codex_session_csv),
                    "detail_xlsx": str(detail_xlsx),
                },
                "summary": {
                    "claude_requests": claude_summary.claude_requests,
                    "codex_usage_records": codex_summary.codex_usage_records,
                    "claude_total_tokens": claude_summary.claude_total_tokens,
                    "codex_total_tokens": codex_summary.codex_total_tokens,
                },
                "verification": {
                    "detail_csv_exists": detail_csv.exists(),
                    "detail_csv_lines": detail_line_count,
                    "detail_csv_header": detail_header,
                    "detail_csv_has_data_rows": detail_line_count > 1,
                    "codex_session_csv_exists": codex_session_csv.exists(),
                    "codex_session_csv_lines": session_line_count,
                    "codex_session_csv_header": session_header,
                    "xlsx_exists": detail_xlsx.exists(),
                    "xlsx_has_detail_sheet": xlsx_ok,
                },
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
