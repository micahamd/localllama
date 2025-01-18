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

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

UPLOAD_FOLDER = 'uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
gemini_chat = GeminiChat()
rag = None
selected_model = None
selected_embedding_model = None
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

@app.route('/batch', methods=['POST'])
def batch_process():
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    prompt = request.form.get('prompt')
    
    if not prompt:
        return jsonify({'error': 'No prompt provided'}), 400
    
    if file:
        filename = secure_filename(file.filename)
        file_path = os.path.join(UPLOAD_FOLDER, filename)
        file.save(file_path)
        
        try:
            content = extract_content(file_path)
            if content:
                message = {
                    'role': 'user',
                    'content': f"{prompt}\n\nDocument content:\n{content}"
                }
                
                if selected_model:
                    response = ollama.chat(
                        model=selected_model,
                        messages=[message],
                        options={
                            "temperature": 0.7,
                            "num_ctx": 4096
                        }
                    )
                    return jsonify({'response': response['message']['content']})
                else:
                    return jsonify({'error': 'No model selected'}), 400
            else:
                return jsonify({'error': 'Could not extract content from file'}), 400
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
            if file:
                filename = secure_filename(file.filename)
                file_path = os.path.join(UPLOAD_FOLDER, filename)
                file.save(file_path)
                file_paths.append(file_path)
        
        if rag:
            rag.ingest_data(file_paths)
            return jsonify({'message': 'Files ingested successfully'})
        else:
            return jsonify({'error': 'RAG not initialized'}), 500
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
    file_content = data.get('file_content', '')
    file_path = data.get('file_path', '')
    temperature = data.get('temperature', 0.4)
    context_size = data.get('context_size', 4096)
    rag_files = data.get('rag_files', [])
    
    if not selected_model:
        return jsonify({'error': 'No model selected'}), 400
    
    if not message:
        return jsonify({'error': 'No message provided'}), 400
    
    messages = []
    if system_msg:
        messages.append({
            'role': 'system',
            'content': system_msg
        })
    
    content = message
    if include_file and file_content:
        content += f"\n\nDocument content:\n{file_content}"
        content += f"\n\nFile path: {file_path}"
    
    if include_chat:
        # TODO: Implement chat history
        pass
    
    if rag_files:
        if not rag:
            rag = RAG(embedding_model_name = selected_embedding_model, chunk_size = chunk_size, use_semantic_chunking = use_semantic_chunking)
        rag_context = rag.retrieve_context(query=message)
        content += f"\n\nRAG Context:\n{rag_context}"
    
    messages.append({
        'role': 'user',
        'content': content
    })
    
    try:
        if developer == 'ollama':
            stream = ollama.chat(
                model=selected_model,
                messages=messages,
                stream=True,
                options={
                    "temperature": temperature,
                    "num_ctx": context_size
                }
            )
            response = ""
            for chunk in stream:
                if stop_event.is_set():
                    break
                if chunk and 'message' in chunk and 'content' in chunk['message']:
                    response += chunk['message']['content']
            return jsonify({'response': response})
        else: # google
            stream = gemini_chat.get_response(
                messages=messages,
                temperature=temperature,
                max_tokens=context_size
            )
            response = ""
            for chunk in stream:
                if stop_event.is_set():
                    break
                if chunk and 'message' in chunk and 'content' in chunk['message']:
                    response += chunk['message']['content']
            return jsonify({'response': response})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/models', methods=['GET'])
def list_models():
    global selected_model, selected_embedding_model
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
            return jsonify({'llm_models': llm_models, 'embedding_models': embedding_models})
        else: # google
            gemini_models = gemini_chat.list_models()
            if gemini_models:
                selected_model = gemini_models[0]
            selected_embedding_model = 'models/text-embedding-004'
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
        else:
            rag.update_embedding_function(selected_embedding_model)
            rag.chunk_size = chunk_size
            rag.use_semantic_chunking = use_semantic_chunking
    
    return jsonify({'message': 'Model set successfully'})

@app.route('/stop', methods=['POST'])
def stop_processing():
    global stop_event
    stop_event.set()
    return jsonify({'message': 'Stopped ongoing processes'})

if __name__ == '__main__':
    app.run(debug=True, port=5001)
