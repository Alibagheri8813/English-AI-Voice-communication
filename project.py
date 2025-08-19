from vosk import Model , KaldiRecognizer
import pyaudio
import time 
from playsound import playsound
import json
import edge_tts
from openai import OpenAI
VOICE = "en-US-JessaNeural"
OUTPUT_FILE = "C:/Users/Mobile Gandom/Desktop/project_files/test_en.mp3"
messages = []
client = OpenAI(
    base_url="https://api-inference.huggingface.co/v1/",
    api_key="your_api_key"
)
model = Model("Path-to-your-english-vosk-model")
recognizer = KaldiRecognizer(model, 16000)
with open("ttt.txt", 'w') as file:  
    pass 
# Start audio stream
mic = pyaudio.PyAudio()
stream = mic.open(            format=pyaudio.paInt16,
            channels=1,
            rate=16000,
            input=True,
            frames_per_buffer=8000)
stream.start_stream()


last_two_partials = ["", ""]
is_recognizing = False
a = 0
while True:
    print("Listening...")
    data = stream.read(4000, exception_on_overflow=False)  
    
    ########################
    if recognizer.AcceptWaveform(data):
        result = recognizer.Result()
    else :
        result = recognizer.PartialResult()
    try:
        result_dict = json.loads(result)  
    except json.JSONDecodeError:
        continue
    if "start" in result_dict.get("text", ""):
        if not is_recognizing: 
            is_recognizing = True
            print("recognition started!")
            playsound("C:/Users/Mobile Gandom/Desktop/project_files/ding.mp3")
    elif "end" in result_dict.get("text", ""):
        if is_recognizing:  
            is_recognizing = False
            print("recognition stopted")
            playsound("C:/Users/Mobile Gandom/Desktop/project_files/ding.mp3")
    ###################
    if "partial" in result_dict:

        partial_text = result_dict["partial"].strip()

        if partial_text and is_recognizing:
            last_two_partials[0], last_two_partials[1] = last_two_partials[
                            1], partial_text 
            print(f"speaking : {partial_text}")
        else:  # اگر partial خالی بود، آخرین partial غیرخالی را در فایل ذخیره می‌کنیم
            if last_two_partials[1]:  # اگر آخرین partial معتبر است
                with open("ttt.txt", mode="a", encoding="utf-8") as f:
                    f.write(("User's question : "+(last_two_partials[1]).replace("end"," ")) + "\n")
                    text = (last_two_partials[1]).replace("end","")

                    translated_text = text
                    username = "your username"
                    assistant_name = "your ai username"
                    a = a + 1
                    if a == 1:
                        prompt = f"""Generate a response that
                        avoids using the characters '#' and '*'.
                        The content should be clear and informative
                        without including these symbols. 
                        Question: {translated_text}"""
                        messages.append({"role":"user","content":translated_text})
                        response = client.chat.completions.create(
                                        model="Qwen/Qwen2.5-72B-Instruct",
                                        messages=[{"role": "user", "content": prompt}],
                                        temperature=0.5,
                                        max_tokens=1024,
                                        top_p=0.7,
                                    )
                    else:
                        messages.append({"role":"user","content":translated_text})
                        response = client.chat.completions.create(
                                        model="Qwen/Qwen2.5-72B-Instruct",
                                        messages=[{"role": "user", "content": translated_text}],
                                        temperature=0.5,
                                        max_tokens=1024,
                                        top_p=0.7,
                                    )
                    msg = response.choices[0].message.content
                    messages.append({"role": "assistant", "content": msg})
                    with open("tt.txt", mode="a", encoding="utf-8") as f:
                        f.write(('English answer : '+msg) + "\n")
                    communicate = edge_tts.Communicate(msg, VOICE)
                    with open(OUTPUT_FILE, "wb") as file:
                        for chunk in communicate.stream_sync():
                            if chunk["type"] == "audio":
                                file.write(chunk["data"])
                    playsound(OUTPUT_FILE)
                    is_recognizing = False

                last_two_partials = ["", ""]
                


