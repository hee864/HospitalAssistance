from flask_socketio import SocketIO
from flask import Flask, render_template,send_from_directory
import time
app = Flask(__name__)
import os
from rclpy.node import Node
import random
# from hospital_interfaces.srv import SayText
import pydicom
from PIL import Image
from hospital_interfaces.srv import ObjectTarget
import rclpy
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DICOM_FOLDER = os.path.join(BASE_DIR, "dicom_output")
IMAGE_FOLDER = os.path.join(BASE_DIR, "static/converted")
os.makedirs(IMAGE_FOLDER, exist_ok=True)

# 전역 변수로 마지막 DICOM 파일 추적

# 그리퍼 정보
# 로봇의 이동 정보 
latest_dicom_filename = None

class ROSServer(Node):
    def __init__(self):
        super().__init__('ros_server')
        # self.srv = self.create_service(SayText, '/say_text', self.say_text_callback)
    #서비스 클라이언트 || 서버 = get_keyword노드
        # self.get_keyword_client = self.create_client(ObjectTarget, "/get_keyword")
        # while not self.get_keyword_client.wait_for_service(timeout_sec=3.0):
        #     self.get_logger().info("Waiting for get_keyword service...")
        # self.get_keyword_request = ObjectTarget.Request()
    #이거 받아서 object/target으로 뭐 받았는지 띄워주기 
    def say_text_callback(self, request, response):
        text = request.text_to_read.strip()
        global latest_dicom_filename  # 전역 변수 선언

        self.get_logger().info(f"[SayText 서비스 요청] text={text}")


        if text == "info/info":
            if latest_dicom_filename:
                try:
                    # 메타데이터 읽어서 음성 출력
                    dicom_path = os.path.join(DICOM_FOLDER, latest_dicom_filename)
                    ds = pydicom.dcmread(dicom_path)

                    name = str(ds.get("PatientName", "Unknown"))
                    sex = ds.get("PatientSex", "Unknown")
                    age = ds.get("PatientAge", "Unknown")

                    sex_kor = "남성" if sex == "M" else "여성" if sex == "F" else "성별 정보 없음"
                    try:
                        age_year = int(age.strip("Y"))
                        age_str = f"{age_year}살"
                    except:
                        age_str = "나이 정보 없음"

                    full_text = f"{name}님의 성별은 {sex_kor}이고, 나이는 {age_str}입니다."

                    # TTS
                    import pyttsx3
                    engine = pyttsx3.init()
                    engine.say(full_text)
                    engine.runAndWait()

                    response.success = True
                except Exception as e:
                    self.get_logger().error(f"[TTS 실패] {e}")
                    response.success = False
            else:
                self.get_logger().warn("latest_dicom_filename이 설정되지 않음")
                response.success = False
        else:
            self.get_logger().info("info/info가 아님 → 무시")
            response.success = False

        return response

# 전역 ROS 노드 객체
ros_node = None



@app.route("/")

def dicom_images():
    global latest_dicom_filename
    files = [f for f in os.listdir(DICOM_FOLDER) if f.endswith(".dcm")]
    random.shuffle(files)
    files = files[:1]  # 무작위로 10개만 표시

    image_metadata = []
    if files:
        latest_dicom_filename = files[0]  # 첫 번째 파일 기준으로 메타정보 읽게 설정

    for dicom_file in files:
        dicom_path = os.path.join(DICOM_FOLDER, dicom_file)
        ds = pydicom.dcmread(dicom_path)

        arr = ds.pixel_array
        img = Image.fromarray(arr)
        png_name = os.path.splitext(dicom_file)[0] + ".png"
        png_path = os.path.join(IMAGE_FOLDER, png_name)
        img.save(png_path)

        image_metadata.append({
              "filename": dicom_file,
                "image": png_name,
                "PatientName": ds.get("PatientName", "Unknown"),
                "PatientSex": ds.get("PatientSex", "Unknown"),
                "PatientAge": ds.get("PatientAge", "Unknown"),
                "PatientID": ds.get("PatientID", "Unknown"),
                "PatientSpeciesDescription": ds.get("PatientSpeciesDescription", "Unknown"),
                "PatientBreedDescription": ds.get("PatientBreedDescription", "Unknown"),
                "SeriesDescription": ds.get("SeriesDescription", "Unknown"),
                "StudyDate": ds.get("StudyDate", "Unknown"),
                "StudyTime": ds.get("StudyTime", "Unknown")
            
        })

    return render_template("index.html",images=image_metadata)


# socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')
from flask_socketio import SocketIO, emit
# self.srv = self.create_service(SayText, '/say_text', self.say_text_callback)
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
@socketio.on("keyword_text")
def handle_keyword_text(data):
    print(f"🗣️ 사용자가 말한 텍스트: {data['text']}")
    socketio.emit("keyword_text", data, broadcast=True)  # 모든 웹 클라이언트에 전송


@socketio.on("say_metadata")
def handle_say_metadata(data):
    filename = data.get("filename")
    print(f"📥 [say_metadata] 파일: {filename}")

    global latest_dicom_filename
    latest_dicom_filename = filename  # 최신 파일 설정

    # ROS 노드의 say_text 서비스 호출
    from hospital_interfaces.srv import SayText
    if ros_node:
        client = ros_node.create_client(SayText, "/say_text")
        if not client.wait_for_service(timeout_sec=2.0):
            print("⛔ say_text 서비스 대기 실패")
            return

        req = SayText.Request()
        req.text_to_read = "info/info"

        future = client.call_async(req)

        def done_cb(fut):
            if fut.result():
                print("✅ TTS 성공:", fut.result().success)
            else:
                print("⛔ TTS 실패")

        future.add_done_callback(done_cb)


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




@app.route("/converted/<filename>")

def serve_image(filename):
    return send_from_directory(IMAGE_FOLDER, filename)
def start_ros_node():
        global ros_node
        rclpy.init()
        ros_node = ROSServer()
        print("✅ ROS2 Node started.")
        import threading
        threading.Thread(target=rclpy.spin, args=(ros_node,), daemon=True).start()



if __name__ == '__main__':
    start_ros_node()
    socketio.run(app, host='0.0.0.0', port=5000, debug=False)


