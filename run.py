from pywinusb import hid
from time import sleep
import threading
from threading import Timer
from threading import Lock
import usb.core
import usb.util
import os
import logging
import usb.backend.libusb1
import json
import simplejson
from flask_socketio import SocketIO, emit, join_room, leave_room, close_room, rooms, disconnect
from flask import Flask, render_template, session, request, copy_current_request_context


vendor_id = 0x054c
product_id = 0x1000
devices = hid.HidDeviceFilter(vendor_id=vendor_id, product_id=product_id).get_devices()
backend = usb.backend.libusb1.get_backend(find_library=lambda x: "libusb-1.0.dll")
deviceTR = usb.core.find(backend=backend, idVendor=vendor_id, idProduct=product_id)
notPressedRED = True;
FlashStart = False;
BlockedRED = True;
CurrentType = False;
ActiveRed = False;
CurrentQuestionPoints = 0;
points = {'1': 0, '2': 0, '3': 0}
selectedOption1 = False
selectedOption2 = False
selectedOption3 = False
selectedOption4 = False

pressedREDHost1 = False
pressedREDHost2 = False

json_q = os.path.join(os.path.dirname(__file__), 'static/q.json')
#############FLASK
async_mode = 'threading' 
app = Flask(__name__, template_folder='templates')
log = logging.getLogger('werkzeug')
log.disabled = True
socketio = SocketIO(app, async_mode=async_mode)
def start_flask_app():
    socketio.run(app,host='0.0.0.0', port=80,allow_unsafe_werkzeug=True)

@app.route('/')
def index():
    return render_template('index.html', async_mode=socketio.async_mode)

@app.route('/play')
def play():
    return render_template('start.html', async_mode=socketio.async_mode)

@app.route('/questions')
def questions():
    return render_template('questions.html', async_mode=socketio.async_mode)

@socketio.event
def question_type(type):
    global CurrentType
    selectedOption1 = False
    selectedOption2 = False
    selectedOption3 = False
    pressedREDHost1 = False
    pressedREDHost2 = False
    CurrentType = type


@socketio.event
def question_response(message):
    global BlockedRED, selectedOption1,selectedOption2, selectedOption3

    if message['type'] != '..':
      if message['status'] == 'show' and message['type'] == 'fast':  BlockedRED = False;
      if message['status'] == 'show' and message['type'] == 'basic':  BlockedRED = False; selectedOption1 = False;selectedOption2 = False; selectedOption3 = False
      if message['status'] == 'hide': BlockedRED = True 

@socketio.event
def LightOff():
    resetRED()

@socketio.event
def QuestionPoints(points):
    global CurrentQuestionPoints
    CurrentQuestionPoints = points

@socketio.event
def my_event(message):
    if message['data'] == 'run-app':
        efektai() 
    if message['data'] == 'showBoard':
        socketio.emit('my_response', {'data': 'showBoard'})  
    if message['data'] == 'correct_team' and message['array'] :
        if(message['array'][0] == True): addPoints(1)
        if(message['array'][1] == True): addPoints(2)
        if(message['array'][2] == True): addPoints(3)
    print(message)
    if message['data'] == 'markPress' and message['button']:
        global selectedOption1,selectedOption2,selectedOption3 
        
        if(message['button'] == '1-blue' or message['button'] == '1-orange' or message['button'] == '1-green' or message['button'] == '1-yellow'): selectedOption1 = True
        if(message['button'] == '2-blue' or message['button'] == '2-orange' or message['button'] == '2-green' or message['button'] == '2-yellow'): selectedOption2 = True
        if(message['button'] == '3-blue' or message['button'] == '3-orange' or message['button'] == '3-green' or message['button'] == '3-yellow'): selectedOption3 = True
 

@socketio.event
def jsonfile(message):
    twitterDataFile = open(json_q, "w",encoding="utf-8")
    twitterDataFile.write(simplejson.dumps(simplejson.loads(message['data']), indent=4, sort_keys=True))
    socketio.emit('my_response', {'data': 'makeCacheRefresh'}) 

##############

def lightAll():
    lights = [0xFF, 0xFF, 0xFF, 0xFF]
    deviceTR.ctrl_transfer(0x21, 0x09, 0x0200, 0, [0,lights[0],lights[1],lights[2],lights[3],0,0,])
def ligthController(controller=0):
    lights = [0, 0, 0, 0]
    if controller==1: control = 1
    if controller==2: control = 2
    if controller==3: control = 4
    if controller==4: control = 8
    if controller==0: control = 0
    lights[0] = (0xFF if control & 1 else 0)
    lights[1] = (0xFF if control & 2 else 0)
    lights[2] = (0xFF if control & 4 else 0)
    lights[3] = (0xFF if control & 8 else 0)
    deviceTR.ctrl_transfer(0x21, 0x09, 0x0200, 0, [0,lights[0],lights[1],lights[2],lights[3],0,0,])

def checkButton(controller,button,data):
    r = False;
    if(controller == 1 and button == 'red' and data[3] == 1): r = True
    if(controller == 2 and button == 'red' and data[3] == 32): r = True
    if(controller == 3 and button == 'red' and data[4] == 4): r = True
    if(controller == 4 and button == 'red' and data[4] == 128): r = True

    if(controller == 1 and button == 'blue' and data[3] == 16): r = True
    if(controller == 2 and button == 'blue' and data[4] == 2): r = True
    if(controller == 3 and button == 'blue' and data[4] == 64): r = True
    if(controller == 4 and button == 'blue' and data[5] == 248): r = True

    if(controller == 1 and button == 'orange' and data[3] == 8): r = True
    if(controller == 2 and button == 'orange' and data[4] == 1): r = True
    if(controller == 3 and button == 'orange' and data[4] == 32): r = True
    if(controller == 4 and button == 'orange' and data[5] == 244): r = True

    if(controller == 1 and button == 'green' and data[3] == 4): r = True
    if(controller == 2 and button == 'green' and data[3] == 128): r = True
    if(controller == 3 and button == 'green' and data[4] == 16): r = True
    if(controller == 4 and button == 'green' and data[5] == 242): r = True

    if(controller == 1 and button == 'yellow' and data[3] == 2): r = True
    if(controller == 2 and button == 'yellow' and data[3] == 64): r = True
    if(controller == 3 and button == 'yellow' and data[4] == 8): r = True
    if(controller == 4 and button == 'yellow' and data[5] == 241): r = True

    return r

def ligthFirstOnly(controller):
    global notPressedRED
    global ActiveRed
    if(notPressedRED == True):
        notPressedRED = False
        socketio.emit('my_response', {'data': f"{controller}-RED"})
        ligthController(controller)
        ActiveRed = controller
def resetRED():
    global notPressedRED
    notPressedRED = True
    ActiveRed = False
    ligthController(0)
    socketio.emit('my_response', {'data': 'color-reset-fast'});


def resetBasic():
    global selectedOption1,selectedOption2,selectedOption3, pressedREDHost1, pressedREDHost2
    selectedOption1 = False
    selectedOption2 = False
    selectedOption3 = False
    pressedREDHost1 = False
    pressedREDHost2 = False
    socketio.emit('my_response', {'data': 'color-reset'});

def nextQuestion():
    socketio.emit('my_response', {'next_question': True});
def efektai():
    for x in range(0, 12):
        ligthController(1)
        sleep(0.05)
        ligthController(2)
        sleep(0.05)
        ligthController(3)
        sleep(0.05)
        ligthController(4)
        sleep(0.05)
    ligthController(0)
def addPoints(player):
    points[f'{player}'] += int(CurrentQuestionPoints);
    socketio.emit('my_response', {'points': points});

def on_data_received(data):
    #print(f'1 - {data[1]}')
    #print(f'2 - {data[2]}')
    #print(f'3 - {data[3]}')
    #print(f'4 - {data[4]}')
    #print(f'5 - {data[5]}')
    global selectedOption1,selectedOption2,selectedOption3, pressedREDHost1, pressedREDHost2 
    match CurrentType:
        case 'fast':
            if(BlockedRED == False):
                if(checkButton(1,'red',data)): ligthFirstOnly(1);
                if(checkButton(2,'red',data)): ligthFirstOnly(2);
                if(checkButton(3,'red',data)): ligthFirstOnly(3);
                if(ActiveRed):
                    if(checkButton(4,'blue',data)): addPoints(ActiveRed); resetRED(); nextQuestion();
                    if(checkButton(4,'orange',data)): resetRED()
        case 'image':
            
            #print("Received data:")
            #print(f"1 - {data[1]}")
            #print(f"2 - {data[2]}")
            #print(f"3 - {data[3]}")
            #print(f"4 - {data[4]}")
            #print(f"5 - {data[5]}")
            print(selectedOption1)
            print(selectedOption2)
            print(selectedOption3)
    
            if(checkButton(1,'blue',data) and selectedOption1 == False): socketio.emit('my_response', {'data': '1-blue'});
            if(checkButton(2,'blue',data) and selectedOption2 == False): socketio.emit('my_response', {'data': '2-blue'});
            if(checkButton(3,'blue',data) and selectedOption3 == False): socketio.emit('my_response', {'data': '3-blue'});

            if(checkButton(1,'orange',data) and selectedOption1 == False):  socketio.emit('my_response', {'data': '1-orange'});
            if(checkButton(2,'orange',data) and selectedOption2 == False):  socketio.emit('my_response', {'data': '2-orange'});
            if(checkButton(3,'orange',data) and selectedOption3 == False):  socketio.emit('my_response', {'data': '3-orange'});

            if(checkButton(1,'green',data) and selectedOption1 == False):  socketio.emit('my_response', {'data': '1-green'});
            if(checkButton(2,'green',data) and selectedOption2 == False):  socketio.emit('my_response', {'data': '2-green'});
            if(checkButton(3,'green',data) and selectedOption3 == False):  socketio.emit('my_response', {'data': '3-green'});

            if(checkButton(1,'yellow',data) and selectedOption1 == False): socketio.emit('my_response', {'data': '1-yellow'});
            if(checkButton(2,'yellow',data) and selectedOption2 == False): socketio.emit('my_response', {'data': '2-yellow'});
            if(checkButton(3,'yellow',data) and selectedOption3 == False): socketio.emit('my_response', {'data': '3-yellow'});
            if(checkButton(4,'blue',data) and [selectedOption1,selectedOption2,selectedOption3].count(True) < 3):
                resetBasic()

            if(selectedOption1 == True and selectedOption2 == True and selectedOption3 == True):
                if(checkButton(4,'red',data)):
                    if(checkButton(4,'red',data) and pressedREDHost1 == False):
                        pressedREDHost1 = True
                        socketio.emit('my_response', {'data': 'show_answer'}) 
                        socketio.emit('my_response', {'data': 'calculatePoints'})
                if(checkButton(4,'blue',data) and pressedREDHost1 == True):
                        pressedREDHost1 = False
                        resetBasic()
                        nextQuestion()

        case 'basic':
            if(checkButton(1,'blue',data) and selectedOption1 == False): socketio.emit('my_response', {'data': '1-blue'});
            if(checkButton(2,'blue',data) and selectedOption2 == False): socketio.emit('my_response', {'data': '2-blue'});
            if(checkButton(3,'blue',data) and selectedOption3 == False): socketio.emit('my_response', {'data': '3-blue'});

            if(checkButton(1,'orange',data) and selectedOption1 == False):  socketio.emit('my_response', {'data': '1-orange'});
            if(checkButton(2,'orange',data) and selectedOption2 == False):  socketio.emit('my_response', {'data': '2-orange'});
            if(checkButton(3,'orange',data) and selectedOption3 == False):  socketio.emit('my_response', {'data': '3-orange'});

            if(checkButton(1,'green',data) and selectedOption1 == False):  socketio.emit('my_response', {'data': '1-green'});
            if(checkButton(2,'green',data) and selectedOption2 == False):  socketio.emit('my_response', {'data': '2-green'});
            if(checkButton(3,'green',data) and selectedOption3 == False):  socketio.emit('my_response', {'data': '3-green'});

            if(checkButton(1,'yellow',data) and selectedOption1 == False): socketio.emit('my_response', {'data': '1-yellow'});
            if(checkButton(2,'yellow',data) and selectedOption2 == False): socketio.emit('my_response', {'data': '2-yellow'});
            if(checkButton(3,'yellow',data) and selectedOption3 == False): socketio.emit('my_response', {'data': '3-yellow'});
            if(checkButton(4,'blue',data) and [selectedOption1,selectedOption2,selectedOption3].count(True) < 3):
                resetBasic()

            if(selectedOption1 == True and selectedOption2 == True and selectedOption3 == True):
                if(checkButton(4,'red',data)):
                    if(checkButton(4,'red',data) and pressedREDHost1 == False):
                        pressedREDHost1 = True
                        socketio.emit('my_response', {'data': 'show_answer'}) 
                        socketio.emit('my_response', {'data': 'calculatePoints'})
                if(checkButton(4,'blue',data) and pressedREDHost1 == True):
                        pressedREDHost1 = False
                        resetBasic()
                        nextQuestion()
                    
        



if devices:
    device = devices[0]
    device.open()
    resetRED()
    if(FlashStart == False):
        flask_thread = threading.Thread(target=start_flask_app)
        flask_thread.start()
        FlashStart = True
    device.set_raw_data_handler(on_data_received)
    while device.is_plugged():
        pass
    device.close()
    print("USB device not found")
    os._exit(0)
    
else:
    print("USB device not found")

