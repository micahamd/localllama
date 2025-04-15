import os
from typing import List
import chromadb
from chromadb.utils import embedding_functions
from markitdown import MarkItDown
import ollama
import nltk
from nltk.tokenize import sent_tokenize
# Removed unused imports for better performance

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
    def __init__(self, embedding_model_name, persist_directory="chroma_db", chunk_size=128):
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

        # Add use_semantic_chunking property with default value False
        # This is for backward compatibility with code that might check this property
        self.use_semantic_chunking = False

        try:
            nltk.data.find("tokenizers/punkt")
        except LookupError:
            nltk.download("punkt") # Download punkt sentence tokenizer if not available
        try:
            nltk.data.find("tokenizers/punkt_tab")
        except LookupError:
            nltk.download("punkt_tab")

        # Set with validation
        self._set_chunk_size(chunk_size)

    def _set_chunk_size(self, size):
        """Safely set chunk size with validation."""
        try:
            size = int(size)
            self._chunk_size = max(1, size)  # Ensure positive value
        except (ValueError, TypeError):
            print(f"Invalid chunk size: {size}, using default of 128")
            self._chunk_size = 128

    # Semantic chunking methods removed for better performance

    @property
    def chunk_size(self):
        return self._chunk_size

    @chunk_size.setter
    def chunk_size(self, value):
        self._set_chunk_size(value)

    # Semantic chunking property methods removed for better performance

    # Add _model_loaded property for backward compatibility
    @property
    def _model_loaded(self):
        """Always returns True for backward compatibility."""
        return True

    # Sentence transformer methods removed for better performance

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
        """Basic chunking method - semantic chunking removed for better performance."""
        print("Using basic chunking")
        return self._chunk_sentences(sentences, self.chunk_size, 1)

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

    # Semantic chunking status method removed for better performance

    # Model load error method removed for better performance
