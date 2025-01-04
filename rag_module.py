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
    def __init__(self, embedding_model_name, persist_directory="chroma_db"):
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
        try:
            self.sentence_transformer = SentenceTransformer('all-mpnet-base-v2')  # or any model
        except Exception as e:
            print(f"Error loading sentence transformer model: {e}")
            self.sentence_transformer = None  # Set to None if there's an error

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
       if self.sentence_transformer is None:
           print("Sentence transformer model not loaded. Using basic chunking")
           return self._chunk_sentences(sentences, max_chunk_size, 1)

       chunks = []
       current_chunk = []
       for sentence in sentences:
           if not current_chunk:
              current_chunk.append(sentence) # start a new chunk
           else:
                # compute the embedding for this sentence and the current chunk
               current_chunk_embedding = self.sentence_transformer.encode(' '.join(current_chunk))
               sentence_embedding = self.sentence_transformer.encode(sentence)
               
                # compute cosine similarity
               similarity = np.dot(current_chunk_embedding, sentence_embedding) / (np.linalg.norm(current_chunk_embedding) * np.linalg.norm(sentence_embedding))

                # if the similarity is low, start a new chunk
               if similarity < 0.7 or len(current_chunk) >= max_chunk_size:
                    chunks.append(" ".join(current_chunk))
                    current_chunk = [sentence]
               else:
                  current_chunk.append(sentence)

       if current_chunk:
             chunks.append(" ".join(current_chunk))
       return chunks
    
    def _chunk_sentences(self, sentences: List[str], chunk_size: int = 4, chunk_overlap: int = 1) -> List[str]:
          """Chunks a list of sentences into chunks with overlap."""
          chunks = []
          for i in range(0, len(sentences), chunk_size - chunk_overlap):
            chunk = sentences[i:i + chunk_size]
            chunks.append(" ".join(chunk))
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
            embeddings = self.embedding_function(chunks) # batch the embeddings
            self.collection.add(documents=chunks, ids=ids, embeddings=embeddings)
            print(f"Successfully ingested {len(chunks)} chunks")
        else:
            print("No content found to ingest")

    def retrieve_context(self, query: str, n_results: int = 5) -> str:
      """Retrieves context for the given query"""
      results = self.collection.query(query_texts=[query], n_results=n_results)
      if results and 'documents' in results and results['documents']:  # Check if there are any results
            return "\n".join(results['documents'][0])  # Return the document strings
      else:
          return "No context retrieved"  # Handle the case of no results

    def clear_db(self):
        """Clears the current database"""
        try:
            self.client.delete_collection(name="rag_collection")
            self.collection = self.get_or_create_collection()
            print("Chroma DB cleared")
        except Exception as e:
            print(f"Error clearing Chroma DB {e}")