import pyttsx3

try:
    engine = pyttsx3.init()
    engine.setProperty('volume',10.0)
    engine.setProperty('rate', 100)
    engine.say("The wombles of Wimbledon, common are we")
    print("Spoken")
    engine.runAndWait()

except Exception as e:
    print(f'{e}')


