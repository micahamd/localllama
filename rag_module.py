import os
import re
from typing import List, Dict, Tuple, Any
import chromadb
from chromadb.utils import embedding_functions
from markitdown import MarkItDown
import ollama
import numpy as np
import nltk
from nltk.tokenize import sent_tokenize
import threading
import importlib.util
import google.generativeai as genai

class OllamaEmbeddingFunction(embedding_functions.EmbeddingFunction):
    def __init__(self, model_name: str):
        self.model_name = model_name

    def __call__(self, texts: List[str]) -> List[List[float]]:
        embeddings = []
        for text in texts:
            try:
                # Call ollama.embeddings to get the embedding
                response = ollama.embeddings(model=self.model_name, prompt=text)
                if response and 'embedding' in response and response['embedding'] is not None:
                    embeddings.append(response['embedding'])
                else:
                    print(f"Error: Ollama embedding is None for text '{text}'. Using fallback.")
                    embeddings.append([0.0] * 1024) # use zero embedding as a fallback
            except Exception as e:
                 print(f"Error getting embedding for text '{text}': {e}")
                 embeddings.append([0.0] * 1024) # use zero embedding as a fallback
        return embeddings

class GeminiEmbeddingFunction(embedding_functions.EmbeddingFunction):
    def __init__(self, gemini_chat):
        self.gemini_chat = gemini_chat

    def __call__(self, texts: List[str]) -> List[List[float]]:
        embeddings = []
        for text in texts:
            try:
                # Call gemini_chat.get_embedding to get the embedding
                embedding = self.gemini_chat.get_embedding(text, model=self.gemini_chat.api_config.get_default_embedding_model())
                if embedding is not None:
                    embeddings.append(embedding)
                else:
                    print(f"Error: Gemini embedding is None for text '{text}'. Using fallback.")
                    embeddings.append([0.0] * 768) # use zero embedding as a fallback
            except Exception as e:
                 print(f"Error getting embedding for text '{text}': {e}")
                 embeddings.append([0.0] * 768) # use zero embedding as a fallback
        return embeddings

class DeepSeekEmbeddingFunction(embedding_functions.EmbeddingFunction):
    def __init__(self, deepseek_client):
        self.deepseek_client = deepseek_client

    def __call__(self, texts: List[str]) -> List[List[float]]:
        embeddings = []
        for text in texts:
            try:
                # Call deepseek client to get the embedding
                embedding = self.deepseek_client.get_embedding(text)
                if embedding is not None:
                    embeddings.append(embedding)
                else:
                    print(f"Error: DeepSeek embedding is None for text '{text}'. Using fallback.")
                    embeddings.append([0.0] * 1024)  # use zero embedding as a fallback
            except Exception as e:
                print(f"Error getting embedding for text '{text}': {e}")
                embeddings.append([0.0] * 1024)  # use zero embedding as a fallback
        return embeddings

class RAG:
    def __init__(self, embedding_model_name, persist_directory="chroma_db", chunk_size=128, 
                 use_semantic_chunking=False, min_chunk_size=2, max_chunk_size=5):
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
            
        # Initialize semantic chunking settings but don't load model yet
        self.sentence_transformer = None
        self._is_loading_model = False
        self._model_loaded = False
        self._model_load_error = None
        
        self.chunk_size = chunk_size
        self.use_semantic_chunking = use_semantic_chunking
        self.min_chunk_size = min_chunk_size
        self.max_chunk_size = max_chunk_size

    def _check_sentence_transformer_installed(self):
        """Check if sentence-transformers package is installed"""
        return importlib.util.find_spec("sentence_transformers") is not None

    def _load_sentence_transformer(self):
        """Load the sentence transformer model in a separate thread to avoid UI freezing"""
        if self._is_loading_model:
            return  # Already loading
            
        if self._model_loaded:
            return  # Already loaded
            
        if not self._check_sentence_transformer_installed():
            self._model_load_error = "sentence-transformers package is not installed. Please install it with 'pip install sentence-transformers'."
            print(self._model_load_error)
            return
            
        # Start loading in a separate thread
        self._is_loading_model = True
        threading.Thread(target=self._load_model_thread, daemon=True).start()
    
    def _load_model_thread(self):
        """Thread function to load the model"""
        try:
            from sentence_transformers import SentenceTransformer
            self.sentence_transformer = SentenceTransformer('all-mpnet-base-v2')
            self._model_loaded = True
            print("Sentence transformer model loaded successfully")
        except Exception as e:
            self._model_load_error = f"Error loading sentence transformer model: {e}"
            print(self._model_load_error)
            self.sentence_transformer = None
        finally:
            self._is_loading_model = False

    def get_embedding_function(self):
        """Retrieves the correct embedding function based on the selected model."""
        if not self.embedding_model_name or self.embedding_model_name == "":
            # Return default embedding function
            return embedding_functions.DefaultEmbeddingFunction()
            
        if 'embed' in self.embedding_model_name and 'nomic' not in self.embedding_model_name:
            # Ollama embedding model
            return OllamaEmbeddingFunction(model_name=self.embedding_model_name)
        elif 'nomic' in self.embedding_model_name:
            # Use HuggingFace for nomic models
            return embedding_functions.HuggingFaceEmbeddingFunction(
                api_key="",  # No API key needed for local models
                model_name="nomic-ai/nomic-embed-text-v1"
            )
        elif 'text-embedding' in self.embedding_model_name:
            # Google embedding model
            from models_manager import GeminiManager
            gemini_chat = GeminiManager()
            return GeminiEmbeddingFunction(gemini_chat=gemini_chat)
        elif 'deepseek' in self.embedding_model_name:
            # DeepSeek embedding model
            from models_manager import DeepSeekManager
            deepseek_client = DeepSeekManager()
            return DeepSeekEmbeddingFunction(deepseek_client=deepseek_client)
        else:
            # Default to OpenAI compatible embedding function
            return embedding_functions.OpenAIEmbeddingFunction(
                api_key="",  # Not used but required
                model_name="text-embedding-ada-002"
            )

    def get_or_create_collection(self):
        """Retrieves or creates a chroma collection."""
        try:
            return self.client.get_collection(name="rag_collection", embedding_function=self.embedding_function)
        except chromadb.errors.InvalidCollectionException:
            return self.client.create_collection(name="rag_collection", embedding_function=self.embedding_function)
    
    def update_embedding_function(self, new_embedding_model_name):
        """Updates the embedding function and recreates the collection if needed."""
        if self.embedding_model_name != new_embedding_model_name:
            self.embedding_model_name = new_embedding_model_name
            self.embedding_function = self.get_embedding_function()
            self.clear_db() #clear the old collection since embeddings will be incompatible
            self.collection = self.get_or_create_collection() # create new collection using new function
            print(f"Updated embedding function to {self.embedding_model_name}")
    
    def _extract_sentences(self, text: str) -> List[str]:
        """Extracts sentences from the given text."""
        return sent_tokenize(text)

    def _semantic_chunk(self, sentences):
        """Group sentences semantically."""
        # If semantic chunking is disabled, use basic chunking
        if not self.use_semantic_chunking:
            print("Using basic chunking")
            return self._chunk_sentences(sentences, self.chunk_size, 1)
            
        # If using semantic chunking but model isn't loaded yet, try loading it
        if self.use_semantic_chunking and not self._model_loaded and not self._is_loading_model:
            self._load_sentence_transformer()
        
        # If model is still loading or failed to load, fall back to basic chunking
        if self._is_loading_model or not self._model_loaded:
            print("Sentence transformer not available, falling back to basic chunking")
            return self._chunk_sentences(sentences, self.chunk_size, 1)
        
        print(f"Using semantic chunking (min: {self.min_chunk_size}, max: {self.max_chunk_size})")
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

                # if the similarity is low or max size reached, start a new chunk
                if similarity < 0.7 or len(current_chunk) >= self.max_chunk_size:
                    chunks.append(" ".join(current_chunk))
                    current_chunk = [sentence]
                else:
                    current_chunk.append(sentence)

        # Add the last chunk if it has enough sentences
        if current_chunk and len(current_chunk) >= self.min_chunk_size:
            chunks.append(" ".join(current_chunk))
        elif current_chunk:  # If chunk is too small but not empty, add it anyway
            chunks.append(" ".join(current_chunk))
            
        return chunks
    
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
            ids = []
            metadatas = []
            
            # Keep track of chunk index within the entire corpus
            global_chunk_index = 0
            
            for file_path in file_paths:
                file_text = self._extract_text_from_files([file_path])
                if file_text:
                    file_sentences = self._extract_sentences(file_text)
                    file_chunks = self._semantic_chunk(file_sentences)
                    for i, chunk in enumerate(file_chunks):
                        ids.append(str(global_chunk_index))
                        metadatas.append({'source': os.path.basename(file_path), 'chunk_index': i})
                        global_chunk_index += 1

            # Ensure we have the same number of chunks, IDs and metadata
            if len(chunks) != len(ids) or len(chunks) != len(metadatas):
                print(f"Warning: Mismatch in chunks ({len(chunks)}), ids ({len(ids)}), and metadata ({len(metadatas)})")
                # Adjust to make them match - use the shortest length
                min_length = min(len(chunks), len(ids), len(metadatas))
                chunks = chunks[:min_length]
                ids = ids[:min_length]
                metadatas = metadatas[:min_length]

            if chunks:
                # Get embeddings and add to collection
                try:
                    embeddings = self.embedding_function(chunks)
                    self.collection.add(documents=chunks, ids=ids, embeddings=embeddings, metadatas=metadatas)
                    print(f"Successfully ingested {len(chunks)} chunks from {len(file_paths)} files")
                except Exception as e:
                    print(f"Error adding to collection: {e}")
            else:
                print("No chunks created for ingestion")
        else:
            print("No content found to ingest")

    def retrieve_context(self, query: str, n_results: int = 5) -> str:
        """Retrieves context for the given query, preserving original order."""
        try:
            results = self.collection.query(query_texts=[query], n_results=n_results, include=['documents', 'metadatas', 'distances'])
            
            if not results or 'documents' not in results or not results['documents'] or not results['documents'][0]:
                return "No context retrieved"
                
            chunk_data = []
            for doc_group, metadata_group, distance_group in zip(results['documents'], results['metadatas'], results['distances']):
                for doc, metadata, distance in zip(doc_group, metadata_group, distance_group):
                    # Calculate relevance score from distance
                    relevance_score = 1 / (1 + distance)
                    chunk_data.append({
                        'text': doc,
                        'source': metadata.get('source', 'Unknown'),
                        'chunk_index': metadata.get('chunk_index', -1),
                        'relevance': relevance_score
                    })

            # Sort by source and then chunk index
            sorted_chunks = sorted(chunk_data, key=lambda x: (x['source'], x['chunk_index']))
            
            # Extract just the text for the combined context string
            ordered_chunks_text = [chunk['text'] for chunk in sorted_chunks]

            return "\n\n".join(ordered_chunks_text)
        except Exception as e:
            print(f"Error retrieving context: {e}")
            return "Error retrieving context"

    def clear_db(self):
        """Clears the current database"""
        try:
            self.client.delete_collection(name="rag_collection")
            self.collection = self.get_or_create_collection()
            print("Chroma DB cleared")
        except Exception as e:
            print(f"Error clearing Chroma DB {e}")
            
    def get_semantic_chunking_status(self):
        """Return current status of semantic chunking"""
        if not self.use_semantic_chunking:
            return "disabled"
        elif self._is_loading_model:
            return "loading"
        elif self._model_loaded:
            return "ready"
        else:
            return "error"
            
    def get_model_load_error(self):
        """Return error message if model failed to load"""
        return self._model_load_error
