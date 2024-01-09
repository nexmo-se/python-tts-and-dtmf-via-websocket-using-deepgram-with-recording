Python TTS via websocket using Python GTTS Library with recording
A sample app that shows how to use GTTS for TTS and how to record it
##Running

pip install -r requirements.txt
python app.py
##Other requirements

Set your Vonage callbacks to the following
Answer callback URL: GET {APP_URL}/webhooks/answer
Event URL: GET {APP_URL}/webhooks/call-event
