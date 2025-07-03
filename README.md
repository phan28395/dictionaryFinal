# Dictionary Database Builder Package

## Project Structure
```
E:\Company\database_final_BEST\
├── data\
│   └── source\
│       ├── wordFrequency.xlsx
│       └── wn.xml
├── database\
│   └── dictionary.db (output)
└── scripts\
    ├── phase1_excel_to_db.py
    ├── phase2_xml_to_json.py
    ├── phase3_json_to_db.py
    ├── build_complete.py
    └── config.py
```

---

## README.md

# Dictionary Database Builder

A three-phase pipeline to build a comprehensive dictionary database from Excel frequency data and WordNet XML.

## Quick Start

```bash
cd E:\Company\database_final_BEST\scripts
python build_complete.py
```

## Pipeline Overview

### Phase 1: Excel → Database
- **Input**: `wordFrequency.xlsx`
- **Output**: SQLite database with lemmas, word forms, and frequency data
- **Creates**: Base database structure with frequency information

### Phase 2: XML → JSON
- **Input**: WordNet XML (`wn.xml`)
- **Output**: Structured JSON with definitions, synonyms, hypernyms
- **Purpose**: Extract and structure WordNet data for easier processing

### Phase 3: JSON → Database
- **Input**: JSON from Phase 2
- **Output**: Complete database with definitions and cross-references
- **Adds**: Definitions, synonyms, clickable word references

## Configuration

Edit `config.py` to change paths or parameters:

```python
# Paths
SOURCE_PATH = r"E:\Company\database_final_BEST\data\source"
DATABASE_PATH = r"E:\Company\database_final_BEST\database"

# Processing parameters
SAMPLE_ROWS = 5  # For testing with smaller datasets
MIN_WORD_LENGTH = 2  # Minimum word length for cross-references
```

## Individual Phase Usage

```bash
# Run only Phase 1
python phase1_excel_to_db.py

# Run only Phase 2
python phase2_xml_to_json.py

# Run only Phase 3
python phase3_json_to_db.py
```

## Modifying the Pipeline

### To change input files:
- Edit file names in `config.py`

### To add new data sources:
- Create a new phase script following the pattern
- Add to `build_complete.py`

### To modify database schema:
- Edit schema in `phase1_excel_to_db.py`
- Update corresponding insert methods

---





## Usage Instructions

1. **Place your source files** in:
   - `E:\Company\database_final_BEST\data\source\wordFrequency.xlsx`
   - `E:\Company\database_final_BEST\data\source\wn.xml`

2. **Navigate to scripts folder**:
   ```bash
   cd E:\Company\database_final_BEST\scripts
   ```

3. **Run the complete pipeline**:
   ```bash
   python build_complete.py
   ```

4. **Find your database** at:
   - `E:\Company\database_final_BEST\database\dictionary.db`

The pipeline will create a comprehensive dictionary database with:
- Word frequencies and rankings
- Inflected forms
- Definitions with examples
- Synonyms and hypernyms
- Cross-references between words
- Context-based frequencies (domains and subgenres)