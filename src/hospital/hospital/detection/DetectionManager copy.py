import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from vision_msgs.msg import Detection2DArray
from cv_bridge import CvBridge
import cv2

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
        self.scalpel_detections = []     # 항상 발행되는 디텍션
        self.tracking_detections = []    # 선택적 발행 디텍션
        self.last_tracking_time = None   # tracking time 기록

        # 이미지 프레임 구독
        self.create_subscription(Image, '/camera/camera/color/image_raw', self.image_callback, 10)

        # 칼끝 트래킹 정보 구독 (항상 들어옴)
        self.create_subscription(Detection2DArray, '/scalpel_result', self.scalpel_callback, 10)

        # 다른 객체 탐지 정보 구독 (항상 들어옴)
        self.create_subscription(Detection2DArray, '/general_result', self.detection_callback, 10)

        # 타이머
        self.create_timer(0.1, self.timer_callback)
        self.get_logger().info("🟢 DetectionVisualizer Node started.")

    def image_callback(self, msg):
        # self.get_logger().info("🖼️ image_callback 호출됨!")  # 디버그 추가
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
                raw_id = det.results[0].hypothesis.class_id
                label = CLASS_DICT.get(str(raw_id), raw_id)
                score = det.results[0].hypothesis.score

            cv2.rectangle(img, (x1, y1), (x2, y2), color, 2)
            y1 = max(y1 - 10, 0)
            text = f"{label}: {score:.2f}"
            cv2.putText(img, text, (x1, y1), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

    def timer_callback(self):
        if self.current_frame is None:
            return

        img = self.current_frame.copy()

        # 항상 초록색으로 표시되는 scalpel_result
        self.draw_detections(img, self.scalpel_detections, (0, 255, 0))

        # detection_result는 수신 시간 기준 조건부 표시
        show_tracking = False
        if self.last_tracking_time is not None:
            elapsed = (self.get_clock().now() - self.last_tracking_time).nanoseconds / 1e9
            if elapsed < 0.5:
                show_tracking = True

        if show_tracking:
            self.draw_detections(img, self.tracking_detections, (255, 0, 0))
        else:
            self.tracking_detections = []

        cv2.imshow("Detection Visualizer", img)
        cv2.waitKey(1)

def main(args=None):
    rclpy.init(args=args)
    node = DetectionVisualizer()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()
        cv2.destroyAllWindows()

if __name__ == '__main__':
    main()
