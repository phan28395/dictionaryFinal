import xml.etree.ElementTree as ET
import json
import sys
from collections import defaultdict

def get_all_hypernyms(synset_id, synset_map, synset_to_lemmas, visited_synsets=None):
    """
    Recursively collects all hypernyms for a given synset ID.
    A hypernym is a word with a broad meaning that more specific words fall under.
    
    Args:
        synset_id (str): The ID of the starting synset.
        synset_map (dict): A mapping of synset IDs to their XML elements.
        synset_to_lemmas (dict): A mapping of synset IDs to a list of lemma strings.
        visited_synsets (set, optional): A set of already visited synset IDs to prevent infinite loops. Defaults to None.

    Returns:
        list: A list of all hypernym strings, across all levels.
    """
    if visited_synsets is None:
        visited_synsets = set()

    if synset_id in visited_synsets:
        return []

    visited_synsets.add(synset_id)
    
    hypernyms = []
    synset_element = synset_map.get(synset_id)
    if synset_element is None:
        return []

    # Find all hypernym relations for the current synset
    for relation in synset_element.findall("SynsetRelation[@relType='hypernym']"):
        target_id = relation.get('target')
        # Get the actual words (lemmas) for the target hypernym synset
        target_lemmas = synset_to_lemmas.get(target_id, [])
        hypernyms.extend(target_lemmas)
        # Recursively find the hypernyms of the target synset
        hypernyms.extend(get_all_hypernyms(target_id, synset_map, synset_to_lemmas, visited_synsets))
        
    return hypernyms

def create_json_from_xml(xml_file_path, json_file_path):
    """
    Parses a WordNet XML file and creates a structured JSON file.

    Args:
        xml_file_path (str): The path to the input XML file.
        json_file_path (str): The path where the output JSON file will be saved.
    """
    print("Parsing XML file...")
    try:
        tree = ET.parse(xml_file_path)
        root = tree.getroot()
    except ET.ParseError as e:
        print(f"Error parsing XML file: {e}")
        return
    except FileNotFoundError:
        print(f"Error: XML file not found at '{xml_file_path}'")
        return

    # --- Pre-computation Step ---
    # Create lookup maps for efficient data retrieval.
    print("Building lookup maps for synsets and lemmas...")
    synset_map = {s.get('id'): s for s in root.findall(".//Synset")}
    synset_to_lemmas = defaultdict(list)
    for entry in root.findall('.//LexicalEntry'):
        lemma_form = entry.find('Lemma').get('writtenForm')
        for sense in entry.findall('Sense'):
            synset_id = sense.get('synset')
            if lemma_form not in synset_to_lemmas[synset_id]:
                synset_to_lemmas[synset_id].append(lemma_form)

    # --- Data Extraction Step ---
    print("Extracting and structuring data...")
    output_data = defaultdict(dict)

    for entry in root.findall('.//LexicalEntry'):
        lemma_element = entry.find('Lemma')
        lemma = lemma_element.get('writtenForm')
        pos = lemma_element.get('partOfSpeech')

        # Initialize structure if it doesn't exist
        if pos not in output_data[lemma]:
            output_data[lemma][pos] = {
                "definitions": [],
                "hypernyms": [],
                "synonyms": [],
                "examples": [] # Added field for examples
            }
        
        # Aggregate data from all senses of the lemma
        for sense in entry.findall('Sense'):
            synset_id = sense.get('synset')
            synset_element = synset_map.get(synset_id)

            # Find examples directly within the Sense element
            for example in sense.findall('Example'):
                if example.text:
                    output_data[lemma][pos]["examples"].append(example.text.strip())

            if synset_element is not None:
                # Get definition
                definition = synset_element.find('Definition')
                if definition is not None and definition.text:
                    output_data[lemma][pos]["definitions"].append(definition.text.strip())

                # Find examples within the Synset element
                for example in synset_element.findall('Example'):
                    if example.text:
                        output_data[lemma][pos]["examples"].append(example.text.strip())

                # Get synonyms
                synonyms = synset_to_lemmas.get(synset_id, [])
                output_data[lemma][pos]["synonyms"].extend(s for s in synonyms if s != lemma)
                
                # Get hypernyms
                hypernyms = get_all_hypernyms(synset_id, synset_map, synset_to_lemmas)
                output_data[lemma][pos]["hypernyms"].extend(hypernyms)


    # --- Finalization Step ---
    print("Finalizing JSON structure and removing duplicates...")
    final_json = {}
    for lemma, pos_data in output_data.items():
        final_json[lemma] = []
        for pos, data in pos_data.items():
            # Remove duplicates by converting to set and back to list
            unique_definitions = sorted(list(set(data["definitions"])))
            unique_hypernyms = sorted(list(set(data["hypernyms"])))
            unique_synonyms = sorted(list(set(data["synonyms"])))
            unique_examples = sorted(list(set(data["examples"]))) # Added for examples
            
            final_json[lemma].append({
                "pos": pos,
                "definitions": unique_definitions,
                "hypernyms": unique_hypernyms,
                "synonyms": unique_synonyms,
                "examples": unique_examples # Added to final JSON
            })

    # --- Write to JSON file ---
    print(f"Writing output to {json_file_path}...")
    try:
        with open(json_file_path, 'w', encoding='utf-8') as f:
            json.dump(final_json, f, ensure_ascii=False, indent=4)
        print("Successfully created JSON file.")
    except IOError as e:
        print(f"Error writing to file: {e}")


if __name__ == '__main__':
    # This allows the script to be run from the command line.
    # Example usage: python your_script_name.py input.xml output.json
    
    if len(sys.argv) != 3:
        print("Usage: python script.py <path_to_input_xml> <path_to_output_json>")
        # Use default filenames if not provided via command line, for easier testing.
        print("Attempting to use default filenames: 'input.xml' and 'output.json'")
        xml_file = 'data/source/wn.xml'
        json_file = 'data/processed/Wordnet_data_Phase2.json'
    else:
        xml_file = sys.argv[1]
        json_file = sys.argv[2]
        
    create_json_from_xml(xml_file, json_file)
