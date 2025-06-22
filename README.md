# ROBOKRATES: 동물 수술용 보조 로봇

수의사 보조 인력 부족 문제 해결을 위한 ROS2 기반 협동로봇 프로젝트

---

## 프로젝트 개요

### **프로젝트 소개 및 목적**

현재 수의사 의료 현장은 **보조 인력의 부족**, **높은 노동 강도** 등으로 많은 어려움을 겪고 있습니다.  
2024년, **두산로보틱스**는 사람을 대상으로 한 내시경 수술에서 협동로봇을 성공적으로 적용하여 보조 인력의 부담을 줄이고 수술의 정밀도를 향상시켰습니다.  

`ROBOKRATES`는 이와 같은 기술을 **동물 수술에 적용**함으로써, 수의사의 피로를 줄이고 수술 효율성과 정확도를 동시에 향상시키고자 합니다.

---

## 동작 영상

[![Video Label](http://img.youtube.com/vi/FbygqjIFBR0/0.jpg)](https://youtu.be/FbygqjIFBR0)

---


## 사용 장비 및 개발 환경

### **하드웨어**

| 장비 | 사양 |
|------|------|
| **로봇 제어용 PC** | RTX4060 탑재 MSI 노트북, Ubuntu 22.04, ROS 2 Humble |
| **두산 M0609 협동로봇** | 6축 고성능 모터, 가반하중 6kg, 작업반경 900mm, 반복정밀도 ±0.03mm |
| **RG2 그리퍼** | 그리핑 범위: 0~110mm, 힘: 40N, Payload: Force Fit 2kg / Form Fit 5kg |
| **Intel RealSense D435i** | 스테레오 Depth 센서 + IR Projector + RGB 카메라 |

---

## 소프트웨어 및 기술 스택

### **AI 및 컴퓨터 비전**

- **YOLOv8n**: 로보플로우 기반 라벨링 및 파인튜닝
- **DeepSORT**: 객체 추적  
- **OpenCV**: 영상처리 (외곽선 검출 등)

### **웹 UI 및 음성 인터페이스**

- **Flask + Flask-SocketIO**: 실시간 영상 스트리밍 및 감지 결과 전송
- **STT / TTS**: gTTS, playsound, openwakeword, langchain, pyaudio, sounddevice
- **DICOM Viewer**: pydicom, PIL 기반 의료 영상 뷰어 기능

### **운영체제 및 ROS2 통신**

- **OS**: Ubuntu 22.04 LTS
- **ROS2**: Humble (Python 기반 rclpy 멀티 노드 구조, 총 9개 노드 운영)
- **로봇 통신**: Doosan DRL API, pymodbus (Modbus TCP 기반 RG2 그리퍼 제어)
- **센서 통합**: Intel RealSense 연동 (cv_bridge, sensor_msgs/Image)

---

## 주요 기능 시나리오

1. 로봇이 **자체 음성 안내**로 환자의 병적 상태를 수의사에게 전달  
2. 수의사 음성 인식 후, 로봇이 **메스**를 집어 수의사의 손에 전달  
3. 음성 명령에 따라, 로봇이 **소독 스프레이**를 잡아 환부에 분사  
4. 음성 명령에 따라, 로봇이 **석션 도구**를 사용해 **메스 끝단**을 트래킹  
5. 석션 도구를 제자리에 복귀시키고 **로봇은 홈 위치로 원복**

---

## 프로젝트 트리 구조

```
robokrates_ws/
├── build/
├── flask_hospital/
│   ├── dicom_output/
│   │   ├── 1.2.410.200028.100.3.20190920.1208500638.12380.1.5.dcm
│   │   ├── 1.2.410.200028.100.3.20190924.1430080534.21770.1.1.dcm
│   │   └── 1.2.410.200028.100.3.20190925.1056080334.32610.1.2.dcm
│   ├── flask_server_fin.py
│   ├── png_input/
│   │   ├── 1.2.410.200028.100.3.20190920.1208500638.12380.1.5.png
│   │   ├── 1.2.410.200028.100.3.20190924.1430080534.21770.1.1.png
│   │   └── 1.2.410.200028.100.3.20190925.1056080334.32610.1.2.png
│   ├── __pycache__/
│   │   ├── ros2_bridge.cpython-310.pyc
│   │   └── ros_bridge_node.cpython-310.pyc
│   ├── static/
│   │   └── converted
│   │       ├── 1.2.410.200028.100.3.20190920.1208500638.12380.1.5.png
│   │       ├── 1.2.410.200028.100.3.20190924.1430080534.21770.1.1.png
│   │       └── 1.2.410.200028.100.3.20190925.1056080334.32610.1.2.png
│   ├── templates/
│   │   └── index.html
│   ├── test.py
│   └── webcam.py
├── install/
├── log/
└── src/
    ├── hospital/
    │   ├── hospital/
    │   │   ├── controller/
    │   │   │   ├── __init__.py
    │   │   │   ├── onrobot.py
    │   │   │   ├── robot_control.py
    │   │   │   └── tracking.py
    │   │   ├── detection/
    │   │   │   ├── DetectionManager.py
    │   │   │   ├── detection.py
    │   │   │   ├── __init__.py
    │   │   │   ├── realsense.py
    │   │   │   ├── tracking_detection.py
    │   │   │   ├── yolo.py
    │   │   │   └── yolo_scalpel_tip.py
    │   │   ├── __init__.py
    │   │   ├── manager/
    │   │   │   └── __init__.py
    │   │   └── voice/
    │   │       ├── get_keyword.py
    │   │       ├── __init__.py
    │   │       ├── MicController.py
    │   │       ├── __pycache__/
    │   │       │   ├── get_keyword.cpython-310.pyc
    │   │       │   ├── __init__.cpython-310.pyc
    │   │       │   ├── MicController.cpython-310.pyc
    │   │       │   └── wakeup_word.cpython-310.pyc
    │   │       ├── stt.py
    │   │       ├── test_wake_up.py
    │   │       ├── voice_TTS.py
    │   │       └── wakeup_word.py
    │   ├── package.xml
    │   ├── resource/
    │   │   ├── .env
    │   │   ├── best.pt
    │   │   ├── best_scalpel_tip.pt
    │   │   ├── class_name_tool.json
    │   │   ├── hello_rokey_8332_32.tflite
    │   │   ├── hospital
    │   │   ├── promt_content.txt
    │   │   ├── surgery_info.txt
    │   │   ├── T_gripper2camera.npy
    │   │   ├── T_gripper2suction.npy
    │   │   └── tts.mp3
    │   ├── setup.cfg
    │   └── setup.py
    ├── hospital_interfaces/
    │   ├── CMakeLists.txt
    │   ├── LICENSE
    │   ├── package.xml
    │   └── srv/
    │       ├── DepthAnglePos.srv
    │       └── ObjectTarget.srv
    └── DoosanBootcamp3rd/
        ├── calibration/
        ├── dsr_bringup2/
        ├── ...
        ...
```
**requirement**

src/hospital/resource/.env 파일에 OPENAI_API_KEY=~~ 부분에 키를 수정해줘야함

**설치방법**

robokrates_ws 를 다운받고

```bash
cd robokrates_ws/
colcon build
```
---

## ROS2 노드 구성 (요약)

- **doosan robot**
- **realsense**
- **get_keyword**
- **robot_control**
- **tracking**
- **tracking_detection**
- **detection**
- **detection_manager**
- **flask server**


<img src="https://github.com/user-attachments/assets/f5d80b67-d562-4793-8ef6-46ee1e6478e5" width="1280"/>




# Prerequirement
[InstallFile.zip](https://github.com/user-attachments/files/20845782/InstallFile.zip)

**순서대로 .sh 파일 실행하여 설치**

주의사항) 이 부분은 압축을 푼후 01-prerequirements.sh 파일 실행 후 중간에 패스워드 입력하라는 창이 뜨는 경우, 새로운 패스워드 등록 후 잘 기억하고 재부팅시 파란화면(MOK화면)이 뜨신 분만 따라하시면 됩니다. 그리고 중간에 패스워드 입력하라고 할 시 위에서 입력했었던 패스워드 입력하면 됩니다.
```
Perform MOK management 화면(파란 화면) → [Enroll MOK] → [View key 0] → [Esc] → [Continue] → [YES] → [Reboot]
```

---
## 1. 두산 로봇 노드

## 외부 패키지 DoosanBootcamp3rd 설치
이 프로젝트는 다음 외부 패키지의 설치를 요구합니다:

[DoosanBootcamp3rd GitHub](https://github.com/ROKEY-SPARK/DoosanBootcamp3rd)

robokrates_ws/src/ 에 DoosanBootcamp3rd/ 를 넣고 src에서 colcon build 후 source install/setup.bash

**터미널1 doosan robot 노드 실행**
```bash
ros2 launch dsr_bringup2 dsr_bringup2_rviz.launch.py mode:=real host:=192.168.1.100 port:=12345 model:=m0609
```
---
## 2. realsense 노드

**터미널2 realsense 노드 실행**
```bash
ros2 launch realsense2_camera rs_align_depth_launch.py depth_module.depth_profile:=640x480x15 rgb_camera.color_profile:=640x480x15 initial_reset:=true align_depth.enable:=true enable_rgbd:=true
```

---

## 3. get_keyword 노드

사용자의 음성 명령을 인식하여 **도구(Object)** 및 **목적지(Target)** 정보를 추출하고, 이를 ROS2 서비스 형태로 다른 노드(예: robot_control)로 전달하는 **음성 기반 인터페이스 핵심 노드**입니다.

<img src="https://github.com/user-attachments/assets/a3fca366-3c46-4b91-b6db-2c9d00567403" width="1280"/>

### 주요 기능

1. **Wake Word 감지**
   - `"hello rokey"`를 감지하면 대기 상태에서 활성 상태로 전환
   - `"Yes, I'm ready"` TTS 응답으로 사용자와 인터랙션 시작

2. **STT → GPT-4o 기반 명령어 분석**
   - 사용자의 음성을 **텍스트로 변환 (STT)**
   - LangChain + GPT-4o 모델을 통해 텍스트에서 명령어 추출  
   - 예:  
     - `"메스"` → `object: scalpel`, `target: hands`  
     - `"트래킹 시작해줘"` → `object: start`, `target: tracking`

3. **명령어 전송 및 응답 처리**
   - 추출된 명령어를 ROS2 서비스 응답 및 Socket.IO를 통해 다른 모듈로 전달  
   - 명령 유형에 따라 **TTS 안내** 또는 **웹 UI 알림 송신**


### 지원 명령어 예시

| 사용자 입력 | Object | Target | 특이 처리 |
|-------------|--------|--------|------------|
| "메스" | scalpel | hands | TTS 응답 |
| "스프레이" | spray | scar | "소독을 시작합니다" |
| "석션" | suction | scar | TTS 응답 |
| "수술정보" | info | info | Socket.IO로 info emit |
| "트래킹 시작해줘" | start | tracking | TTS "tracking_start" |
| "트래킹 종료해줘" | stop | tracking | TTS "tracking_stop" |


### AI 처리 파이프라인

```text
STT (MicController → OpenAI Whisper) 
→ LangChain Prompt (GPT-4o) 
→ 도구 및 목적지 추출 
→ ROS2 Service 응답 or SocketIO 이벤트 발행
```

### ROS2 인터페이스
Service: /get_keyword
Request: 없음 (std_srvs/Trigger 스타일)
Response:
object (str): 예: scalpel
target (str): 예: hands
commands (str): 예: tracking_start

### 웹 연동
Socket.IO 서버와 연결하여 UI 및 실시간 피드백 제공
아래 이벤트를 emit:
"keyword_text" → 감지된 명령 표시
"info" → "수술정보" 명령 시 전송


**터미널3 get_keyword 노드 실행**
```bash
cd robokrates_ws/
ros2 run hospital get_keyword
```


---

## 4. Robot Control 노드

`get_keyword` 노드로부터 전달된 **object, target, command** 정보를 바탕으로 Doosan M0609 협동로봇 및 RG2 그리퍼를 제어하는 핵심 노드입니다.  
명령어 분석 → 위치 계산 → TCP/Base 좌표 변환 → 로봇 이동 및 도구 조작까지 전 과정을 수행합니다.


### 주요 기능 및 흐름

1. **get_keyword 서비스 호출**  
   - `/get_keyword` 서비스 요청 → 음성 명령 기반 `object`, `target`, `commands` 수신

2. **트래킹 제어 (start/stop)**  
   - `object:start`, `target:tracking` → `/tracking_trigger` 서비스로 `True` 전송  
   - `object:stop`, `target:tracking` → `/tracking_trigger` 서비스로 `False` 전송, 트래킹 종료 후 홈 위치 복귀

3. **물체(Scalpel, Spray, Suction) 조작**  
   - /get_3d_position 서비스 호출 → `depth_position`(x,y,z) + `theta` 수신  
   - 현재 로봇 포즈 조회 (`get_current_posx`)  
   - TCP→Base 좌표 변환 → 절대 좌표 계산 (gripper2cam, transform 등)  
   - 이동 및 그리퍼 동작: `movel`, `movej`, `gripper.close/open/move`  
   - 장애 처리 및 예외 케이스:
     - 위치 탐지 실패 시 재시도 또는 홈 복귀
     - 그리핑 실패 시 TTS 알림 및 재시도 로직
     - Spray: 대상 위치 접근 후 분사 동작 (그리퍼 반복 제어)
   - 작업 종료 시 홈 또는 대기 위치로 복귀


### 주요 ROS2 서비스 및 통신

- **Clients**  
  - `/get_keyword` (`ObjectTarget`): 음성 명령 분석  
  - `/get_3d_position` (`DepthAnglePos`): 감지된 객체의 3D 위치 & theta  
  - `/tracking_trigger` (`SetBool`): 트래킹 제어

- **로봇 제어 인터페이스**  
  - `DSR_ROBOT2` 패키지를 통한 `movej`, `movel`, `get_current_posx`, `mwait`  
  - TCP(Base) 좌표 계산 및 변환  
  - GRIPPER via Modbus TCP (`hospital.controller.onrobot.RG`)


### 예외 처리 및 안정성

- 위치(z, 합계) 이상 시 재탐색 조건 적용 (`z_step` 상승 → 서비스 재호출)  
- 그리핑 실패 → 재시도 및 TTS 경고  
- 감지되지 않거나 제어 실패시 대체 흐름 (홈/대기 위치 이동)


### 코드 구조 요약

| 기능 | 설명 |
|------|------|
| `robot_control()` | 메인 루프: 음성 명령 수신 → object/target 분기 처리 |
| `get_target_pos()` | 감지 노드로부터 3D 위치 수신 및 좌표 변환 |
| `transform_to_base()` | TCP→Base 좌표 변환 수학 계산 |
| `pick_and_place_target()` | 실제 로봇 이동 및 그리퍼 작동 |
| `init_robot()` | 대기 위치 및 그리퍼 오픈으로 시스템 초기화 |



**터미널4 robot_control 노드 실행**
```bash
cd robokrates_ws/
ros2 run hospital robot_control
```

---
# 5. Tracking 노드

이 ROS 2 노드는 카메라로 인식된 수술 도구(예: 메스 팁)의 3D 위치를 실시간으로 추적하고, DSR(Doosan) 로봇이 해당 위치를 따라가도록 제어하는 기능을 수행합니다. YOLO 객체 인식 결과를 바탕으로 특정 클래스의 객체를 추적하고, 로봇의 좌표계를 기준으로 변환하여 움직임을 제어합니다.


## 주요 기능

- `/tracking_trigger` 서비스(`std_srvs/SetBool`)를 통해 추적 시작/중지 제어
- `/tracked_objects_3d` (`std_msgs/Float32MultiArray`)로부터 객체 3D 위치 구독
- `class_id == 5`이면서 이름이 `"scarpel_tip"`인 객체만 필터링
- `/dsr01/msg/current_posx` (`std_msgs/Float64MultiArray`)를 통해 로봇 현재 위치 구독
- 좌표 변화가 일정 이상일 때만 로봇 제어 수행 (노이즈 제거)
- 카메라 프레임에서 로봇 베이스 프레임으로 좌표 변환 (보정 매트릭스 사용)
- 로봇 제어 명령 `amovel` 호출로 비동기 이동 명령 발행
- 깊이 유효성 검사 및 오프셋 보정 포함

## 주요 토픽 및 서비스

| 항목 | 이름 | 타입 | 설명 |
|------|------|------|------|
| 서비스 | `/tracking_trigger` | `std_srvs/SetBool` | 추적 ON/OFF 제어 |
| 구독 | `/tracked_objects_3d` | `Float32MultiArray` | 3D 객체 위치 (x, y, z, class_id, conf 등) |
| 구독 | `/dsr01/msg/current_posx` | `Float64MultiArray` | 로봇의 현재 위치 |
| 내부 동작 | `amovel(pos)` | 로봇 API 호출 | 대상 위치로 로봇 이동 |


**터미널5 tracking 노드 실행** 
```bash
cd robokrates_ws/
ros2 run hospital tracking
```

tracking start/stop service call 예시
```bash
# 추적 시작
ros2 service call /tracking_trigger std_srvs/srv/SetBool "{data: true}"

# 추적 중지
ros2 service call /tracking_trigger std_srvs/srv/SetBool "{data: false}"
```

## 참고 사항
추적 대상 객체는 "scarpel_tip"이라는 이름을 가진 클래스 ID 5번 객체로 한정되어 있음
로봇 제어 명령은 추적 대상의 위치 변화가 delta > 10 mm 일 때만 발행됨
좌표계 보정 매트릭스는 수동 캘리브레이션을 통해 생성된 .npy 파일을 사용함

비동기 이동명령
```python
amovel(target_pos, vel=20, acc=20, mod=0, radius=10, ra=DR_MV_RA_OVERRIDE)
wait(0.8)
```

<img src="https://github.com/user-attachments/assets/95128038-90ee-4bab-812e-66641f633f45" width="1280"/>

pos = 10, 30, 10, 30, 20 으로 이동할 경우
파란선은 radius = 0, 주황선은 radius = 10 그래프

radius 값을 줌으로써 위치정밀도는 조금 떨어지지만 이동을 부드럽게 바꿀 수 있었음.


---

# 6. Detection 노드

이 노드는 Realsense RGB 및 Depth 영상을 기반으로 의료 도구(예: 메스)를 인식하고, 해당 객체의 3D 위치 및 기울기(theta)를 계산하여 `robot_control` 노드에 제공합니다. 또한, 객체 내부의 검은 선(예: 테이프)을 검출하여 정밀한 위치/방향 추정을 수행합니다.


## 주요 기능

- YOLO 모델을 통한 객체 탐지
- 검출된 객체의 중심점 또는 검은선 중심점을 기준으로 3D 위치 추출
- `robot_control` 노드에 `/get_3d_position` 서비스로 위치와 각도 제공
- 검은 선 기울기 추정 (`theta`)
- `Detection2DArray` 메시지로 인식 결과 퍼블리시



## 사용 토픽 및 서비스

| 유형 | 이름 | 메시지 타입 | 설명 |
|-----|----|----|------|
| 구독 | /camera/camera/color/image_raw | sensor_msgs/Image | RGB 이미지 |
| 구독 | /camera/camera/ aligned_depth_to_color/image_raw | sensor_msgs/Image | 깊이 이미지 |
| 구독 | /camera/camera/color/camera_info | sensor_msgs/CameraInfo | 카메라 내부 파라미터 |
| 서비스서버 | /get_3d_position | hospital_interfaces/ srv/DepthAnglePos | 객체 3D 위치 및 각도 요청 처리 |
| 퍼블리시 | /detection_result | vision_msgs/Detection2DArray | 객체 바운딩 박스 및 클래스 퍼블리시 |




## 주요 로직 요약

### 1. 객체 인식 및 바운딩 박스 추출
- `YOLOv8n` 모델을 통해 지정된 클래스를 탐지
- 신뢰도가 가장 높은 바운딩 박스를 사용

### 2. 검은 선 검출 (중심점 + 기울기)
- 바운딩 박스 내부에서 `cv2.threshold()`로 마스킹
- `cv2.findContours()`로 윤곽선 추출
- `cv2.minAreaRect()`로 중심점 및 각도 계산

### 3. 3D 위치 추출
- 중심점 또는 검은 선 중심점의 픽셀 좌표로부터 깊이(z) 획득
- 카메라 내부 파라미터를 활용한 카메라 좌표계 변환

### 4. 서비스 응답
- 위치: `(x, y, z)`
- 각도: `theta` (검은선 기울기)
- 실패 시 기본값 반환



**터미널6 detection 노드 실행**
```bash
cd robokrates_ws/
ros2 run hospital object_detection
```


## 참고
검은 선이 감지되지 않을 경우 중심점 기준으로 위치 및 기울기 0으로 반환
대상 클래스가 scalpel일 경우 영상 밝기 보정 적용

---
# 7. tracking_detection 노드

이 노드는 RealSense 카메라로부터 RGB/Depth 이미지를 받아 의료 도구(`scalpel_tip`)를 실시간으로 탐지하고, **DeepSORT** 알고리즘으로 객체를 추적하여 **3D 위치 좌표**를 계산 및 발행합니다. 감지된 객체의 바운딩 박스와 클래스 정보도 detection_manager 노드 등으로 퍼블리시됩니다.



## 주요 기능

- RealSense 카메라의 RGB, Depth, Camera Info 토픽 구독
- `YOLO` 모델을 통해 `scalpel_tip` 객체 탐지
- `DeepSORT`로 `scalpel_tip` 지속적 추적
- 객체의 **3D 위치 ([x, y, z])** 계산 및 발행
- `/scalpel_result` 토픽으로 추적된 scalpel 결과 발행
- `/general_result` 토픽으로 일반 객체 탐지 결과 발행
- `/tracked_objects_3d` 토픽으로 추적된 scalpel_tip의 3D 좌표 발행


## 토픽 및 메시지

| 구분 | 토픽명 | 메시지 타입 | 설명 |
|------|-----|----|------|
| 구독 | `/camera/camera/color/image_raw` | `sensor_msgs/Image` | RGB 영상 입력 |
| 구독 | `/camera/camera/ aligned_depth_to_color/image_raw` | `sensor_msgs/Image` | Depth 영상 입력 |
| 구독 | `/camera/camera/color/camera_info` | `sensor_msgs/CameraInfo` | 카메라 내부 파라미터 |
| 발행 | `/scalpel_result` | `vision_msgs/Detection2DArray` | 추적된 scalpel_tip 바운딩 박스 결과 |
| 발행 | `/general_result` | `vision_msgs/Detection2DArray` | 일반 YOLO 탐지 결과 |
| 발행 | `/tracked_objects_3d` | `std_msgs/Float32MultiArray` | 추적된 scalpel_tip의 [track_id, class_id, x, y, z] 좌표 목록 |


## 동작 방식 요약

### 1. 초기화
- `YOLO` 모델 (scalpel 전용 + 일반) 로딩
- RealSense 이미지/깊이 노드 초기화
- DeepSORT 추적기 구성

### 2. 객체 감지 및 추적
- `YOLOv8n`로 `scalpel_tip` 감지
- 신뢰도 0.6 이상만 필터링
- DeepSORT를 통해 트랙 유지 및 ID 할당

### 3. 3D 위치 계산
- 바운딩 박스 중심점 픽셀 좌표에서 깊이 추출
- 카메라 내파라미터를 이용해 실세계 3D 좌표 변환
- `/tracked_objects_3d` 토픽으로 전송

### 4. 시각화 결과 발행
- `/scalpel_result`: 추적된 scalpel_tip 객체 정보
- `/general_result`: 일반 YOLO 탐지 결과

---

**터미널7 tracking_detection 노드 실행**
```bash
cd robokrates_ws/
ros2 run hospital tracking_detection
```

# 8. detection_manager 노드

이 노드는 RealSense RGB 영상과 객체 탐지 결과(`/scalpel_result`, `/general_result`)를 받아 OpenCV 창 및 웹 클라이언트에 실시간으로 시각화하고, 선택된 객체 정보를 처리하는 인터페이스 역할을 수행합니다.



## 주요 기능

- RealSense RGB 이미지 토픽 구독 (`/camera/camera/color/image_raw`)
- `tracking_detection` 노드의 YOLO 탐지 결과 수신
  - `/scalpel_result`: 의료 도구 `scalpel_tip` 추적 결과
  - `/general_result`: 일반 객체 탐지 결과
- 객체 바운딩 박스 시각화 (OpenCV)
- SocketIO를 통해 웹에 이미지 및 탐지 결과 전송
- 웹에서 객체 선택 클릭 이벤트 수신 (`pick_object`)
- 선택된 객체에 대한 강조 시각화 처리



## 사용 토픽 및 이벤트

### 구독 토픽

| 토픽명 | 메시지 타입 | 설명 |
|------|------|------|
| `/camera/camera/color/image_raw` | `sensor_msgs/Image` | RealSense RGB 이미지 |
| `/scalpel_result` | `vision_msgs/Detection2DArray` | Scalpel 객체 탐지 결과 |
| `/general_result` | `vision_msgs/Detection2DArray` | 일반 객체 탐지 결과 |

### 웹 Emit 이벤트

| 이벤트명 | 설명 |
|-------|------|
| `binary_frame` | 웹으로 전송되는 JPEG 이미지 프레임 (Base64 인코딩) |
| `detection_list` | 현재 추적된 객체 리스트 (label, class_id, 신뢰도 포함) |

### 웹 수신 이벤트

| 이벤트명 | 설명 |
|-------|------|
| `pick_object` | 웹 UI에서 선택된 객체 전달 (label + raw_id) |


## 시각화 예시

- `scalpel_tip`: 하늘색 박스 (`/scalpel_result`)
- 일반 객체: 초록색 박스 (`/general_result`)
- 선택된 객체: 파란색 강조


## 동작 흐름

1. RealSense RGB 이미지 수신 → OpenCV 이미지 변환
2. YOLO 결과 (`/scalpel_result`, `/general_result`)를 받아 시각화
3. 바운딩 박스와 클래스 정보를 이미지에 그리기
4. 웹으로:
   - 실시간 영상 프레임 전송
   - 탐지된 객체 리스트 전송
5. 웹에서 선택된 객체(raw_id)를 다시 수신해 강조 시각화


**터미널8 detection_manager 노드 실행**
```bash
cd robokrates_ws/
ros2 run hospital detection_manager
```

---

# 9. Flask Server 

이 Flask 서버는 DICOM 의료 영상의 시각화와 실시간 객체 탐지 정보의 SocketIO 통신을 동시에 제공하는 통합 웹 서버입니다. 수술 현장의 데이터 시각화, 음성 출력, 명령 수신, 객체 선택 등을 브라우저와 연동하여 처리할 수 있습니다.

<img src="https://github.com/user-attachments/assets/b0ee48bb-22ae-474f-a91e-ff185bab4a2e" width="1280"/>

## 주요 기능

### DICOM 뷰어
- `dicom_output/` 폴더에서 `.dcm` 파일 자동 로드
- DICOM → PNG로 변환하여 웹 브라우저에 표시
- 환자 정보(PatientName, 성별, 나이, 종 등) 메타데이터 표시

### SocketIO 실시간 통신
- 웹 → 서버: 명령어 전송 (`keyword_text`, `pick_object`)
- 서버 → 웹: 객체 선택 반영 (`selection_confirmed`), 탐지 결과 공유 (`detection_list`)
- 웹 ↔ Python Client: `binary_frame` 및 객체 리스트 상호 전송

### gTTS 음성 출력

- 환자 메타데이터를 텍스트로 구성해 `gTTS`로 음성 출력
- `info` 이벤트로 트리거됨
- 웹 클라이언트에 텍스트 결과 전송



**터미널9 flask 서버 실헹**
```bash
cd robokrates_ws/flask_hospital/
python3 flask_server_fin.py
```

## 의존 라이브러리
```bash
pip install flask flask_socketio gtts playsound pydicom pillow langchain sounddevice openwakeword
```

### SocketIO 이벤트 정리
### 웹에서 서버로
|이벤트명	|설명|
|--------|--------|
|keyword_text	|명령어(JSON) 수신: object, target, commands|
|info	|현재 DICOM 파일 정보 → 음성 출력 요청|
|pick_object	|객체 선택 (label, raw_id)|
|binary_frame	|탐지 이미지 프레임 전달|
|detection_list	|탐지된 객체 리스트 전달|

### 서버에서 웹으로
|이벤트명	|설명|
|--------|--------|
|spoken_text	|음성으로 출력된 텍스트 반환|
|selection_confirmed	|선택된 객체 ID 및 label 확인|
|binary_frame	|실시간 이미지 스트림|
|detection_list	|객체 리스트 공유|
|pick_object	|Python 클라이언트에서 전파된 선택|

### 동작 예시 흐름
- 웹에서 DICOM 뷰어 접근 → .dcm 이미지 변환 후 표시
- /info 요청 → 환자 이름/성별/나이를 음성으로 출력 (gTTS)
- 웹에서 객체 선택 → pick_object SocketIO 이벤트 발생
- Python ROS 클라이언트로 선택 객체 전달
- 실시간 탐지 프레임 → binary_frame으로 웹 스트리밍


---

## 전체 노드 실행 순서

<img src="https://github.com/user-attachments/assets/71b2445a-b805-4df6-bea2-24032527cc84" width="1280"/>

---
## 욜로 학습 곡선 및 탐지 결과

<img src="https://github.com/user-attachments/assets/1bfd6365-c0da-46fa-8160-fdf5a114a38c" width="1280"/>

<img src="https://github.com/user-attachments/assets/a3f041d5-10d0-4f37-858e-a2bce9ad9c58" width="1280"/>



---
## 팀 소개

**TEAM C-4조 - ROBOKRATES**  
- 이희우  
- 정석환  
- 김동건  
- 김재훈

---

## 라이선스

본 프로젝트는 연구 및 학습 목적으로 개발되었으며, 상업적 사용을 금합니다.

---

