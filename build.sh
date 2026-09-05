#!/usr/bin/env bash
set -e
pip install -r requirements.txt
pip uninstall -y discord.py || true
pip install --force-reinstall "py-cord[voice]>=2.6.0" PyNaCl>=1.5.0
