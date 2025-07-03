
## phase2_xml_to_json.py


import xml.etree.ElementTree as ET
import json
import sys
import os
from collections import defaultdict
from pathlib import Path
import logging

# Add parent directory to path for config import
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import *

# Set up logging
logging.basicConfig(level=LOG_LEVEL, format=LOG_FORMAT)
logger = logging.getLogger(__name__)

def get_all_hypernyms(synset_id, synset_map, synset_to_lemmas, visited_synsets=None):
    """Recursively collects all hypernyms for a given synset ID."""
    if visited_synsets is None:
        visited_synsets = set()

    if synset_id in visited_synsets:
        return []

    visited_synsets.add(synset_id)
    
    hypernyms = []
    synset_element = synset_map.get(synset_id)
    if synset_element is None:
        return []

    for relation in synset_element.findall("SynsetRelation[@relType='hypernym']"):
        target_id = relation.get('target')
        target_lemmas = synset_to_lemmas.get(target_id, [])
        hypernyms.extend(target_lemmas)
        hypernyms.extend(get_all_hypernyms(target_id, synset_map, synset_to_lemmas, visited_synsets))
        
    return hypernyms

def create_json_from_xml(xml_file_path=XML_FILE, json_file_path=JSON_FILE):
    """Parses a WordNet XML file and creates a structured JSON file."""
    logger.info(f"Starting XML to JSON conversion")
    logger.info(f"Input XML: {xml_file_path}")
    logger.info(f"Output JSON: {json_file_path}")
    
    logger.info("Parsing XML file...")
    try:
        tree = ET.parse(xml_file_path)
        root = tree.getroot()
    except ET.ParseError as e:
        logger.error(f"Error parsing XML file: {e}")
        return
    except FileNotFoundError:
        logger.error(f"Error: XML file not found at '{xml_file_path}'")
        return

    logger.info("Building lookup maps for synsets and lemmas...")
    synset_map = {s.get('id'): s for s in root.findall(".//Synset")}
    synset_to_lemmas = defaultdict(list)
    
    for entry in root.findall('.//LexicalEntry'):
        lemma_form = entry.find('Lemma').get('writtenForm')
        for sense in entry.findall('Sense'):
            synset_id = sense.get('synset')
            if lemma_form not in synset_to_lemmas[synset_id]:
                synset_to_lemmas[synset_id].append(lemma_form)

    logger.info(f"Found {len(synset_map)} synsets")
    
    logger.info("Extracting and structuring data...")
    output_data = defaultdict(dict)
    
    total_entries = len(root.findall('.//LexicalEntry'))
    processed = 0

    for entry in root.findall('.//LexicalEntry'):
        lemma_element = entry.find('Lemma')
        lemma = lemma_element.get('writtenForm')
        pos = lemma_element.get('partOfSpeech')

        if pos not in output_data[lemma]:
            output_data[lemma][pos] = {
                "definitions": [],
                "hypernyms": [],
                "synonyms": [],
                "examples": []
            }
        
        for sense in entry.findall('Sense'):
            synset_id = sense.get('synset')
            synset_element = synset_map.get(synset_id)

            for example in sense.findall('Example'):
                if example.text:
                    output_data[lemma][pos]["examples"].append(example.text.strip())

            if synset_element is not None:
                definition = synset_element.find('Definition')
                if definition is not None and definition.text:
                    output_data[lemma][pos]["definitions"].append(definition.text.strip())

                for example in synset_element.findall('Example'):
                    if example.text:
                        output_data[lemma][pos]["examples"].append(example.text.strip())

                synonyms = synset_to_lemmas.get(synset_id, [])
                output_data[lemma][pos]["synonyms"].extend(s for s in synonyms if s != lemma)
                
                hypernyms = get_all_hypernyms(synset_id, synset_map, synset_to_lemmas)
                output_data[lemma][pos]["hypernyms"].extend(hypernyms)
        
        processed += 1
        if processed % 1000 == 0:
            logger.info(f"Processed {processed}/{total_entries} entries")

    logger.info("Finalizing JSON structure and removing duplicates...")
    final_json = {}
    for lemma, pos_data in output_data.items():
        final_json[lemma] = []
        for pos, data in pos_data.items():
            unique_definitions = sorted(list(set(data["definitions"])))
            unique_hypernyms = sorted(list(set(data["hypernyms"])))
            unique_synonyms = sorted(list(set(data["synonyms"])))
            unique_examples = sorted(list(set(data["examples"])))
            
            final_json[lemma].append({
                "pos": pos,
                "definitions": unique_definitions,
                "hypernyms": unique_hypernyms,
                "synonyms": unique_synonyms,
                "examples": unique_examples
            })

    logger.info(f"Writing output to {json_file_path}...")
    try:
        with open(json_file_path, 'w', encoding='utf-8') as f:
            json.dump(final_json, f, ensure_ascii=False, indent=4)
        logger.info(f"Successfully created JSON file with {len(final_json)} lemmas")
    except IOError as e:
        logger.error(f"Error writing to file: {e}")

def main():
    if not Path(XML_FILE).exists():
        logger.error(f"XML file not found: {XML_FILE}")
        return
        
    create_json_from_xml()

if __name__ == '__main__':
    main()
