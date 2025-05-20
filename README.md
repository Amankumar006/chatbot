# Gemini AI Chatbot

A Python chatbot powered by Google's Gemini Pro model. This project includes both a command-line interface and a web interface using Streamlit.

## Features

- Natural language conversation using Google's Gemini Pro model
- Persistent conversation history
- Friendly, helpful persona
- Available as both CLI and web application
- Secure API key storage

## Setup

1. Clone this repository
2. Install the required packages:
   ```
   pip install -r requirements.txt
   ```
3. Create a `.env` file in the project root and add your Google API key:
   ```
   GOOGLE_API_KEY=your_api_key_here
   ```
   You can get an API key from [Google AI Studio](https://makersuite.google.com/)

## Usage

### Command-line Interface

Run the CLI version with:

```
python cli_chatbot.py
```

Type your messages and press Enter to get responses. Type 'exit' to end the conversation.

### Web Interface

Run the web interface with:

```
streamlit run web_chatbot.py
```

The web interface will open in your default browser, where you can interact with the chatbot.

## Customization

You can customize the chatbot's personality by modifying the system prompt in either `cli_chatbot.py` or `web_chatbot.py`.

## Error Handling

The chatbot includes basic error handling for API connection issues and rate limits. Check the console output for detailed error messages if you encounter problems.

## License

MIT
# chatbot
