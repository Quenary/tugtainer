#!/bin/bash
python -m venv .venv
source .venv/bin/activate
pip install -r agent/requirements.txt
pip install -r backend/requirements.txt