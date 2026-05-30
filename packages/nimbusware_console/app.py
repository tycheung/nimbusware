"""Nimbusware Streamlit operator console entrypoint."""

from __future__ import annotations

from nimbusware_env import load_dotenv

load_dotenv()

import streamlit as st

from nimbusware_console.main import render_main

st.set_page_config(page_title="Nimbusware Console", layout="wide")
render_main()
