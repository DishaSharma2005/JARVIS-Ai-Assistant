import speech_recognition as sr
import pyttsx3
import requests
import webbrowser
import time
import os
import json
import geocoder
import cohere  # New import for Cohere AI
from googletrans import Translator
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
WEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")
IPINFO_TOKEN = os.getenv("IPINFO_TOKEN")
COHERE_API_KEY = os.getenv("COHERE_API_KEY")  # New Cohere API key

# Initialize components
engine = pyttsx3.init()
recognizer = sr.Recognizer()
translator = Translator(service_urls=['translate.google.com'])
co = cohere.Client(COHERE_API_KEY)  # Initialize Cohere client

# Language Configuration
LANGUAGES = {
    "en": {
        "welcome": "Welcome back, Ma'am",
        "assist_today": "How can I assist you today?",
        "help": "How may I help?",
        "weather_response": "The current temperature in {city}, {country} is {temp}°C with {desc}",
        "language_set": "Language switched to English",
        "ai_thinking": "Let me think about that",
        "no_command": "I didn't recognize that command",
        "goodbye": "Goodbye!"
    },
    "hi": {
        "welcome": "स्वागत है !!",
        "assist_today": "आज मैं आपकी कैसे सहायता करूँ?",
        "help": "मैं कैसे मदद करूं?",
        "weather_response": "{city}, {country} में वर्तमान तापमान {temp}°C है और {desc}",
        "language_set": "हिंदी में बदल गया",
        "ai_thinking": "मुझे इसके बारे में सोचने दो",
        "no_command": "मैं उस आदेश को नहीं पहचान पाया",
        "goodbye": "अलविदा!"
    }
}

current_lang = "en"  # Default language

def speak(text):
    """Improved TTS with language awareness"""
    try:
        print(f"Jarvis: {text}")
        if current_lang != "en":
            text = translate_text(text, current_lang)
        engine.say(text)
        engine.runAndWait()
    except Exception as e:
        print(f"TTS Error: {e}")

def translate_text(text, target_lang):
    """Robust translation with fallback"""
    try:
        return translator.translate(text, dest=target_lang).text
    except:
        return text

def listen():
    """Enhanced speech recognition with language support"""
    with sr.Microphone() as source:
        print("Listening...")
        recognizer.adjust_for_ambient_noise(source)
        try:
            audio = recognizer.listen(source, timeout=5, phrase_time_limit=8)
            query = recognizer.recognize_google(audio, language=current_lang if current_lang in ['en', 'hi'] else 'en-IN')
            print(f"User: {query}")
            return query.lower()
        except sr.UnknownValueError:
            speak("Sorry, I didn't catch that" if current_lang == "en" else "मैं समझ नहीं पाया")
            return ""
        except Exception as e:
            print(f"Recognition Error: {e}")
            return ""

def ask_cohere(prompt):
    """Query Cohere's AI model for responses"""
    try:
        speak(LANGUAGES[current_lang]["ai_thinking"])
        response = co.generate(
            model="command",  # Cohere's best general-purpose model
            prompt=prompt,
            max_tokens=100,  # Shorter responses to save tokens
            temperature=0.7,  # Balance creativity vs. determinism
        )
        return response.generations[0].text
    except Exception as e:
        print(f"Cohere API Error: {e}")
        return "I couldn't process that request" if current_lang == "en" else "मैं उस अनुरोध को संसाधित नहीं कर सका"

def get_current_location():
    """Reliable location detection with fallbacks"""
    try:
        # Try ipinfo.io first for better accuracy
        if IPINFO_TOKEN:
            response = requests.get(f"https://ipinfo.io?token={IPINFO_TOKEN}", timeout=3)
            if response.status_code == 200:
                data = response.json()
                return data.get('city', 'Unknown'), data.get('country', 'Unknown')
        
        # Fallback to geocoder
        g = geocoder.ip('me')
        if g.ok:
            return g.city or 'Unknown', g.country or 'Unknown'
            
        return None, None
    except Exception as e:
        print(f"Location Error: {e}")
        return None, None

def get_weather(city=None, country=None, use_current=False):
    """Improved weather fetching with better error handling"""
    params = {
        "appid": WEATHER_API_KEY,
        "units": "metric"
    }
    
    try:
        if use_current:
            params['q'] = f"{city},{country}" if city and country else city or "Delhi"
            url = "http://api.openweathermap.org/data/2.5/weather"
        else:
            url = "http://api.openweathermap.org/data/2.5/weather"
            if city and country:
                params['q'] = f"{city},{country}"
            elif city:
                params['q'] = city
            else:
                speak("Please specify a location" if current_lang == "en" else "कृपया स्थान बताएं")
                return None

        response = requests.get(url, params=params, timeout=5)
        data = response.json()

        if data.get("cod") != 200:
            error_msg = data.get("message", "Unknown error")
            return f"Error: {error_msg}" if current_lang == "en" else f"त्रुटि: {error_msg}"

        weather_data = {
            'city': data['name'],
            'country': data['sys']['country'],
            'temp': data['main']['temp'],
            'desc': data['weather'][0]['description'].capitalize()
        }
        
        return LANGUAGES[current_lang]["weather_response"].format(**weather_data)
        
    except requests.exceptions.Timeout:
        return "Request timed out" if current_lang == "en" else "अनुरोध समय समाप्त"
    except Exception as e:
        print(f"Weather API Error: {e}")
        return "Service unavailable" if current_lang == "en" else "सेवा उपलब्ध नहीं"

def weather_assistant():
    """Refactored weather assistant flow"""
    current_city, current_country = get_current_location()
    
    if current_city:
        speak("Fetching current location ....")
        speak(f"I detect you're in {current_city}" if current_lang == "en" else f"मैंने पता लगाया आप {current_city} में हैं")
    else:
        speak("Location detection failed" if current_lang == "en" else "स्थान का पता लगाने में विफल")

    while True:
        speak("Current location or another place?" if current_lang == "en" else "वर्तमान स्थान या कोई अन्य स्थान?")
        choice = listen()
        
        if not choice:
            continue
            
        if any(word in choice for word in ["current", "वर्तमान"]):
            if current_city:
                weather = get_weather(city=current_city, country=current_country, use_current=True)
                speak(weather)
            else:
                speak("Current location unknown" if current_lang == "en" else "वर्तमान स्थान अज्ञात")
                continue
        else:
            speak("City name?" if current_lang == "en" else "शहर का नाम?")
            city = listen()
            
            if not city:
                continue
                
            speak("Country? (say skip)" if current_lang == "en" else "देश? (छोड़ने के लिए 'स्किप' कहें)")
            country = listen()
            
            weather = get_weather(city=city, country=None if "skip" in country else country)
            speak(weather)

        while True:
            speak("Check another? (yes/no)" if current_lang == "en" else "क्या कोई और जांच करें? (हां/नहीं)")
            repeat = listen()
            
            if "no" in repeat or "नहीं" in repeat:
                speak(LANGUAGES[current_lang]["goodbye"])
                return
            elif "yes" in repeat or "हां" in repeat:
                break
            else:
                speak("Please say yes or no" if current_lang == "en" else "कृपया हां या नहीं कहें")

def handle_command(command):
    """Enhanced command handler with language switching and AI integration"""
    global current_lang
    
    if not command:
        return
        
    # Language switching
    if "hindi" in command or "हिंदी" in command:
        current_lang = "hi"
        speak(LANGUAGES["hi"]["language_set"])
        return
    elif "english" in command or "अंग्रेजी" in command:
        current_lang = "en"
        speak(LANGUAGES["en"]["language_set"])
        return
        
        
    # Command processing
    if "open google" in command:
        speak("Opening Google" if current_lang == "en" else "गूगल खोल रहा हूँ")
        webbrowser.open("https://www.google.com")
    elif "open youtube" in command:
        speak("Opening YouTube" if current_lang == "en" else "यूट्यूब खोल रहा हूँ")
        webbrowser.open("https://www.youtube.com")
    elif "weather" in command or "मौसम" in command:
        weather_assistant()
    elif any(word in command for word in ["exit", "quit", "बंद"]):
        speak(LANGUAGES[current_lang]["goodbye"])
        exit()
    else:
        # If not a recognized command, ask Cohere AI
        ai_response = ask_cohere(command)
        speak(ai_response)

def main():
    """Main program loop"""
    speak(LANGUAGES[current_lang]["welcome"])
    speak(LANGUAGES[current_lang]["assist_today"])
    
    while True:
        command = listen()
        if command:
            handle_command(command)
        speak(LANGUAGES[current_lang]["help"])

if __name__ == "__main__":
    # Set Hindi voice if available
    voices = engine.getProperty('voices')
    hindi_voice = next((v for v in voices if 'hindi' in v.name.lower()), None)
    if hindi_voice:
        engine.setProperty('voice', hindi_voice.id)
    
    main()