import tts

#tts.getData("Hello")

#f=open('data.txt')

with open ("data.txt", "r") as myfile:
    data=myfile.readlines()
subscription_key = '2d7670a72130498abe28498ffee48a26'
app=tts.TextToSpeech(subscription_key,str(data))
app.get_token()
app.save_audio()