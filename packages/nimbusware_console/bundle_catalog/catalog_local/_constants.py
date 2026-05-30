from __future__ import annotations

import csv
import json
import re
from collections import Counter
from collections.abc import Mapping, Sequence
from datetime import datetime, timezone
from io import StringIO
from pathlib import Path
from typing import Any

BUNDLE_FAISS_INDEX_WORKFLOW_RELPATH = ".github/workflows/bundle_faiss_index.yml"

_LOCAL_CATALOG_RELPATH = "configs/bundles/catalog.yaml"

