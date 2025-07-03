
## phase1_excel_to_db.py


import pandas as pd
import sqlite3
import json
from pathlib import Path
import logging
from typing import Dict, List, Tuple, Optional
import re
import sys
import os

# Add parent directory to path for config import
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import *

# Set up logging
logging.basicConfig(level=LOG_LEVEL, format=LOG_FORMAT)
logger = logging.getLogger(__name__)

class DictionaryDatabaseBuilder:
    def __init__(self, excel_file_path: str = EXCEL_FILE, db_path: str = DATABASE_FILE):
        self.excel_file_path = excel_file_path
        self.db_path = db_path
        self.conn = None
        
    def create_database_schema(self):
        """Create all database tables with proper schema"""
        schema_sql = """
        -- Languages table
        CREATE TABLE IF NOT EXISTS languages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code VARCHAR(5) NOT NULL UNIQUE,
            name VARCHAR(100) NOT NULL
        );
        
        -- Lemmas table (core table)
        CREATE TABLE IF NOT EXISTS lemmas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            lemma VARCHAR(255) NOT NULL,
            language_id INTEGER NOT NULL,
            lemma_frequency INTEGER DEFAULT 0,
            lemma_rank INTEGER DEFAULT 0,
            dispersion_score REAL DEFAULT 0.0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (language_id) REFERENCES languages(id),
            UNIQUE(lemma, language_id)
        );
        
        -- Inflected forms table
        CREATE TABLE IF NOT EXISTS inflected_forms (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            lemma_id INTEGER NOT NULL,
            form VARCHAR(255) NOT NULL,
            pos VARCHAR(50) NOT NULL,
            form_frequency INTEGER DEFAULT 0,
            form_rank INTEGER DEFAULT 0,
            inflection_type VARCHAR(100),
            grammatical_info TEXT,
            FOREIGN KEY (lemma_id) REFERENCES lemmas(id),
            UNIQUE(form, lemma_id, pos)
        );
        
        -- Context frequencies table
        CREATE TABLE IF NOT EXISTS context_frequencies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            lemma_id INTEGER NOT NULL,
            pos VARCHAR(50) NOT NULL,
            context_type VARCHAR(100) NOT NULL,
            context_name VARCHAR(100) NOT NULL,
            frequency INTEGER DEFAULT 0,
            context_metadata TEXT,
            FOREIGN KEY (lemma_id) REFERENCES lemmas(id)
        );
        
        -- Definitions table
        CREATE TABLE IF NOT EXISTS definitions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            lemma_id INTEGER NOT NULL,
            pos VARCHAR(50) NOT NULL,
            definition_text TEXT,
            definition_order INTEGER DEFAULT 1,
            example_sentence TEXT,
            hypernyms TEXT,
            FOREIGN KEY (lemma_id) REFERENCES lemmas(id)
        );
        
        -- Word references table
        CREATE TABLE IF NOT EXISTS word_references (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_definition_id INTEGER NOT NULL,
            referenced_lemma_id INTEGER NOT NULL,
            word_position INTEGER NOT NULL,
            word_text VARCHAR(255) NOT NULL,
            reference_type VARCHAR(50) DEFAULT 'definition',
            FOREIGN KEY (source_definition_id) REFERENCES definitions(id),
            FOREIGN KEY (referenced_lemma_id) REFERENCES lemmas(id)
        );
        
        -- Synonyms table
        CREATE TABLE IF NOT EXISTS synonyms (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            lemma_id INTEGER NOT NULL,
            synonym_lemma_id INTEGER NOT NULL,
            pos_specific VARCHAR(50),
            similarity_score DECIMAL(4,3) DEFAULT 0.0,
            FOREIGN KEY (lemma_id) REFERENCES lemmas(id),
            FOREIGN KEY (synonym_lemma_id) REFERENCES lemmas(id)
        );
        
        -- Pronunciations table
        CREATE TABLE IF NOT EXISTS pronunciations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            lemma_id INTEGER NOT NULL,
            ipa_notation VARCHAR(255),
            audio_file_path VARCHAR(500),
            accent_variety VARCHAR(50) DEFAULT 'general',
            FOREIGN KEY (lemma_id) REFERENCES lemmas(id)
        );
        """
        
        cursor = self.conn.cursor()
        cursor.executescript(schema_sql)
        self.conn.commit()
        logger.info("Database schema created successfully")
    
    def create_indexes(self):
        """Create performance indexes"""
        indexes_sql = """
        CREATE INDEX IF NOT EXISTS idx_lemmas_lemma ON lemmas(lemma);
        CREATE INDEX IF NOT EXISTS idx_lemmas_frequency ON lemmas(lemma_frequency DESC);
        CREATE INDEX IF NOT EXISTS idx_lemmas_rank ON lemmas(lemma_rank);
        CREATE INDEX IF NOT EXISTS idx_inflected_forms_form ON inflected_forms(form);
        CREATE INDEX IF NOT EXISTS idx_inflected_forms_lemma_id ON inflected_forms(lemma_id);
        CREATE INDEX IF NOT EXISTS idx_inflected_forms_pos ON inflected_forms(pos);
        CREATE INDEX IF NOT EXISTS idx_inflected_forms_frequency ON inflected_forms(form_frequency DESC);
        CREATE INDEX IF NOT EXISTS idx_context_freq_lemma_pos ON context_frequencies(lemma_id, pos);
        CREATE INDEX IF NOT EXISTS idx_context_freq_type ON context_frequencies(context_type);
        CREATE INDEX IF NOT EXISTS idx_context_freq_name ON context_frequencies(context_name);
        CREATE INDEX IF NOT EXISTS idx_word_references_source ON word_references(source_definition_id);
        CREATE INDEX IF NOT EXISTS idx_word_references_target ON word_references(referenced_lemma_id);
        """
        
        cursor = self.conn.cursor()
        cursor.executescript(indexes_sql)
        self.conn.commit()
        logger.info("Database indexes created successfully")
    
    def insert_default_language(self):
        """Insert default English language"""
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT OR IGNORE INTO languages (code, name) 
            VALUES ('en', 'English')
        """)
        self.conn.commit()
        cursor.execute("SELECT id FROM languages WHERE code = 'en'")
        return cursor.fetchone()[0]
    
    def load_excel_data(self) -> Dict[str, pd.DataFrame]:
        """Load all tabs from Excel file"""
        logger.info(f"Loading Excel file: {self.excel_file_path}")
        
        try:
            excel_data = {}
            nrows = SAMPLE_ROWS if SAMPLE_ROWS else None
            
            excel_data['wordforms'] = pd.read_excel(self.excel_file_path, sheet_name=SHEETS['wordforms'], nrows=nrows)
            excel_data['lemmas'] = pd.read_excel(self.excel_file_path, sheet_name=SHEETS['lemmas'], nrows=nrows)
            excel_data['subgenres'] = pd.read_excel(self.excel_file_path, sheet_name=SHEETS['subgenres'], nrows=nrows)
            
            logger.info(f"Loaded {len(excel_data['wordforms'])} word forms")
            logger.info(f"Loaded {len(excel_data['lemmas'])} lemma entries")
            logger.info(f"Loaded {len(excel_data['subgenres'])} subgenre entries")
            
            return excel_data
        except Exception as e:
            logger.error(f"Error loading Excel file: {e}")
            raise
    
    def process_lemmas_data(self, lemmas_df: pd.DataFrame, language_id: int):
        """Process and insert lemma data with dispersion scores"""
        logger.info("Processing lemmas data...")
        
        unique_lemmas = lemmas_df.groupby('lemma').agg({
            'disp': 'first',
        }).reset_index()
        
        lemma_data = []
        for _, row in unique_lemmas.iterrows():
            lemma_data.append((
                row['lemma'],
                language_id,
                0,
                0,
                float(row['disp']) if pd.notna(row['disp']) else 0.0
            ))
        
        cursor = self.conn.cursor()
        cursor.executemany("""
            INSERT OR IGNORE INTO lemmas (lemma, language_id, lemma_frequency, lemma_rank, dispersion_score)
            VALUES (?, ?, ?, ?, ?)
        """, lemma_data)
        
        self.conn.commit()
        logger.info(f"Inserted {len(lemma_data)} unique lemmas")
    
    def process_wordforms_data(self, wordforms_df: pd.DataFrame):
        """Process and insert word forms data"""
        logger.info("Processing word forms data...")
        
        lemma_updates = wordforms_df.groupby('lemma').agg({
            'lemFreq': 'first',
            'lemRank': 'first'
        }).reset_index()
        
        cursor = self.conn.cursor()
        
        for _, row in lemma_updates.iterrows():
            cursor.execute("""
                UPDATE lemmas 
                SET lemma_frequency = ?, lemma_rank = ?
                WHERE lemma = ?
            """, (
                int(row['lemFreq']) if pd.notna(row['lemFreq']) else 0,
                int(row['lemRank']) if pd.notna(row['lemRank']) else 0,
                row['lemma']
            ))
        
        inflected_forms_data = []
        for _, row in wordforms_df.iterrows():
            cursor.execute("SELECT id FROM lemmas WHERE lemma = ?", (row['lemma'],))
            lemma_result = cursor.fetchone()
            if lemma_result:
                lemma_id = lemma_result[0]
                inflected_forms_data.append((
                    lemma_id,
                    row['word'],
                    row['PoS'],
                    int(row['wordFreq']) if pd.notna(row['wordFreq']) else 0,
                    0,
                    None,
                    None
                ))
        
        # Batch insert
        for i in range(0, len(inflected_forms_data), BATCH_SIZE):
            batch = inflected_forms_data[i:i + BATCH_SIZE]
            cursor.executemany("""
                INSERT OR IGNORE INTO inflected_forms 
                (lemma_id, form, pos, form_frequency, form_rank, inflection_type, grammatical_info)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, batch)
        
        self.conn.commit()
        logger.info(f"Inserted {len(inflected_forms_data)} inflected forms")
    
    def process_broad_domains(self, lemmas_df: pd.DataFrame):
        """Process broad domain frequencies"""
        logger.info("Processing broad domain frequencies...")
        
        domain_columns = []
        for col in lemmas_df.columns:
            if col not in ['lemma', 'PoS', 'disp'] and lemmas_df.columns.get_loc(col) >= 9:
                if lemmas_df.columns.get_loc(col) <= 24:
                    domain_columns.append(col)
        
        if not domain_columns:
            logger.warning("No broad domain columns found")
            return
        
        logger.info(f"Found {len(domain_columns)} broad domain columns: {domain_columns}")
        
        cursor = self.conn.cursor()
        context_data = []
        
        for _, row in lemmas_df.iterrows():
            cursor.execute("SELECT id FROM lemmas WHERE lemma = ?", (row['lemma'],))
            lemma_result = cursor.fetchone()
            if lemma_result:
                lemma_id = lemma_result[0]
                pos = row['PoS']
                
                for domain_col in domain_columns:
                    frequency = row[domain_col]
                    if pd.notna(frequency) and frequency > 0:
                        context_data.append((
                            lemma_id,
                            pos,
                            'broad_domain',
                            domain_col,
                            int(frequency),
                            None
                        ))
        
        if context_data:
            for i in range(0, len(context_data), BATCH_SIZE):
                batch = context_data[i:i + BATCH_SIZE]
                cursor.executemany("""
                    INSERT INTO context_frequencies 
                    (lemma_id, pos, context_type, context_name, frequency, context_metadata)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, batch)
            
            self.conn.commit()
            logger.info(f"Inserted {len(context_data)} broad domain frequency records")
    
    def process_subgenres(self, subgenres_df: pd.DataFrame):
        """Process subgenre frequencies"""
        logger.info("Processing subgenre frequencies...")
        
        subgenre_columns = []
        for col in subgenres_df.columns:
            if str(col).startswith('x') and str(col)[1:].isdigit():
                col_num = int(str(col)[1:])
                if 101 <= col_num <= 214:
                    subgenre_columns.append(col)
        
        if not subgenre_columns:
            logger.warning("No subgenre columns found")
            return
        
        logger.info(f"Found {len(subgenre_columns)} subgenre columns")
        
        cursor = self.conn.cursor()
        context_data = []
        
        for _, row in subgenres_df.iterrows():
            cursor.execute("SELECT id FROM lemmas WHERE lemma = ?", (row['lemma'],))
            lemma_result = cursor.fetchone()
            if lemma_result:
                lemma_id = lemma_result[0]
                pos = row['PoS']
                
                for subgenre_col in subgenre_columns:
                    frequency = row[subgenre_col]
                    if pd.notna(frequency) and frequency > 0:
                        context_data.append((
                            lemma_id,
                            pos,
                            'subgenre',
                            subgenre_col,
                            int(frequency),
                            None
                        ))
        
        if context_data:
            for i in range(0, len(context_data), BATCH_SIZE):
                batch = context_data[i:i + BATCH_SIZE]
                cursor.executemany("""
                    INSERT INTO context_frequencies 
                    (lemma_id, pos, context_type, context_name, frequency, context_metadata)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, batch)
            
            self.conn.commit()
            logger.info(f"Inserted {len(context_data)} subgenre frequency records")
    
    def build_database(self):
        """Main method to build the complete database"""
        logger.info("Starting database build process...")
        logger.info(f"Excel file: {self.excel_file_path}")
        logger.info(f"Database output: {self.db_path}")
        
        try:
            self.conn = sqlite3.connect(self.db_path)
            
            self.create_database_schema()
            self.create_indexes()
            
            language_id = self.insert_default_language()
            
            excel_data = self.load_excel_data()
            
            self.process_lemmas_data(excel_data['lemmas'], language_id)
            self.process_wordforms_data(excel_data['wordforms'])
            self.process_broad_domains(excel_data['lemmas'])
            self.process_subgenres(excel_data['subgenres'])
            
            self.generate_statistics()
            
            logger.info("Database build completed successfully!")
            
        except Exception as e:
            logger.error(f"Error building database: {e}")
            raise
        finally:
            if self.conn:
                self.conn.close()
    
    def generate_statistics(self):
        """Generate and display database statistics"""
        cursor = self.conn.cursor()
        
        stats = {}
        
        tables = ['lemmas', 'inflected_forms', 'context_frequencies']
        for table in tables:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            stats[table] = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(DISTINCT lemma) FROM lemmas")
        stats['unique_lemmas'] = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(DISTINCT pos) FROM inflected_forms")
        stats['unique_pos'] = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(DISTINCT context_name) FROM context_frequencies WHERE context_type = 'broad_domain'")
        stats['broad_domains'] = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(DISTINCT context_name) FROM context_frequencies WHERE context_type = 'subgenre'")
        stats['subgenres'] = cursor.fetchone()[0]
        
        logger.info("Database Statistics:")
        for key, value in stats.items():
            logger.info(f"  {key}: {value:,}")

def main():
    if not Path(EXCEL_FILE).exists():
        logger.error(f"Excel file not found: {EXCEL_FILE}")
        return
    
    builder = DictionaryDatabaseBuilder()
    builder.build_database()
    
    logger.info(f"Dictionary database created successfully at: {DATABASE_FILE}")

if __name__ == "__main__":
    main()
