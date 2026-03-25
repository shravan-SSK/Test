#!/usr/bin/env bash

echo "Installing dependencies..."
pip install -r requirements.txt

echo "Starting Sales CRM..."
cd sales-crm/backend
exec python main.py
