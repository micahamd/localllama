from flask import Flask, request, jsonify, send_from_directory
import os
import threading
import ollama
from gemini_module import GeminiChat
from sentence_transformers import SentenceTransformer
from rag_module import RAG
from werkzeug.utils import secure_filename
from markitdown import MarkItDown
import re
from flask_cors import CORS
import base64

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

UPLOAD_FOLDER = 'uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
gemini_chat = GeminiChat()
rag = None  # Will be initialized when developer and model are selected
selected_model = None
selected_embedding_model = None
developer = 'ollama'  # Default developer
chunk_size = 128
use_semantic_chunking = False
stop_event = threading.Event()

# Serve static files from the frontend directory
@app.route('/', defaults={'path': 'index.html'})
@app.route('/<path:path>')
def serve_static(path):
    if "frontend" in path:
        return send_from_directory(os.path.join(os.path.dirname(__file__), 'frontend'), path)
    return send_from_directory(os.path.join(os.path.dirname(__file__)), path)

def extract_content(file_path):
    try:
        md = MarkItDown()
        result = md.convert(file_path)
        return result.text_content
    except Exception as e:
        print(f"Error extracting content: {str(e)}")
        return None

@app.route('/process_file', methods=['POST'])
def process_file():
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    if file:
        filename = secure_filename(file.filename)
        file_path = os.path.join(UPLOAD_FOLDER, filename)
        try:
            file.save(file_path)
            content = extract_content(file_path)
            if content:
                word_count = len(re.findall(r'\w+', content))
                return jsonify({
                    'content': content,
                    'wordCount': word_count
                })
            return jsonify({'error': 'Could not extract content from file'}), 400
        finally:
            # Clean up uploaded file
            if os.path.exists(file_path):
                os.remove(file_path)
    
    return jsonify({'error': 'Invalid file'}), 400

@app.route('/batch', methods=['POST'])
def batch_process():
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    prompt = request.form.get('prompt')
    system_msg = request.form.get('system_msg', '').strip()
    temperature = float(request.form.get('temperature', 0.4))
    context_size = int(request.form.get('context_size', 4096))
    
    if not prompt:
        return jsonify({'error': 'No prompt provided'}), 400
    
    if file:
        filename = secure_filename(file.filename)
        file_path = os.path.join(UPLOAD_FOLDER, filename)
        file.save(file_path)
        
        try:
            # First process the file to get its content
            content = extract_content(file_path)
            if not content:
                return jsonify({'error': 'Could not extract content from file'}), 400
            
            # Get word count for logging
            word_count = len(re.findall(r'\w+', content))
            
            # Prepare message content
            content_text = f"{prompt}\n\nDocument content ({word_count} words):\n{content}"
            content_text += f"\n\nFile path: {filename}"
            
            # Create messages array with system message if provided
            messages = []
            if system_msg:
                messages.append({
                    'role': 'system',
                    'content': system_msg
                })
            
            messages.append({
                'role': 'user',
                'content': content_text
            })
            
            if not selected_model:
                return jsonify({'error': 'No model selected'}), 400
                
            response = ollama.chat(
                model=selected_model,
                messages=messages,
                options={
                    "temperature": temperature,
                    "num_ctx": context_size
                }
            )
            return jsonify({'response': response['message']['content']})
        finally:
            # Clean up uploaded file
            if os.path.exists(file_path):
                os.remove(file_path)
    
    return jsonify({'error': 'Invalid file'}), 400

@app.route('/rag/ingest', methods=['POST'])
def ingest_rag_files():
    if 'files' not in request.files:
        return jsonify({'error': 'No files provided'}), 400
    
    files = request.files.getlist('files')
    file_paths = []
    
    try:
        for file in files:
            if stop_event.is_set():
                break  # Exit loop if stop is signaled
            if file:
                filename = secure_filename(file.filename)
                file_path = os.path.join(UPLOAD_FOLDER, filename)
                file.save(file_path)
                file_paths.append(file_path)
        
        if not rag:
            return jsonify({'error': 'RAG not initialized'}), 500
            
        # Process files with MarkItDown first
        processed_contents = []
        for path in file_paths:
            content = extract_content(path)
            if content:
                processed_contents.append(content)
            else:
                return jsonify({'error': f'Could not extract content from file: {os.path.basename(path)}'}), 400
        
        rag.clear_db()  # Clear existing RAG data
        rag.ingest_data(processed_contents)
        return jsonify({'message': 'Files ingested successfully'})
    finally:
        # Clean up uploaded files
        for path in file_paths:
            if os.path.exists(path):
                os.remove(path)

@app.route('/chat', methods=['POST'])
def chat():
    global selected_model, selected_embedding_model, chunk_size, use_semantic_chunking, rag
    data = request.get_json()
    message = data.get('message')
    developer = data.get('developer', 'ollama')
    system_msg = data.get('system_msg', '')
    include_chat = data.get('include_chat', False)
    include_file = data.get('include_file', False)
    temperature = data.get('temperature', 0.4)
    context_size = data.get('context_size', 4096)
    rag_files = data.get('rag_files', [])
    file_data = data.get('file')
    
    if not selected_model:
        return jsonify({'error': 'No model selected'}), 400
    
    if not message:
        return jsonify({'error': 'No message provided'}), 400
    
    # Initialize messages array with system message if provided
    messages = []
    if system_msg and system_msg.strip():  # Only add if not empty
        messages.append({
            'role': 'system',
            'content': system_msg.strip()
        })
    
    content = message
    
    # Handle file content if present and included
    if file_data:
        if include_file:
            if file_data['type'] == 'image':
                # For images, add to the message's images field
                try:
                    image_bytes = base64.b64decode(file_data['content'])
                    messages.append({
                        'role': 'user',
                        'content': content,
                        'images': [image_bytes]
                    })
                    return handle_chat(messages, developer, temperature, context_size)
                except Exception as e:
                    return jsonify({'error': f'Error processing image: {str(e)}'}), 500
            else:
                # For documents, add content to the message only if include_file is true
                content += f"\n\nDocument content:\n{file_data['content']}"
                content += f"\n\nFile path: {file_data['name']}"
    
    if include_chat and data.get('chat_history'):
        chat_history = data.get('chat_history')
        # Exclude file content from chat history if not including it
        if not include_file and file_data:
            chat_history = chat_history.replace(file_data['content'], '')
        content += f"\n\nChat history:\n{chat_history}"
    
    # Handle RAG files if they exist
    if data.get('rag_files') and rag:
        try:
            rag_context = rag.retrieve_context(query=message)
            if rag_context:
                content += f"\n\nRAG Context:\n{rag_context}"
        except Exception as e:
            return jsonify({'error': f'Error retrieving RAG context: {str(e)}'}), 500
    
    messages.append({
        'role': 'user',
        'content': content
    })
    
    return handle_chat(messages, developer, temperature, context_size)

def handle_chat(messages, developer, temperature, context_size):
    """Handle the chat response for both Ollama and Google"""
    def generate():
        try:
            if developer == 'ollama':
                # Validate and clamp temperature and context size
                temp = round(max(0.0, min(2.0, float(temperature))), 2) 
                ctx = max(1000, min(128000, int(context_size)))  # Clamp between 1000 and 128000
                
                stream = ollama.chat(
                    model=selected_model,
                    messages=messages,
                    stream=True,
                    options={
                        "temperature": temp,
                        "num_ctx": ctx
                    }
                )
                
                for chunk in stream:
                    if stop_event.is_set():
                        break
                    if chunk and 'message' in chunk and 'content' in chunk['message']:
                        yield f"data: {chunk['message']['content']}\n\n"
            else: # google
                # Validate and clamp temperature and context size for Gemini
                temp = round(max(0.0, min(2.0, float(temperature))), 2) 
                ctx = max(1000, min(128000, int(context_size)))  # Clamp between 1000 and 128000
                
                stream = gemini_chat.get_response(
                    messages=messages,
                    temperature=temp,
                    max_tokens=ctx
                )
                
                for chunk in stream:
                    if stop_event.is_set():
                        break
                    if chunk and 'message' in chunk and 'content' in chunk['message']:
                        yield f"data: {chunk['message']['content']}\n\n"
        except Exception as e:
            yield f"data: Error: {str(e)}\n\n"
    
    return app.response_class(
        generate(),
        mimetype='text/event-stream',
        headers={'Cache-Control': 'no-cache', 'X-Accel-Buffering': 'no'}
    )

@app.route('/models', methods=['GET'])
def list_models():
    global selected_model, selected_embedding_model, developer, rag
    developer = request.args.get('developer', 'ollama')
    try:
        if developer == 'ollama':
            models = ollama.list()
            all_model_names = [model.model for model in models.models]
            llm_models = [name for name in all_model_names if 'embed' not in name]
            embedding_models = [name for name in all_model_names if 'embed' in name]
            if llm_models:
                selected_model = llm_models[0]
            if embedding_models:
                selected_embedding_model = embedding_models[0]
                if not rag:
                    rag = RAG(embedding_model_name=selected_embedding_model, chunk_size=chunk_size, use_semantic_chunking=use_semantic_chunking)
            return jsonify({'llm_models': llm_models, 'embedding_models': embedding_models})
        else: # google
            gemini_models = gemini_chat.list_models()
            if gemini_models:
                selected_model = gemini_models[0]
                selected_embedding_model = 'models/text-embedding-004'
                if not rag:
                    rag = RAG(embedding_model_name='models/text-embedding-004', chunk_size=chunk_size, use_semantic_chunking=use_semantic_chunking)
            return jsonify({'llm_models': gemini_models, 'embedding_models': ['models/text-embedding-004']})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/set_model', methods=['POST'])
def set_model():
    global selected_model, selected_embedding_model, chunk_size, use_semantic_chunking, rag
    data = request.get_json()
    selected_model = data.get('model')
    selected_embedding_model = data.get('embedding_model')
    chunk_size = data.get('chunk_size', 128)
    use_semantic_chunking = data.get('semantic_chunking', False)
    
    if selected_embedding_model:
        if not rag:
            rag = RAG(embedding_model_name = selected_embedding_model, chunk_size = chunk_size, use_semantic_chunking = use_semantic_chunking)
        elif rag.embedding_model_name != selected_embedding_model:
            # Only update if embedding model actually changed
            rag.update_embedding_function(selected_embedding_model)
            rag.chunk_size = chunk_size
            rag.use_semantic_chunking = use_semantic_chunking
        else:
            # Just update chunk size and semantic chunking if only those changed
            rag.chunk_size = chunk_size
            rag.use_semantic_chunking = use_semantic_chunking
    
    return jsonify({'message': 'Model set successfully'})

@app.route('/stop', methods=['POST'])
def stop_processing():
    global stop_event
    stop_event.set()
    # Reset stop_event immediately after setting it
    stop_event.clear()
    return jsonify({'message': 'Stopped ongoing processes'})

if __name__ == '__main__':
    app.run(debug=True, port=5001)
