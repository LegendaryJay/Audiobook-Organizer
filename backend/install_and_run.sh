#!/bin/bash

# Installation script for Audiobook Organizer Python backend

echo "Installing Python dependencies..."
pip install -r requirements.txt

echo "Creating data directories..."
mkdir -p metadata
mkdir -p covers

echo "Starting the Flask backend..."
python app.py
