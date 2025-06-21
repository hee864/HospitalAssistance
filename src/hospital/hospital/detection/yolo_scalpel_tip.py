# detection.yolo_scalpel_tip.py
########## YoloModel ##########
import os
import json
import time
from collections import Counter

import rclpy
from ament_index_python.packages import get_package_share_directory
from ultralytics import YOLO
import numpy as np


PACKAGE_NAME = "hospital"
PACKAGE_PATH = get_package_share_directory(PACKAGE_NAME)

# YOLO_MODEL_FILENAME = "yolov8n_tools_0122.pt"
YOLO_MODEL_FILENAME = "best_scalpel_tip.pt"
YOLO_CLASS_NAME_JSON = "class_name_tool.json"

YOLO_MODEL_PATH = os.path.join(PACKAGE_PATH, "resource", YOLO_MODEL_FILENAME)
YOLO_JSON_PATH = os.path.join(PACKAGE_PATH, "resource", YOLO_CLASS_NAME_JSON)
#########scalpel_tip에서 가져오는 것은 tracking_붙임

class YoloModel_Scalpel_Tip:
    def __init__(self): #device 삭제 원랴는 없는데 노트북 하고 연결 후 확인
        # self.device = device
        self.model = YOLO(YOLO_MODEL_PATH)  
        # self.model.to(self.device)  # 장치 지정
        with open(YOLO_JSON_PATH, "r", encoding="utf-8") as file:
            class_dict = json.load(file)
            self.reversed_class_dict = {v: int(k) for k, v in class_dict.items()}

    def tracking_get_frames(self, img_node, duration=0.2):#수정 1-> 0.2
        """get frames while target_time
        1초 동안 RGB 카메라 프레임들을 모아서 리스트로 반환하는 함수
        """
        end_time = time.time() + duration
        frames = {}

        while time.time() < end_time:
            rclpy.spin_once(img_node) 
            frame = img_node.get_color_frame()
            stamp = img_node.get_color_frame_stamp()
            if frame is not None:
                frames[stamp] = frame
            time.sleep(0.01)

        if not frames:
            print("No frames captured in %.2f seconds", duration)

        print("%d frames captured", len(frames))
        return list(frames.values())

    def tracking_get_best_detection(self, img_node, target):
        """
        여러 장의 카메라 프레임에서 target 객체를 YOLO로 감지한 뒤, 가장 신뢰도 높은 탐지 결과를 반환하는 함수입니다.
        """
        # rclpy.spin_once(img_node)
        frames = self.tracking_get_frames(img_node)
        if not frames:  # Check if frames are empty
            return None

        results = self.model(frames, verbose=False)
        print("classes: ")
        print(results[0].names)
        detections = self.tracking_aggregate_detections(results)#프레임마다 나온 감지 결과들을 통합 (중복 제거, 평균 처리 등)
        label_id = self.reversed_class_dict[target]
        #대상 클래스 이름을 숫자 ID로 바꾸고, 그 label에 해당하는 감지만 필터링
        print("label_id: ", label_id)
        print("detections: ", detections)

        ##여러 클래스가 감지되어도, 사용자가 지정한 target 클래스만 필터링해서, 
        # 그 중 최고 신뢰도 하나만 반환"**하는 방식입니다.
        matches = [d for d in detections if d["label"] == label_id]
        if not matches:
            print("No matches found for the target label.")
            return None, None
        best_det = max(matches, key=lambda x: x["score"])
        return best_det["box"], best_det["score"]

    def tracking_aggregate_detections(self, results, confidence_threshold=0.5, iou_threshold=0.5):
        """
        confidence_threshold=0.5 = score 50이상만 사용
        iou_threshold=0.5 박스가 50%이상 겹칠때만 같은 객체로 인식
        Fuse raw detection boxes across frames using IoU-based grouping
        and majority voting for robust final detections.
        여러 프레임에서 감지된 객체들 중 **겹치는 박스들(같은 물체로 추정)**을
        하나로 묶고, 평균을 내서 최종 감지 결과 리스트를 만드는 함수입니다.
        """
        raw = []
        for res in results:
            for box, score, label in zip(
                res.boxes.xyxy.tolist(),
                res.boxes.conf.tolist(),
                res.boxes.cls.tolist(),
            ):
                if score >= confidence_threshold:
                    raw.append({"box": box, "score": score, "label": int(label)})

        final = []
        used = [False] * len(raw)

        for i, det in enumerate(raw):
            if used[i]:
                continue
            group = [det]
            used[i] = True
            for j, other in enumerate(raw):
                if not used[j] and other["label"] == det["label"]:
                    if self.tracking_iou(det["box"], other["box"]) >= iou_threshold:
                        group.append(other)
                        used[j] = True

            boxes = np.array([g["box"] for g in group])
            scores = np.array([g["score"] for g in group])
            labels = [g["label"] for g in group]

            final.append(
                {
                    "box": boxes.mean(axis=0).tolist(),
                    "score": float(scores.mean()),
                    "label": Counter(labels).most_common(1)[0][0],
                }
            )

        return final

    def tracking_iou(self, box1, box2):
        """
        Compute Intersection over Union (IoU) between two boxes [x1, y1, x2, y2].
        두 박스 간의 IoU(Intersection over Union)를 계산해 얼마나 겹치는지 비율로 반환합니다.
        """
        x1, y1 = max(box1[0], box2[0]), max(box1[1], box2[1])
        x2, y2 = min(box1[2], box2[2]), min(box1[3], box2[3])
        inter = max(0.0, x2 - x1) * max(0.0, y2 - y1)
        area1 = (box1[2] - box1[0]) * (box1[3] - box1[1])
        area2 = (box2[2] - box2[0]) * (box2[3] - box2[1])
        union = area1 + area2 - inter
        return inter / union if union > 0 else 0.0
