#!/usr/bin/env python3
from gevent import pywsgi
from gevent import monkey
monkey.patch_all(ssl=False)
from flask import Flask, request, jsonify
from flask_sock import Sock
from werkzeug.routing import Map, Rule
import time, struct, math, json, io, os
import vonage
from deepgram_processor import dg
dg = dg()
app = Flask(__name__)
sock = Sock(app)
PORT = int(os.getenv('PORT', 3003))
APP_ID = os.getenv('APP_ID', "YOUR_APP_ID") #or set it in your environmental var APP_ID
client = vonage.Client(
    application_id=APP_ID,
    private_key="private.key",
)

SHORT_NORMALIZE = (1.0/32768.0)
swidth = 2
Threshold = 10
TIMEOUT_LENGTH = 0.5 #The silent length we allow before cutting recognition
DTMF_TIMEOUT_LENGTH = 1 #The silent length we allow before we process the DTMF

def rms(frame): #Root mean Square: a function to check if the audio is silent. Commonly used in Audio stuff
    count = len(frame) / swidth
    format = "%dh" % (count) 
    shorts = struct.unpack(format, frame) #unpack a frame into individual Decimal Value
    #print(shorts)
    sum_squares = 0.0
    for sample in shorts:
        n = sample * SHORT_NORMALIZE #get the level of a sample and normalize it a bit (increase levels)
        sum_squares += n * n #get square of level
    rms = math.pow(sum_squares / count, 0.5) #summ all levels and get mean
    return rms * 1000 #raise value a bit so it's easy to read 

@app.route("/webhooks/answer")
def answer_call():
    print("Ringing",request.host)
    uuid = request.args.get("conversation_uuid")
    ncco = [
        {
            "action": "talk",
            "text": "Loading Demo",
        },
        {
            "action": "record",
            "eventMethod": "GET",
            "eventUrl": [
            f'https://{request.host}/webhooks/record-event'
            ]
        },
        {
            "action": "connect",
            "from": "Vonage",
            "endpoint": [
                {
                    "type": "websocket",
                    "uri": f'wss://{request.host}/socket'.format(request.host),
                    "content-type": "audio/l16;rate=16000",
                    "headers": {
                        "uuid": uuid}
                }
            ],
        }

    ]
    return jsonify(ncco)


@app.route("/webhooks/call-event", methods=["POST"])
def call_events():
    #request_body = request.data.decode("utf-8")  # Assuming it's a text-based request body
    #print("Request Body:", request_body)
    return "200"

@app.route("/webhooks/rtc-event", methods=["POST"])
def RTC_events():
    #request_body = request.data.decode("utf-8")  # Assuming it's a text-based request body
    #print("Request Body:", request_body)
    return "200"

@app.route("/webhooks/record-event", methods=["GET"])
def record_events():
    recording_url = request.args.get("recording_url")
    print("Recording URL", recording_url)
    if recording_url == "":
        return "200"
    print("Using Recording URL", recording_url)
    response = client.voice.get_recording(recording_url)
    filename = f'recording_{str(int(time.time()))}.mp3'

    with open("recordings/"+filename, "wb") as binary_file:   
        # Write bytes to file
        binary_file.write(response)
        binary_file.close()   
    print("Recording saved")
    return "200"

@sock.route("/socket")
def echo_socket(ws):
    uuid = ''
    
    #Audio 
    rec = []
    current = 1
    end = 0
    

    #DTMF
    dtmf_stack = []
    dtmf_current = 1
    dtmf_end = 0
    dtmf_received = None

    #Do TTS
    tts_dat = dg.speak("This is a Deepgram Speech to Text and Text to Speech with Voice Echo demo. Please speak after the ding.")
    tts_dat = b''.join(tts_dat)
    # chunk it and send it out
    for i in range(0, len(tts_dat), 640): #we send out the audio buffers 640 bytes at a time                    
        chunk = (tts_dat[i:i+640])
        ws.send(chunk)

    #This part sends a wav file called ding.wav
    #we open the wav file
    with open("./ding.wav", "rb") as file:
        buffer = file.read()
    
    #we then chunk it out
    for i in range(0, len(buffer), 640):
        chunk = (buffer[i:i+640])
        ws.send(bytes(chunk))
    
    dg.start() #start deepgram
    #!!!This part will echo whatever the user says if it detects a pause!!!
    while True:
        received = ws.receive()
        audio = b"" #blank byte
        if isinstance(received, bytes):
            audio = received
            rms_val = rms(audio)
        elif isinstance(received, str):
            print("STR", received)
            data = json.loads(received)
            if data["event"] == "websocket:connected":
                uuid = data["uuid"]
            
            #if we received a DTMF
            elif data["event"] == "websocket:dtmf":
                #uuid = data["uuid"]
                dtmf_received = data["digit"]\
                .replace("#","hash key").replace("*","star") #comment this out if you don't need to replace # and *
                print("DTMF_RECEIVED", dtmf_received)
            continue #if this is a string, we don't handle it
        else:
            continue #do nothing

        #If audio is loud enough, set the current timeout to now and end timeout to now + TIMEOUT_LENGTH
        #This will start the next part that stores the audio until it's quiet again
        if rms_val > Threshold and not current <= end :
            print("Heard Something")
            current = time.time()
            end = time.time() + TIMEOUT_LENGTH

        #If levels are higher than threshold add audio to record array and move the end timeout to now + TIMEOUT_LENGTH
        #When the levels go lower than threshold, continue recording until timeout. 
        #By doing this, we only capture relevant audio and not continously call our STT/NLP with nonsensical sounds
        #By adding a trailing TIMEOUT_LENGTH we can capture natural pauses and make things not sound robotic
        if current <= end: 
            if rms_val >= Threshold: end = time.time() + TIMEOUT_LENGTH
            current = time.time()
            dg.send(audio) #send the audio to deepgram speech to text
            rec.append(audio)

        #process audio if we have an array of non-silent audio
        else:
            if len(rec)>0: 
                
                #Do TTS
                tts_dat = dg.speak("I heard you say...")
                tts_dat = b''.join(tts_dat)
                # chunk it and send it out
                for i in range(0, len(tts_dat), 640): #we send out the audio buffers 640 bytes at a time                    
                    chunk = (tts_dat[i:i+640])
                    ws.send(chunk)

                #ECHO Audio
                print("Echoing Audio", uuid)

                output_audio = b''.join(rec) #get whatever we heard
                #chunk it and send it out
                for i in range(0, len(output_audio), 640):
                    chunk = (output_audio[i:i+640])
                    ws.send(bytes(chunk))
                
                rec = [] #reset audio array to blank

        #This parts handles DTMF input from users
        #If there is a DTMF input, set the current dtmf timeout to now and dtmf end timeout to now + DTMF_TIMEOUT_LENGTH
        #This will start the next part that stores the DTMF until no input is detected
        if dtmf_received and not dtmf_current <= dtmf_end :
            dtmf_current = time.time()
            dtmf_end = time.time() + DTMF_TIMEOUT_LENGTH

        #If no DTMF input for DTMF_TIMEOUT_LENGTH, append the dtmf_receved to our dtmf_stack
        if dtmf_current <= dtmf_end: 
            if dtmf_received: 
                dtmf_end = time.time() + DTMF_TIMEOUT_LENGTH
                dtmf_stack.append(dtmf_received)
            dtmf_current = time.time()
            dtmf_received = None

        #process DTMF if we have an array of DTMF_STACK
        else:
            if len(dtmf_stack)>0: 
                print("DTMF STACK",dtmf_stack)
                dtmf = ','.join(dtmf_stack)
                dtmf_stack = [] # reset dtmf_stack for next batch

                #here you can do whatever you want with the DTMF, I'm letting the TTS speak the DTMF digits here
                #Do TTS
                tts_dat = dg.speak('DTMF Input is '+dtmf)
                tts_dat = b''.join(tts_dat)
                # chunk it and send it out
                for i in range(0, len(tts_dat), 640): #we send out the audio buffers 640 bytes at a time                    
                    chunk = (tts_dat[i:i+640])
                    ws.send(chunk)
    dg.stop() #stop deepgram

if __name__ == "__main__":
    server = pywsgi.WSGIServer(("0.0.0.0", PORT), app)
    print(f'Application with ID: {APP_ID} runninng on port {PORT}')
    server.serve_forever()