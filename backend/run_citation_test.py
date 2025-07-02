#!/usr/bin/env python3
import os
import sys
from dotenv import load_dotenv

# Load environment variables
env_path = os.path.join(os.path.dirname(__file__), '..', '.env')
load_dotenv(env_path)

# Ensure API key is loaded
if 'ANTHROPIC_API_KEY' not in os.environ:
    print("Loading API key from .env file...")
    with open(env_path, 'r') as f:
        for line in f:
            if line.startswith('ANTHROPIC_API_KEY='):
                key, value = line.strip().split('=', 1)
                os.environ[key] = value.strip('"').strip("'")
                print(f"Loaded {key}: ...{value[-4:]}")

# Run the test
os.system('python pdf_processing/test_citations.py')