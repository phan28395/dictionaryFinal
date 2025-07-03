## config.py

import os
from pathlib import Path

# Base paths
SOURCE_PATH = r"E:\Company\database_final_BEST\data\source"
DATABASE_PATH = r"E:\Company\database_final_BEST\database"

# Ensure paths exist
Path(DATABASE_PATH).mkdir(parents=True, exist_ok=True)

# Input files
EXCEL_FILE = os.path.join(SOURCE_PATH, "wordFrequency.xlsx")
XML_FILE = os.path.join(SOURCE_PATH, "wn.xml")

# Output files
DATABASE_FILE = os.path.join(DATABASE_PATH, "dictionary.db")
JSON_FILE = os.path.join(DATABASE_PATH, "wordnet_processed.json")

# Processing parameters
BATCH_SIZE = 1000
MIN_WORD_LENGTH = 2
SAMPLE_ROWS = 5  # For testing, set to None for full processing

# Excel sheet names
SHEETS = {
    'lemmas': '1 lemmas',
    'subgenres': '2 subgenres',
    'wordforms': '3 wordForms'
}

# Logging
LOG_LEVEL = "INFO"
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

