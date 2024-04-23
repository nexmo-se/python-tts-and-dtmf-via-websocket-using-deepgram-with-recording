
# Python STT and TTS via VAPI websocket using Deepgram with recording

A sample app that shows how to use Deepgram for TTS and STT and how to record it.

This sample also shows how to handle DTMF signals via Websocket.

We have samples for Flask (`app.py`) and Fast API (`app_fast_api.py`)

## Setup and Running

### Requires Python 3.10+

### Private Key
- Generate aprivate key for you Vonage app and put it inside `private.key`

### For Deepgram
1. Register at [Deepgram](https://deepgram.com/) for a free account
2. Generate an API Key
3. Put your API Key Inside `depepgram_processor.py`, line 16
4. Set the desired Speech-to-text language inisde `deepgram_processor.py` line 27
  
### Flask
1. `pip install -r requirements.txt`
2. `PORT=<PORT> APP_ID=<APP_ID> python app.py`
     

 *note:* You can also set the **PORT** number and **APP_ID** inside `app.py` if you don't want to set environmental variables. Just run:
 `python app.py`
 if you set those variables in app

### Fast-API
1. `pip install -r requirements.txt`
2. `APP_ID=<APP_ID> uvicorn --reload  --port <PORT> app_fast_api:app`
     

 *note:* You can also set **APP_ID** inside `app_fast_api.py` if you don't want to set environmental variables. Just run:
  `uvicorn --reload  --port <PORT> app_fast_api:app`
  if you set the **APP_ID** in app
## Other requirements

  

Set your Vonage callbacks to the following

- Answer callback URL: GET {APP_URL}/webhooks/answer

- Event URL: GET {APP_URL}/webhooks/call-event


## Tunneling

- [Ngrok](https://ngrok.com/) would be a good option.
