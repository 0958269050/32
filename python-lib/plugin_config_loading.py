# -*- coding: utf-8 -*-
"""Module with utility functions for loading, resolving and validating plugin parameters"""

import logging
import re
import os
from typing import Dict, Set

import dataiku
from dataiku.customrecipe import (
    get_recipe_config,
    get_input_names_for_role,
    get_output_names_for_role,
    get_recipe_resource,
)

from plugin_io_utils import clean_text_df
from language_dict import SUPPORTED_LANGUAGES_SYMSPELL


def custom_vocabulary_checker(custom_vocabulary_dataset: dataiku.Dataset) -> Set:
    """Utility function to check the content of the optional custom vocabulary dataset"""
    dataset_schema = custom_vocabulary_dataset.get_config()["schema"]
    columns = dataset_schema["columns"]
    assert len(columns) == 1, "Custom vocabulary dataset must have only one column"

    col_name = columns[0]["name"]
    col_type = columns[0]["type"]
    assert col_type == "string", "Column of custom vocabulary dataset must be of string type"

    df = clean_text_df(custom_vocabulary_dataset.get_dataframe())
    custom_vocabulary = set(df[col_name].astype(str).str.lower().tolist())
    return custom_vocabulary


def custom_corrections_checker(custom_corrections_dataset: dataiku.Dataset) -> Dict:
    """Utility function to check the content of the optional custom corrections dataset"""
    dataset_schema = custom_corrections_dataset.get_config()["schema"]
    columns = dataset_schema["columns"]
    assert len(columns) == 2, "Custom corrections dataset must have only two columns"

    (word_column, correction_column) = (columns[0], columns[1])
    column_string_types = word_column["type"] == "string" and correction_column["type"] == "string"
    assert column_string_types, "Columns of custom corrections dataset must be of string type"

    df = custom_corrections_dataset.get_dataframe(infer_with_pandas=False)
    df = clean_text_df(df, dropna_columns=[word_column["name"]]).fillna("").astype(str)
    custom_corrections_dict = {row[0]: row[1] for row in df.itertuples(index=False)}
    return custom_corrections_dict


def load_plugin_config() -> Dict:
    """Utility function to load, resolve and validate all plugin config into a clean `params` dictionary"""
    params = {}
    recipe_config = get_recipe_config()

    # input dataset
    input_dataset_names = get_input_names_for_role("input_dataset")
    assert len(input_dataset_names) != 0, "Please specify input dataset"
    params["input_dataset"] = dataiku.Dataset(input_dataset_names[0])

    # output dataset
    output_dataset_names = get_output_names_for_role("output_dataset")
    assert len(output_dataset_names) != 0, "Please specify output dataset"
    params["output_dataset"] = dataiku.Dataset(output_dataset_names[0])

    # diagnosis dataset
    diagnosis_dataset_names = get_output_names_for_role("diagnosis_dataset")
    params["diagnosis_dataset"] = None
    params["compute_diagnosis"] = False
    if len(diagnosis_dataset_names) != 0:
        logging.info("Spellchecker diagnosis will be computed")
        params["compute_diagnosis"] = True
        params["diagnosis_dataset"] = dataiku.Dataset(diagnosis_dataset_names[0])
    else:
        logging.info("Spellchecker diagnosis will not be computed")

    # custom_vocabulary (optional input dataset)
    params["custom_vocabulary_set"] = set()
    custom_vocabulary_input = get_input_names_for_role("custom_vocabulary")
    if len(custom_vocabulary_input) != 0:
        custom_vocabulary_dataset = dataiku.Dataset(custom_vocabulary_input[0])
        params["custom_vocabulary_set"] = custom_vocabulary_checker(custom_vocabulary_dataset)
    logging.info("Custom vocabulary set: {}".format(params["custom_vocabulary_set"]))

    # custom_corrections (optional input dataset)
    params["custom_corrections"] = {}
    custom_corrections_input = get_input_names_for_role("custom_corrections")
    if len(custom_corrections_input) != 0:
        custom_corrections_dataset = dataiku.Dataset(custom_corrections_input[0])
        params["custom_corrections"] = custom_corrections_checker(custom_corrections_dataset)
    logging.info("Custom corrections: {}".format(params["custom_corrections"]))

    # path to the folder of dictionaries
    params["dictionary_folder_path"] = os.path.join(get_recipe_resource(), "dictionaries")

    # List of text columns
    params["text_column"] = recipe_config.get("text_column")
    logging.info("Text column: {}".format(params["text_column"]))
    assert params["text_column"] != "", "Empty text column selection"

    # Language selection
    params["language"] = recipe_config.get("language")
    if params["language"] == "language_column":
        params["language_column"] = recipe_config.get("language_column")
        assert (
            params["language_column"] is not None and params["language_column"] != ""
        ), "Empty language column selection"
        logging.info("Language column: {}".format(params["language_column"]))
    else:
        assert params["language"] is not None and params["language"] != "", "Empty language selection"
        assert params["language"] in SUPPORTED_LANGUAGES_SYMSPELL.keys(), "Unsupported language code: {}".format(
            params["language"]
        )
        params["language_column"] = ""
        logging.info("Language: {}".format(params["language"]))

    # Expert mode
    if recipe_config.get("expert"):
        logging.info("Expert mode is enabled")
    else:
        logging.info("Expert mode is disabled")

    # edit distance
    params["edit_distance"] = recipe_config.get("edit_distance")
    assert params["edit_distance"] >= 1 and params["edit_distance"] <= 100, "Edit distance must be between 2 and 100"
    logging.info("Maximum edit distance: {}".format(params["edit_distance"]))

    # ignore token
    if len(recipe_config.get("ignore_word_regex")) == 0:
        logging.info("No regular expression for words  not to be corrected")
        params["ignore_word_regex"] = None  # symspellpy wants None
    else:
        params["ignore_word_regex"] = recipe_config.get("ignore_word_regex")
        # Check for valid regex
        try:
            ignore_token_compiled = re.compile(params["ignore_word_regex"])
        except re.error:
            assert False, "Ignore pattern parameter: Invalid regex"
        params["ignore_word_regex"] = ignore_token_compiled.pattern
        logging.info("Regular expression for words not to be corrected: {}".format(params["ignore_word_regex"]))

    return params
