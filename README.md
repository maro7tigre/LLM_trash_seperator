# LLM_trash_seperator
 
## Setup Instructions

1. Create and activate virtual environment:
```bash
python -m venv .venv

# On Windows
.venv\Scripts\activate

# On macOS/Linux 
source .venv/bin/activate
```

2. Install required packages:
```bash
pip install pillow
pip install opencv-python
pip install google-generativeai # For Google's AI
pip install openai               # For OpenAI API
pip install groq                 # For Groq API
```

3. create `credentials.py` file in the root directory and add the following content:
```python
"""
API Key Management for Trash Analyzer
This file should be added to .gitignore to prevent API keys from being committed
"""

# API keys for different providers
GEMINI_API_KEY = "YOUR_GEMINI_API_KEY"
OPENAI_API_KEY = "YOUR_OPENAI_API_KEY"
GROQ_API_KEY = "YOUR_GROQ_API_KEY"

def get_api_key(provider=None):
    """
    Get API key for a specific provider
    
    Args:
        provider: Provider name ('gemini', 'openai', 'groq') or None
                 If None, returns the Gemini API key for backward compatibility
    
    Returns:
        API key as string
    """
    # Default to gemini for backward compatibility
    if provider is None or provider.lower() == 'gemini':
        return GEMINI_API_KEY
    elif provider.lower() == 'openai':
        return OPENAI_API_KEY
    elif provider.lower() == 'groq':
        return GROQ_API_KEY
    else:
        return None
```
4. replace the API keys with your own API keys. 
- Gemini API key: https://console.cloud.google.com/apis/
- OpenAI API key: https://platform.openai.com/settings/organization/api-keys
- Groq API key: https://console.groq.com/keys

5. unzip the `complete_dataset.rar` for example datasets with get rundom images option
6. Run the program:
```bash
python main.py
```

## Project Structure
- `main.py`: Entry point for the application
- `app.py`: Main application class
- `ui_helper.py`: UI helper functions
- `model_helper.py`: Model handling functions
- `image_utils.py`: Image processing utilities
- `credentials.py`: API key management (gitignored)

## Aknowledgements
`complete_dataset.rar` is provided by [trashNet](https://github.com/garythung/trashnet.git) under MIT License.