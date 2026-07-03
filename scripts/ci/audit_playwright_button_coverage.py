#!/usr/bin/env python3

from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
UI_ROOTS = (
    ROOT / "packages" / "maker_web",
    ROOT / "packages" / "admin_ui",
)
PLAYWRIGHT_DIR = ROOT / "tests" / "e2e" / "web"
DEFAULT_OUT = ROOT / "tests" / "web" / "playwright_button_inventory.yaml"

BUTTON_TESTID_RE = re.compile(
    r"<button\b[^>]*\bdata-testid=[\"']([^\"']+)[\"']",
    re.IGNORECASE,
)
DATASET_TESTID_RE = re.compile(
    r"\.dataset\.testid\s*=\s*[\"']([^\"']+)[\"']",
)
ROLE_BUTTON_RE = re.compile(
    r"<button\b[^>]*>([^<]{1,80})</button>",
    re.IGNORECASE,
)
SPEC_CLICK_TESTID_RE = re.compile(
    r"getByTestId\(\s*[`\"']([^`\"']+)[`\"']\s*\)\s*\.click\(",
)
SPEC_CLICK_TESTID_CHAIN_RE = re.compile(
    r"getByTestId\(\s*[`\"']([^`\"']+)[`\"']\s*\)\s*\.\s*first\(\)\s*;",
)
SPEC_VISIBLE_TESTID_RE = re.compile(
    r"getByTestId\(\s*[`\"']([^`\"']+)[`\"']\s*\)[^;\n]*\.toBeVisible\(",
)
SPEC_ROLE_CLICK_RE = re.compile(
    r'getByRole\(\s*["\']button["\']\s*,\s*\{\s*name:\s*["\']([^"\']+)["\']\s*\}\s*\)'
    r"(?:\s*\.\s*first\(\))?\s*\.click\(",
)


@dataclass(frozen=True)
class ButtonRow:
    test_id: str
    app: str
    source: str
    label: str = ""


def _rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def _app_for(path: Path) -> str:
    return "maker" if "maker_web" in path.parts else "admin"


def _scan_ui_buttons() -> list[ButtonRow]:
    rows: list[ButtonRow] = []
    seen: set[str] = set()
    for root in UI_ROOTS:
        if not root.is_dir():
            continue
        for path in root.rglob("*"):
            if path.suffix not in {".js", ".tsx", ".ts", ".html"}:
                continue
            text = path.read_text(encoding="utf-8", errors="replace")
            for match in BUTTON_TESTID_RE.finditer(text):
                tid = match.group(1).strip()
                if not tid or tid in seen:
                    continue
                seen.add(tid)
                label = ""
                for role_match in ROLE_BUTTON_RE.finditer(text):
                    if tid in role_match.group(0):
                        label = role_match.group(1).strip()
                        break
                rows.append(
                    ButtonRow(
                        test_id=tid,
                        app=_app_for(path),
                        source=_rel(path),
                        label=label,
                    )
                )
            for match in DATASET_TESTID_RE.finditer(text):
                tid = match.group(1).strip()
                if not tid or tid in seen:
                    continue
                seen.add(tid)
                rows.append(
                    ButtonRow(
                        test_id=tid,
                        app=_app_for(path),
                        source=_rel(path),
                        label="(dynamic)",
                    )
                )
    rows.sort(key=lambda r: (r.app, r.test_id))
    return rows


def _scan_playwright_usage() -> tuple[dict[str, list[str]], dict[str, list[str]]]:
    clicked: dict[str, list[str]] = {}
    visible: dict[str, list[str]] = {}
    if not PLAYWRIGHT_DIR.is_dir():
        return clicked, visible
    for spec in sorted(PLAYWRIGHT_DIR.glob("*.spec.ts")):
        rel = _rel(spec)
        text = spec.read_text(encoding="utf-8", errors="replace")
        spec_clicked: set[str] = set(SPEC_CLICK_TESTID_RE.findall(text))
        if ".click(" in text:
            for tid in SPEC_CLICK_TESTID_CHAIN_RE.findall(text):
                spec_clicked.add(tid)
        for tid in spec_clicked:
            clicked.setdefault(tid, []).append(rel)
        for match in SPEC_VISIBLE_TESTID_RE.finditer(text):
            visible.setdefault(match.group(1), []).append(rel)
    return clicked, visible


def build_inventory() -> dict:
    buttons = _scan_ui_buttons()
    clicked, visible = _scan_playwright_usage()
    entries = []
    click_count = 0
    visible_only_count = 0
    for row in buttons:
        click_specs = sorted(set(clicked.get(row.test_id, [])))
        visible_specs = sorted(
            set(visible.get(row.test_id, [])) - set(click_specs),
        )
        if click_specs:
            click_count += 1
        elif visible_specs:
            visible_only_count += 1
        entries.append(
            {
                "test_id": row.test_id,
                "app": row.app,
                "source": row.source,
                "label": row.label,
                "clicked_in": click_specs,
                "visible_only_in": visible_specs,
            }
        )
    unwired = sum(1 for e in entries if not e["clicked_in"] and not e["visible_only_in"])
    total = len(entries)
    return {
        "summary": {
            "total_buttons": total,
            "clicked": click_count,
            "visible_only": visible_only_count,
            "unwired": unwired,
            "click_ratio": round(click_count / total, 4) if total else 0.0,
        },
        "buttons": entries,
    }


def _dump(data: dict) -> str:
    return yaml.safe_dump(data, sort_keys=False, allow_unicode=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Audit Playwright button coverage")
    parser.add_argument(
        "--out",
        type=Path,
        default=DEFAULT_OUT,
        help="Inventory YAML path",
    )
    parser.add_argument(
        "--write",
        action="store_true",
        help="Write inventory YAML",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Fail if inventory on disk is stale",
    )
    args = parser.parse_args(argv)
    data = build_inventory()
    rendered = _dump(data)
    summary = data["summary"]
    print(
        "playwright buttons: "
        f"{summary['total_buttons']} total, "
        f"{summary['clicked']} clicked, "
        f"{summary['visible_only']} visible-only, "
        f"{summary['unwired']} unwired "
        f"({summary['click_ratio']:.0%} click ratio)"
    )
    if args.write:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(rendered, encoding="utf-8")
        print(f"wrote {args.out.relative_to(ROOT)}")
    if args.check:
        if not args.out.is_file():
            print(f"missing inventory: {args.out}")
            return 1
        on_disk = args.out.read_text(encoding="utf-8")
        if on_disk != rendered:
            print(f"stale inventory: run poetry run python {_rel(Path(__file__))} --write")
            return 1
        print("inventory fresh")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
