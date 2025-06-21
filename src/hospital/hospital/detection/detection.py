import cv2
import os
import numpy as np
import rclpy
from rclpy.node import Node
from typing import Any, Callable, Optional, Tuple
from datetime import datetime

from ament_index_python.packages import get_package_share_directory
# from od_msg.srv import SrvDepthPosition
from hospital_interfaces.srv import DepthAnglePos
from hospital.detection.realsense import ImgNode
from hospital.detection.yolo import YoloModel

from vision_msgs.msg import Detection2DArray, Detection2D, ObjectHypothesisWithPose, ObjectHypothesis
from vision_msgs.msg import BoundingBox2D, Pose2D, Point2D
from std_msgs.msg import Header
from geometry_msgs.msg import Point

PACKAGE_NAME = 'hospital'
PACKAGE_PATH = get_package_share_directory(PACKAGE_NAME)


class ObjectDetectionNode(Node):
    def __init__(self, model_name='yolo'):
        super().__init__('object_detection_node')
        self.img_node = ImgNode()
        self.model = self._load_model(model_name)
        self.intrinsics = self._wait_for_valid_data(
            self.img_node.get_camera_intrinsic, "camera intrinsics"
        )

        self.detection_pub = self.create_publisher(Detection2DArray, 'detection_result', 10)
        
        self.target_pub = self.create_publisher(Point, '/target_pose', 10)

        # 서비스 서버 생성 || 클라이언트 : robot_control노드
        self.create_service(
            DepthAnglePos,
            '/get_3d_position',
            self.handle_get_depth
        )
        self.get_logger().info("ObjectDetectionNode initialized.")

    def _load_model(self, name):
        """모델 이름에 따라 인스턴스를 반환합니다."""
        if name.lower() == 'yolo':
            return YoloModel()
        raise ValueError(f"Unsupported model: {name}")

    def handle_get_depth(self, request, response):
        """클라이언트 요청을 처리해 3D 좌표를 반환합니다."""
        self.get_logger().info(f"Received request: {request}")
        coords,theta = self._compute_position(request.target)
        #_pixel_to_camera_coords에서 
        #return ((x - ppx) * z / fx,(y - ppy) * z / fy,z,theta)
        response.depth_position = [float(x) for x in coords]
        try:
            if theta is not None:
                response.theta = float(theta)
            else:
                response.theta = 0.0  # 또는 적절한 기본값
            # response.theta = theta  # 이거를 어떻게 보낼지
        except Exception as e:
            print(f'예외발생:{e}')
        self.get_logger().info(f"==============================")
        self.get_logger().info(f"sned respon: {request}")
        self.get_logger().info(f"==============================")
        return response

    def _compute_position(self, target):
        """이미지를 처리해 객체의 카메라 좌표를 계산합니다.
        robot_control에서 찾아 달라오는데 카메라에 없으면  여기서 회전??
        어떤식으로?
        큰일났다
        모션 컨트롤 매니저 만들어야 하나
        만들면 서비스로 찾아달라 요청을 보내나?
        도구 놔두는 스페이스 좌표 지정하면 
        서비스로 모션 컨트롤 매니저한테 요청보내고 도구 스페이스 쳐다보게
        그냥 마구잡이로 회전하며 찾는건 힘들거 같아요
        """

        rclpy.spin_once(self.img_node)  # 해당 노드를 단 한 번만 이벤트 처리 시도합니다.
        
        # box, score, frame = self.model.get_best_detection(self,img_node, target)
        box, score = self.model.get_best_detection(self.img_node, target)
        frame = self.img_node.get_color_frame()



        if box is None or score is None:
            self.get_logger().warn("===========================")
            self.get_logger().warn("box is None")
            self.get_logger().warn("===========================")
            return (0.0, 0.0, 0.0), 0.0

        self.get_logger().info(f"Detection: box={box}, score={score}")
        # ````박스 안에서 검은색 부분 추출해서 x,y잡게 ````
        cx, cy = map(int, [(box[0] + box[2]) / 2, (box[1] + box[3]) / 2])
        if frame is None:
            self.get_logger().warn("[_compute_position 함수] : 이미지 프레임 못받음~~~~~~")
        else:
            angle, direction = self._get_black_line_angle(frame, box,target)
            #angle은 검출 못하면 None
            #direction은 뺄까?
            if angle is None:
                self.get_logger().warn("[_compute_position 함수] : angle 못받음~~~~~~")
                # 여기까지는  들어ㅇ모
            else:
                self.get_logger().info(
                    f"Black line angle: {angle:.2f}° {direction}")
                # 각도 정보 발행
                #angle은 각도


        cz = self._get_depth(cx, cy)
        if cz is None:
            self.get_logger().warn("====================================")
            self.get_logger().warn("Depth out of range.")
            self.get_logger().warn("[_compute_position함수]")
            self.get_logger().warn("====================================")
            return (0.0, 0.0, 0.0), 0.0
        
        try: #cx_black, cy_black 전에꺼 가져다 쓰는 늒미인데
            #윤관선 검출은 실패 했지만 cz_black성공
            #첫번째 호스 잡기는 성공, 상처부위로 못가는 이유는?
            #AssertionError: The 'theta' field must be of type 'float'
            cz_black = self._get_depth(int(self.cx_black), int(self.cy_black))

            self.get_logger().info(f"cx_black , cy_black : {self.cx_black}, {self.cy_black}")
            self.get_logger().info(f"테이프 중앙 검출 성공 : cz_black = {cz_black}")
            #중앙값 좌표 반환
        #---------------Point메시지 구성----------------------#
            msg = Point()
            msg.x = self.cx_black #Point데이터 형식 확인
            msg.y = self.cy_black
            msg.z = 0.0  # 안 쓰면 0으로
            self.target_pub.publish(msg)

        except:
            cz_black = 0.0
            self.get_logger().warn("테이프 중앙 검출 실패 : cz_black = 0.0")

         # ---------------------- Detection2D 메시지 구성 ---------------------- #
        detection_array = Detection2DArray()
        detection_array.header = Header()
        detection_array.header.stamp = self.get_clock().now().to_msg()
        detection_array.header.frame_id = "camera_frame" 

        detection = Detection2D()
        detection.bbox.center.position.x = float(cx)
        detection.bbox.center.position.y = float(cy)
        detection.bbox.size_x = float(box[2] - box[0])
        detection.bbox.size_y = float(box[3] - box[1])

        hypothesis = ObjectHypothesisWithPose()
        hypothesis.hypothesis.class_id = target
        hypothesis.hypothesis.score = float(score)

        detection.results.append(hypothesis)
        detection_array.detections.append(detection)

        self.detection_pub.publish(detection_array)
        self.get_logger().info(f"Published detection result for '{target}'")

                
        if cz_black == 0.0 or target == "hands":  # 검은선이 없으면 비박스 중심값의 좌표 리턴, 검은선 있으면 검은선 중심점 좌표 리턴
            return self._pixel_to_camera_coords(cx, cy, cz,0.0)
        else:
            return self._pixel_to_camera_coords(self.cx_black,self.cy_black, cz_black, angle)
    
    #################각도 처리용 함수 부분
    def _get_black_line_angle(self, frame, bbox,target):
        """바운딩 박스 내에서 검은 선의 기울기를 계산"""
        # 바운딩 박스 영역 추출
        x1, y1, x2, y2 = map(int, bbox)

        self.cx_black=None #None으로 초기화
        self.cy_black=None

        roi = frame[y1:y2, x1:x2]
        
        if roi.size == 0:
            return None, None

        # 영상 밝기 보정 -scalpel일때
        print(target)
        print(type(target))
        if target=="scalpel":
            roi = cv2.convertScaleAbs(roi, alpha=1.0, beta=30)

       
        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        _, mask = cv2.threshold(gray, 80, 255, cv2.THRESH_BINARY_INV)
        # hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
        # lower_black = np.array([0, 0, 0])# 검정색 범위 정의 (채도 낮고 명도 낮은 영역)
        # upper_black = np.array([180, 255, 50])  # V가 낮은 애들만
        #이거를 좀 범위를 늘리기?
        # mask = cv2.inRange(hsv, lower_black, upper_black)# 마스크 생성


        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        #    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        angle = None
        direction = "None"

        if not contours:
            self.get_logger().warn("[_get_black_line_angle] 함수 윤곽선 검출 실패")
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

            # mask 저장
            cv2.imwrite(f"/home/bako98/test_ws/asd/mask_fail_{timestamp}.jpg", mask)

            # 객체 검출 박스 저장 (실제 눈으로 확인할 수 있는 이미지)
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
            cv2.imwrite(f"/home/bako98/test_ws/asd/black_fail_{timestamp}.jpg",frame)
            # 2. ROI 저장
            cv2.imwrite(f"/home/bako98/test_ws/asd/roi_fail_{timestamp}.jpg", roi)
    
            # # 전체 frame 위에 bbox 시각화해서 저장
            # debug_frame = frame.copy()
            # x1, y1, x2, y2 = map(int, bbox)
            # cv2.rectangle(debug_frame, (x1, y1), (x2, y2), (0, 0, 255), 2)  # 빨간색 박스
            # cv2.imwrite(f"/home/bako98/test_ws/flask_hospital/asd/frame_fail_{timestamp}.jpg", debug_frame)
            white_pixels = np.sum(mask == 255)
            self.get_logger().info(f"[DEBUG] mask 흰 픽셀 수 (255): {white_pixels}")

            self.get_logger().info(f"[DEBUG] 저장된 실패 이미지: mask / roi / frame_fail")
            
            return None, None
            
        else: #윤곽선 검출되었을때
            largest = max(contours, key=cv2.contourArea)
            #가장 큰 윤곽선(max)을 골라서 검은 선을 대표하는 contour로 사용

            if cv2.contourArea(largest) > 40:#
                rect = cv2.minAreaRect(largest) #rect = ((cx, cy), (w, h), θ)
                #해당 contour를 완전히 감쌀 수 있는 가장 작은 회전된 사각형을 구함

                box = cv2.boxPoints(rect)
                #rect 정보를 바탕으로, 실제 회전된 사각형의 4개 꼭짓점 좌표 (x, y) 를 계산

                box = np.int32(box)
                self.cx_black = rect[0][0] + x1  # rect[0][0] 자체는 bbox에서의 검은 중심점 좌표임 따라서 bbox의 x1 값을 더해줘야함
                self.cy_black = rect[0][1] + y1
                
                width, height = rect[1]
                angle_raw = rect[2]
                
                if width < height:
                    corrected_angle = angle_raw - 90
                else:
                    corrected_angle = angle_raw

                angle = corrected_angle
                print(angle)
                if angle > 10:
                    direction = " CW"
                elif angle < -10:
                    direction = " CCW"
                else:
                    direction = "수평"
 # =========================== 시각화 및 저장 ========= #
                vis_frame = frame.copy()

                # bbox 표시 (초록색)
                cv2.rectangle(vis_frame, (x1, y1), (x2, y2), (0, 255, 0), 2)

                # 검은 선 사각형 (파란색)
                shifted_box = box + np.array([x1, y1])
                cv2.drawContours(vis_frame, [shifted_box], 0, (255, 0, 0), 2)

                # 중앙점 흰 점
                cv2.circle(vis_frame, (int(self.cx_black), int(self.cy_black)), 4, (255, 255, 255), -1)
                # ===== 검은 선 기울기 방향 선 시각화 추가 =====

                length = 1000  # 선 길이
                rad = np.deg2rad(angle)  # 각도를 라디안으로 변환
                dx = int(np.cos(rad) * length)
                dy = int(np.sin(rad) * length)
                pt1 = (int(self.cx_black - dx), int(self.cy_black - dy))
                pt2 = (int(self.cx_black + dx), int(self.cy_black + dy))
                cv2.line(vis_frame, pt1, pt2, (0, 0, 255), 2)  # 빨간색 선으로 기울기 표시

            
                os.makedirs("/home/bako98/test_ws/asd/target_result_img", exist_ok=True)
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"/home/bako98/test_ws/asd/target_detect_{timestamp}.jpg"
                cv2.imwrite(filename, vis_frame)
                self.get_logger().info(f"Detection result image saved: {filename}")

                # 시각화 (디버깅용)
                # cv2.drawContours(roi, [box], 0, (0, 255, 0), 2)
                # cv2.putText(roi, f"{angle:.2f}° {direction}", (10, 30),
                #             cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)
                # cv2.imshow("ROI Detection", roi)
                # cv2.waitKey(1)
            else:
                 self.get_logger().warn(f"임계값 넘는 라인 없음")

        return angle, direction #검출 없으면 None, "None"반환
###########################################

    def _get_depth(self, x, y):
        """픽셀 좌표의 depth 값을 안전하게 읽어옵니다."""
        frame = self._wait_for_valid_data(
            self.img_node.get_depth_frame, "depth frame")
        try:
            return frame[y, x]
        except IndexError:
            self.get_logger().warn(f"Coordinates ({x},{y}) out of range.")
            return None

    def _wait_for_valid_data(self, getter, description):
        """getter 함수가 유효한 데이터를 반환할 때까지 spin 하며 재시도합니다."""
        data = getter()
        while data is None or (isinstance(data, np.ndarray) and not data.any()):
            rclpy.spin_once(self.img_node)
            self.get_logger().info(f"Retry getting {description}.")
            data = getter()
        return data

    def _pixel_to_camera_coords(self, x, y, z, theta):
        """픽셀 좌표와 intrinsics를 이용해 카메라 좌표계로 변환합니다."""
        fx = self.intrinsics['fx']
        fy = self.intrinsics['fy']
        ppx = self.intrinsics['ppx']
        ppy = self.intrinsics['ppy']
        self.get_logger().info(f"좌표값  x :{(x - ppx) * z / fx}, y :{(y - ppy) * z / fy}, z : {z}, theta :{theta}")
        return (((x - ppx) * z / fx, (y - ppy) * z / fy, z),theta)


def main(args=None):
    rclpy.init(args=args)
    node = ObjectDetectionNode()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
