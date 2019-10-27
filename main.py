#from pyimagesearch.motion_detection import SingleMotionDetector
import cv2
import pickle
import numpy as np
import tensorflow as tf
from cnn_tf import cnn_model_fn
import os
import sqlite3
import pyttsx3
from keras.models import load_model
from threading import Thread
from imutils.video import VideoStream
from flask import Response
from flask import Flask
from flask import render_template
import threading
import argparse
import datetime
import imutils
import time
import cv2

engine = pyttsx3.init()
engine.setProperty('rate', 150)
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
model = load_model('cnn_model_keras2.h5')


def get_hand_hist():
    with open("hist", "rb") as f:
        hist = pickle.load(f)
    return hist


def get_image_size():
    img = cv2.imread('gestures/1/100.jpg', 0)
    return img.shape


image_x, image_y = get_image_size()


def keras_process_image(img):
    img = cv2.resize(img, (image_x, image_y))
    img = np.array(img, dtype=np.float32)
    img = np.reshape(img, (1, image_x, image_y, 1))
    return img


def keras_predict(model, image):
    processed = keras_process_image(image)
    pred_probab = model.predict(processed)[0]
    pred_class = list(pred_probab).index(max(pred_probab))
    return max(pred_probab), pred_class


def get_pred_text_from_db(pred_class):
    conn = sqlite3.connect("gesture_db.db")
    cmd = "SELECT g_name FROM gesture WHERE g_id="+str(pred_class)
    cursor = conn.execute(cmd)
    for row in cursor:
        return row[0]


def get_pred_from_contour(contour, thresh):
    x1, y1, w1, h1 = cv2.boundingRect(contour)
    save_img = thresh[y1:y1+h1, x1:x1+w1]
    text = ""
    if w1 > h1:
        save_img = cv2.copyMakeBorder(save_img, int(
            (w1-h1)/2), int((w1-h1)/2), 0, 0, cv2.BORDER_CONSTANT, (0, 0, 0))
    elif h1 > w1:
        save_img = cv2.copyMakeBorder(save_img, 0, 0, int(
            (h1-w1)/2), int((h1-w1)/2), cv2.BORDER_CONSTANT, (0, 0, 0))
    pred_probab, pred_class = keras_predict(model, save_img)
    if pred_probab*100 > 70:
        text = get_pred_text_from_db(pred_class)
    return text


def get_operator(pred_text):
    try:
        pred_text = int(pred_text)
    except:
        return ""
    operator = ""
    if pred_text == 1:
        operator = "+"
    elif pred_text == 2:
        operator = "-"
    elif pred_text == 3:
        operator = "*"
    elif pred_text == 4:
        operator = "/"
    elif pred_text == 5:
        operator = "%"
    elif pred_text == 6:
        operator = "**"
    elif pred_text == 7:
        operator = ">>"
    elif pred_text == 8:
        operator = "<<"
    elif pred_text == 9:
        operator = "&"
    elif pred_text == 0:
        operator = "|"
    return operator


hist = get_hand_hist()
x, y, w, h = 300, 100, 300, 300
is_voice_on = True

data = ""


def get_img_contour_thresh(img):
    img = cv2.flip(img, 1)
    imgHSV = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    dst = cv2.calcBackProject([imgHSV], [0, 1], hist, [0, 180, 0, 256], 1)
    disc = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (10, 10))
    cv2.filter2D(dst, -1, disc, dst)
    blur = cv2.GaussianBlur(dst, (11, 11), 0)
    blur = cv2.medianBlur(blur, 15)
    thresh = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY+cv2.THRESH_OTSU)[1]
    thresh = cv2.merge((thresh, thresh, thresh))
    thresh = cv2.cvtColor(thresh, cv2.COLOR_BGR2GRAY)
    thresh = thresh[y:y+h, x:x+w]
    contours = cv2.findContours(
        thresh.copy(), cv2.RETR_TREE, cv2.CHAIN_APPROX_NONE)[0]
    return img, contours, thresh


def say_text(text):
    if not is_voice_on:
        return
    while engine._inLoop:
        pass
    engine.say(text)
    engine.runAndWait()


def calculator_mode(cam):
    global is_voice_on
    flag = {"first": False, "operator": False, "second": False, "clear": False}
    count_same_frames = 0
    first, operator, second = "", "", ""
    pred_text = ""
    calc_text = ""
    info = "Enter first number"
    Thread(target=say_text, args=(info,)).start()
    count_clear_frames = 0
    while True:
        img = cam.read()[1]
        img = cv2.resize(img, (640, 480))
        img, contours, thresh = get_img_contour_thresh(img)
        old_pred_text = pred_text
        if len(contours) > 0:
            contour = max(contours, key=cv2.contourArea)
            if cv2.contourArea(contour) > 10000:
                pred_text = get_pred_from_contour(contour, thresh)
                if old_pred_text == pred_text:
                    count_same_frames += 1
                else:
                    count_same_frames = 0

                if pred_text == "C":
                    if count_same_frames > 5:
                        count_same_frames = 0
                        first, second, operator, pred_text, calc_text = '', '', '', '', ''
                        flag['first'], flag['operator'], flag['second'], flag['clear'] = False, False, False, False
                        info = "Enter first number"
                        Thread(target=say_text, args=(info,)).start()

                elif pred_text == "Best of Luck " and count_same_frames > 15:
                    count_same_frames = 0
                    if flag['clear']:
                        first, second, operator, pred_text, calc_text = '', '', '', '', ''
                        flag['first'], flag['operator'], flag['second'], flag['clear'] = False, False, False, False
                        info = "Enter first number"
                        Thread(target=say_text, args=(info,)).start()
                    elif second != '':
                        flag['second'] = True
                        info = "Clear screen"
                        #Thread(target=say_text, args=(info,)).start()
                        second = ''
                        flag['clear'] = True
                        try:
                            calc_text += "= "+str(eval(calc_text))
                        except:
                            calc_text = "Invalid operation"
                        if is_voice_on:
                            speech = calc_text
                            speech = speech.replace('-', ' minus ')
                            speech = speech.replace('/', ' divided by ')
                            speech = speech.replace(
                                '**', ' raised to the power ')
                            speech = speech.replace('*', ' multiplied by ')
                            speech = speech.replace('%', ' mod ')
                            speech = speech.replace(
                                '>>', ' bitwise right shift ')
                            speech = speech.replace(
                                '<<', ' bitwise leftt shift ')
                            speech = speech.replace('&', ' bitwise and ')
                            speech = speech.replace('|', ' bitwise or ')
                            Thread(target=say_text, args=(speech,)).start()
                    elif first != '':
                        flag['first'] = True
                        info = "Enter operator"
                        Thread(target=say_text, args=(info,)).start()
                        first = ''

                elif pred_text != "Best of Luck " and pred_text.isnumeric():
                    if flag['first'] == False:
                        if count_same_frames > 15:
                            count_same_frames = 0
                            Thread(target=say_text, args=(pred_text,)).start()
                            first += pred_text
                            calc_text += pred_text
                    elif flag['operator'] == False:
                        operator = get_operator(pred_text)
                        if count_same_frames > 15:
                            count_same_frames = 0
                            flag['operator'] = True
                            calc_text += operator
                            info = "Enter second number"
                            Thread(target=say_text, args=(info,)).start()
                            operator = ''
                    elif flag['second'] == False:
                        if count_same_frames > 15:
                            Thread(target=say_text, args=(pred_text,)).start()
                            second += pred_text
                            calc_text += pred_text
                            count_same_frames = 0

        if count_clear_frames == 30:
            first, second, operator, pred_text, calc_text = '', '', '', '', ''
            flag['first'], flag['operator'], flag['second'], flag['clear'] = False, False, False, False
            info = "Enter first number"
            Thread(target=say_text, args=(info,)).start()
            count_clear_frames = 0

        blackboard = np.zeros((480, 640, 3), dtype=np.uint8)
        cv2.putText(blackboard, "Calculator Mode", (100, 50),
                    cv2.FONT_HERSHEY_TRIPLEX, 1.5, (255, 0, 0))
        cv2.putText(blackboard, "Predicted text- " + pred_text,
                    (30, 100), cv2.FONT_HERSHEY_TRIPLEX, 1, (255, 255, 0))
        cv2.putText(blackboard, "Operator " + operator, (30, 140),
                    cv2.FONT_HERSHEY_TRIPLEX, 1, (255, 255, 127))
        cv2.putText(blackboard, calc_text, (30, 240),
                    cv2.FONT_HERSHEY_TRIPLEX, 2, (255, 255, 255))
        cv2.putText(blackboard, info, (30, 440),
                    cv2.FONT_HERSHEY_TRIPLEX, 1, (0, 255, 255))
        if is_voice_on:
            cv2.putText(blackboard, "Voice on", (450, 440),
                        cv2.FONT_HERSHEY_TRIPLEX, 1, (255, 127, 0))
        else:
            cv2.putText(blackboard, "Voice off", (450, 440),
                        cv2.FONT_HERSHEY_TRIPLEX, 1, (255, 127, 0))
        cv2.rectangle(img, (x, y), (x+w, y+h), (0, 255, 0), 2)
        res = np.hstack((img, blackboard))
        cv2.imshow("Recognizing gesture", res)
        data = res
        print(data)
        cv2.imshow("thresh", thresh)
        keypress = cv2.waitKey(1)
        if keypress == ord('q') or keypress == ord('t'):
            break
        if keypress == ord('v') and is_voice_on:
            is_voice_on = False
        elif keypress == ord('v') and not is_voice_on:
            is_voice_on = True

    if keypress == ord('t'):
        return 1
    else:
        return 0


def text_mode(cam):
    global is_voice_on
    text = ""
    word = ""
    count_same_frame = 0
    while True:
        img = cam.read()[1]
        img = cv2.resize(img, (640, 480))
        img, contours, thresh = get_img_contour_thresh(img)
        old_text = text
        if len(contours) > 0:
            contour = max(contours, key=cv2.contourArea)
            if cv2.contourArea(contour) > 10000:
                text = get_pred_from_contour(contour, thresh)
                if old_text == text:
                    count_same_frame += 1
                else:
                    count_same_frame = 0

                if count_same_frame > 20:
                    if len(text) == 1:
                        Thread(target=say_text, args=(text, )).start()
                    word = word + text
                    if word.startswith('I/Me '):
                        word = word.replace('I/Me ', 'I ')
                    elif word.endswith('I/Me '):
                        word = word.replace('I/Me ', 'me ')
                    count_same_frame = 0

            elif cv2.contourArea(contour) < 1000:
                if word != '':
                    # print('yolo')
                    # say_text(text)
                    Thread(target=say_text, args=(word, )).start()
                text = ""
                word = ""
        else:
            if word != '':
                # print('yolo1')
                # say_text(text)
                Thread(target=say_text, args=(word, )).start()
            text = ""
            word = ""
        blackboard = np.zeros((480, 640, 3), dtype=np.uint8)
        cv2.putText(blackboard, "Text Mode", (180, 50),
                    cv2.FONT_HERSHEY_TRIPLEX, 1.5, (255, 0, 0))
        cv2.putText(blackboard, "Predicted text- " + text, (30, 100),
                    cv2.FONT_HERSHEY_TRIPLEX, 1, (255, 255, 0))
        cv2.putText(blackboard, word, (30, 240),
                    cv2.FONT_HERSHEY_TRIPLEX, 2, (255, 255, 255))
        if is_voice_on:
            cv2.putText(blackboard, "Voice on", (450, 440),
                        cv2.FONT_HERSHEY_TRIPLEX, 1, (255, 127, 0))
        else:
            cv2.putText(blackboard, "Voice off", (450, 440),
                        cv2.FONT_HERSHEY_TRIPLEX, 1, (255, 127, 0))
        cv2.rectangle(img, (x, y), (x+w, y+h), (0, 255, 0), 2)
        res = np.hstack((img, blackboard))
        cv2.imshow("Recognizing gesture", res)
        cv2.imshow("thresh", thresh)
        keypress = cv2.waitKey(1)
        if keypress == ord('q') or keypress == ord('c'):
            break
        if keypress == ord('v') and is_voice_on:
            is_voice_on = False
        elif keypress == ord('v') and not is_voice_on:
            is_voice_on = True

    if keypress == ord('c'):
        return 2
    else:
        return 0


def recognize():
    cam = cv2.VideoCapture(1)
    if cam.read()[0] == False:
        cam = cv2.VideoCapture(0)
    text = ""
    word = ""
    count_same_frame = 0
    keypress = 1
    while True:
        if keypress == 1:
            keypress = text_mode(cam)
        elif keypress == 2:
            keypress = calculator_mode(cam)
        else:
            break


keras_predict(model, np.zeros((50, 50), dtype=np.uint8))
# recognize()

# USAGE
# python webstreaming.py --ip 0.0.0.0 --port 8000

# import the necessary packages


# initialize the output frame and a lock used to ensure thread-safe
# exchanges of the output frames (useful for multiple browsers/tabs
# are viewing tthe stream)
outputFrame = None
lock = threading.Lock()

# initialize a flask object
app = Flask(__name__)

# initialize the video stream and allow the camera sensor to
# warmup
#vs = VideoStream(usePiCamera=1).start()
vs = VideoStream(src=0).start()
time.sleep(2.0)


@app.route("/")
def index():
    # return the rendered template
    return render_template("index.html")


def detect_motion(frameCount):
    # grab global references to the video stream, output frame, and
    # lock variables
    global vs, outputFrame, lock

    # initialize the motion detector and the total number of frames
    # read thus far
    #md = SingleMotionDetector(accumWeight=0.1)
    total = 0
#global is_voice_on
    text = ""
    word = ""
    count_same_frame = 0

    # loop over frames from the video stream
    while True:
        img = vs.read()
        img = cv2.resize(img, (640, 480))
        img, contours, thresh = get_img_contour_thresh(img)
        old_text = text
        if len(contours) > 0:
            contour = max(contours, key=cv2.contourArea)
            if cv2.contourArea(contour) > 10000:
                text = get_pred_from_contour(contour, thresh)
                if old_text == text:
                    count_same_frame += 1
                else:
                    count_same_frame = 0

                if count_same_frame > 20:
                    if len(text) == 1:
                        Thread(target=say_text, args=(text, )).start()
                    word = word + text
                    if word.startswith('I/Me '):
                        word = word.replace('I/Me ', 'I ')
                    elif word.endswith('I/Me '):
                        word = word.replace('I/Me ', 'me ')
                    count_same_frame = 0

            elif cv2.contourArea(contour) < 1000:
                if word != '':
                    # print('yolo')
                    # say_text(text)
                    Thread(target=say_text, args=(word, )).start()
                text = ""
                word = ""
        else:
            if word != '':
                # print('yolo1')
                # say_text(text)
                Thread(target=say_text, args=(word, )).start()
            text = ""
            word = ""
        blackboard = np.zeros((480, 640, 3), dtype=np.uint8)
        cv2.putText(blackboard, "Text Mode", (180, 50),
                    cv2.FONT_HERSHEY_TRIPLEX, 1.5, (255, 0, 0))
        cv2.putText(blackboard, "Predicted text- " + text, (30, 100),
                    cv2.FONT_HERSHEY_TRIPLEX, 1, (255, 255, 0))
        cv2.putText(blackboard, word, (30, 240),
                    cv2.FONT_HERSHEY_TRIPLEX, 2, (255, 255, 255))
        # if is_voice_on:
        #     cv2.putText(blackboard, "Voice on", (450, 440),
        #                 cv2.FONT_HERSHEY_TRIPLEX, 1, (255, 127, 0))
        # else:
        #     cv2.putText(blackboard, "Voice off", (450, 440),
        #                 cv2.FONT_HERSHEY_TRIPLEX, 1, (255, 127, 0))
        if total>frameCount:
            cv2.rectangle(img, (x, y), (x+w, y+h), (0, 255, 0), 2)
            res = np.hstack((img, blackboard))
            cv2.imshow("Recognizing gesture", res)
            cv2.imshow("thresh", thresh)

       
        
     
        # frame = imutils.resize(frame, width=400)
        # gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        # gray = cv2.GaussianBlur(gray, (7, 7), 0)

        # grab the current timestamp and draw it on the frame
        # timestamp = datetime.datetime.now()
        # cv2.putText(frame, timestamp.strftime(
        # 	"%A %d %B %Y %I:%M:%S%p"), (10, frame.shape[0] - 10),
        # 	cv2.FONT_HERSHEY_SIMPLEX, 0.35, (0, 0, 255), 1)

        # if the total number of frames has reached a sufficient
        # number to construct a reasonable background model, then
        # continue to process the frame
        # if total > frameCount:
        # 	# detect motion in the image
        # 	motion = md.detect(gray)

        # 	# cehck to see if motion was found in the frame
        # 	if motion is not None:
        # 		# unpack the tuple and draw the box surrounding the
        # 		# "motion area" on the output frame
        # 		(thresh, (minX, minY, maxX, maxY)) = motion
        # 		cv2.rectangle(frame, (minX, minY), (maxX, maxY),
        # 			(0, 0, 255), 2)

        # # update the background model and increment the total number
        # # of frames read thus far
        # md.update(gray)
        total += 1

        # acquire the lock, set the output frame, and release the
        # lock
        with lock:
            outputFrame = img.copy()


def generate():
    # grab global references to the output frame and lock variables
    global outputFrame, lock

    # loop over frames from the output stream
    while True:
        # wait until the lock is acquired
        with lock:
            # check if the output frame is available, otherwise skip
            # the iteration of the loop
            if outputFrame is None:
                continue

            # encode the frame in JPEG format
            (flag, encodedImage) = cv2.imencode(".jpg", outputFrame)

            # ensure the frame was successfully encoded
            if not flag:
                continue

        # yield the output frame in the byte format
        yield(b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' +
              bytearray(encodedImage) + b'\r\n')


@app.route("/video_feed")
def video_feed():
    # return the response generated along with the specific media
    # type (mime type)
    return Response(generate(),
                    mimetype="multipart/x-mixed-replace; boundary=frame")


# check to see if this is the main thread of execution
if __name__ == '__main__':
    # construct the argument parser and parse command line arguments
    ap = argparse.ArgumentParser()
    ap.add_argument("-i", "--ip", type=str, required=True,
                    help="ip address of the device")
    ap.add_argument("-o", "--port", type=int, required=True,
                    help="ephemeral port number of the server (1024 to 65535)")
    ap.add_argument("-f", "--frame-count", type=int, default=32,
                    help="# of frames used to construct the background model")
    args = vars(ap.parse_args())

    # start a thread that will perform motion detection
    t = threading.Thread(target=detect_motion, args=(
        args["frame_count"],))
    t.daemon = True
    t.start()

    # start the flask app
    app.run(host=args["ip"], port=args["port"], debug=True,
            threaded=True, use_reloader=False)

# release the video stream pointer
vs.stop()
