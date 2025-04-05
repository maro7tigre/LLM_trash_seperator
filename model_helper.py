"""
LLM model helper functions for Trash Analyzer
Contains functions for Gemini, OpenAI multimodal models, and local LM Studio models
"""

import os
import requests
from image_utils import prepare_image_for_api
from credentials import get_api_key

# MARK: - Available Models by Provider
AVAILABLE_MODELS = {
    'Gemini': [
        "gemini-2.0-flash",
        "gemini-2.0-flash-lite",
        "gemini-1.5-flash",
    ],
    'OpenAI': [
        "gpt-4o",
        "gpt-4o-mini",
    ],
    'Local': [
        "gemma-3-4b-it",
        # Uncomment the following if you later run additional local models:
        # "gemma-3-12b",
        # "gemma-3-27b"
    ]
}

# MARK: - Provider Availability
def get_available_providers():
    """Check which providers have API keys configured or are available locally"""
    available = []
    
    # Check Gemini
    if get_api_key('gemini'):
        available.append('Gemini')
    
    # Check OpenAI
    if get_api_key('openai'):
        available.append('OpenAI')
    
    # Local provider is assumed to be available if LM Studio local server is running
    available.append('Local')
    
    return available

def get_models_for_provider(provider):
    """Get available models for a provider"""
    if provider in AVAILABLE_MODELS:
        return AVAILABLE_MODELS[provider]
    return []

# MARK: - Analysis Functions
def analyze_with_gemini(prompt, image_data, model_name, temperature=0.7, max_tokens=100):
    """Analyze an image using Google's Gemini API"""
    try:
        import google.generativeai as genai
        
        # Get API key - use the default method if no specific provider is given
        api_key = get_api_key()
        if not api_key:
            return "ERROR: Gemini API key not configured"
        
        # Configure the API
        genai.configure(api_key=api_key)
        
        # Prepare the image - convert BGR to RGB and get PIL image
        import cv2
        from PIL import Image
        img_rgb = cv2.cvtColor(image_data, cv2.COLOR_BGR2RGB)
        pil_image = Image.fromarray(img_rgb)
        
        # Create the model with generation config
        model = genai.GenerativeModel(
            model_name=model_name,
            generation_config={
                "temperature": temperature,
                "max_output_tokens": max_tokens,
                "top_p": 0.95,
                "top_k": 64
            }
        )
        
        # Generate content - passing both prompt and image
        response = model.generate_content([prompt, pil_image])
        
        # Return result
        return response.text if hasattr(response, 'text') else str(response)
    
    except ImportError:
        return "ERROR: Google Generative AI library not installed. Install with: pip install google-generativeai"
    except Exception as e:
        return f"ERROR: Gemini API error: {str(e)}"

def analyze_with_openai(prompt, image_data, model_name, temperature=0.7, max_tokens=100):
    """Analyze an image using OpenAI's API"""
    try:
        from openai import OpenAI
        
        # Get API key
        api_key = get_api_key('openai')
        if not api_key:
            return "ERROR: OpenAI API key not configured"
        
        # Create client (current SDK pattern)
        client = OpenAI(api_key=api_key)
        
        # Prepare image (base64)
        base64_image = prepare_image_for_api(image_data, 'openai')
        
        # Create message with image in Vision API format
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}
                    }
                ]
            }
        ]
        
        # Generate content using chat completions API
        response = client.chat.completions.create(
            model=model_name,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens
        )
        
        # Return result
        if response.choices and len(response.choices) > 0:
            return response.choices[0].message.content
        return "No response received from OpenAI"
    
    except ImportError:
        return "ERROR: OpenAI library not installed. Install with: pip install openai"
    except Exception as e:
        return f"ERROR: OpenAI API error: {str(e)}"

def analyze_with_local(prompt, image_data, model_name, temperature=0.7, max_tokens=100):
    """Analyze an image using OpenAI's API"""
    try:
        from openai import OpenAI
        
        
        # Create client (current SDK pattern)
        client = OpenAI(base_url="http://127.0.0.1:1234/v1", api_key="lm-studio")
        
        # Prepare image (base64)
        base64_image = prepare_image_for_api(image_data, 'openai')
        
        # Create message with image in Vision API format
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}
                    }
                ]
            }
        ]
        
        # Generate content using chat completions API
        response = client.chat.completions.create(
            model=model_name,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens
        )
        
        # Return result
        if response.choices and len(response.choices) > 0:
            return response.choices[0].message.content
        return "No response received from OpenAI"
    
    except ImportError:
        return "ERROR: OpenAI library not installed. Install with: pip install openai"
    except Exception as e:
        return f"ERROR: OpenAI API error: {str(e)}"

# MARK: - Bridge Function
def analyze_image(provider, model_name, prompt, image_data, temperature=0.7, max_tokens=100):
    """
    Analyze image using the appropriate provider
    
    Args:
        provider: Provider name ('Gemini', 'OpenAI', 'Local')
        model_name: Name of the model
        prompt: Text prompt for analysis
        image_data: Image data in OpenCV format (BGR)
        temperature: Temperature for model generation
        max_tokens: Maximum tokens for output
        
    Returns:
        Analysis result as text
    """
    if provider == 'Gemini':
        return analyze_with_gemini(prompt, image_data, model_name, temperature, max_tokens)
    elif provider == 'OpenAI':
        return analyze_with_openai(prompt, image_data, model_name, temperature, max_tokens)
    elif provider == 'Local':
        return analyze_with_local(prompt, image_data, model_name, temperature, max_tokens)
    else:
        return f"ERROR: Unknown provider: {provider}"
