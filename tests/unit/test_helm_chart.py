from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

CHART = Path("charts/nimbusware")


def test_helm_chart_files_exist() -> None:
    assert (CHART / "Chart.yaml").is_file()
    assert (CHART / "values.yaml").is_file()
    templates = list((CHART / "templates").glob("*.yaml"))
    assert len(templates) >= 5


def test_helm_lint_and_template_when_available() -> None:
    if shutil.which("helm") is None:
        return
    subprocess.run(["helm", "lint", str(CHART)], check=True, capture_output=True)
    out = subprocess.run(
        ["helm", "template", "nimbusware-test", str(CHART)],
        check=True,
        capture_output=True,
        text=True,
    )
    rendered = out.stdout
    assert "kind: Deployment" in rendered
    assert "nimbusware-api" in rendered
