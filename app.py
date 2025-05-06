import datetime
import speech_recognition as sr
import pyttsx3
import requests
import webbrowser
import time
import os
import json
import geocoder
import cohere
from googletrans import Translator
from dotenv import load_dotenv
from gtts import gTTS
import tempfile
import pygame 
from youtube_search import YoutubeSearch  # Added for YouTube search

# Load environment variables
load_dotenv()
WEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")
IPINFO_TOKEN = os.getenv("IPINFO_TOKEN")
COHERE_API_KEY = os.getenv("COHERE_API_KEY")

# Global variables for interruptible speech
speech_active = False
current_speech_thread = None

# Language Configuration
LANGUAGES = {
    "en": {
        "welcome": "Welcome back ",
        "assist_today": "How can I assist you today?",
        "help": "How may I help?",
        "weather_response": "The current temperature in {city}, {country} is {temp}°C with {desc}",
        "language_set": "Language switched to English",
        "ai_thinking": "Let me think about that",
        "no_command": "I didn't recognize that command",
        "goodbye": "Goodbye!",
        "yes_response": "Yes",
        "playing": "Playing on YouTube",
        "search_query": "What would you like to play?"
    },
    "hi": {
        "welcome": "स्वागत है !!",
        "assist_today": "आज मैं आपकी कैसे सहायता करूँ?",
        "help": "मैं कैसे मदद करूं?",
        "weather_response": "{city}, {country} में वर्तमान तापमान {temp}°C है और {desc}",
        "language_set": "हिंदी में बदल गया",
        "ai_thinking": "मुझे इसके बारे में सोचने दो",
        "no_command": "मैं उस आदेश को नहीं पहचान पाया",
        "goodbye": "अलविदा!",
        "yes_response": "हाँ",
        "playing": "यूट्यूब पर चल रहा है",
        "search_query": "आप क्या खेलना चाहेंगे?"
    }
}

current_lang = "en"  # Default language
# Initialize engine with thread-safe approach
# Initialize engine directly without threading
engine = pyttsx3.init()
engine.setProperty('rate', 160)  # Set default speech rate
engine.setProperty('volume', 0.9)

def speak(text):
    print(f"Jarvis: {text}")
    try:
        if current_lang == "hi":
            # Hindi handling with gTTS
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as fp:
                tts = gTTS(text=text, lang='hi')
                tts.save(fp.name)
                pygame.mixer.init()
                pygame.mixer.music.load(fp.name)
                pygame.mixer.music.play()
                while pygame.mixer.music.get_busy():
                    pygame.time.Clock().tick(10)
                pygame.mixer.quit()
                os.unlink(fp.name)
        else:
            # Direct pyttsx3 usage
            engine.say(text)
            engine.runAndWait()
    except Exception as e:
        print(f"Speech Error: {e}")

def listen():
    """Simplified listening without interrupt checks"""
    with sr.Microphone() as source:
        print("Listening...")
        recognizer = sr.Recognizer()
        recognizer.adjust_for_ambient_noise(source)
        try:
            audio = recognizer.listen(source, timeout=10, phrase_time_limit=8)
            query = recognizer.recognize_google(audio, language=current_lang if current_lang in ['en', 'hi'] else 'en-IN')
            print(f"User: {query}")
            return query.lower()
        except sr.UnknownValueError:
            return ""
        except Exception as e:
            print(f"Recognition Error: {e}")
            return ""
        
def is_stop_command(text):
    return text and any(word in text for word in ["stop", "रुक", "cancel", "रद्द"])

def play_youtube_video(query=None):
    """Search and play YouTube video"""
    if not query:
        speak(LANGUAGES[current_lang]["search_query"])
        query = listen()
        user_input = listen()
        if is_stop_command(user_input):
            speak(LANGUAGES[current_lang]["help"])
            return  # or continue, or break, depending on your function context

        if not query:
            return
    
    try:
        results = YoutubeSearch(query, max_results=1).to_dict()
        if results:
            video_url = f"https://youtube.com{results[0]['url_suffix']}"
            speak(LANGUAGES[current_lang]["playing"])
            webbrowser.open(video_url)
        else:
            speak("No results found" if current_lang == "en" else "कोई परिणाम नहीं मिला")
    except Exception as e:
        print(f"YouTube Error: {e}")
        speak("Error playing video" if current_lang == "en" else "वीडियो चलाने में त्रुटि")

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
    """Get city and country using IP geolocation"""
    try:
        if IPINFO_TOKEN:
            data = requests.get(f"https://ipinfo.io?token={IPINFO_TOKEN}", timeout=3).json()
            return data.get('city', 'Unknown'), data.get('country', 'Unknown')
        g = geocoder.ip('me')
        return (g.city or 'Unknown', g.country or 'Unknown') if g.ok else (None, None)
    except Exception as e:
        print(f"Location Error: {e}")
        return None, None

def get_weather(city=None, country=None, use_current=False):
    """Fetch weather data from OpenWeatherMap"""
    params = {"appid": WEATHER_API_KEY, "units": "metric"}
    try:
        params['q'] = f"{city or 'Delhi'},{country}" if use_current else city or None
        if not params['q']:
            speak("Please specify location" if current_lang == "en" else "कृपया स्थान बताएं")
            return None
            
        data = requests.get("http://api.openweathermap.org/data/2.5/weather", params=params, timeout=5).json()
        if data.get("cod") != 200:
            error = data.get("message", "Unknown error")
            return f"Error: {error}" if current_lang == "en" else f"त्रुटि: {error}"

        return LANGUAGES[current_lang]["weather_response"].format(
            city=data['name'],
            country=data['sys']['country'],
            temp=data['main']['temp'],
            desc=data['weather'][0]['description'].capitalize()
        )
    except requests.exceptions.Timeout:
        return "Request timed out" if current_lang == "en" else "अनुरोध समय समाप्त"
    except Exception as e:
        print(f"Weather Error: {e}")
        return "Service unavailable" if current_lang == "en" else "सेवा उपलब्ध नहीं"

def weather_assistant():
    """Interactive weather checking flow with stop support"""
    city, country = get_current_location()
    if city:
        speak(f"I detect you're in {city}" if current_lang == "en" else f"मैंने पता लगाया आप {city} में हैं")
    while True:
        speak("Current location or another place?" if current_lang == "en" else "वर्तमान स्थान या कोई अन्य स्थान?")
        choice = listen()
        if is_stop_command(choice):
            speak(LANGUAGES[current_lang]["help"])
            return
        elif "current place" in choice or "वर्तमान" in choice:

               city, country = get_current_location()
               if city and country:
                  speak(f"Your current location is {city}, {country}" if current_lang == "en"
              else f"आपका वर्तमान स्थान {city}, {country} है")


        elif "another place" in choice or "शहर" in choice:

            speak("City name?" if current_lang == "en" else "शहर का नाम?")
            city_input = listen()
            if is_stop_command(city_input):
                speak(LANGUAGES[current_lang]["help"])
                return
            if not city_input: continue
            speak("Country? (say skip)" if current_lang == "en" else "देश? (छोड़ने के लिए 'स्किप' कहें)")
            country_input = listen()
            if is_stop_command(country_input):
                speak(LANGUAGES[current_lang]["help"])
                return
            country = None if "skip" in country_input else country_input
            speak(get_weather(city_input, country))
        while True:
            speak("Check another? (yes/no)" if current_lang == "en" else "क्या कोई और जांच करें? (हां/नहीं)")
            repeat = listen()
            if is_stop_command(repeat):
                speak(LANGUAGES[current_lang]["help"])
                return
            if "no" in repeat or "नहीं" in repeat:
                speak(LANGUAGES[current_lang]["goodbye"])
                return
            if "yes" in repeat or "हां" in repeat: break


def lock_windows():
    """Locks the Windows computer"""
    try:
        os.system('rundll32.exe user32.dll,LockWorkStation')
        speak("Windows locked" if current_lang == "en" else "विंडोज लॉक किया गया")
    except Exception as e:
        print(f"Lock Error: {e}")
        speak("Failed to lock" if current_lang == "en" else "लॉक करने में विफल")
def set_brightness(level):
    """Adjust screen brightness (0-100)"""
    try:
        import screen_brightness_control as sbc
        sbc.set_brightness(level)
        speak(f"Brightness set to {level}%" if current_lang == "en" else f"चमक {level}% पर सेट की गई")
    except Exception as e:
        print(f"Brightness Error: {e}")
        speak("Brightness control failed" if current_lang == "en" else "चमक नियंत्रण विफल")
def open_folder(path):
    """Open specified folder in file explorer"""
    try:
        if os.path.exists(path):
            os.startfile(path)
            speak(f"Opening {os.path.basename(path)}" if current_lang == "en" else f"{os.path.basename(path)} खोल रहा हूँ")
        else:
            speak("Folder not found" if current_lang == "en" else "फ़ोल्डर नहीं मिला")
    except Exception as e:
        print(f"Folder Error: {e}")
        speak("Failed to open folder" if current_lang == "en" else "फ़ोल्डर खोलने में विफल")
def search_and_open_file():
    """Search for files and open them interactively, with repeat/continue support."""
    try:
        speak("What file are you looking for?" if current_lang == "en" else "आप कौन सी फ़ाइल ढूंढ रहे हैं?")
        search_query = listen()
        if is_stop_command(search_query):
            speak(LANGUAGES[current_lang]["help"])
            return

        if not search_query:
            speak(LANGUAGES[current_lang]["help"])
            return

        speak("Searching..." if current_lang == "en" else "खोज रहा हूँ...")

        # Search in common directories
        search_dirs = [
            os.path.expanduser('~'),
            'C:/',
            os.path.expanduser('~/Documents'),
            os.path.expanduser('~/Downloads')
        ]

        matches = []
        for root_dir in search_dirs:
            for root, _, files in os.walk(root_dir):
                for file in files:
                    if search_query.lower() in file.lower():
                        matches.append(os.path.join(root, file))
                        if len(matches) >= 5:  # Limit to 5 matches
                            break
                if len(matches) >= 5:
                    break
            if len(matches) >= 5:
                break

        if not matches:
            speak("No files found" if current_lang == "en" else "कोई फाइल नहीं मिली")
            speak(LANGUAGES[current_lang]["help"])
            return

        if len(matches) == 1:
            os.startfile(matches[0])
            speak(f"Opening {os.path.basename(matches[0])}" if current_lang == "en"
                  else f"{os.path.basename(matches[0])} खोल रहा हूँ")
            speak(LANGUAGES[current_lang]["help"])
            return

        # Present multiple options
        speak(f"I found {len(matches)} files:" if current_lang == "en"
              else f"मुझे {len(matches)} फाइलें मिलीं:")
        for i, match in enumerate(matches[:5], 1):
            speak(f"Option {i}: {os.path.basename(match)}" if current_lang == "en"
                  else f"विकल्प {i}: {os.path.basename(match)}")
            time.sleep(0.5)

        while True:
            speak("Which one would you like to open? Say the number." if current_lang == "en"
                  else "आप कौन सी खोलना चाहेंगे? नंबर बताएं।")
            choice = listen()
            if is_stop_command(choice):
                speak(LANGUAGES[current_lang]["help"])
                return
            try:
                index = int(choice) - 1
                if 0 <= index < len(matches):
                    os.startfile(matches[index])
                    speak(f"Opening {os.path.basename(matches[index])}" if current_lang == "en"
                          else f"{os.path.basename(matches[index])} खोल रहा हूँ")
                    speak(LANGUAGES[current_lang]["help"])
                    return
                else:
                    speak("Invalid choice" if current_lang == "en" else "अमान्य विकल्प")
            except ValueError:
                speak("I didn't understand your choice" if current_lang == "en"
                      else "मैं आपका चयन नहीं समझ पाया")

            # Ask if user wants to repeat or continue
            speak("Would you like to repeat the choice or continue? Say 'repeat' to try again or 'continue' to exit to main help." if current_lang == "en"
                  else "क्या आप फिर से प्रयास करना चाहेंगे या मुख्य सहायता पर लौटना चाहेंगे? 'फिर से' कहें या 'जारी रखें' कहें।")
            follow_up = listen()
            if is_stop_command(follow_up):
                speak(LANGUAGES[current_lang]["help"])
                return
            if "continue" in follow_up or "जारी" in follow_up:
                speak(LANGUAGES[current_lang]["help"])
                return
            # If "repeat" or anything else, the loop continues

    except Exception as e:
        print(f"File Search Error: {e}")
        speak("Error during file search" if current_lang == "en" else "फाइल खोज में त्रुटि")
        speak(LANGUAGES[current_lang]["help"])

def wishMe():
    hour = int(datetime.datetime.now().hour)
    if hour >= 0 and hour < 12:
        speak("Good Morning!")
    elif hour >= 12 and hour < 18:
        speak("Good Afternoon!")
    else:
        speak("Good Evening!")
    
def handle_command(command):
    """Enhanced command handler with interrupt support"""
    global current_lang
    
    if not command:
        return
    # Language switching
    if any(word in command for word in ["hindi", "हिंदी"]):
        current_lang = "hi"
        speak(LANGUAGES["hi"]["language_set"])
        return
    elif any(word in command for word in ["english", "अंग्रेजी"]):
        current_lang = "en"
        speak(LANGUAGES["en"]["language_set"])
        return
        
    # YouTube playback
    if "play" in command or "चलाओ" in command:
        query = command.replace("play", "").replace("चलाओ", "").strip()
        play_youtube_video(query if query else None)
        return
        
    # Existing command processing
    if "open google" in command or "गूगल" in command:
        speak("Opening Google" if current_lang == "en" else "गूगल खोल रहा हूँ")
        webbrowser.open("https://www.google.com")
    elif "open youtube" in command or "यूट्यूब" in command:
        speak("Opening YouTube" if current_lang == "en" else "यूट्यूब खोल रहा हूँ")
        webbrowser.open("https://www.youtube.com")
    elif "open youtube" in command or "यूट्यूब" in command:
        speak("Opening  Linkedin" if current_lang == "en" else "लिंक्डइन खोल रहा हूँ")
        webbrowser.open("https://www.Linkedin.com")
    elif "weather" in command or "मौसम" in command:
         speak("Fetching current location")
         weather_assistant()
    elif any(word in command for word in ["exit", "quit", "बंद"]):
        speak(LANGUAGES[current_lang]["goodbye"])
        exit()
    elif any(phrase in command for phrase in [
    "current location", "my current location", "tell my current location", "वर्तमान स्थान" ]):
     city, country = get_current_location()
     if city and country:
                speak(f"Your current location is {city}, {country}" if current_lang == "en"
                    else f"आपका वर्तमान स्थान {city}, {country} है")
     else:
                speak("Location unknown" if current_lang == "en" else "स्थान अज्ञात")

    elif any(phrase in command.lower() for phrase in [
    "lock windows", "windows lock", "windows band karo", "band karo windows",
    "windows बंद करो", "लॉक विंडोज़", "lock my computer", "computer lock",
    "windows बंद कर दो", "लॉक", "lock"]):
     speak("Locking windows.." if current_lang == "en" else "विंडोज़ लॉक कर रहा हूँ")
     lock_windows()

    elif "dim" in command or "कम" in command:
        set_brightness(30)  # Set to 30% brightness
    elif "bright" in command or "तेज" in command:
        set_brightness(100)  # Set to 100% brightness
    elif "open downloads" in command or "डाउनलोड" in command:
        speak("Opening downloads")
        open_folder(os.path.expanduser('~/Downloads'))
    elif "open documents" in command or "दस्तावेज़" in command:
        speak("Opening Documents")
        open_folder(os.path.expanduser('~/Documents'))
    elif any(phrase in command for phrase in ["find file", "search file", "फाइल ढूंढो", "खोजो फाइल"]):
        search_and_open_file()
    elif "stop " in command :
     if is_stop_command(command):
        speak(LANGUAGES[current_lang]["help"])
        return

    else:
        ai_response = ask_cohere(command)
        speak(ai_response)

def main():
    # """Simplified main loop"""
    # wishMe()
    # speak(LANGUAGES[current_lang]["welcome"])
    # speak(LANGUAGES[current_lang]["assist_today"])
    # command = listen()
    # if command:
    #         if any(word in command for word in ["exit", "quit", "बंद"]):
    #             speak(LANGUAGES[current_lang]["goodbye"])
    #             return 
    #         handle_command(command)
    while True:
        speak(LANGUAGES[current_lang]["help"])
        command = listen()
        if command:
            if any(word in command for word in ["exit", "quit", "बंद"]):
                speak(LANGUAGES[current_lang]["goodbye"])
                break
            handle_command(command)

if __name__ == "__main__":
    try:
        recognizer = sr.Recognizer()
        translator = Translator(service_urls=['translate.google.com'])
        co = cohere.Client(COHERE_API_KEY)
    except Exception as e:
        print(f"Initialization failed: {e}")
    main()