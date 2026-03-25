#!/usr/bin/env bash
set -e

echo "Installing dependencies..."
pip install -r sales-crm/backend/requirements.txt -q

echo "Starting Sales CRM..."
cd sales-crm/backend
exec python main.py
