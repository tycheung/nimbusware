#!/usr/bin/env python3
"""Build optional FAISS index for ``configs/bundles/catalog.yaml``.

Requires: ``poetry install --with faiss`` (``faiss-cpu`` + ``numpy``).

Writes ``faiss.index`` + ``bundle_order.json`` + ``embeddings.npy`` under the output directory.
Defaults match the CI **bundle_faiss_index** workflow (see
``.github/workflows/bundle_faiss_index.yml``):
``poetry run python`` ``scripts/build_bundle_faiss_index.py`` from repo root.
Local wrappers (same commands): ``scripts/build_bundle_faiss_index.ps1`` (Windows) and
``scripts/build_bundle_faiss_index.sh`` (POSIX).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]


def _embed(text: str) -> np.ndarray:
    h = hashlib.sha256(text.encode()).digest()
    vec = np.frombuffer(h[:32], dtype=np.uint8).astype(np.float32)
    return vec / (float(np.linalg.norm(vec)) + 1e-9)


def build_bundle_faiss_index(*, catalog_path: Path, out_dir: Path) -> int:
    try:
        import faiss  # type: ignore[import-not-found]
    except ImportError:
        print("faiss not installed; run: poetry install --with faiss", file=sys.stderr)
        return 1

    from nimbusware_extensions import BundleCatalog

    out_dir.mkdir(parents=True, exist_ok=True)

    cat = BundleCatalog(catalog_path)
    bundles = cat.list_bundles()
    if not bundles:
        print("No bundles in catalog", file=sys.stderr)
        return 1
    order = [str(b["id"]) for b in bundles if b.get("id")]
    mat = np.stack([_embed(bid) for bid in order], axis=0).astype(np.float32)
    dim = mat.shape[1]
    index = faiss.IndexFlatIP(dim)
    index.add(mat)
    faiss.write_index(index, str(out_dir / "faiss.index"))
    (out_dir / "bundle_order.json").write_text(json.dumps(order), encoding="utf-8")
    np.save(out_dir / "embeddings.npy", mat)
    print(f"Wrote FAISS index for {len(order)} bundles under {out_dir}")
    return 0


def _build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Build optional FAISS index for bundle catalog search.",
    )
    p.add_argument(
        "--repo-root",
        type=Path,
        default=ROOT,
        help="Repository root for default --catalog / --out-dir paths (default: script parent)",
    )
    p.add_argument(
        "--catalog",
        type=Path,
        default=None,
        help="Path to catalog.yaml (default: <repo-root>/configs/bundles/catalog.yaml)",
    )
    p.add_argument(
        "--out-dir",
        type=Path,
        default=None,
        help="Output directory for faiss.index + bundle_order.json (default: "
        "<repo-root>/configs/bundles/index)",
    )
    return p


def main(argv: list[str] | None = None) -> int:
    args = _build_arg_parser().parse_args(argv)
    repo = args.repo_root.resolve()
    catalog = (args.catalog or repo / "configs" / "bundles" / "catalog.yaml").resolve()
    out_dir = (args.out_dir or repo / "configs" / "bundles" / "index").resolve()
    return build_bundle_faiss_index(catalog_path=catalog, out_dir=out_dir)


if __name__ == "__main__":
    raise SystemExit(main())
