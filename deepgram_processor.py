# Deepgram Procesor
# Copyright 2024
# Beejay Urzo CSE Vonage


import logging, verboselogs
import threading
import requests
from deepgram import (
    DeepgramClient,
    DeepgramClientOptions,
    LiveTranscriptionEvents,
    LiveOptions,
)

DEEPGRAM_API_KEY = "Put your DEEPGRAM KEY here"
DEEPGRAM_URL = "https://api.deepgram.com/v1/speak?encoding=linear16&model=aura-asteria-en&sample_rate=16000"

headers = {
    "Authorization": f"Token {DEEPGRAM_API_KEY}",
    "Content-Type": "application/json"
}

deepgram_stt_options: LiveOptions = LiveOptions(
            model="nova-2",
            punctuate=True,
            language="ja-JP", #en-US. ja-JP
            encoding="linear16",
            channels=1,
            sample_rate=16000,
            # To get UtteranceEnd, the following must be set:
            interim_results=True,
            utterance_end_ms="1000",
            vad_events=True,
        )
    

class dg:
    def __init__(self):
        
        self.started = False
        # example of setting up a client config. logging values: WARNING, VERBOSE, DEBUG, SPAM
        config = DeepgramClientOptions(
            verbose=logging.WARNING, options={"keepalive": "true"}
        )
        # deepgram: DeepgramClient = DeepgramClient("", config)
        self.deepgram: DeepgramClient = DeepgramClient(DEEPGRAM_API_KEY,  config)            

        # Create a websocket connection to Deepgram
        self.dg_connection = self.deepgram.listen.live.v("1")
        self.deepgram.speak.v("1")

        self.dg_connection.on(LiveTranscriptionEvents.Open, self.__on_open)
        self.dg_connection.on(LiveTranscriptionEvents.Transcript, self.__on_message)
        self.dg_connection.on(LiveTranscriptionEvents.Metadata, self.__on_metadata)
        self.dg_connection.on(LiveTranscriptionEvents.SpeechStarted, self.__on_speech_started)
        self.dg_connection.on(LiveTranscriptionEvents.UtteranceEnd, self.__on_utterance_end)
        self.dg_connection.on(LiveTranscriptionEvents.Close, self.__on_close)
        self.dg_connection.on(LiveTranscriptionEvents.Error, self.__on_error)
        self.dg_connection.on(LiveTranscriptionEvents.Unhandled, self.__on_unhandled)

        # connect to websocket
        
    def start(self):
        try:
            if self.dg_connection.start(deepgram_stt_options) is False:
                print("Failed to start connection")
            else:
                print("Deepgram Started")
                self.started = True
            return
        except Exception as e:    
            print(f"Could not open socket: {e}")
            return

    def stop(self):
        self.started = False
        self.dg_connection.finish()        
        print("Deepgram Stopped")

    def send(self, data):
        if(self.started):
            res = self.dg_connection.send(data)
        else:
            print("Deepgram Not Running")
            print("Start Deepgram first")
    
    def speak(self, text):
        payload = {
            "text": text
        }
        response = requests.post(DEEPGRAM_URL, headers=headers, json=payload, stream=True)
        res = []
        for chunk in response.iter_content(chunk_size=1024):
            if chunk:
                res.append(chunk)
        return res

    def __on_open(_self, self, open, **kwargs):
                print(f"DG Starting \n\n{open}\n\n")

    def __on_message(_self, self, result, **kwargs):
        sentence = result.channel.alternatives[0].transcript
        if result.is_final:
            if len(sentence) == 0:
                return ""
            print(f"speaker: {sentence}")
            return result
        return ""

    def __on_metadata(_self, self, metadata, **kwargs):
        print(f"DG Meta Data\n\n{metadata}\n\n")

    def __on_speech_started(_self, self, speech_started, **kwargs):
        pass
        # print(f"DG Speech Started\n\n{speech_started}\n\n")

    def __on_utterance_end(_self, self, utterance_end, **kwargs):
        print(f"Utterance\n\n{utterance_end}\n\n")

    def __on_close(_self, self, close, **kwargs):
        print(f"Closed\n\n{close}\n\n")

    def __on_error(_self, self, error, **kwargs):
        print(f"DG Error\n\n{error}\n\n")

    def __on_unhandled(_self, self, unhandled, **kwargs):
        print(f"DG Unhandled Errr\n\n{unhandled}\n\n")
