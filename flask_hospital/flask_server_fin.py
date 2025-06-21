from flask_socketio import SocketIO, emit
from flask import Flask, render_template, send_from_directory
import time
import os
import random
import pydicom
from PIL import Image

# Flask 초기화
app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins='*')

# 경로 설정
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DICOM_FOLDER = "/home/bako98/test_ws/flask_hospital/dicom_output" # os.path.join(BASE_DIR, "dicom_output")
IMAGE_FOLDER = "/home/bako98/test_ws/flask_hospital/png_input" # os.path.join(BASE_DIR, "static/converted")
os.makedirs(IMAGE_FOLDER, exist_ok=True)

# 최신 파일 추적용
latest_dicom_filename = None


@app.route("/")
def dicom_images():
    global latest_dicom_filename
    files = [f for f in os.listdir(DICOM_FOLDER) if f.endswith(".dcm")]
    random.shuffle(files)
    files = files[:1]

    image_metadata = []
    if files:
        latest_dicom_filename = files[0]  # 첫 번째 기준

    for dicom_file in files:
        dicom_path = os.path.join(DICOM_FOLDER, dicom_file)
        ds = pydicom.dcmread(dicom_path)

        # PNG 저장
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

    return render_template("index.html", images=image_metadata)


@app.route("/converted/<filename>")
def serve_image(filename):
    return send_from_directory(IMAGE_FOLDER, filename)


@socketio.on("connect")
def on_connect():
    print("✅ Web client connected")



@socketio.on("keyword_text")
def handle_keyword_text(data):
    print(f"🗣️ 감지된 명령 - Object: {data.get('object')}, Target: {data.get('target')}, Command: {data.get('commands')}")
    socketio.emit("keyword_text", data, to=None)  # 모든 웹 클라이언트에 전송


@socketio.on("info")
def handle_info_event(data):
    print("📥 [info 이벤트 수신] 수술 정보 음성 출력 요청 감지")
    
    global latest_dicom_filename
    if not latest_dicom_filename:
        print("❌ DICOM 파일 없음")
        return

    try:
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

        print(f"🔊 gTTS로 출력할 텍스트: {full_text}")

        from gtts import gTTS
        import uuid
        tmp_path = f"/tmp/{uuid.uuid4()}.mp3"
        gTTS(text=full_text, lang='ko').save(tmp_path)

        from playsound import playsound
        playsound(tmp_path)
        os.remove(tmp_path)

        socketio.emit("spoken_text", {"text": full_text})

    except Exception as e:
        print(f"❌ gTTS 메타데이터 음성 출력 실패: {e}")

@socketio.on("pick_object")
def handle_pick_object(data):
    try:
        raw_id = str(data['raw_id'])
        print(f"🎯 Selected object - Label: {data['id']}, Raw ID: {raw_id}")

        socketio.emit('pick_object', data)

        emit('selection_confirmed', {
            'raw_id': raw_id,
            'label': data['id'],
            'timestamp': time.time()
        }, broadcast=True)

    except Exception as e:
        print(f"Selection error: {str(e)}")


@socketio.on("detection_list")
def handle_detection_list(data):
    # print(f"📡 Detection list received: {len(data)} objects")
    emit("detection_list", data, broadcast=True)
@socketio.on('connect')
def on_connect():
    print("✅ Web client connected")


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


@socketio.on("binary_frame")
def handle_binary_frame(data):
    emit("binary_frame", data, broadcast=True)


if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5000, debug=False)
