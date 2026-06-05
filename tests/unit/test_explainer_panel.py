from __future__ import annotations

from nimbusware_console.components.explainer_panel import nimbusware_download_filename


def test_nimbusware_download_filename_metrics_json() -> None:
    assert nimbusware_download_filename("slug", "ts", kind="metrics", ext="json") == (
        "nimbusware_slug_ts.json"
    )


def test_nimbusware_download_filename_explainer_csv() -> None:
    assert nimbusware_download_filename("slug", "ts", kind="explainer", ext="csv") == (
        "nimbusware_slug_explainer_ts.csv"
    )
