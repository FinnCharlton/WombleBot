import pyttsx3
import subprocess
def tts():
    try:
        engine = pyttsx3.init()
        engine.setProperty('volume',10.0)
        engine.setProperty('rate', 100)
        engine.say("The wombles of Wimbledon, common are we")
        print("Spoken")
        engine.runAndWait()

    except Exception as e:
        print(f'{e}')

def ai_tts(notification):
    CHUNK_SIZE = 1024
    url = "https://api.elevenlabs.io/v1/text-to-speech/Xb7hH8MSUJpSbSDYk0k2"

    headers = {
    "Accept": "audio/mpeg",
    "Content-Type": "application/json",
    "xi-api-key": voice_key
    }

    data = {
    "text": notification,
    "model_id": "eleven_monolingual_v1",
    "voice_settings": {
        "stability": 0.5,
        "similarity_boost": 0.5
    }
    }

    response = requests.post(url, json=data, headers=headers)
    with open('output.mp3', 'wb') as f:
        for chunk in response.iter_content(chunk_size=CHUNK_SIZE):
            if chunk:
                f.write(chunk)
        
    subprocess.call(['xdg-open','/home/finncharlton/Documents/WombleBot/output.mp3'])


