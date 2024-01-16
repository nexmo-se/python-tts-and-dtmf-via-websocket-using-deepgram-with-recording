
# Python TTS via websocket using Python GTTS Library with recording

A sample app that shows how to use GTTS for TTS and how to record it. We have samples for Flask (`app.py`) and Fast API (`app_fast_api.py`)

## Running

  
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