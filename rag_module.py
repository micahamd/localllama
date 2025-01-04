import os
import re
from typing import List
import chromadb
from chromadb.utils import embedding_functions
from markitdown import MarkItDown
import ollama
import numpy as np
import nltk
from nltk.tokenize import sent_tokenize
from sentence_transformers import SentenceTransformer

class OllamaEmbeddingFunction(embedding_functions.EmbeddingFunction):
    def __init__(self, model_name: str):
        self.model_name = model_name

    def __call__(self, texts: List[str]) -> List[List[float]]:
        embeddings = []
        for text in texts:
            try:
                # Call ollama.embeddings to get the embedding
                response = ollama.embeddings(model=self.model_name, prompt=text)
                # Extract the embedding from the dictionary and append to the list
                embeddings.append(response['embedding'])
            except Exception as e:
                 print(f"Error getting embedding for text '{text}': {e}")
                 embeddings.append([0.0] * 1024) # use zero embedding as a fallback
        return embeddings # Return the embeddings, not the dictionaries

class RAG:
    def __init__(self, embedding_model_name, persist_directory="chroma_db", chunk_size=128):
        self.embedding_model_name = embedding_model_name
        self.persist_directory = persist_directory
        self.client = chromadb.PersistentClient(path=self.persist_directory)
        self.embedding_function = self.get_embedding_function()
        self.collection = self.get_or_create_collection()
        try:
            nltk.data.find("tokenizers/punkt")
        except LookupError:
            nltk.download("punkt") # Download punkt sentence tokenizer if not available
        try:
            nltk.data.find("tokenizers/punkt_tab")
        except LookupError:
            nltk.download("punkt_tab")
        self.sentence_transformer = None # Removed Sentence Transformer
        self.chunk_size = chunk_size

    def get_embedding_function(self):
        """Retrieves a ollama embedding function."""
        return OllamaEmbeddingFunction(model_name=self.embedding_model_name)

    def get_or_create_collection(self):
        """Retrieves or creates a chroma collection."""
        try:
            return self.client.get_collection(name="rag_collection", embedding_function=self.embedding_function)
        except chromadb.errors.InvalidCollectionException:
            return self.client.create_collection(name="rag_collection", embedding_function=self.embedding_function)
    
    def update_embedding_function(self, new_embedding_model_name):
        """Updates the embedding function and recreates the collection."""
        self.embedding_model_name = new_embedding_model_name
        self.embedding_function = self.get_embedding_function()
        self.clear_db() #clear the old collection
        self.collection = self.get_or_create_collection() # create new collection using new function
        print(f"Updated embedding function to {self.embedding_model_name}")
    
    def _extract_sentences(self, text: str) -> List[str]:
        """Extracts sentences from the given text."""
        return sent_tokenize(text)

    def _semantic_chunk(self, sentences, max_chunk_size=5, min_chunk_size=2):
       """Group sentences semantically."""
       print("Using basic chunking")
       return self._chunk_sentences(sentences, max_chunk_size, 1)
    
    def _chunk_sentences(self, sentences: List[str], chunk_size: int = 4, chunk_overlap: int = 1) -> List[str]:
          """Chunks a list of sentences into chunks with overlap."""
          chunks = []
          current_chunk = []
          for sentence in sentences:
             current_chunk.append(sentence)
             if len(current_chunk) >= chunk_size:
                chunks.append(" ".join(current_chunk))
                current_chunk = []
          if current_chunk:
             chunks.append(" ".join(current_chunk))
          return chunks


    def _extract_text_from_files(self, file_paths: List[str]) -> str:
        """Extracts and concatenates text from the given file paths."""
        md = MarkItDown()
        all_text = []
        for file_path in file_paths:
            file = None
            try:
                file = open(file_path, 'r', encoding='utf-8', errors='ignore')
                text = md.convert(file_path).text_content
                all_text.append(text)
            except Exception as e:
                print(f"Error reading file {file_path}: {e}")
            finally:
                if file:
                    file.close()
        return "\n".join(all_text)

    def ingest_data(self, file_paths: List[str]):
        """Ingests data from file paths, processes and stores into the db"""
        text = self._extract_text_from_files(file_paths)
        if text:
            sentences = self._extract_sentences(text)
            chunks = self._semantic_chunk(sentences)
            ids = [str(i) for i in range(len(chunks))]
            embeddings = self.embedding_function(chunks)
            self.collection.add(documents=chunks, ids=ids, embeddings=embeddings)
            print(f"Successfully ingested {len(chunks)} chunks")
        else:
            print("No content found to ingest")

    def retrieve_context(self, query: str, n_results: int = 5) -> str:
        """Retrieves context for the given query, preserving original order."""
        results = self.collection.query(query_texts=[query], n_results=n_results, include=['documents', 'metadatas'])
        if results and 'documents' in results and results['metadatas']:
            # Create a list of (chunk, id) tuples
            chunk_id_pairs = []
            for doc_group, metadata_group in zip(results['documents'], results['metadatas']):
                for doc, metadata in zip(doc_group, metadata_group):
                    if metadata and 'id' in metadata:
                        chunk_id_pairs.append((doc, int(metadata.get('id'))))
                    else:
                       chunk_id_pairs.append((doc, -1)) # if no id, append with -1 to maintain order
            
            # Sort by the integer ID
            sorted_pairs = sorted(chunk_id_pairs, key=lambda x: x[1])
            
            # Extract the ordered chunks
            ordered_chunks = [chunk for chunk, _ in sorted_pairs]
            
            return "\n".join(ordered_chunks)
        else:
            return "No context retrieved"

    def clear_db(self):
        """Clears the current database"""
        try:
            self.client.delete_collection(name="rag_collection")
            self.collection = self.get_or_create_collection()
            print("Chroma DB cleared")
        except Exception as e:
            print(f"Error clearing Chroma DB {e}")