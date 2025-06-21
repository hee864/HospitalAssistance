import socketio

sio = socketio.Client()

@sio.event
def connect():
    print("✅ Flask 서버에 연결되었습니다.")

@sio.event
def connect_error(data):
    print("❌ 연결 실패:", data)

@sio.event
def disconnect():
    print("🔌 연결 종료됨")

def emit_image_to_web(frame):
    _, buffer = cv2.imencode('.jpg', frame)
    jpg_as_text = base64.b64encode(buffer).decode('utf-8')
    sio.emit('image', jpg_as_text)

# Flask 서버에 연결
sio.connect("http://localhost:5000")
sio = socketio.Client(logger=True, engineio_logger=True)  # 디버깅 정보 출력용



import time
time.sleep(5)  # 연결 후 5초 동안 대기
sio.disconnect()