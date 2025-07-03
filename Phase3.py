import json

import sqlite3

import logging

import re

from typing import Dict, List, Set, Tuple, Optional

from pathlib import Path


# Set up logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

logger = logging.getLogger(__name__)


class DefinitionsLoader:

    def __init__(self, db_path: str = "dictionary.db"):

        self.db_path = db_path

        self.conn = None

        self.lemma_id_cache = {}  # Cache for lemma lookups

        

    def connect_database(self):

        """Connect to the existing database"""

        try:

            self.conn = sqlite3.connect(self.db_path)

            self.conn.row_factory = sqlite3.Row  # Enable column access by name

            logger.info(f"Connected to database: {self.db_path}")

        except Exception as e:

            logger.error(f"Failed to connect to database: {e}")

            raise

    

    def load_lemma_cache(self):

        """Load all lemmas into memory for fast lookups"""

        cursor = self.conn.cursor()

        cursor.execute("SELECT id, lemma FROM lemmas")

        self.lemma_id_cache = {row['lemma'].lower(): row['id'] for row in cursor.fetchall()}

        logger.info(f"Loaded {len(self.lemma_id_cache)} lemmas into cache")

    

    def clean_text(self, text: str) -> str:

        """Clean text for processing"""

        if not text:

            return ""

        # Remove extra whitespace

        text = re.sub(r'\s+', ' ', text.strip())

        return text

    

    def extract_words_from_text(self, text: str) -> List[Tuple[int, str]]:

        """Extract words with their positions from text"""

        if not text:

            return []

        

        words = []

        # Split by word boundaries, keeping track of positions

        word_pattern = re.compile(r'\b[a-zA-Z]+\b')

        for match in word_pattern.finditer(text):

            word = match.group().lower()

            position = match.start()

            # Only include words longer than 2 characters that exist in our lemma cache

            if len(word) > 2 and word in self.lemma_id_cache:

                words.append((position, word))

        

        return words

    

    def insert_definition(self, lemma_id: int, pos: str, definition_text: str, 

                         order: int, example: str = None, hypernyms: List[str] = None) -> int:

        """Insert a definition and return its ID"""

        cursor = self.conn.cursor()

        

        hypernyms_json = json.dumps(hypernyms) if hypernyms else None

        

        cursor.execute("""

            INSERT INTO definitions (lemma_id, pos, definition_text, definition_order, example_sentence, hypernyms)

            VALUES (?, ?, ?, ?, ?, ?)

        """, (lemma_id, pos, self.clean_text(definition_text), order, 

              self.clean_text(example) if example else None, hypernyms_json))

        

        return cursor.lastrowid

    

    def insert_word_references(self, definition_id: int, text: str, reference_type: str = 'definition'):

        """Insert word references for clickable cross-references"""

        if not text:

            return

        

        words_with_positions = self.extract_words_from_text(text)

        

        if not words_with_positions:

            return

        

        cursor = self.conn.cursor()

        reference_data = []

        

        for position, word in words_with_positions:

            lemma_id = self.lemma_id_cache.get(word.lower())

            if lemma_id:

                reference_data.append((

                    definition_id,

                    lemma_id,

                    position,

                    word,

                    reference_type

                ))

        

        if reference_data:

            cursor.executemany("""

                INSERT INTO word_references 

                (source_definition_id, referenced_lemma_id, word_position, word_text, reference_type)

                VALUES (?, ?, ?, ?, ?)

            """, reference_data)

    

    def insert_synonyms(self, lemma_id: int, pos: str, synonyms: List[str]):

        """Insert synonyms for a lemma-POS combination"""

        if not synonyms:

            return

        

        cursor = self.conn.cursor()

        synonym_data = []

        

        for synonym in synonyms:

            synonym_clean = self.clean_text(synonym).lower()

            # Check if synonym exists as a lemma

            synonym_lemma_id = self.lemma_id_cache.get(synonym_clean)

            if synonym_lemma_id and synonym_lemma_id != lemma_id:

                synonym_data.append((

                    lemma_id,

                    synonym_lemma_id,

                    pos,

                    1.0  # Default similarity score

                ))

        

        if synonym_data:

            cursor.executemany("""

                INSERT OR IGNORE INTO synonyms (lemma_id, synonym_lemma_id, pos_specific, similarity_score)

                VALUES (?, ?, ?, ?)

            """, synonym_data)

    

    def process_lemma_entry(self, lemma: str, lemma_data: List[Dict]):

        """Process all POS entries for a single lemma"""

        lemma_clean = lemma.lower()

        lemma_id = self.lemma_id_cache.get(lemma_clean)

        

        if not lemma_id:

            logger.warning(f"Lemma '{lemma}' not found in database. Skipping.")

            return 0

        

        total_definitions = 0

        

        for pos_data in lemma_data:

            pos = pos_data.get('pos', '').lower()

            definitions = pos_data.get('definitions', [])

            hypernyms = pos_data.get('hypernyms', [])

            synonyms = pos_data.get('synonyms', [])

            examples = pos_data.get('examples', [])

            

            # Insert synonyms for this POS

            self.insert_synonyms(lemma_id, pos, synonyms)

            

            # Process each definition

            for def_order, definition in enumerate(definitions, 1):

                # Get corresponding example if available

                example = examples[def_order - 1] if def_order <= len(examples) else None

                

                # Insert definition

                definition_id = self.insert_definition(

                    lemma_id, pos, definition, def_order, example, hypernyms

                )

                

                # Create word references for clickable words in definition

                self.insert_word_references(definition_id, definition, 'definition')

                

                # Create word references for clickable words in example

                if example:

                    self.insert_word_references(definition_id, example, 'example')

                

                total_definitions += 1

        

        return total_definitions

    

    def load_json_definitions(self, json_file_path: str):

        """Load definitions from JSON file"""

        logger.info(f"Loading definitions from: {json_file_path}")

        

        try:

            with open(json_file_path, 'r', encoding='utf-8') as f:

                definitions_data = json.load(f)

            

            logger.info(f"Loaded JSON data for {len(definitions_data)} lemmas")

            return definitions_data

            

        except Exception as e:

            logger.error(f"Error loading JSON file: {e}")

            raise

    

    def clear_existing_definitions(self):

        """Clear existing definitions data (for re-loading)"""

        cursor = self.conn.cursor()

        

        # Clear in reverse dependency order

        cursor.execute("DELETE FROM word_references")

        cursor.execute("DELETE FROM synonyms") 

        cursor.execute("DELETE FROM definitions")

        

        self.conn.commit()

        logger.info("Cleared existing definitions data")

    

    def create_additional_indexes(self):

        """Create additional indexes for definition lookups"""

        indexes_sql = """

        -- Definition-specific indexes

        CREATE INDEX IF NOT EXISTS idx_definitions_lemma_pos ON definitions(lemma_id, pos);

        CREATE INDEX IF NOT EXISTS idx_definitions_lemma_order ON definitions(lemma_id, definition_order);

        

        -- Synonym indexes

        CREATE INDEX IF NOT EXISTS idx_synonyms_lemma_pos ON synonyms(lemma_id, pos_specific);

        CREATE INDEX IF NOT EXISTS idx_synonyms_target ON synonyms(synonym_lemma_id);

        

        -- Enhanced word reference indexes

        CREATE INDEX IF NOT EXISTS idx_word_refs_type ON word_references(reference_type);

        CREATE INDEX IF NOT EXISTS idx_word_refs_position ON word_references(source_definition_id, word_position);

        """

        

        cursor = self.conn.cursor()

        cursor.executescript(indexes_sql)

        self.conn.commit()

        logger.info("Created additional indexes for definitions")

    

    def process_definitions_file(self, json_file_path: str, clear_existing: bool = False):

        """Main method to process the definitions JSON file"""

        logger.info("Starting definitions loading process...")

        

        try:

            # Connect to database

            self.connect_database()

            

            # Load lemma cache for fast lookups

            self.load_lemma_cache()

            

            # Clear existing data if requested

            if clear_existing:

                self.clear_existing_definitions()

            

            # Load JSON data

            definitions_data = self.load_json_definitions(json_file_path)

            

            # Process each lemma

            total_definitions = 0

            total_lemmas = len(definitions_data)

            

            for i, (lemma, lemma_data) in enumerate(definitions_data.items(), 1):

                if i % 100 == 0:

                    logger.info(f"Processing lemma {i}/{total_lemmas}: {lemma}")

                

                definitions_count = self.process_lemma_entry(lemma, lemma_data)

                total_definitions += definitions_count

            

            # Create additional indexes

            self.create_additional_indexes()

            

            # Commit all changes

            self.conn.commit()

            

            # Generate statistics

            self.generate_statistics()

            

            logger.info(f"Successfully loaded {total_definitions} definitions for {total_lemmas} lemmas")

            

        except Exception as e:

            logger.error(f"Error processing definitions: {e}")

            if self.conn:

                self.conn.rollback()

            raise

        finally:

            if self.conn:

                self.conn.close()

    

    def generate_statistics(self):

        """Generate and display loading statistics"""

        cursor = self.conn.cursor()

        

        stats = {}

        

        # Count definitions

        cursor.execute("SELECT COUNT(*) FROM definitions")

        stats['total_definitions'] = cursor.fetchone()[0]

        

        # Count by POS

        cursor.execute("""

            SELECT pos, COUNT(*) as count 

            FROM definitions 

            GROUP BY pos 

            ORDER BY count DESC

        """)

        stats['definitions_by_pos'] = cursor.fetchall()

        

        # Count synonyms

        cursor.execute("SELECT COUNT(*) FROM synonyms")

        stats['total_synonyms'] = cursor.fetchone()[0]

        

        # Count word references

        cursor.execute("SELECT COUNT(*) FROM word_references")

        stats['total_word_references'] = cursor.fetchone()[0]

        

        # Count by reference type

        cursor.execute("""

            SELECT reference_type, COUNT(*) as count 

            FROM word_references 

            GROUP BY reference_type

        """)

        stats['references_by_type'] = cursor.fetchall()

        

        # Count lemmas with definitions

        cursor.execute("""

            SELECT COUNT(DISTINCT lemma_id) FROM definitions

        """)

        stats['lemmas_with_definitions'] = cursor.fetchone()[0]

        

        logger.info("Loading Statistics:")

        logger.info(f"  Total definitions: {stats['total_definitions']:,}")

        logger.info(f"  Total synonyms: {stats['total_synonyms']:,}")

        logger.info(f"  Total word references: {stats['total_word_references']:,}")

        logger.info(f"  Lemmas with definitions: {stats['lemmas_with_definitions']:,}")

        

        logger.info("  Definitions by POS:")

        for pos, count in stats['definitions_by_pos']:

            logger.info(f"    {pos}: {count:,}")

        

        logger.info("  Word references by type:")

        for ref_type, count in stats['references_by_type']:

            logger.info(f"    {ref_type}: {count:,}")


def test_cross_references(db_path: str = "dictionary.db"):

    """Test function to show cross-reference functionality"""

    conn = sqlite3.connect(db_path)

    conn.row_factory = sqlite3.Row

    cursor = conn.cursor()

    

    # Get a sample definition with cross-references

    cursor.execute("""

        SELECT d.definition_text, l.lemma

        FROM definitions d

        JOIN lemmas l ON d.lemma_id = l.id

        WHERE d.id IN (

            SELECT DISTINCT source_definition_id 

            FROM word_references 

            LIMIT 1

        )

        LIMIT 1

    """)

    

    result = cursor.fetchone()

    if result:

        definition_id = cursor.execute("""

            SELECT d.id FROM definitions d

            JOIN lemmas l ON d.lemma_id = l.id

            WHERE l.lemma = ? AND d.definition_text = ?

        """, (result['lemma'], result['definition_text'])).fetchone()[0]

        

        logger.info(f"\nExample cross-reference for '{result['lemma']}':")

        logger.info(f"Definition: {result['definition_text']}")

        

        # Get clickable words

        cursor.execute("""

            SELECT wr.word_position, wr.word_text, l.lemma as target_lemma

            FROM word_references wr

            JOIN lemmas l ON wr.referenced_lemma_id = l.id

            WHERE wr.source_definition_id = ?

            ORDER BY wr.word_position

        """, (definition_id,))

        

        clickable_words = cursor.fetchall()

        if clickable_words:

            logger.info("Clickable words:")

            for word in clickable_words:

                logger.info(f"  '{word['word_text']}' -> links to '{word['target_lemma']}'")

    

    conn.close()


def main():

    """Example usage"""

    # Update this path to your JSON file

    json_file_path = "definitions.json"

    

    # Check if file exists

    if not Path(json_file_path).exists():

        logger.error(f"JSON file not found: {json_file_path}")

        logger.info("Please update the json_file_path variable with the correct path to your definitions JSON file")

        return

    

    # Check if database exists

    db_path = "dictionary.db"

    if not Path(db_path).exists():

        logger.error(f"Database not found: {db_path}")

        logger.info("Please run the database builder script first to create the base database")

        return

    

    # Load definitions

    loader = DefinitionsLoader(db_path)

    loader.process_definitions_file(json_file_path, clear_existing=True)

    

    # Test cross-references

    test_cross_references(db_path)

    

    logger.info("Definitions loading completed successfully!")


if __name__ == "__main__":

    main() 