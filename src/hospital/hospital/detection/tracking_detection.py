# detection.detection.py

# 주요 변경 사항:
# _get_black_line_angle() 메서드 추가: YOLO로 감지된 바운딩 박스 내에서 검은 선의 기울기를 계산
# _compute_position() 메서드에서 바운딩 박스가 감지되면 검은 선 각도 계산 수행
# 검은 선 각도 계산 결과를 로그로 출력하고 토픽으로 발행
# 이제 이 노드는:
# YOLO로 객체 감지
# 감지된 객체의 3D 위치 계산 및 발행
# 동시에 바운딩 박스 내에서 검은 선의 기울기 계산 및 발행을 수행합니다
import gc
from rclpy.logging import get_logger
import numpy as np
import rclpy
from rclpy.node import Node
from typing import Any, Callable, Optional, Tuple

from ament_index_python.packages import get_package_share_directory
from od_msg.srv import SrvDepthPosition
from hospital.detection.realsense import ImgNode
from hospital.detection.yolo import YoloModel

from hospital.detection.yolo_scalpel_tip import YoloModel_Scalpel_Tip

from hospital.detection.yolo import YoloModel  ## 방금추가함

from vision_msgs.msg import Detection2DArray, Detection2D, ObjectHypothesisWithPose, ObjectHypothesis
from vision_msgs.msg import BoundingBox2D, Pose2D, Point2D
from std_msgs.msg import Header
import cv2
from deep_sort_realtime.deepsort_tracker import DeepSort
from std_msgs.msg import Float32MultiArray

TRACKING_CLASS_ID=5

PACKAGE_NAME = 'hospital'
PACKAGE_PATH = get_package_share_directory(PACKAGE_NAME)
#################이 디텍션은 트래킹만 하는 함수로 고침########################

class ObjectTrackingNode(Node):
    def __init__(self, model_name='yolo'):
        super().__init__('object_tracking_node')
        self.img_node = ImgNode()
        self.model_scalpel_tip = self._load_model_scalpel_tip(model_name)
    
        self.model_general = self._load_model_general() # 방금추가함


        self.intrinsics = self._wait_for_valid_data(
            self.img_node.get_camera_intrinsic, "camera intrinsics"
        )

        self.tracker = DeepSort(
            max_age=10,  # 객체가 사라진 후 유지되는 프레임 수 (기존 30 → 15)
            nn_budget=50,  # 메모리 사용량 추가 감소
            n_init=5,  # 초기 검출 요구 횟수
            max_iou_distance=0.7,
            max_cosine_distance=0.4
        )

        # Detection 결과 발행 토픽
        self.detection_pub = self.create_publisher(Detection2DArray, '/scalpel_result', 10)

        # 방금추가함
        self.general_detection_pub = self.create_publisher(Detection2DArray, '/general_result', 10)


        # 객체 위치(3D 좌표) 토픽 추가 - 예: /tracked_objects_3d
        self.position_pub = self.create_publisher(Float32MultiArray, '/tracked_objects_3d', 10)

        # 타이머 주기 조정 (0.1초 → 0.2초)
        self.timer = self.create_timer(0.2, self.timer_callback)  # 기존 0.1초에서 변경


        self.get_logger().info("트래킹 노드 시작")

        self.get_logger().set_level(rclpy.logging.LoggingSeverity.WARN)  # INFO → WARN
        #INFO 이하 메시지는 출력하지 않고WARN, ERROR, FATAL만 출력하게 설정한 것입니다.


    # YOLO 모델 초기화 시 GPU 명시적 지정        
    def _load_model_scalpel_tip(self, name):
        if name.lower() == 'yolo':
            return YoloModel_Scalpel_Tip() # GPU 지정
        raise ValueError(f"Unsupported model: {name}")
    
    # 방금 추가함
    def _load_model_general(self):
        return YoloModel()

#########################여기서 추적 ###################
#클래스 하나에 대해서만 추적
    def timer_callback(self): ####0.2초마다 실행되는 타이머 콜백 함수
        gc.collect()#

        rclpy.spin_once(self.img_node)

        # 해상도 절반으로 다운샘플링
        frame = self.img_node.get_color_frame()
        if frame is None:
            self.get_logger().warn("타이머 콜백에서 프레임 못받음~~~~~~~~~~~~~")
            return
        results_scalpel_tip = self.model_scalpel_tip.model(frame)
        # 클래스별 최상위 감지 결과만 선택
        detections = []

        for box, score, cls in zip(
            results_scalpel_tip[0].boxes.xyxy.tolist(),
            results_scalpel_tip[0].boxes.conf.tolist(),
            results_scalpel_tip[0].boxes.cls.tolist(),
        ):
            if score < 0.6:#스코어로 거름
                self.get_logger().info("스코어 낮아서 거름")
                continue
            detections.append((
                    [box[0], box[1], box[2] - box[0], box[3] - box[1]],  # xywh
                    score,
                    TRACKING_CLASS_ID
                )) #ㅡㄹ래스 Id=10으로 고정
        tracks = self.tracker.update_tracks(detections, frame=frame)

        detection_array = Detection2DArray()
        detection_array.header.stamp = self.get_clock().now().to_msg()
        detection_array.header.frame_id = "camera_frame"

        positions_msg = Float32MultiArray()
        positions_data = []

        for track in tracks:
            if not track.is_confirmed():
                continue

            track_id = track.track_id
            ltrb = track.to_ltrb()
            class_id = track.det_class if hasattr(track, 'det_class') else -1

            try:
                raw_score = getattr(track, 'det_conf', None)
                score = float(raw_score)
                if np.isnan(score) or score < 0.0 or score > 1.0:
                    self.get_logger().warn(f"[track_id {track.track_id}] 비정상 score 값 감지: {score}, fallback to 0.0")
                    score = 0.0
            except Exception as e:
                self.get_logger().warn(f"[track_id {track.track_id}] det_conf 처리 중 예외: {e}, fallback to 0.0")
                score = 0.0

            # det_class 처리
            try:
                class_id = int(getattr(track, 'det_class', -1))
            except Exception as e:
                self.get_logger().warn(f"[track_id {track.track_id}] det_class 처리 중 예외: {e}, fallback to -1")
                class_id = -1
            ###상황	처리 결과 det_conf가 None, NaN, 음수	score = 0.0, det_class가 없거나 타입이 이상함	class_id = -1
            
            # raw_score = getattr(track, 'det_conf', 1.0)
            # score = float(raw_score) if raw_score is not None else 0.0
            #track 객체에 det_class 속성이 존재하면 그 값을 사용하고, 없으면 -1로 처리하라

            cx = (ltrb[0] + ltrb[2]) / 2
            cy = (ltrb[1] + ltrb[3]) / 2
            cz = self._get_depth(int(cx), int(cy))

            if cz is None or np.isnan(cz) or cz <= 0:
                cz = 0.0

            detection = Detection2D()
            detection.bbox.center.position.x = cx
            detection.bbox.center.position.y = cy
            detection.bbox.size_x = ltrb[2] - ltrb[0]
            detection.bbox.size_y = ltrb[3] - ltrb[1]

            hypothesis = ObjectHypothesisWithPose()
            hypothesis.hypothesis.class_id = str(class_id)
            hypothesis.hypothesis.score = score  # 또는 score 추적 값에 따라 조절 가능

            detection.results.append(hypothesis)
            detection_array.detections.append(detection)

            x3d, y3d, z3d = self.tracking_pixel_to_camera_coords(cx, cy, cz)
            positions_data.extend([
                float(track_id),
                float(class_id),
                float(x3d),
                float(y3d),
                float(z3d)
            ])

        # 발행
        self.detection_pub.publish(detection_array)
        positions_msg.data = positions_data
        self.position_pub.publish(positions_msg)



        #방금추가함------------------------------------------------------
        results_general = self.model_general.model(frame)

        detection_array_general = Detection2DArray()
        detection_array_general.header.stamp = self.get_clock().now().to_msg()
        detection_array_general.header.frame_id = "camera_frame"

        for box, score, cls in zip(
            results_general[0].boxes.xyxy.tolist(),
            results_general[0].boxes.conf.tolist(),
            results_general[0].boxes.cls.tolist(),
        ):
            if score < 0.5:  # 일반 모델 기준 점수
                continue

            detection = Detection2D()
            detection.bbox.center.position.x = (box[0] + box[2]) / 2
            detection.bbox.center.position.y = (box[1] + box[3]) / 2
            detection.bbox.size_x = box[2] - box[0]
            detection.bbox.size_y = box[3] - box[1]

            hypothesis = ObjectHypothesisWithPose()
            hypothesis.hypothesis.class_id = str(int(cls))
            hypothesis.hypothesis.score = score

            detection.results.append(hypothesis)
            detection_array_general.detections.append(detection)

        # 발행
        self.general_detection_pub.publish(detection_array_general)
        #방금추가함------------------------------------------------------

############################################


    
    def handle_get_depth(self, request, response):
        self.get_logger().info(f"Received request: {request}")
        coords = self._compute_position(request.target)

        response.depth_position=[float(x) for x in coords]

        return response

    def _compute_position(self, target):
        """이미지를 처리해 객체의 카메라 좌표를 계산합니다."""
        rclpy.spin_once(self.img_node)
        box, score = self.model_scalpel_tip.tracking_get_best_detection(self.img_node, target)#이거 맞냐?
        if box is None or score is None:
            self.get_logger().warn("컴퓨트 포지션 함수 No detection found.")
            return 0.0, 0.0, 0.0

        self.get_logger().info(f"Detection: box={box}, score={score}")
        cx, cy = map(int, [(box[0] + box[2]) / 2, (box[1] + box[3]) / 2])
        cz = self._get_depth(cx, cy)
        if cz is None:
            self.get_logger().warn("Depth out of range.")
            return 0.0, 0.0, 0.0

        return self.tracking_pixel_to_camera_coords(cx, cy, cz) 

    def _get_depth(self, x, y):
        depth_frame = self.img_node.get_depth_frame()
        if depth_frame is None:
            return None
        h, w = depth_frame.shape
        if 0 <= y < h and 0 <= x < w:
            return float(depth_frame[int(y), int(x)])
        else:
            return None
    def _wait_for_valid_data(self, getter, description):
        data = getter()
        while data is None or (isinstance(data, np.ndarray) and not data.any()):
            rclpy.spin_once(self.img_node)
            self.get_logger().info(f"Retry getting {description}.")
            data = getter()
        return data

    def tracking_pixel_to_camera_coords(self, x, y, z):
        fx = self.intrinsics['fx']
        fy = self.intrinsics['fy']
        ppx = self.intrinsics['ppx']
        ppy = self.intrinsics['ppy']
        return (x - ppx) * z / fx,(y - ppy) * z / fy,z


def main(args=None):
    rclpy.init(args=args)
    node = ObjectTrackingNode()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()