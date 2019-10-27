from flask import Flask, render_template, Response
from camera import VideoCamera
import random
import string

app = Flask(__name__)



    

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/recvid')
def index():
    return render_template('index.html')

@app.route('/signup.html')
def signup():
    return render_template('signup.html')

@app.route('/index.html')
def ind():
    return render_template('index.html')


@app.route('/login.html')
def login():
    return render_template('login.html')
@app.route('/docu.html')
def docu():
    return render_template('docu.html')
def gen(camera):
    while True:
        frame = camera.get_frame()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n\r\n')

@app.route('/video_feed')
def video_feed():
    return Response(gen(VideoCamera()),
                    mimetype='multipart/x-mixed-replace; boundary=frame')




@app.route('/docusign')
def docsign():
    return render_template('docusign.html')

if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True)