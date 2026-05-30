"""Nimbusware Admin Console Streamlit entrypoint."""

from __future__ import annotations

from nimbusware_env import load_dotenv

load_dotenv()

import streamlit as st

from nimbusware_console.admin_gate import require_admin_session
from nimbusware_console.main import render_main

st.set_page_config(page_title="Nimbusware Admin Console", layout="wide")
require_admin_session()
render_main()
