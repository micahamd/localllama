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

        # Initialize embedding cache
        self._embedding_cache = {}
        self._cache_hits = 0
        self._cache_misses = 0
        self._max_cache_size = 1000  # Maximum number of embeddings to cache

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

        # Set with validation
        self._set_chunk_size(chunk_size)
        self.use_semantic_chunking = use_semantic_chunking
        self._set_min_chunk_size(min_chunk_size)
        self._set_max_chunk_size(max_chunk_size)

    def _set_chunk_size(self, size):
        """Safely set chunk size with validation."""
        try:
            size = int(size)
            self._chunk_size = max(1, size)  # Ensure positive value
        except (ValueError, TypeError):
            print(f"Invalid chunk size: {size}, using default of 128")
            self._chunk_size = 128

    def _set_min_chunk_size(self, size):
        """Safely set minimum chunk size with validation."""
        try:
            size = int(size)
            self._min_chunk_size = max(1, size)  # Ensure positive value
        except (ValueError, TypeError):
            print(f"Invalid min chunk size: {size}, using default of 2")
            self._min_chunk_size = 2

    def _set_max_chunk_size(self, size):
        """Safely set maximum chunk size with validation."""
        try:
            size = int(size)
            self._max_chunk_size = max(self._min_chunk_size, size)  # Ensure at least equal to min size
        except (ValueError, TypeError):
            print(f"Invalid max chunk size: {size}, using default of 5")
            self._max_chunk_size = 5

    @property
    def chunk_size(self):
        return self._chunk_size

    @chunk_size.setter
    def chunk_size(self, value):
        self._set_chunk_size(value)

    @property
    def min_chunk_size(self):
        return self._min_chunk_size

    @min_chunk_size.setter
    def min_chunk_size(self, value):
        self._set_min_chunk_size(value)
        if self._max_chunk_size < self._min_chunk_size:
            self._max_chunk_size = self._min_chunk_size

    @property
    def max_chunk_size(self):
        return self._max_chunk_size

    @max_chunk_size.setter
    def max_chunk_size(self, value):
        self._set_max_chunk_size(value)

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
            # Use DefaultEmbeddingFunction for nomic models since HuggingFace requires a valid API key
            print("Using default embedding function for nomic models to avoid API key requirement")
            return embedding_functions.DefaultEmbeddingFunction()
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
            try:
                # Try to get an API key from environment or config
                import os
                api_key = os.environ.get('OPENAI_API_KEY', 'sk-no-key-provided')

                # If the key starts with 'sk-', it's likely a valid format
                if not api_key.startswith('sk-'):
                    api_key = f"sk-placeholder-key-{api_key}"

                return embedding_functions.OpenAIEmbeddingFunction(
                    api_key=api_key,
                    model_name="text-embedding-ada-002"
                )
            except Exception as e:
                print(f"Error creating OpenAI embedding function: {e}")
                # Fallback to default embedding function
                return embedding_functions.DefaultEmbeddingFunction()

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
        """Group sentences semantically with performance optimizations."""
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

        # Process sentences in batches for better performance
        batch_size = 10  # Process 10 sentences at a time

        for i in range(0, len(sentences), batch_size):
            batch = sentences[i:i+batch_size]

            # If this is the first batch and current_chunk is empty
            if not current_chunk and batch:
                current_chunk = [batch[0]]
                batch = batch[1:]

            if not batch:  # Skip empty batches
                continue

            # Compute embeddings for all sentences in the batch at once
            if current_chunk:
                current_chunk_text = ' '.join(current_chunk)
                batch_texts = [current_chunk_text] + batch

                # Use cached embeddings when available
                all_embeddings = []
                texts_to_encode = []
                text_indices = []

                # Check cache for each text
                for idx, text in enumerate(batch_texts):
                    text_hash = hash(text)
                    if text_hash in self._embedding_cache:
                        all_embeddings.append(self._embedding_cache[text_hash])
                        self._cache_hits += 1
                    else:
                        texts_to_encode.append(text)
                        text_indices.append(idx)
                        self._cache_misses += 1

                # Encode only texts not in cache
                if texts_to_encode:
                    new_embeddings = self.sentence_transformer.encode(texts_to_encode)

                    # Add new embeddings to cache and results
                    for i, text_idx in enumerate(text_indices):
                        text_hash = hash(batch_texts[text_idx])
                        self._embedding_cache[text_hash] = new_embeddings[i]

                        # Manage cache size
                        if len(self._embedding_cache) > self._max_cache_size:
                            # Remove a random item if cache is full
                            self._embedding_cache.pop(next(iter(self._embedding_cache)))

                # Reorder embeddings to match original batch order
                ordered_embeddings = [None] * len(batch_texts)
                for idx, text in enumerate(batch_texts):
                    text_hash = hash(text)
                    ordered_embeddings[idx] = self._embedding_cache[text_hash]

                all_embeddings = ordered_embeddings

                # First embedding is for the current chunk
                current_chunk_embedding = all_embeddings[0]
                sentence_embeddings = all_embeddings[1:]

                # Process each sentence in the batch
                for j, sentence in enumerate(batch):
                    sentence_embedding = sentence_embeddings[j]

                    # Compute cosine similarity
                    similarity = np.dot(current_chunk_embedding, sentence_embedding) / \
                                (np.linalg.norm(current_chunk_embedding) * np.linalg.norm(sentence_embedding))

                    # If similarity is low or max size reached, start a new chunk
                    if similarity < 0.7 or len(current_chunk) >= self.max_chunk_size:
                        chunks.append(" ".join(current_chunk))
                        current_chunk = [sentence]
                        # Update current_chunk_embedding for the next iteration
                        current_chunk_embedding = sentence_embedding
                    else:
                        current_chunk.append(sentence)
                        # Recompute the embedding for the updated chunk
                        if j < len(batch) - 1:  # Only if not the last sentence in batch
                            current_chunk_text = ' '.join(current_chunk)
                            current_chunk_embedding = self.sentence_transformer.encode(current_chunk_text)

        # Add the last chunk if it has enough sentences
        if current_chunk and len(current_chunk) >= self.min_chunk_size:
            chunks.append(" ".join(current_chunk))
        elif current_chunk:  # If chunk is too small but not empty, add it anyway
            chunks.append(" ".join(current_chunk))

        return chunks

    def _chunk_sentences(self, sentences: List[str], chunk_size: int = 4, chunk_overlap: int = 1) -> List[str]:
        """Chunks a list of sentences into chunks with overlap."""
        # More efficient implementation using list slicing
        chunks = []

        # Process in batches for better performance
        for i in range(0, len(sentences), max(1, chunk_size - chunk_overlap)):
            end_idx = min(i + chunk_size, len(sentences))
            chunk = sentences[i:end_idx]
            if chunk:  # Only add non-empty chunks
                chunks.append(" ".join(chunk))

        return chunks

    def get_cache_stats(self):
        """Return statistics about the embedding cache."""
        total_requests = self._cache_hits + self._cache_misses
        hit_rate = 0 if total_requests == 0 else (self._cache_hits / total_requests) * 100

        return {
            "cache_size": len(self._embedding_cache),
            "max_cache_size": self._max_cache_size,
            "cache_hits": self._cache_hits,
            "cache_misses": self._cache_misses,
            "hit_rate_percent": hit_rate
        }

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
        """Ingests data from file paths, processes and stores into the db with optimized processing"""
        # Process files in batches to reduce memory usage
        batch_size = 5  # Process 5 files at a time
        all_chunks = []
        all_ids = []
        all_metadatas = []
        global_chunk_index = 0

        # Process files in batches
        for i in range(0, len(file_paths), batch_size):
            batch_files = file_paths[i:i+batch_size]
            print(f"Processing batch {i//batch_size + 1}/{(len(file_paths) + batch_size - 1)//batch_size}")

            # Process each file in the batch
            for file_path in batch_files:
                try:
                    # Extract text from the file
                    file_text = self._extract_text_from_files([file_path])
                    if not file_text:
                        print(f"No content found in {file_path}")
                        continue

                    # Process the file text
                    file_sentences = self._extract_sentences(file_text)
                    file_chunks = self._semantic_chunk(file_sentences)

                    # Create metadata for each chunk
                    for i in range(len(file_chunks)):
                        all_chunks.append(file_chunks[i])
                        all_ids.append(str(global_chunk_index))
                        all_metadatas.append({'source': os.path.basename(file_path), 'chunk_index': i})
                        global_chunk_index += 1

                except Exception as e:
                    print(f"Error processing file {file_path}: {e}")

        # Add chunks to the collection
        if all_chunks:
            # Add in smaller batches to avoid memory issues
            chunk_batch_size = 100  # Add 100 chunks at a time
            total_added = 0

            for j in range(0, len(all_chunks), chunk_batch_size):
                end_idx = min(j + chunk_batch_size, len(all_chunks))
                batch_chunks = all_chunks[j:end_idx]
                batch_ids = all_ids[j:end_idx]
                batch_metadatas = all_metadatas[j:end_idx]

                try:
                    # Try using the embedding function directly
                    self.collection.add(
                        documents=batch_chunks,
                        ids=batch_ids,
                        metadatas=batch_metadatas
                    )
                    total_added += len(batch_chunks)
                    print(f"Added batch {j//chunk_batch_size + 1}/{(len(all_chunks) + chunk_batch_size - 1)//chunk_batch_size} ({total_added}/{len(all_chunks)} chunks)")
                except Exception as e:
                    try:
                        # Fallback: manually compute embeddings first
                        print(f"First attempt failed: {e}. Trying alternative embedding approach...")
                        embeddings = self.embedding_function(batch_chunks)
                        self.collection.add(
                            documents=batch_chunks,
                            ids=batch_ids,
                            embeddings=embeddings,
                            metadatas=batch_metadatas
                        )
                        total_added += len(batch_chunks)
                        print(f"Added batch {j//chunk_batch_size + 1}/{(len(all_chunks) + chunk_batch_size - 1)//chunk_batch_size} ({total_added}/{len(all_chunks)} chunks)")
                    except Exception as e2:
                        print(f"Error adding batch to collection: {e2}")

            print(f"Successfully ingested {total_added} chunks from {len(file_paths)} files")

            # Print cache statistics
            if self.use_semantic_chunking and self._model_loaded:
                stats = self.get_cache_stats()
                print(f"Embedding cache: {stats['cache_size']}/{stats['max_cache_size']} entries, "
                      f"{stats['hit_rate_percent']:.1f}% hit rate")
        else:
            print("No chunks created for ingestion")

    def retrieve_context(self, query: str, n_results: int = 5) -> str:
        """Retrieves context for the given query, preserving original order with optimized processing."""
        try:
            # Check if collection is empty
            collection_data = self.collection.get()
            if not collection_data or not collection_data.get('documents'):
                return "No documents in the collection"

            # Use cached query results if the same query was made recently
            query_hash = hash(query)
            if hasattr(self, '_query_cache') and query_hash in self._query_cache:
                print("Using cached query results")
                return self._query_cache[query_hash]

            # Initialize query cache if it doesn't exist
            if not hasattr(self, '_query_cache'):
                self._query_cache = {}
                self._max_query_cache_size = 20  # Store up to 20 recent queries

            # Perform the query
            results = self.collection.query(
                query_texts=[query],
                n_results=n_results,
                include=['documents', 'metadatas', 'distances']
            )

            if not results or 'documents' not in results or not results['documents'] or not results['documents'][0]:
                return "No context retrieved"

            # Process results more efficiently
            chunk_data = []
            doc_group = results['documents'][0]
            metadata_group = results['metadatas'][0]
            distance_group = results['distances'][0]

            # Pre-allocate the list with the correct size
            chunk_data = [None] * len(doc_group)

            # Process all chunks in a single loop
            for i in range(len(doc_group)):
                # Calculate relevance score from distance
                relevance_score = 1 / (1 + distance_group[i])
                chunk_data[i] = {
                    'text': doc_group[i],
                    'source': metadata_group[i].get('source', 'Unknown'),
                    'chunk_index': metadata_group[i].get('chunk_index', -1),
                    'relevance': relevance_score
                }

            # Sort by source and then chunk index
            sorted_chunks = sorted(chunk_data, key=lambda x: (x['source'], x['chunk_index']))

            # Extract just the text for the combined context string
            ordered_chunks_text = [chunk['text'] for chunk in sorted_chunks]
            result = "\n\n".join(ordered_chunks_text)

            # Cache the result
            self._query_cache[query_hash] = result

            # Manage cache size
            if len(self._query_cache) > self._max_query_cache_size:
                # Remove oldest entry (first key)
                self._query_cache.pop(next(iter(self._query_cache)))

            return result
        except Exception as e:
            print(f"Error retrieving context: {e}")
            return f"Error retrieving context: {str(e)}"

    def clear_db(self):
        """Clears the current database and all caches"""
        try:
            # Clear the database
            self.client.delete_collection(name="rag_collection")
            self.collection = self.get_or_create_collection()

            # Clear the embedding cache
            self._embedding_cache = {}
            self._cache_hits = 0
            self._cache_misses = 0

            # Clear the query cache if it exists
            if hasattr(self, '_query_cache'):
                self._query_cache = {}

            print("Chroma DB and caches cleared")
        except Exception as e:
            print(f"Error clearing Chroma DB: {e}")

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
