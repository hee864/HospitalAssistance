# flask_server.py

from flask_socketio import SocketIO
from flask import Flask, render_template
import time
app = Flask(__name__)
# socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')
from flask_socketio import SocketIO, emit

socketio = SocketIO(app, cors_allowed_origins='*')
@socketio.on('detection_list')
def handle_detection_list(data):
    print(f"📡 Received detection list with {len(data)} objects")
    emit('detection_list', data, broadcast=True)  # <- 브라우저 클라이언트에 다시 전송

@socketio.on('binary_frame')
def handle_binary_frame(data):
    #print("📦 Received binary frame on server")
    # 처리 코드 (이미지 저장, 디코딩 등)
    emit('binary_frame', data, broadcast=True)  # ← 수신한 데이터를 웹 클라이언트로 전파

@socketio.on('connect')
def on_connect():
    print("✅ Web client connected")




# # flask_server.py 수정
@socketio.on('pick_object')
def handle_pick_object(data):
    try:
        raw_id = str(data['raw_id'])
        print(f"Selected object - Label: {data['id']}, Raw ID: {raw_id}")

        # Python client로 동일 이벤트명 emit
        socketio.emit('pick_object', data)

        emit('selection_confirmed', {
            'raw_id': raw_id,
            'label': data['id'],
            'timestamp': time.time()
        }, broadcast=True)

    except Exception as e:
        print(f"Selection error: {str(e)}")



@app.route('/')
def index():
    return render_template('index.html')


if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000, debug=False)
