#!/bin/bash
# Script to create the project directory structure

# Create main directories
mkdir -p components/metrics
mkdir -p components/ml
mkdir -p components/remediation
mkdir -p components/streaming
mkdir -p components/monitoring
mkdir -p components/pipeline
mkdir -p data
mkdir -p models
mkdir -p static

# Create __init__.py files to make directories as packages
touch components/__init__.py
touch components/metrics/__init__.py
touch components/ml/__init__.py
touch components/remediation/__init__.py
touch components/streaming/__init__.py
touch components/monitoring/__init__.py
touch components/pipeline/__init__.py

# Create placeholder files for remaining modules
touch components/metrics/__init__.py
touch components/ml/__init__.py
touch components/ml/training.py
touch components/ml/evaluation.py
touch components/remediation/__init__.py
touch components/remediation/actions.py
touch components/remediation/gpt.py
touch components/streaming/__init__.py
touch components/streaming/consumer.py
touch components/monitoring/__init__.py
touch components/pipeline/__init__.py

echo "Project directory structure created successfully!"