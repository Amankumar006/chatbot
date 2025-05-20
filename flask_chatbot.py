#!/usr/bin/env python3
"""
Flask web interface for the Gemini AI Chatbot.
This script provides a Flask-based web interface with Socket.IO for real-time chatting
with Google's Gemini AI models including Gemini 2.0 Flash.
"""

import os
import json
import datetime
import google.generativeai as genai
from dotenv import load_dotenv
from flask import Flask, render_template, request, jsonify, session
from flask_socketio import SocketIO, emit

# Load environment variables
load_dotenv()

# Configure API key
api_key = os.getenv("GOOGLE_API_KEY")
if not api_key:
    print("Error: No API key found. Please set GOOGLE_API_KEY in .env file")
    print("Get your API key from https://makersuite.google.com/")
    exit(1)

# Configure the API
try:
    genai.configure(api_key=api_key)
except Exception as e:
    print(f"Error configuring API: {str(e)}")
    exit(1)

# Create conversations directory if it doesn't exist
os.makedirs("conversations", exist_ok=True)

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'gemini-chatbot-secret')
socketio = SocketIO(app, cors_allowed_origins="*")

# Available models
AVAILABLE_MODELS = [
    "gemini-2.0-flash",
    "gemini-pro",
    "gemini-1.5-flash"
]

# Conversation cache
conversations = {}

def save_conversation(conversation_id, conversation_data):
    """Save the current conversation to a JSON file"""
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"conversations/gemini_chat_{conversation_id}_{timestamp}.json"
    
    try:
        with open(filename, 'w') as f:
            json.dump(conversation_data, f, indent=2)
        return filename
    except Exception as e:
        return f"Error saving conversation: {str(e)}"

def get_streaming_response(model_name, conversation_id, user_input):
    """Get streaming response from the model"""
    # Initialize model if not already done
    if conversation_id not in conversations:
        try:
            model = genai.GenerativeModel(model_name)
            
            # Set up system prompt to define personality
            system_prompt = """You are a helpful AI assistant with a friendly, casual tone.
            You excel at explaining technical concepts in simple terms.
            You can answer questions about programming, technology, science, and more.
            You're always respectful and aim to provide accurate information."""
            
            # Initialize conversation with personality
            chat = model.start_chat(history=[
                {'role': 'user', 'parts': [system_prompt]},
                {'role': 'model', 'parts': ['I understand! I\'ll be a friendly, helpful assistant who explains technical concepts simply.']}
            ])
            
            conversations[conversation_id] = {
                'model': model,
                'chat': chat,
                'model_name': model_name,
                'history': []
            }
        except Exception as e:
            emit('error', {'error': str(e)})
            return
    
    # Get the conversation
    conversation = conversations[conversation_id]
    chat = conversation['chat']
    
    # Add user message to history
    conversation['history'].append({
        'role': 'user',
        'content': user_input,
        'timestamp': datetime.datetime.now().isoformat()
    })
    
    try:
        # Stream the response
        stream_response = chat.send_message(user_input, stream=True)
        
        full_response = ""
        for chunk in stream_response:
            if chunk.text:
                full_response += chunk.text
                # Emit each chunk to the client
                socketio.emit('message_chunk', {
                    'chunk': chunk.text,
                    'conversation_id': conversation_id
                })
                # Small delay for smooth streaming effect
                socketio.sleep(0.01)
        
        # Add assistant response to history
        conversation['history'].append({
            'role': 'assistant',
            'content': full_response,
            'timestamp': datetime.datetime.now().isoformat()
        })
        
        # Emit end of response
        socketio.emit('message_complete', {
            'conversation_id': conversation_id,
            'full_response': full_response
        })
        
    except Exception as e:
        error_msg = str(e)
        socketio.emit('error', {
            'error': error_msg,
            'conversation_id': conversation_id
        })

@app.route('/')
def index():
    """Render the main page"""
    # Generate a unique conversation ID if not in session
    if 'conversation_id' not in session:
        session['conversation_id'] = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    
    return render_template('index.html', 
                          models=AVAILABLE_MODELS, 
                          default_model='gemini-2.0-flash',
                          conversation_id=session['conversation_id'])

@app.route('/api/models')
def get_models():
    """Return the list of available models"""
    return jsonify(AVAILABLE_MODELS)

@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    print('Client connected')

@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection"""
    print('Client disconnected')

@socketio.on('send_message')
def handle_message(data):
    """Handle incoming messages from the client"""
    user_input = data.get('message', '')
    conversation_id = data.get('conversation_id', '')
    model_name = data.get('model', 'gemini-2.0-flash')
    
    if not user_input or not conversation_id:
        emit('error', {'error': 'Invalid message or conversation ID'})
        return
    
    # Process message in a background thread to not block
    socketio.start_background_task(
        get_streaming_response, model_name, conversation_id, user_input
    )

@socketio.on('change_model')
def handle_model_change(data):
    """Handle model change requests"""
    model_name = data.get('model', '')
    conversation_id = data.get('conversation_id', '')
    
    if not model_name or not conversation_id:
        emit('error', {'error': 'Invalid model or conversation ID'})
        return
    
    if model_name not in AVAILABLE_MODELS:
        emit('error', {'error': f'Invalid model: {model_name}'})
        return
    
    # Clear existing conversation
    if conversation_id in conversations:
        del conversations[conversation_id]
    
    try:
        # Initialize new model
        model = genai.GenerativeModel(model_name)
        
        # Set up system prompt to define personality
        system_prompt = """You are a helpful AI assistant with a friendly, casual tone.
        You excel at explaining technical concepts in simple terms.
        You can answer questions about programming, technology, science, and more.
        You're always respectful and aim to provide accurate information."""
        
        # Initialize conversation with personality
        chat = model.start_chat(history=[
            {'role': 'user', 'parts': [system_prompt]},
            {'role': 'model', 'parts': ['I understand! I\'ll be a friendly, helpful assistant who explains technical concepts simply.']}
        ])
        
        conversations[conversation_id] = {
            'model': model,
            'chat': chat,
            'model_name': model_name,
            'history': []
        }
        
        emit('model_changed', {
            'model': model_name,
            'conversation_id': conversation_id,
            'message': f'Model changed to {model_name}'
        })
    
    except Exception as e:
        emit('error', {'error': f'Error changing model: {str(e)}'})

@socketio.on('clear_conversation')
def handle_clear_conversation(data):
    """Handle clearing the conversation"""
    conversation_id = data.get('conversation_id', '')
    model_name = data.get('model', 'gemini-2.0-flash')
    
    if not conversation_id:
        emit('error', {'error': 'Invalid conversation ID'})
        return
    
    # Reinitialize the conversation with the same model
    if conversation_id in conversations:
        model_name = conversations[conversation_id]['model_name']
        del conversations[conversation_id]
    
    try:
        # Initialize model
        model = genai.GenerativeModel(model_name)
        
        # Set up system prompt to define personality
        system_prompt = """You are a helpful AI assistant with a friendly, casual tone.
        You excel at explaining technical concepts in simple terms.
        You can answer questions about programming, technology, science, and more.
        You're always respectful and aim to provide accurate information."""
        
        # Initialize conversation with personality
        chat = model.start_chat(history=[
            {'role': 'user', 'parts': [system_prompt]},
            {'role': 'model', 'parts': ['I understand! I\'ll be a friendly, helpful assistant who explains technical concepts simply.']}
        ])
        
        conversations[conversation_id] = {
            'model': model,
            'chat': chat,
            'model_name': model_name,
            'history': []
        }
        
        emit('conversation_cleared', {
            'conversation_id': conversation_id,
            'message': 'Conversation cleared'
        })
    
    except Exception as e:
        emit('error', {'error': f'Error clearing conversation: {str(e)}'})

@socketio.on('save_conversation')
def handle_save_conversation(data):
    """Handle saving the conversation"""
    conversation_id = data.get('conversation_id', '')
    filename = data.get('filename', '')
    
    if not conversation_id:
        emit('error', {'error': 'Invalid conversation ID'})
        return
    
    if conversation_id not in conversations:
        emit('error', {'error': 'Conversation not found'})
        return
    
    conversation_data = conversations[conversation_id]['history']
    
    if filename:
        saved_filename = f"conversations/{filename}.json"
    else:
        saved_filename = save_conversation(conversation_id, conversation_data)
    
    emit('conversation_saved', {
        'conversation_id': conversation_id,
        'filename': saved_filename,
        'message': f'Conversation saved to {saved_filename}'
    })

if __name__ == '__main__':
    # Create template directory if it doesn't exist
    os.makedirs('templates', exist_ok=True)
    
    # Check if template exists before starting the server
    template_path = os.path.join('templates', 'index.html')
    if not os.path.exists(template_path):
        print(f"Template not found at {template_path}.")
        print("Please create the template first.")
        exit(1)
    
    print("Starting Flask server at http://127.0.0.1:5000")
    socketio.run(app, debug=True, allow_unsafe_werkzeug=True)
