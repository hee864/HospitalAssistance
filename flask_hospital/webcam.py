# webcam.py

from flask import Flask, Response
import cv2
import time
import numpy as np
import atexit

app = Flask(__name__)

class CameraManager:
    def __init__(self):
        self.camera = None
        self.init_camera()
        atexit.register(self.cleanup)  # 프로그램 종료 시 정리

    def init_camera(self, max_retries=3):
        for i in range(max_retries):
            for camera_idx in range(3):  # 0, 1, 2 시도
                try:
                    self.camera = cv2.VideoCapture(camera_idx)
                    if self.camera.isOpened():
                        print(f"카메라 {camera_idx}번에서 연결 성공")
                        self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                        self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
                        return
                    else:
                        self.camera.release()
                except Exception as e:
                    print(f"카메라 {camera_idx}번 연결 시도 실패: {str(e)}")
            time.sleep(1)  # 재시도 전 대기
        print("모든 카메라 연결 시도 실패")
        self.camera = None

    def get_frame(self):
        if self.camera is None:
            self.init_camera()  # 재연결 시도
            
        if self.camera and self.camera.isOpened():
            ret, frame = self.camera.read()
            if ret:
                return frame
        
        # 실패 시 검은 화면 반환
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        cv2.putText(frame, "카메라 연결 없음", (50, 240), 
                   cv2.FONT_HERSHEY_SIMPLEX, 1, (255,255,255), 2)
        return frame

    def cleanup(self):
        if self.camera and self.camera.isOpened():
            self.camera.release()
        print("카메라 리소스 정리 완료")

camera_manager = CameraManager()

def generate_frames():
    while True:
        frame = camera_manager.get_frame()
        ret, buffer = cv2.imencode('.jpg', frame)
        frame_bytes = buffer.tobytes()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
        time.sleep(0.033)  # 30FPS 유지

@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(),
                   mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/')
def index():
    return """
    <html>
    <head>
        <title>웹캠 스트리밍</title>
        <meta http-equiv="refresh" content="5">  <!-- 5초마다 페이지 새로고침 -->
        <style>
            .status { margin-top: 20px; padding: 10px; background: #f0f0f0; }
            .error { color: red; }
        </style>
    </head>
    <body>
        <h1>웹캠 스트리밍</h1>
        <img src="/video_feed" width="640" height="480" onerror="document.getElementById('status').innerHTML='<div class=\\'error\\'>카메라 연결 오류 발생</div>'">
        <div id="status" class="status">상태: 연결 중...</div>
        <p>문제가 지속되면 서버를 재시작해 주세요.</p>
    </body>
    </html>
    """

if __name__ == '__main__':
    try:
        app.run(host='0.0.0.0', port=5000, debug=False)  # debug=False로 설정
    finally:
        camera_manager.cleanup()