#!/usr/bin/env python3
"""
Command-line interface for the Gemini AI Chatbot.
This script provides a simple terminal-based interface for interacting with Google's Gemini AI models,
including the latest Gemini 2.0 Flash model. Now with voice input and output capabilities!
"""

import os
import json
import time
import datetime
import sys
import signal
import threading
import google.generativeai as genai
from dotenv import load_dotenv
from colorama import Fore, Back, Style, init

# Voice recognition and text-to-speech imports
import speech_recognition as sr
import pyttsx3

# Initialize colorama for cross-platform colored terminal text
init(autoreset=True)

# Load environment variables
load_dotenv()

# Configure API key with better error handling
api_key = os.getenv("GOOGLE_API_KEY")
if not api_key:
    print(f"{Fore.RED}Error:{Style.RESET_ALL} No API key found. Please set GOOGLE_API_KEY in .env file")
    print(f"Get your API key from {Fore.BLUE}https://makersuite.google.com/{Style.RESET_ALL}")
    sys.exit(1)

# Create conversations directory if it doesn't exist
os.makedirs("conversations", exist_ok=True)

# Configure the API
try:
    genai.configure(api_key=api_key)
except Exception as e:
    print(f"{Fore.RED}Error configuring API:{Style.RESET_ALL} {str(e)}")
    sys.exit(1)

def get_model_response(conversation, user_input, stream=True):
    """
    Get response from the Gemini model
    
    Args:
        conversation: The ongoing conversation object
        user_input: The user's input text
        stream: Whether to stream the response or not
        
    Returns:
        Tuple of (response_text, error_message)
    """
    try:
        # Show a simple spinner
        chars = "|/-\\"
        for _ in range(3):  # Reduced spinner time for faster response
            for char in chars:
                sys.stdout.write(f"\r{Fore.BLUE}Thinking {char}{Style.RESET_ALL}")
                sys.stdout.flush()
                time.sleep(0.1)
        
        # Clear the spinner line
        sys.stdout.write("\r" + " " * 20 + "\r")
        sys.stdout.flush()
        
        if stream:
            # Stream the response
            response_stream = conversation.send_message(user_input, stream=True)
            full_response = ""
            
            # Print the header for the response first
            print(f"\n{Fore.CYAN}Gemini:{Style.RESET_ALL} ", end="")
            
            # Stream the response chunks
            for chunk in response_stream:
                if chunk.text:
                    print(chunk.text, end="", flush=True)
                    full_response += chunk.text
            
            # Add a newline at the end
            print()
            
            return full_response, None
        else:
            # Non-streaming response for compatibility
            response = conversation.send_message(user_input)
            return response.text, None
    except Exception as e:
        # Clear the spinner line if needed
        sys.stdout.write("\r" + " " * 20 + "\r")
        sys.stdout.flush()
        
        error_msg = str(e)
        if "API_KEY_INVALID" in error_msg:
            return None, "Your API key appears to be invalid. Please check your .env file and update it with a valid key from https://makersuite.google.com/"
        elif "PERMISSION_DENIED" in error_msg:
            return None, "Permission denied. Your API key may not have access to this model or your quota might be exceeded."
        elif "RESOURCE_EXHAUSTED" in error_msg:
            return None, "Resource exhausted. You've exceeded your quota or rate limit."
        else:
            return None, f"Error: {error_msg}"

def save_conversation(conversation, filename=None):
    """
    Save the current conversation to a JSON file
    
    Args:
        conversation: The conversation object
        filename: Optional custom filename
    """
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = filename or f"conversations/gemini_chat_{timestamp}.json"
    
    try:
        # Extract conversation history
        history = []
        for message in conversation.history:
            history.append({
                'role': message.role,
                'parts': [part for part in message.parts],
                'timestamp': timestamp
            })
        
        # Save to file
        with open(filename, 'w') as f:
            json.dump(history, f, indent=2)
        
        return filename
    except Exception as e:
        return f"Error saving conversation: {str(e)}"

def get_voice_status_icon(enabled):
    """
    Get a colorful status icon for voice features
    
    Args:
        enabled: Whether the feature is enabled
        
    Returns:
        Colored icon string
    """
    if enabled:
        return f"{Fore.GREEN}✓ ON {Style.RESET_ALL}"
    else:
        return f"{Fore.RED}✗ OFF{Style.RESET_ALL}"

def handle_command(cmd, conversation, model_name, voice_input=False, voice_output=False):
    """
    Handle special commands
    
    Args:
        cmd: The command string (without the leading '/')
        conversation: The current conversation object
        model_name: Current model name
        voice_input: Whether voice input is enabled
        voice_output: Whether voice output is enabled
        
    Returns:
        Tuple of (should_continue, response_message, new_model, voice_settings)
    """
    cmd_parts = cmd.split()
    base_cmd = cmd_parts[0].lower()
    new_model = None
    
    if base_cmd == "exit" or base_cmd == "quit":
        return False, "Goodbye!", None
    
    elif base_cmd == "help":
        help_text = """
Available Commands:
/exit or /quit - Exit the chatbot
/help - Show this help message
/clear - Clear the current conversation
/save [filename] - Save conversation to a file
/model [model_name] - Change the model
  Available models: gemini-2.0-flash, gemini-pro, gemini-1.5-flash
/info - Show current model and settings
/voice_input - Toggle voice input on/off
/voice_output - Toggle voice output on/off
/voice - Toggle both voice input and output on/off
        """
        return True, help_text, None
    
    elif base_cmd == "clear":
        return True, "Conversation cleared. Starting fresh.", None
    
    elif base_cmd == "save":
        custom_filename = None
        if len(cmd_parts) > 1:
            custom_filename = f"conversations/{cmd_parts[1]}.json"
        
        filename = save_conversation(conversation, custom_filename)
        return True, f"Conversation saved to {filename}", None
    
    elif base_cmd == "model":
        if len(cmd_parts) > 1:
            new_model_name = cmd_parts[1]
            valid_models = ["gemini-2.0-flash", "gemini-pro", "gemini-1.5-flash"]
            
            if new_model_name in valid_models:
                return True, f"Changing model to {new_model_name}...", new_model_name
            else:
                return True, f"Invalid model: {new_model_name}\nAvailable models: {', '.join(valid_models)}", None
        else:
            return True, f"Current model: {model_name}\nAvailable models: gemini-2.0-flash, gemini-pro, gemini-1.5-flash", None
    
    elif base_cmd == "info":
        return True, f"Current model: {model_name}\nAPI key: {api_key[:4]}...{api_key[-4:] if len(api_key) > 8 else ''}\nConversation length: {len(conversation.history)} messages\nVoice input: {'enabled' if voice_input else 'disabled'}\nVoice output: {'enabled' if voice_output else 'disabled'}", None
    
    elif base_cmd == "voice_input":
        new_status = not voice_input
        status_msg = f"{Fore.MAGENTA}🎤 Voice input: {get_voice_status_icon(new_status)}{Style.RESET_ALL}"
        if new_status:
            status_msg += f"\n{Fore.CYAN}Speak to me! I'm listening...{Style.RESET_ALL}"
        return True, status_msg, None, {'toggle_voice_input': True}
    
    elif base_cmd == "voice_output":
        new_status = not voice_output
        status_msg = f"{Fore.MAGENTA}🔊 Voice output: {get_voice_status_icon(new_status)}{Style.RESET_ALL}"
        if new_status:
            status_msg += f"\n{Fore.CYAN}I'll read my responses aloud!{Style.RESET_ALL}"
        return True, status_msg, None, {'toggle_voice_output': True}
    
    elif base_cmd == "voice":
        new_status = not (voice_input or voice_output)
        voice_status = get_voice_status_icon(new_status)
        status_msg = f"{Fore.MAGENTA}🎙️ Voice mode: {voice_status}{Style.RESET_ALL}"
        if new_status:
            status_msg += f"\n{Fore.CYAN}Voice conversation activated! Speak to me and I'll respond verbally.{Style.RESET_ALL}"
        return True, status_msg, None, {'toggle_both': True}
    
    else:
        return True, f"Unknown command: {base_cmd}. Type /help for available commands.", None, None

def setup_voice_engine():
    """
    Set up the text-to-speech engine
    
    Returns:
        The initialized pyttsx3 engine
    """
    engine = pyttsx3.init()
    
    # Get available voices and set to a more natural sounding voice if available
    voices = engine.getProperty('voices')
    for voice in voices:
        # Try to find a natural sounding voice
        if "natural" in voice.name.lower() or "samantha" in voice.name.lower():
            engine.setProperty('voice', voice.id)
            break
    
    # Set properties (can be adjusted for better experience)
    engine.setProperty('rate', 180)    # Speed of speech
    engine.setProperty('volume', 0.9)  # Volume (0.0 to 1.0)
    
    return engine

def listen_for_voice():
    """
    Listen for voice input using microphone with visual feedback
    
    Returns:
        The recognized text or None if recognition failed
    """
    recognizer = sr.Recognizer()
    
    try:
        with sr.Microphone() as source:
            # Visual listening indicator with animation
            print(f"{Fore.CYAN}┌─ Listening ───────────────┐{Style.RESET_ALL}")
            print(f"{Fore.CYAN}│{Style.RESET_ALL} 🎤 {Fore.GREEN}Speak now...{Style.RESET_ALL}        {Fore.CYAN}│{Style.RESET_ALL}")
            
            # Show a simple listening animation
            animation = ['⚫', '⚪']
            for _ in range(3):
                for frame in animation:
                    print(f"{Fore.CYAN}│{Style.RESET_ALL} {frame} Adjusting microphone...{' ' * 5}{Fore.CYAN}│{Style.RESET_ALL}", end='\r')
                    sys.stdout.flush()
                    time.sleep(0.1)
            
            # Adjust for ambient noise and set timeout
            recognizer.adjust_for_ambient_noise(source, duration=0.5)
            
            # Show ready indicator
            print(f"{Fore.CYAN}│{Style.RESET_ALL} ✅ {Fore.GREEN}Ready!{Style.RESET_ALL} Listening...      {Fore.CYAN}│{Style.RESET_ALL}")
            print(f"{Fore.CYAN}└───────────────────────────┘{Style.RESET_ALL}")
            
            # Listen with a simple animated indicator
            print("")
            listening_chars = '▁▂▃▄▅▆▇█▇▆▅▄▃▂▁'
            stop_animation = False
            
            def animate_listening():
                i = 0
                while not stop_animation:
                    char = listening_chars[i % len(listening_chars)]
                    print(f"\r{Fore.GREEN}▶ {char * 5}{Style.RESET_ALL}    ", end='')
                    sys.stdout.flush()
                    time.sleep(0.1)
                    i += 1
            
            # Start animation in a thread
            animation_thread = threading.Thread(target=animate_listening)
            animation_thread.daemon = True
            animation_thread.start()
            
            # Actual listening
            audio = recognizer.listen(source, timeout=10, phrase_time_limit=10)
            
            # Stop animation
            stop_animation = True
            animation_thread.join(0.5)
            print("\r" + " " * 30 + "\r", end='')
            
            print(f"{Fore.BLUE}🔍 Recognizing your speech...{Style.RESET_ALL}")
            text = recognizer.recognize_google(audio)
            print(f"{Fore.GREEN}✓ Recognized!{Style.RESET_ALL}")
            return text
            
    except sr.WaitTimeoutError:
        print(f"\n{Fore.RED}⏱️ Timeout: No speech detected{Style.RESET_ALL}")
    except sr.UnknownValueError:
        print(f"\n{Fore.RED}❓ Could not understand audio{Style.RESET_ALL}")
    except sr.RequestError as e:
        print(f"\n{Fore.RED}🌐 Network error: {e}{Style.RESET_ALL}")
    except Exception as e:
        print(f"\n{Fore.RED}❌ Error: {e}{Style.RESET_ALL}")
    
    return None

def speak_text(engine, text):
    """
    Speak the given text using text-to-speech with natural sentence breaks
    
    Args:
        engine: The pyttsx3 engine
        text: The text to speak
    """
    # Clean up text for better speech synthesis
    text = text.replace('*', '')
    text = text.replace('```', '')
    text = text.replace('`', '')
    text = text.replace('#', 'heading')
    text = text.replace('\n\n', '. ')
    text = text.replace('\n', '. ')
    
    # Replace common technical symbols with spoken equivalents
    replacements = {
        '/': ' slash ',
        '=': ' equals ',
        '>': ' greater than ',
        '<': ' less than ',
        '+': ' plus ',
        '-': ' minus ',
        ':': ', ',
        '|': ' pipe ',
        ';': ', ',
        '&': ' and ',
        '%': ' percent ',
        '$': ' dollar ',
        '@': ' at ',
        '!': ', ',
        '?': '? ',
        '(': ', ',
        ')': ', ',
        '[': ', ',
        ']': ', ',
        '{': ', ',
        '}': ', ',
    }
    
    for symbol, replacement in replacements.items():
        text = text.replace(symbol, replacement)
    
    # Smart sentence splitting - uses multiple delimiters and respects abbreviations
    import re
    
    # Common abbreviations to avoid incorrect breaks
    common_abbr = ['Mr.', 'Mrs.', 'Dr.', 'Prof.', 'St.', 'e.g.', 'i.e.', 'vs.', 'etc.', 'Fig.']
    
    # Temporarily replace abbreviations
    for abbr in common_abbr:
        text = text.replace(abbr, abbr.replace('.', '[DOT]'))
    
    # Split by sentence-ending punctuation with following space or end of text
    sentences = re.split(r'(?<=[.!?])(?:\s|$)', text)
    
    # Restore abbreviations
    for i in range(len(sentences)):
        for abbr in common_abbr:
            sentences[i] = sentences[i].replace(abbr.replace('.', '[DOT]'), abbr)
    
    # Further break long sentences by commas for more natural pauses
    speech_chunks = []
    for sentence in sentences:
        if sentence.strip():
            # If sentence is very long, break it at commas
            if len(sentence) > 100:
                comma_parts = sentence.split(',')
                for part in comma_parts:
                    if part.strip():
                        speech_chunks.append(part.strip())
            else:
                speech_chunks.append(sentence.strip())
    
    # Speak each chunk with natural pauses
    for chunk in speech_chunks:
        if chunk:
            # Normalize whitespace
            chunk = re.sub(r'\s+', ' ', chunk)
            
            # Skip if it's just punctuation or very short
            if len(chunk) <= 1 or all(c in '.!?,;:' for c in chunk):
                continue
                
            # Add period at end if missing to improve intonation
            if chunk[-1] not in '.!?':
                chunk += '.'
                
            engine.say(chunk)
            engine.runAndWait()
            
            # Pause length based on punctuation at end of chunk
            if chunk[-1] == '.':
                time.sleep(0.3)  # Normal pause after period
            elif chunk[-1] == '?':
                time.sleep(0.4)  # Slightly longer for questions
            elif chunk[-1] == '!':
                time.sleep(0.3)  # Normal pause for exclamations
            elif chunk[-1] == ',':
                time.sleep(0.2)  # Short pause for commas
            else:
                time.sleep(0.1)  # Minimal pause

def run_chat():
    """
    Run the chat interface in the command line
    """
    # Set up signal handler for clean exit with Ctrl+C
    def signal_handler(sig, frame):
        print(f"\n{Fore.YELLOW}Exiting chatbot.{Style.RESET_ALL} Goodbye!")
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    
    # Initialize text-to-speech engine
    voice_engine = setup_voice_engine()
    
    # Initialize voice mode flags
    voice_input_enabled = False
    voice_output_enabled = False
    
    # ASCII art title and icons
    print(f"""
{Fore.BLUE}╔════════════════════════════════════════════════════════╗
║  {Fore.CYAN}  ___              _       _    {Fore.BLUE} _____  _           _    {Fore.BLUE}║
║  {Fore.CYAN} / _ \  ___  _ __ (_)_ __ (_)  {Fore.BLUE}/ __\ \| |__   __ _| |_  {Fore.BLUE}║
║  {Fore.CYAN}| | | |/ _ \| '_ \| | '_ \| | {Fore.BLUE}/ /  | | '_ \ / _` | __| {Fore.BLUE}║
║  {Fore.CYAN}| |_| |  __/| | | | | | | | |{Fore.BLUE}/ /___| | |_) | (_| | |_  {Fore.BLUE}║
║  {Fore.CYAN} \___/ \___||_| |_|_|_| |_|_|{Fore.BLUE}\____/|_|_.__/ \__,_|\__| {Fore.BLUE}║{Style.RESET_ALL}
{Fore.BLUE}╚════════════════════════════════════════════════════════╝{Style.RESET_ALL}
""")
    
    # Show features and command guide with icons
    print(f"{Fore.BLUE}┌─ Commands ───────────────────────────────────────────┐{Style.RESET_ALL}")
    print(f"{Fore.BLUE}│{Style.RESET_ALL} {Fore.GREEN}📋 /help{Style.RESET_ALL}      - Show all available commands          {Fore.BLUE}│{Style.RESET_ALL}")
    print(f"{Fore.BLUE}│{Style.RESET_ALL} {Fore.RED}🚪 /exit{Style.RESET_ALL}      - Exit the chatbot                    {Fore.BLUE}│{Style.RESET_ALL}")
    print(f"{Fore.BLUE}│{Style.RESET_ALL} {Fore.CYAN}🤖 /model{Style.RESET_ALL}     - Change AI model (gemini-2.0-flash)   {Fore.BLUE}│{Style.RESET_ALL}")
    print(f"{Fore.BLUE}└──────────────────────────────────────────────────────┘{Style.RESET_ALL}")
    
    # Voice feature guide with status indicators
    print(f"{Fore.BLUE}┌─ Voice Features {Fore.MAGENTA}🎤{Style.RESET_ALL} ─────────────────────────────────┐{Style.RESET_ALL}")
    print(f"{Fore.BLUE}│{Style.RESET_ALL} {Fore.MAGENTA}🎤 /voice_input{Style.RESET_ALL}  - {get_voice_status_icon(voice_input_enabled)} Speaking to chatbot    {Fore.BLUE}│{Style.RESET_ALL}")
    print(f"{Fore.BLUE}│{Style.RESET_ALL} {Fore.MAGENTA}🔊 /voice_output{Style.RESET_ALL} - {get_voice_status_icon(voice_output_enabled)} Hearing responses     {Fore.BLUE}│{Style.RESET_ALL}")
    print(f"{Fore.BLUE}│{Style.RESET_ALL} {Fore.MAGENTA}🎙️ /voice{Style.RESET_ALL}       - Toggle both voice features         {Fore.BLUE}│{Style.RESET_ALL}")
    print(f"{Fore.BLUE}└──────────────────────────────────────────────────────┘{Style.RESET_ALL}")
    
    print(f"Using the new {Fore.CYAN}gemini-2.0-flash{Style.RESET_ALL} model!")
    
    # Initialize model
    model_name = 'gemini-2.0-flash'
    try:
        model = genai.GenerativeModel(model_name)
    except Exception as e:
        print(f"{Fore.RED}Error initializing model:{Style.RESET_ALL} {str(e)}")
        print("Falling back to gemini-pro model...")
        model_name = 'gemini-pro'
        try:
            model = genai.GenerativeModel(model_name)
        except Exception as e:
            print(f"{Fore.RED}Error initializing fallback model:{Style.RESET_ALL} {str(e)}")
            sys.exit(1)
    
    # Set up system prompt to define personality
    system_prompt = """You are a helpful AI assistant with a friendly, casual tone.
    You excel at explaining technical concepts in simple terms.
    You can answer questions about programming, technology, science, and more.
    You're always respectful and aim to provide accurate information."""
    
    # Initialize conversation with personality
    try:
        conversation = model.start_chat(history=[
            {'role': 'user', 'parts': [system_prompt]},
            {'role': 'model', 'parts': ['I understand! I\'ll be a friendly, helpful assistant who explains technical concepts simply.']}
        ])
    except Exception as e:
        print(f"{Fore.RED}Error starting chat:{Style.RESET_ALL} {str(e)}")
        if "API_KEY_INVALID" in str(e):
            print("Your API key appears to be invalid. Please check your .env file and update it.")
        sys.exit(1)
    
    # Initialize voice mode flags
    voice_input_enabled = False
    voice_output_enabled = False
    
    while True:
        # Get user input - either through voice or keyboard
        if voice_input_enabled:
            # Show microphone icon to indicate listening mode
            print(f"\n{Fore.MAGENTA}🎤 {Fore.GREEN}You{Style.RESET_ALL} (speaking)")
            voice_text = listen_for_voice()
            if voice_text:
                user_input = voice_text
                # Display recognized text with icon
                print(f"{Fore.GREEN}You said:{Style.RESET_ALL} {user_input}")
            else:
                # Fallback to text input if voice recognition fails
                print(f"{Fore.YELLOW}Switching to keyboard input{Style.RESET_ALL}")
                user_input = input(f"{Fore.GREEN}You:{Style.RESET_ALL} ")
        else:
            user_input = input(f"\n{Fore.GREEN}You:{Style.RESET_ALL} ")
        
        # Handle empty input
        if not user_input.strip():
            continue
        
        # Check if it's a command
        if user_input.startswith("/"):
            cmd = user_input[1:].strip()
            should_continue, cmd_response, new_model, voice_settings = handle_command(
                cmd, conversation, model_name, voice_input_enabled, voice_output_enabled)
            
            # Handle voice settings changes
            if voice_settings:
                if voice_settings.get('toggle_voice_input'):
                    voice_input_enabled = not voice_input_enabled
                if voice_settings.get('toggle_voice_output'):
                    voice_output_enabled = not voice_output_enabled
                if voice_settings.get('toggle_both'):
                    voice_input_enabled = not voice_input_enabled
                    voice_output_enabled = voice_input_enabled
            
            if cmd_response == "Conversation cleared. Starting fresh.":
                # Reinitialize the conversation
                conversation = model.start_chat(history=[
                    {'role': 'user', 'parts': [system_prompt]},
                    {'role': 'model', 'parts': ['I understand! I\'ll be a friendly, helpful assistant who explains technical concepts simply.']}
                ])
            
            # If model change requested
            if new_model:
                try:
                    print(f"{Fore.YELLOW}Switching to {new_model}...{Style.RESET_ALL}")
                    model = genai.GenerativeModel(new_model)
                    conversation = model.start_chat(history=[
                        {'role': 'user', 'parts': [system_prompt]},
                        {'role': 'model', 'parts': ['I understand! I\'ll be a friendly, helpful assistant who explains technical concepts simply.']}
                    ])
                    model_name = new_model
                    cmd_response = f"Model changed to {new_model}"
                except Exception as e:
                    cmd_response = f"Error changing model: {str(e)}"
            
            # Display command response
            print(f"\n{Fore.YELLOW}System:{Style.RESET_ALL} {cmd_response}")
            
            # Speak the response if voice output is enabled
            if voice_output_enabled:
                # Don't speak long help text or certain system messages
                if len(cmd_response) < 100 and not cmd_response.startswith("Available Commands"):
                    speak_text(voice_engine, cmd_response)
            
            if not should_continue:
                break
            
            continue
        
        # Get and display response with streaming
        response, error = get_model_response(conversation, user_input, stream=True)
        
        if error:
            print(f"\n{Fore.RED}Error:{Style.RESET_ALL} {error}")
            if voice_output_enabled:
                speak_text(voice_engine, f"Error: {error}")
        # No else block needed as streaming response is already printed in the function
        
        # Speak the response if voice output is enabled and no error occurred
        if voice_output_enabled and not error and response:
            # Display speaking indicator
            print(f"{Fore.MAGENTA}🔊 Speaking response...{Style.RESET_ALL}")
            # Use a thread to not block the main program while speaking
            speaking_thread = threading.Thread(target=speak_text, args=(voice_engine, response))
            speaking_thread.daemon = True
            speaking_thread.start()

if __name__ == "__main__":
    run_chat()
