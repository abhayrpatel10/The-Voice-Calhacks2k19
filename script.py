import tts

#tts.getData("Hello")
subscription_key = '2d7670a72130498abe28498ffee48a26'
app=tts.TextToSpeech(subscription_key,"hekllo")
app.get_token()
app.save_audio()