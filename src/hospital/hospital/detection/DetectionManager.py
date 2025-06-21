import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from vision_msgs.msg import Detection2DArray
from cv_bridge import CvBridge
import cv2
import time
import base64
import numpy as np

# 🔌 SocketIO 연동
import socketio
sio = socketio.Client()
sio.connect('http://192.168.10.18:5000');

# sio.connect('http://localhost:5000')  # Flask 서버 주소
print(f"SocketIO connected: {sio.connected}")

CLASS_DICT = {
    "0": "hands",
    "1": "scalpel",
    "2": "scar",
    "3": "spray",
    "4": "suction",
    "5": "scalpel_tip"
}

class DetectionVisualizer(Node):
    def __init__(self):
        super().__init__('detection_visualizer')
        self.bridge = CvBridge()
        self.current_frame = None
        self.scalpel_detections = []
        self.tracking_detections = []
        self.last_tracking_time = None
        self.selected_raw_id = None  # 선택된 객체 ID

        self.create_subscription(Image, '/camera/camera/color/image_raw', self.image_callback, 10)
        self.create_subscription(Detection2DArray, '/scalpel_result', self.scalpel_callback, 10)
        self.create_subscription(Detection2DArray, '/general_result', self.detection_callback, 10)

        self.create_timer(0.1, self.timer_callback)
        self.get_logger().info("🟢 DetectionVisualizer Node started.")

    def image_callback(self, msg):
        self.current_frame = self.bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')

    def scalpel_callback(self, msg):
        self.scalpel_detections = msg.detections

    def detection_callback(self, msg):
        self.tracking_detections = msg.detections
        self.last_tracking_time = self.get_clock().now()

    def draw_detections(self, img, detections, color):
        for det in detections:
            x = int(det.bbox.center.position.x)
            y = int(det.bbox.center.position.y)
            w = int(det.bbox.size_x)
            h = int(det.bbox.size_y)
            x1 = int(x - w / 2)
            y1 = int(y - h / 2)
            x2 = int(x + w / 2)
            y2 = int(y + h / 2)

            label = ""
            score = 0.0
            if det.results:
                raw_id = str(det.results[0].hypothesis.class_id)
                label = CLASS_DICT.get(raw_id, raw_id)
                score = det.results[0].hypothesis.score

                # 선택된 객체 강조
                if  raw_id == self.selected_raw_id: # self.selected_raw_id and
                    color = (255, 0, 0) #파랑
                    thickness = 3
                elif raw_id == "scalpel_tip" or raw_id == "5":
                    color = (255,255,0)
                    thickness = 2
                else:
                    color = (0,255,0) # 초록
                    thickness = 2

                cv2.rectangle(img, (x1, y1), (x2, y2), color, thickness)
                y1 = max(y1 - 10, 0)
                text = f"{label}: {score:.2f}"
                cv2.putText(img, text, (x1, y1), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 1)

    def emit_image_to_web(self, img):
        try:
            img = cv2.resize(img, (640, 480))
            _, buffer = cv2.imencode('.jpg', img, [int(cv2.IMWRITE_JPEG_QUALITY), 70])
            jpg_as_text = base64.b64encode(buffer).decode('utf-8')
            sio.emit('binary_frame', {
                'image': jpg_as_text,
                'timestamp': int(time.time() * 1000)
            })
        except Exception as e:
            self.get_logger().error(f"Emit image error: {e}")

    def emit_detection_list_to_web(self):
        try:
            detection_list = []
            for det in self.tracking_detections:
                if not det.results:
                    continue
                raw_id = str(det.results[0].hypothesis.class_id)
                label = CLASS_DICT.get(raw_id, raw_id)
                score = det.results[0].hypothesis.score

                detection_list.append({
                    'label': label,
                    'raw_id': raw_id,
                    'score': round(score * 100, 1)
                })
            sio.emit('detection_list', detection_list)
        except Exception as e:
            self.get_logger().error(f"Emit detection list error: {e}")

    def timer_callback(self):
        if self.current_frame is None:
            return

        img = self.current_frame.copy()

        # 항상 표시되는 scalpel_result
        self.draw_detections(img, self.scalpel_detections, (255, 255, 0))

        show_tracking = False
        if self.last_tracking_time is not None:
            elapsed = (self.get_clock().now() - self.last_tracking_time).nanoseconds / 1e9
            if elapsed < 0.5:
                show_tracking = True

        if show_tracking:
            self.draw_detections(img, self.tracking_detections, (255, 0, 0))
        else:
            self.tracking_detections = []

        # OpenCV 창 표시 및 웹 전송
        cv2.imshow("Detection Visualizer", img)
        cv2.waitKey(1)
        self.emit_image_to_web(img)
        self.emit_detection_list_to_web()


def main(args=None):
    rclpy.init(args=args)
    node = DetectionVisualizer()

    # 📥 웹에서 pick_object 이벤트 수신 시 처리
    @sio.on('pick_object')
    def on_pick_object(data):
        picked_label = data.get('id')
        raw_id = data.get('raw_id')
        print(f"🎯 Picked from web: {picked_label} (raw_id: {raw_id})")

        if raw_id is not None:
            node.selected_raw_id = raw_id

    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()
        cv2.destroyAllWindows()


if __name__ == '__main__':
    main()
