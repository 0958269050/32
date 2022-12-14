# -*- coding: utf-8 -*-
# This is a test file intended to be used with pytest
# pytest automatically runs all the function starting with "test_"
# see https://docs.pytest.org for more information

import os

import pytest
import pandas as pd

from spacy_tokenizer import MultilingualTokenizer

stopwords_folder_path = os.getenv("STOPWORDS_FOLDER_PATH", "path_is_no_good")


def test_tokenize_df_english():
    input_df = pd.DataFrame({"input_text": ["I hope nothing. I fear nothing. I am free. ๐ฉ ๐ #OMG"]})
    tokenizer = MultilingualTokenizer()
    output_df = tokenizer.tokenize_df(df=input_df, text_column="input_text", language="en")
    tokenized_document = output_df[tokenizer.tokenized_column][0]
    assert len(tokenized_document) == 15


def test_tokenize_df_japanese():
    input_df = pd.DataFrame({"input_text": ["ๆไธไผใ ็ฐไฝๅๅฟใ ใใใงใใ"]})
    tokenizer = MultilingualTokenizer()
    output_df = tokenizer.tokenize_df(df=input_df, text_column="input_text", language="ja")
    tokenized_document = output_df[tokenizer.tokenized_column][0]
    assert len(tokenized_document) == 9


def test_tokenize_df_multilingual():
    input_df = pd.DataFrame(
        {
            "input_text": [
                "I hope nothing. I fear nothing. I am free.",
                " Les sanglots longs des violons d'automne",
                "ๅญๆฐ๏ผโๅญธ่ไธๆๅ็ฝ๏ผๆ่ไธๅญธๅๆฎใโ",
                "ๆไธไผใ ็ฐไฝๅๅฟใ ใใใงใใ",
            ],
            "language": ["en", "fr", "zh", "ja"],
        }
    )
    tokenizer = MultilingualTokenizer(stopwords_folder_path=stopwords_folder_path)
    output_df = tokenizer.tokenize_df(df=input_df, text_column="input_text", language_column="language")
    tokenized_documents = output_df[tokenizer.tokenized_column]
    tokenized_documents_length = [len(doc) for doc in tokenized_documents]
    assert tokenized_documents_length == [12, 8, 13, 9]


def test_tokenize_df_long_text():
    input_df = pd.DataFrame({"input_text": ["Long text"]})
    tokenizer = MultilingualTokenizer(max_num_characters=1)
    with pytest.raises(ValueError):
        tokenizer.tokenize_df(df=input_df, text_column="input_text", language="en")
