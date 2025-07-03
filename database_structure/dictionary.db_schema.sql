-- SQLite Database Schema for: dictionary.db
-- Generated on: 2025-07-03T17:37:03.775609
-- This file contains the complete database schema without any data


-- TABLES
--------------------------------------------------

-- table: context_frequencies
CREATE TABLE context_frequencies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            lemma_id INTEGER NOT NULL,
            pos VARCHAR(50) NOT NULL,
            context_type VARCHAR(100) NOT NULL, -- 'broad_domain' or 'subgenre'
            context_name VARCHAR(100) NOT NULL, -- domain/subgenre name
            frequency INTEGER DEFAULT 0,
            context_metadata TEXT, -- JSON for additional info
            FOREIGN KEY (lemma_id) REFERENCES lemmas(id)
        );

-- table: definitions
CREATE TABLE definitions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            lemma_id INTEGER NOT NULL,
            pos VARCHAR(50) NOT NULL,
            definition_text TEXT,
            definition_order INTEGER DEFAULT 1,
            example_sentence TEXT,
            hypernyms TEXT, -- JSON array
            FOREIGN KEY (lemma_id) REFERENCES lemmas(id)
        );

-- table: inflected_forms
CREATE TABLE inflected_forms (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            lemma_id INTEGER NOT NULL,
            form VARCHAR(255) NOT NULL,
            pos VARCHAR(50) NOT NULL,
            form_frequency INTEGER DEFAULT 0,
            form_rank INTEGER DEFAULT 0,
            inflection_type VARCHAR(100),
            grammatical_info TEXT, -- JSON string
            FOREIGN KEY (lemma_id) REFERENCES lemmas(id),
            UNIQUE(form, lemma_id, pos)
        );

-- table: languages
CREATE TABLE languages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code VARCHAR(5) NOT NULL UNIQUE,
            name VARCHAR(100) NOT NULL
        );

-- table: lemmas
CREATE TABLE lemmas (
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

-- table: pronunciations
CREATE TABLE pronunciations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            lemma_id INTEGER NOT NULL,
            ipa_notation VARCHAR(255),
            audio_file_path VARCHAR(500),
            accent_variety VARCHAR(50) DEFAULT 'general',
            FOREIGN KEY (lemma_id) REFERENCES lemmas(id)
        );

-- table: sqlite_sequence
CREATE TABLE sqlite_sequence(name,seq);

-- table: synonyms
CREATE TABLE synonyms (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            lemma_id INTEGER NOT NULL,
            synonym_lemma_id INTEGER NOT NULL,
            pos_specific VARCHAR(50),
            similarity_score DECIMAL(4,3) DEFAULT 0.0,
            FOREIGN KEY (lemma_id) REFERENCES lemmas(id),
            FOREIGN KEY (synonym_lemma_id) REFERENCES lemmas(id)
        );

-- table: word_references
CREATE TABLE word_references (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_definition_id INTEGER NOT NULL,
            referenced_lemma_id INTEGER NOT NULL,
            word_position INTEGER NOT NULL,
            word_text VARCHAR(255) NOT NULL,
            reference_type VARCHAR(50) DEFAULT 'definition',
            FOREIGN KEY (source_definition_id) REFERENCES definitions(id),
            FOREIGN KEY (referenced_lemma_id) REFERENCES lemmas(id)
        );


-- INDEXS
--------------------------------------------------

-- index: idx_context_freq_lemma_pos
CREATE INDEX idx_context_freq_lemma_pos ON context_frequencies(lemma_id, pos);

-- index: idx_context_freq_name
CREATE INDEX idx_context_freq_name ON context_frequencies(context_name);

-- index: idx_context_freq_type
CREATE INDEX idx_context_freq_type ON context_frequencies(context_type);

-- index: idx_inflected_forms_form
CREATE INDEX idx_inflected_forms_form ON inflected_forms(form);

-- index: idx_inflected_forms_frequency
CREATE INDEX idx_inflected_forms_frequency ON inflected_forms(form_frequency DESC);

-- index: idx_inflected_forms_lemma_id
CREATE INDEX idx_inflected_forms_lemma_id ON inflected_forms(lemma_id);

-- index: idx_inflected_forms_pos
CREATE INDEX idx_inflected_forms_pos ON inflected_forms(pos);

-- index: idx_lemmas_frequency
CREATE INDEX idx_lemmas_frequency ON lemmas(lemma_frequency DESC);

-- index: idx_lemmas_lemma
CREATE INDEX idx_lemmas_lemma ON lemmas(lemma);

-- index: idx_lemmas_rank
CREATE INDEX idx_lemmas_rank ON lemmas(lemma_rank);

-- index: idx_word_references_source
CREATE INDEX idx_word_references_source ON word_references(source_definition_id);

-- index: idx_word_references_target
CREATE INDEX idx_word_references_target ON word_references(referenced_lemma_id);

