import pyttsx3

try:
    engine = pyttsx3.init()
    engine.setProperty('volume',1.0)
    engine.setProperty('rate', 175)
    engine.say("Text to Speech")
    print("Spoken")
    engine.runAndWait()

except Exception as e:
    print(f'{e}')


