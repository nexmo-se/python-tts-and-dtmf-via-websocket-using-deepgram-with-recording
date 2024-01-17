#!/usr/bin/env python3
from fastapi import FastAPI, WebSocket, Request, WebSocketDisconnect
import time, struct, math, json, io, os
import vonage
from gtts import gTTS
from pydub import AudioSegment
app = FastAPI()

APP_ID = "<YOUR_APP_ID>" #or set it in your environmental var APP_ID

SHORT_NORMALIZE = (1.0/32768.0)
swidth = 2
Threshold = 15
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

@app.get("/webhooks/answer")
def answer_call(request: Request):
    print("Ringing",request.query_params)
    uuid = request.query_params["conversation_uuid"]
    ncco = [
        {
            "action": "talk",
            "text": "Voice Echo and DTMF test. Speak after the Ding.",
        },
        {
            "action": "record",
            "eventMethod": "GET",
            "eventUrl": [
            f'https://{request.url.hostname}/webhooks/record-event'
            ]
        },
        {
            "action": "connect",
            "from": "Vonage",
            "endpoint": [
                {
                    "type": "websocket",
                    "uri": f'wss://{request.url.hostname}/socket'.format(request.url.hostname),
                    "content-type": "audio/l16;rate=16000",
                    "headers": {
                        "uuid": uuid}
                }
            ],
        }

    ]
    return ncco


@app.post("/webhooks/call-event")
async def events(request: Request):
    request_body = await request.receive()  # Assuming it's a text-based request body
    print("Request Body:", request_body)
    return "200"

@app.get("/webhooks/record-event")
def record_events(request: Request):
    recording_url = request.query_params["recording_url"]
    print("Recording URL", recording_url)
    if recording_url == "":
        return "200"
    print("Using Recording URL", recording_url)
    client = vonage.Client(
        application_id=os.getenv('APP_ID', APP_ID),
        private_key="private.key",
    )
    response = client.voice.get_recording(recording_url)
    filename = f'recording_{str(int(time.time()))}.mp3'

    with open("recordings/"+filename, "wb") as binary_file:   
        # Write bytes to file
        binary_file.write(response)
        binary_file.close()   
    print("Recording saved")
    return "200"

@app.websocket("/socket")
async def echo_socket(ws: WebSocket):    
    await ws.accept()
    uuid = ''

    #Audio 
    rec = []
    audio_current = 1
    audio_end = 0
    
    #DTMF
    dtmf_stack = []
    dtmf_current = 1
    dtmf_end = 0
    dtmf_received = None

    #This part sends a wav file called ding.wav
    #we open the wav file
    with open("./ding.wav", "rb") as file:
        buffer = file.read()

    #we then chunk it out
    for i in range(0, len(buffer), 640):
        chunk = (buffer[i:i+640])
        await ws.send_bytes(bytes(chunk))
  

  #!!!This part will echo whatever the user says if it detects a pause!!!
    while True:
        try:
            received = await ws.receive()
        except RuntimeError: #the connection has been closed at this point
            break

        audio = b"" #blank byte
        if "bytes" in received:
            audio = received["bytes"]
            rms_val = rms(audio)
        elif "text" in received:
            print("STR", received["text"])
            data = json.loads(received["text"])
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
        if rms_val > Threshold and not audio_current <= audio_end :
            print("Heard Something")
            audio_current = time.time()
            audio_end = time.time() + TIMEOUT_LENGTH

        #If levels are higher than threshold add audio to record array and move the end timeout to now + TIMEOUT_LENGTH
        #When the levels go lower than threshold, continue recording until timeout. 
        #By doing this, we only capture relevant audio and not continously call our STT/NLP with nonsensical sounds
        #By adding a trailing TIMEOUT_LENGTH we can capture natural pauses and make things not sound robotic
        if audio_current <= audio_end: 
            if rms_val >= Threshold: audio_end = time.time() + TIMEOUT_LENGTH
            audio_current = time.time()
            rec.append(audio)

        #process audio if we have an array of non-silent audio
        else:
            if len(rec)>0: 
                
                #Do TTS
                tmp = io.BytesIO()        
                tts = gTTS(text='I heard you say...', lang='en')  
                tts.write_to_fp(tmp)
                tmp.seek(0)                       
                sound = AudioSegment.from_mp3(tmp)
                tmp.close()
                #you have to assign the set_frame_rate to a variable as it does not modify in place
                sound = sound.set_frame_rate(16000)
                #we get the converted bytes
                out = sound.export(format="wav")
                tts_dat = out.read()
                out.close()
                tts_dat = tts_dat[640:]
                # chunk it and send it out
                for i in range(0, len(tts_dat), 640):
                    chunk = (tts_dat[i:i+640])
                    await ws.send_bytes(bytes(chunk))

                #ECHO Audio
                print("Echoing Audio", uuid)

                output_audio = b''.join(rec) #get whatever we heard
                #chunk it and send it out
                for i in range(0, len(output_audio), 640):
                    chunk = (output_audio[i:i+640])
                    await ws.send_bytes(bytes(chunk))
                
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
                tmp = io.BytesIO()
                
                tts = gTTS(text='DTMF Input is '+dtmf, lang='en')  
                tts.write_to_fp(tmp)
                tmp.seek(0)                       
                sound = AudioSegment.from_mp3(tmp)
                tmp.close()
                #you have to assign the set_frame_rate to a variable as it does not modify in place
                sound = sound.set_frame_rate(16000)
                #we get the converted bytes
                out = sound.export(format="wav")
                tts_dat = out.read()
                out.close()
                tts_dat = tts_dat[640:]
                # chunk it and send it out
                for i in range(0, len(tts_dat), 640):
                    chunk = (tts_dat[i:i+640])
                    await ws.send_bytes(bytes(chunk))

               
                
                

