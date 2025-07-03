
## build_complete.py

import sys
import os
import logging
from pathlib import Path
import time

# Add parent directory to path for config import
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from config import *
from phase1_excel_to_db import DictionaryDatabaseBuilder
from phase2_xml_to_json import create_json_from_xml
from phase3_json_to_db import DefinitionsLoader

# Set up logging
logging.basicConfig(level=LOG_LEVEL, format=LOG_FORMAT)
logger = logging.getLogger(__name__)

class CompletePipelineBuilder:
    def __init__(self):
        self.start_time = None
        self.phase_times = {}
        
    def check_prerequisites(self):
        """Check if all required files exist"""
        logger.info("Checking prerequisites...")
        
        required_files = {
            "Excel file": EXCEL_FILE,
            "XML file": XML_FILE
        }
        
        all_present = True
        for file_desc, file_path in required_files.items():
            if Path(file_path).exists():
                logger.info(f"✓ {file_desc}: {file_path}")
            else:
                logger.error(f"✗ {file_desc} not found: {file_path}")
                all_present = False
        
        return all_present
    
    def run_phase(self, phase_num: int, phase_name: str, phase_function):
        """Run a single phase with timing and error handling"""
        logger.info(f"\n{'='*60}")
        logger.info(f"PHASE {phase_num}: {phase_name}")
        logger.info(f"{'='*60}")
        
        phase_start = time.time()
        
        try:
            phase_function()
            phase_time = time.time() - phase_start
            self.phase_times[phase_name] = phase_time
            logger.info(f"✓ Phase {phase_num} completed in {phase_time:.2f} seconds")
            return True
        except Exception as e:
            logger.error(f"✗ Phase {phase_num} failed: {e}")
            return False
    
    def build_complete_database(self):
        """Run the complete pipeline"""
        self.start_time = time.time()
        
        logger.info("Starting complete dictionary database build")
        logger.info(f"Source path: {SOURCE_PATH}")
        logger.info(f"Database path: {DATABASE_PATH}")
        
        # Check prerequisites
        if not self.check_prerequisites():
            logger.error("Prerequisites check failed. Exiting.")
            return False
        
        # Phase 1: Excel to Database
        if not self.run_phase(
            1, 
            "Excel to Database",
            lambda: DictionaryDatabaseBuilder().build_database()
        ):
            return False
        
        # Phase 2: XML to JSON
        if not self.run_phase(
            2,
            "XML to JSON",
            lambda: create_json_from_xml()
        ):
            return False
        
        # Phase 3: JSON to Database
        if not self.run_phase(
            3,
            "JSON to Database (Definitions)",
            lambda: DefinitionsLoader().process_definitions_file(clear_existing=True)
        ):
            return False
        
        # Summary
        total_time = time.time() - self.start_time
        logger.info(f"\n{'='*60}")
        logger.info("PIPELINE COMPLETED SUCCESSFULLY")
        logger.info(f"{'='*60}")
        logger.info("Time Summary:")
        for phase, phase_time in self.phase_times.items():
            logger.info(f"  {phase}: {phase_time:.2f}s")
        logger.info(f"  Total: {total_time:.2f}s")
        logger.info(f"\nDatabase created at: {DATABASE_FILE}")
        
        return True
    
    def validate_output(self):
        """Validate the final database"""
        logger.info("\nValidating final database...")
        
        import sqlite3
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()
        
        validations = [
            ("Lemmas", "SELECT COUNT(*) FROM lemmas"),
            ("Inflected forms", "SELECT COUNT(*) FROM inflected_forms"),
            ("Definitions", "SELECT COUNT(*) FROM definitions"),
            ("Synonyms", "SELECT COUNT(*) FROM synonyms"),
            ("Word references", "SELECT COUNT(*) FROM word_references"),
            ("Context frequencies", "SELECT COUNT(*) FROM context_frequencies"),
        ]
        
        all_valid = True
        for name, query in validations:
            count = cursor.execute(query).fetchone()[0]
            if count > 0:
                logger.info(f"✓ {name}: {count:,} records")
            else:
                logger.warning(f"⚠ {name}: No records found")
                all_valid = False
        
        conn.close()
        return all_valid

def main():
    builder = CompletePipelineBuilder()
    
    if builder.build_complete_database():
        builder.validate_output()
        logger.info("\nDictionary database build completed successfully!")
        logger.info(f"Database location: {DATABASE_FILE}")
    else:
        logger.error("\nPipeline failed. Please check the errors above.")
        sys.exit(1)

if __name__ == "__main__":
    main()

