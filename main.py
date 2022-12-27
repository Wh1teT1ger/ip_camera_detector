import datetime
import os
import threading
import time

import cv2
from flask import Flask, render_template, Response, jsonify, request, redirect, url_for
from camera import VideoCamera
import json
import numpy as np

lock = threading.Lock()
app = Flask(__name__)
global check_camera, masks, name_camera, address_camera, cam, message, outputFrame, t, work, frame_list
work = False
check_camera = 1
with open("config.json", "r") as read_file:
    data = json.load(read_file)
print(data)
masks = []
frame_list = []
name_camera = data['name']
address_camera = ''
cam = None


def parse_masks(dict_masks):
    array_masks = []
    for points in dict_masks:
        mask = []
        for point in points:
            mask.append([point['x'], point['y']])
        mask = np.array(mask)
        mask = mask.reshape((-1, 1, 2))
        array_masks.append(mask)
    return array_masks


if name_camera == '':
    check_camera = False

else:
    check_camera = True
    address_camera = data['address']
    masks = parse_masks(data['masks'])

message = ''
video_camera = None
global_frame = None


@app.route('/')
def index():
    global check_camera
    if check_camera is True:
        return render_template('camera.html')
    return redirect(url_for('add_camera'))


@app.route('/add_camera')
def add_camera():
    global message
    return render_template('form_camera.html', message=message)


@app.route('/add_masks')
def add_masks():
    global message, cam
    return render_template('form_masks.html')


@app.route('/camera')
def camera():
    global check_camera, cam, work
    work = False
    if check_camera is True:
        return render_template('camera.html')
    return redirect(url_for('add_camera'))


@app.route('/motion_camera')
def motion_camera():
    global work
    work = True
    return render_template('motion_camera.html')


def stream():
    global cam, outputFrame, lock, masks, work, frame_list
    motion_start_flag = False
    start_motion = False
    out = None
    recording_flag = False
    fourcc = cv2.VideoWriter_fourcc(*'MPEG')
    while cam.isOpened():
        date = datetime.datetime.now()
        success, frame = cam.read()
        frame = cv2.resize(frame, (1280, 720), interpolation=cv2.INTER_AREA)
        if len(frame_list) < 20 * 3:
            frame_list.append(frame)
        else:
            if not work:
                frame_list.pop(0)
                frame_list.append(frame)

                for mask1 in masks:
                    cv2.polylines(frame, [mask1], True, (0, 0, 255), thickness=2, lineType=8)
                font = cv2.FONT_HERSHEY_PLAIN
                date = date.strftime("%d/%m/%y %H:%M:%S")
                cv2.putText(frame, str(date), (900, 40),
                            font, 2, (255, 255, 255), 2, cv2.LINE_AA)
            if work:
                frame2 = frame_list[-1]
                frame_list.pop(0)
                frame_list.append(frame)
                frame1 = frame.copy()
                diff = cv2.absdiff(frame1, frame2)
                gray = cv2.cvtColor(diff, cv2.COLOR_BGR2GRAY)
                blur = cv2.GaussianBlur(gray, (5, 5), 0)

                for mask in masks:
                    cv2.fillPoly(blur, pts=[mask], color=(0, 0, 0))

                _, thresh = cv2.threshold(blur, 20, 255, cv2.THRESH_BINARY)
                dilated = cv2.dilate(thresh, None, iterations=3)
                contours, _ = cv2.findContours(dilated, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

                motion_flag = False

                for contour in contours:
                    (x, y, w, h) = cv2.boundingRect(contour)
                    if cv2.contourArea(contour) < 1000:
                        continue

                    cv2.rectangle(frame1, (x, y), (x + w, y + h), (0, 255, 0), 2)
                    cv2.putText(frame1, "Status: {}".format("Motion"), (10, 20), cv2.FONT_HERSHEY_SIMPLEX, 1,
                                (255, 255, 255),
                                3,
                                cv2.LINE_AA)
                    motion_flag = True

                font = cv2.FONT_HERSHEY_PLAIN
                date = date.strftime("%d/%m/%y %H:%M:%S")
                cv2.putText(frame1, str(date), (900, 40),
                            font, 2, (255, 255, 255), 2, cv2.LINE_AA)

                if motion_flag and not start_motion:
                    print('Начали запись файла')
                    date = datetime.datetime.now()
                    out = cv2.VideoWriter(f'{str(date)}.avi', fourcc, 20.0, (1280, 720))
                    for frame3 in frame_list:
                        out.write(frame3)
                        recording_flag = True
                        start_motion = True
                if motion_flag:
                    last_motion_time = time.time()
                    out.write(frame1)

                if not motion_flag and recording_flag:
                    current_time = time.time()
                    if current_time - last_motion_time >= 5:
                        recording_flag = False
                        print('Закончилась запись в файл')
                        start_motion = False
                    else:
                        out.write(frame1)
                frame = frame1.copy()
        if recording_flag and not work:
            recording_flag = False
            print('Закончилась запись в файл')
            start_motion = False

        with lock:
            outputFrame = frame.copy()
    cam.relese()


def get_frame():
    global cam, address_camera, outputFrame, lock, t
    print(type(cam))
    print(address_camera)
    if cam is None:
        if address_camera == '0':
            cam = cv2.VideoCapture(0)
        else:
            cam = cv2.VideoCapture(address_camera)
        time.sleep(2.0)
        t = threading.Thread(target=stream)
        t.daemon = True
        t.start()
    while True:
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
        yield (b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' +
               bytearray(encodedImage) + b'\r\n')


@app.route('/check_masks/', methods=['POST', 'GET'])
def data():
    if request.method == 'GET':
        return f"The URL /check_camera is accessed directly. Try going to '/add_camera' to submit form"
    if request.method == 'POST':
        global message, check_camera, masks, name_camera, address_camera
        new_masks = request.get_json()["masks"]
        print(new_masks)
        masks = parse_masks(new_masks)
        print(new_masks)
        json1 = {"name": name_camera, "address": address_camera, "masks": new_masks}
        with open('config.json', 'w') as outfile:
            json.dump(json1, outfile)
        return redirect(url_for('camera'))


@app.route('/check_camera/', methods=['POST', 'GET'])
def check_cam():
    if request.method == 'GET':
        return f"The URL /check_camera is accessed directly. Try going to '/add_camera' to submit form"
    if request.method == 'POST':
        global message, check_camera, masks, name_camera, address_camera, cam
        message = ''
        form_data = request.form
        new_name = request.form.get('Name')
        new_address = request.form.get('Address')
        print(new_name)
        print(new_address)
        if new_address == '0':
            cam = cv2.VideoCapture(0)
        else:
            cam = cv2.VideoCapture(new_address)
        success, frame = cam.read()
        cam.release()
        cam = None
        if not success:
            message = 'Камера не найдена'
            return redirect(url_for('add_camera'))
        check_camera = True
        name_camera = new_name
        address_camera = new_address
        json1 = {"name": name_camera, "address": address_camera, "masks": []}
        with open('config.json', 'w') as outfile:
            json.dump(json1, outfile)
        return redirect(url_for('camera'))


@app.route('/requests', methods=['POST', 'GET'])
def tasks():
    global check_camera, masks, name_camera, address_camera, cam
    if request.method == 'POST':
        if request.form.get('work') == 'Начать работу':
            return redirect(url_for('motion_camera'))
        elif request.form.get('work') == 'Стоп':
            return redirect(url_for('camera'))
        elif request.form.get('delete') == 'Удалить камеру':
            cam.release()
            cv2.destroyAllWindows()
            cam = None
            masks = []
            name_camera = ''
            address_camera = ''
            check_camera = False
            json1 = {"name": name_camera, "address": address_camera, "masks": []}
            with open('config.json', 'w') as outfile:
                json.dump(json1, outfile)
            return redirect(url_for('add_camera'))
        elif request.form.get('mask') == 'Изменить маску':
            p = os.path.sep.join(['static', "mask.png"])
            success, frame = cam.read()
            frame = cv2.resize(frame, (1280, 720), interpolation=cv2.INTER_AREA)
            cv2.imwrite(p, frame)
            cam.release()
            cv2.destroyAllWindows()
            cam = None
            return redirect(url_for('add_masks'))
    elif request.method == 'GET':
        return render_template('camera.html')
    return render_template('camera.html')


@app.route('/check_masks1/', methods=['POST'])
def check_mask():
    global masks
    json1 = request.get_json()
    print(json1)
    status = json1['masks']
    print(status)
    return jsonify(result="started")


@app.route('/video_feed1')
def video_feed1():
    return Response(get_frame1(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')


@app.route('/video_feed')
def video_feed():
    return Response(get_frame(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')


if __name__ == '__main__':
    app.run(host='0.0.0.0', threaded=True)
