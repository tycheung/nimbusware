from __future__ import annotations

from nimbusware_console.components.explainer_panel import hermes_download_filename


def test_hermes_download_filename_metrics_json() -> None:
    assert hermes_download_filename("slug", "ts", kind="metrics", ext="json") == (
        "hermes_slug_ts.json"
    )


def test_hermes_download_filename_explainer_csv() -> None:
    assert hermes_download_filename("slug", "ts", kind="explainer", ext="csv") == (
        "hermes_slug_explainer_ts.csv"
    )
