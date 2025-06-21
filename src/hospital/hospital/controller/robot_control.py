import os
import time
import sys
# from tkinter import Image
from sensor_msgs.msg import Image  # ✅ ROS 2 이미지 메시지 타입

from scipy.spatial.transform import Rotation
import numpy as np
from sympy import Point
import rclpy
from rclpy.node import Node
import DR_init

# from od_msg.srv import SrvDepthPosition
from hospital_interfaces.srv import DepthAnglePos
from hospital_interfaces.srv import ObjectTarget
# from std_srvs.srv import Trigger
from ament_index_python.packages import get_package_share_directory
from hospital.controller.onrobot import RG
import copy
from std_srvs.srv import SetBool
from collections import deque  # 맨 위에 추가
package_path = get_package_share_directory("hospital")

from gtts import gTTS
from playsound import playsound
import uuid
# for single robot
ROBOT_ID = "dsr01"
ROBOT_MODEL = "m0609"
VELOCITY, ACC = 60, 60
# BUCKET_POS = [445.5, -242.6, 174.4, 156.4, 180.0, -112.5]
GRIPPER_NAME = "rg2"
TOOLCHARGER_IP = "192.168.1.1"
TOOLCHARGER_PORT = "502"
DEPTH_OFFSET = -5.0
MIN_DEPTH = 2.0


DR_init.__dsr__id = ROBOT_ID
DR_init.__dsr__model = ROBOT_MODEL

rclpy.init()
dsr_node = rclpy.create_node("robot_control_node", namespace=ROBOT_ID)
DR_init.__dsr__node = dsr_node

try:
    from DSR_ROBOT2 import movej, movel, get_current_posx, mwait, trans,DR_MV_MOD_ABS,DR_MV_MOD_REL
except ImportError as e:
    print(f"Error importing DSR_ROBOT2: {e}")
    sys.exit()

########### Gripper Setup. Do not modify this area ############

gripper = RG(GRIPPER_NAME, TOOLCHARGER_IP, TOOLCHARGER_PORT)


########### Robot Controller ############



class RobotController(Node):
    def __init__(self):
        super().__init__("pick_and_place")
        self.init_robot()
        self.robot_control_running=False
        self.command_stack = []

        #서비스 클라이언트 || 서버 = detection노드
        self.get_position_client = self.create_client( DepthAnglePos, "/get_3d_position")
        while not self.get_position_client.wait_for_service(timeout_sec=3.0):
            self.get_logger().info("Waiting for get_depth_position service...")
        self.get_position_request = DepthAnglePos.Request()

        #서비스 클라이언트 || 서버 = get_keyword노드
        self.get_keyword_client = self.create_client(ObjectTarget, "/get_keyword")
        while not self.get_keyword_client.wait_for_service(timeout_sec=3.0):
            self.get_logger().info("Waiting for get_keyword service...")
        self.get_keyword_request = ObjectTarget.Request()

        #서비스 클라이언트 || 서버 = tracking노드
        self.tracking_trigger_client = self.create_client(SetBool, "/tracking_trigger")
        while not self.tracking_trigger_client.wait_for_service(timeout_sec=3.0):
            self.get_logger().info("Waiting for get_keyword service...")
        self.tracking_trigger_request = SetBool.Request()


    def get_robot_pose_matrix(self, x, y, z, rx, ry, rz):
        R = Rotation.from_euler("ZYZ", [rx, ry, rz], degrees=True).as_matrix()
        T = np.eye(4)
        T[:3, :3] = R
        T[:3, 3] = [x, y, z]
        return T

    def transform_to_base(self, camera_coords, gripper2cam_path, robot_pos):
        """
        Converts 3D coordinates from the camera coordinate system
        to the robot's base coordinate system.
        """
        gripper2cam = np.load(gripper2cam_path)
        coord = np.append(np.array(camera_coords), 1)  # Homogeneous coordinate

        x, y, z, rx, ry, rz = robot_pos
        base2gripper = self.get_robot_pose_matrix(x, y, z, rx, ry, rz)

        # 좌표 변환 (그리퍼 → 베이스)
        base2cam = base2gripper @ gripper2cam
        td_coord = np.dot(base2cam, coord)

        return td_coord[:3]
    
    def robot_control(self):
        ###여기서 스택에 명령모아서 마지막 명령이 셕션 일때만 셕션 시작할게 명령 들어가게
        #겟 키워드에서 할까
        
        self.flag_object="" 
        self.flag_target=""
        # target_list = []
        self.get_logger().info("call get_keyword service")
        self.get_logger().info("say 'Hello Rokey' and speak what you want to pick up")
        get_keyword_future = self.get_keyword_client.call_async(self.get_keyword_request)
        rclpy.spin_until_future_complete(self, get_keyword_future)

        # self.init_robot()

        
        if not get_keyword_future.result().success:
            self.get_logger().warn(f"{get_keyword_future.result().message}")
           

        # get_keyword_result = get_keyword_future.result()

        # target_list = get_keyword_result.message.split()
        service_response_object = get_keyword_future.result().object
        service_response_target = get_keyword_future.result().target
        service_response_command = get_keyword_future.result().commands #tracking_stop, tracking_start옴
        print("================================================================================")
        print(f"[node : robot_control] receive get_keyword service : {service_response_object},{service_response_target}")
        print("=================================================================================")

        if service_response_command=="tracking_start":
            # self.command_stack.append("tracking_start") #트래킹 예외 처리용 리스트
            self.tracking_trigger_request.data = True  # 꼭 True로 설정
            tracking_trigger_future = self.tracking_trigger_client.call_async(self.tracking_trigger_request)
            rclpy.spin_until_future_complete(self, tracking_trigger_future)

            if not tracking_trigger_future.result().success:
                self.get_logger().warn(f"{tracking_trigger_future.result().message}")
            else:
                print("서비스 요청 보내기 완료 : 트래킹 시작")
            #트래킹 시작 요청 보냄
        
        if service_response_command=="tracking_stop":
                # if self.command_stack[-1] !="tracking_start": #마지막 명령이 트래킹 시작일때만 요청 보내게 
                #     print("트래킹 종료 할 수 없음")
                #     return
                
                self.tracking_trigger_request.data = False  #종료 요청
                tracking_trigger_future = self.tracking_trigger_client.call_async(self.tracking_trigger_request)
                rclpy.spin_until_future_complete(self, tracking_trigger_future)

                if not tracking_trigger_future.result().success:
                        self.get_logger().warn(f"{tracking_trigger_future.result().message}")
                else:
                    print("서비스 요청 보내기 완료 : 트래킹 종료")
                    #서비스 요청 보냄 트래킹 종료 요청
                    print("트래킹 끝난 이후 원래 위치 가기 시작")
                    suction_ready = [46.23, 30.76, 24.18, -2.47, 123.49, 46.37] # 잡기 위한 위치 
                    movej(suction_ready, vel=VELOCITY, acc=ACC,mod=DR_MV_MOD_ABS)
                    mwait()
                    movel([-10,0,-362,0,0,0],vel=VELOCITY,acc=ACC,mod=DR_MV_MOD_REL) # 수정히ㅏㅁ
                    mwait()
                    gripper.open_gripper()
                    mwait()
                    movel([10,0,362,0,0,0],vel=VELOCITY,acc=ACC,mod=DR_MV_MOD_REL)
                    mwait()
                    print("홈위치로 이동")
                    self.init_robot()

                    return 
                                
            
        if service_response_object=="suction":
            print('=============')
            print('=셕션 초기 수술대로 이동====')
            print('=============')
            # 1. suction 초기 위치로 이동
            suction_ready = [46.23, 30.76, 24.18, -2.47, 123.49, 46.37] # 잡기 위한 위치 
            # movej(suction_ready, vel=VELOCITY, acc=ACC,mod=DR)
            movej(suction_ready, vel=VELOCITY, acc=ACC,mod=DR_MV_MOD_ABS)

            mwait()

            # 2. 상대적으로 z -362 하강
        
            movel([0,0,-392,0,0,0],vel=VELOCITY,acc=ACC,mod=DR_MV_MOD_REL)
            mwait()

            # 3. 그리퍼 닫기
            gripper.close_gripper()
            while gripper.get_status()[0]:
                time.sleep(0.5)
            mwait()

            

            # 4. 상대적으로 z +362 상승
            
            movel([0,0,392,0,0,0],vel=VELOCITY,acc=ACC,mod=DR_MV_MOD_REL)
            mwait()

            # movel(suction_up, vel=VELOCITY, acc=ACC,mod=0)
            # mwait()

            # 5. 수술대 근처로 이동
            table_pos = [15.19, 13.06, 40.36, -2.47, 110.61, 111.84] #수술대 위치 
            movej(table_pos, vel=VELOCITY, acc=ACC,mod=0)
            mwait()
            print("=========scar 위치 받아서 그곳으로 이동=========")
            print("==========calibration flag 세우기====== ")
            self.flag_object="suction" 
            self.flag_target="scar"
            print(f'flag_object={self.flag_object},flag_target={self.flag_target}')

            print(f"{service_response_target}위치로 이동 진입")     
            print('target 좌표 받아오기 ')         
            target_pos,target_theta=self.get_target_pos(service_response_target)
            if target_pos is None:
                self.get_logger().warn("No target position")
            else:
                self.get_logger().info(f'target_pos={target_pos}')
                print('target_pos로 이동 시작')
                self.get_logger().info(f"target position: {target_pos} target theta:{target_theta}")
                self.pick_and_place_target(target_pos,target_theta)

                print("scar 위치로 이동하기 끝")
                #여기서 서비스 요청을 보내고 응답 받으면 아래 부분 실행시키는 데 해결방법
    

                # print("트래킹 끝난 이후 원래 위치 가기 시작")
                # suction_ready = [46.23, 30.76, 24.18, -2.47, 123.49, 46.37] # 잡기 위한 위치 
                # movej(suction_ready, vel=VELOCITY, acc=ACC,mod=DR_MV_MOD_ABS)
                # mwait()
                # movel([0,0,-362,0,0,0],vel=VELOCITY,acc=ACC,mod=DR_MV_MOD_REL)
                # mwait()
                # gripper.open_gripper()
                # mwait()
                # movel([0,0,362,0,0,0],vel=VELOCITY,acc=ACC,mod=DR_MV_MOD_REL)
                # mwait()
                # print("홈위치로 이동")
                # self.init_robot()
            

        elif service_response_object in ["scalpel", "spray"]:

                            
                

            print(f"{service_response_object}위치 받아오기 진입")
            object_pos,object_theta = self.get_target_pos(service_response_object)

            
            if service_response_object=="spray":
                    spray_return_pos = copy.deepcopy(object_pos)
                    spray_return_theta = object_theta

            if service_response_object=="scalpel":
                    scalpel_return_pos = copy.deepcopy(object_pos)
                    scalpel_return_theta = object_theta


            
                #다시 받아오기 추가 


            if object_pos is None:
                self.get_logger().warn("No object position--retry getting object detection")
                print("====홈 위치로 가기======= ")
                self.init_robot()
                gripper.open_gripper()
                return
                
            else: #object_pos 가 있음
                try:
                    object_pos[2]=54 #잡는 물체는 바닥으로 하기 
                    print('object_pos로 이동 시작')
                    self.get_logger().info(f"target position: {object_pos} target theta:{object_theta}")
                    object_pos[5]+=object_theta
                    self.pick_and_place_target(object_pos,object_theta)
                    print("그리퍼 잡기 시작")
                except:
                    pass

                
                

            # 1회만 명령 전송
            if service_response_object=="scalpel":
                gripper.close_gripper()
            elif service_response_object=="spray":
                gripper.move_gripper(630)

            # 동작이 끝날 때까지 busy(0번 bit)가 꺼질 때까지 대기
            while gripper.get_status()[0] == 1:
                print("[wait] Gripper busy...")
                time.sleep(0.3)

            # 잡기 성공 여부 확인
            status = gripper.get_status()
            if status[1] == 1:
                print("물체 감지됨. 성공!")
            else:
                print("물체 감지 실패. 재시도")

                # 다시 열고
                gripper.open_gripper()

                while gripper.get_status()[0] == 1:
                    print("[wait] Gripper busy (opening)...")
                    time.sleep(0.3)

                time.sleep(0.3)  # 여유 시간
                # 다시 닫기 시도
                gripper.move_gripper(630)

                while gripper.get_status()[0] == 1:
                    print("[wait] Gripper busy (retry gripping)...")
                    time.sleep(0.3)
                    

                # 두 번째 상태 확인
                status = gripper.get_status()
                if status[1] == 1:
                    print("두 번째 시도에서 물체 감지 성공!")
                else:
                    print(" 두 번째 시도에서도 실패. 처리 필요")


                text="물체를 제대로 잡지 못했어요. 다시 말씀해주세요"
                try:
                    tmp_path=f'tmp/{uuid.uuid4()}.mp3'
                    gTTS(text=text,lang='ko').save(tmp_path)
                    playsound(tmp_path)
                    os.remove(tmp_path)
                except:
                    pass
                    

                mwait()
                print("그리퍼 잡기 끝")
                self.init_robot()
                return 

            print("=작업공간으로 이동후 대기====")
            JReady2=[15.19, 13.06, 40.36, -2.47, 110.61, 111.84] # 수술대 좌표
            movej(JReady2, vel=VELOCITY, acc=ACC, mod=DR_MV_MOD_ABS)
            time.sleep(3.0)
            mwait()


            print(f"{service_response_target}위치로 이동 진입")     
            print('target 좌표 받아오기 ')         
            target_pos,target_theta=self.get_target_pos(service_response_target)
            if target_pos is None: #타겟 포즈 없을 떈
                #다시 수술대 위치로 가서
                if service_response_target=="hands":
                    table_pos = [15.19, 13.06, 40.36, -2.47, 110.61, 111.84] #수술대 위치
                elif service_response_target=="scar":
                    table_pos = [15.19, 13.06, 40.36, -2.47, 110.61, 111.84] #수술대 위치
                movej(table_pos, vel=VELOCITY, acc=ACC,mod=0)
                #상처 재탐색
                target_pos,target_theta=self.get_target_pos(service_response_target)
                #상처가 탐색되면
                if target_pos: #손 ,상처 

                    #손이면 내려놓고
                    self.get_logger().info(f'target_pos{target_pos}')
                    self.get_logger().info(f'{service_response_target}으로 이동')
                    self.get_logger().info(f"target position: {target_pos} target theta:{target_theta}")
                    target_pos[2]+=40
                    self.pick_and_place_target(target_pos,target_theta)
                    print(f"{service_response_target}_위치로 이동하기 끝")
                    if service_response_target=="hands":

                        print("손에 내려 놓기")
                        
                        gripper.open_gripper()


                        self.init_robot()
                        return

                    elif service_response_target=="scar":
                        
                        print('분사 시작')
                        for i in range(3):
                            gripper.move_gripper(650)
                            time.sleep(0.3)
                            
                            gripper.move_gripper(700)
                            status=gripper.get_status()[1]
                            print('그리퍼 출력값=',status)
                            time.sleep(0.3)
                            mwait()
                        print('분사 끝')
                        self.get_logger().info("Returning to spray pickup position and placing it.")
                        return_pos = copy.deepcopy(spray_return_pos)
                        return_pos[5] += spray_return_theta
                        return_pos[2] += 150  # 위에서 접근
                        movel(return_pos, vel=VELOCITY, acc=ACC)
                        mwait()

                        return_pos[2] -= 150  # 내려서 놓기
                        movel(return_pos, vel=VELOCITY, acc=ACC)
                        mwait()

                        gripper.open_gripper()
                        mwait()
                        self.init_robot()
                        return


                #scar위치로 가기
                else:#target pos가 또 감지가 안됐을 때 
                    self.get_logger().warn("No target position")
                    print('다시 칼 원래 위치로 돌아가기')
                    if service_response_object == "spray":
                        return_pos = copy.deepcopy(spray_return_pos)
                        return_pos[5] += spray_return_theta
                    elif service_response_object == "scalpel":
                        return_pos = copy.deepcopy(scalpel_return_pos)
                        return_pos[5] += scalpel_return_theta
                    else:
                        print(f"타켓 포즈 감지 안되고 옵젝 이상할때 옵젝, 타겟 : {service_response_object},{service_response_target}")    
                        self.init_robot()
                        return
                    
                    return_pos[2] += 150  # 위에서 접근
                    movel(return_pos, vel=VELOCITY, acc=ACC)
                    mwait()

                    return_pos[2] -= 150  # 내려서 놓기
                    movel(return_pos, vel=VELOCITY, acc=ACC)
                    mwait()

                    gripper.open_gripper()
                    mwait()
                    self.init_robot()
                    return
                # self.get_logger().warn("No target position")
            


            else: #타겟 포즈 있을 경우
                self.get_logger().info(f'target_pos={target_pos}')
                print('target_pos로 이동 시작')
                self.get_logger().info(f"target position: {target_pos} target theta:{target_theta}")
                target_pos[2] += 40
                self.pick_and_place_target(target_pos,target_theta)
                mwait()
                if service_response_target=="hands":
                    print("손에 내려 놓기")
                    
                    gripper.open_gripper()
                    

                    self.init_robot()
                    return

                elif service_response_target=="scar":
                    
                    print('분사 시작')
                    for i in range(3):
                        gripper.move_gripper(650)
                        time.sleep(0.3)
                        
                        gripper.move_gripper(700)
                        status=gripper.get_status()[1]
                        print('그리퍼 출력값=',status)
                        time.sleep(0.3)
                        mwait()
                    print('분사 끝')
                    self.get_logger().info("Returning to spray pickup position and placing it.")
                    return_pos = copy.deepcopy(spray_return_pos)
                    return_pos[5] += spray_return_theta
                    return_pos[2] += 150  # 위에서 접근
                    movel(return_pos, vel=VELOCITY, acc=ACC)
                    mwait()

                    return_pos[2] -= 150  # 내려서 놓기
                    movel(return_pos, vel=VELOCITY, acc=ACC)
                    mwait()

                    gripper.open_gripper()
                    mwait()
                    self.init_robot()
                    return


    def get_target_pos(self, target,max_attempts=3,z_step=10.0):

        """
            탐색 실패 시 탐색 될때까지 재탐색
        """
        attempt = 0
        while attempt < max_attempts:

            self.get_position_request.target = target
            self.get_logger().info("call depth position service with object_detection node")
            get_position_future = self.get_position_client.call_async(
                self.get_position_request
            )
            rclpy.spin_until_future_complete(self, get_position_future)

            if  get_position_future.result():
                
                
                result = get_position_future.result().depth_position.tolist()
                theta = get_position_future.result().theta
                self.get_logger().info(f"Received depth position: {result}")
                self.get_logger().info(f'시도{attempt+1}')
                if sum(result) == 0:
                    print("No target position: get target 포즈 좌표 합 0")
                    self.get_logger().info(f'z축으로 {z_step}mm 상승 후 재탐색 ')
                    movel([0, 0, z_step, 0, 0, 0], vel=VELOCITY, acc=ACC, mod=DR_MV_MOD_REL)
                    mwait()
                    attempt += 1
                #-> 다시 탐색 하는 거 안하나???
                #target이 scar로 들어오면서 위에서 세워둔 object_flag가 suction이면 캘리 바꾸기
                
                else:
                    print("====flag로 세워둔 거 바뀌었는지 확인")
                    self.get_logger().info(f'flag_object={self.flag_object},flag_target={self.flag_target}')
                    if self.flag_object=="suction" and self.flag_target=="scar":
                        npy_name="T_gripper2suction.npy" 
                        self.get_logger().info('상처 캘리브레이션 들어감')
                    else: 
                        npy_name= "T_gripper2camera.npy"
                        self.get_logger().info('기본 캘리브레이션 들어감')
                    gripper2cam_path = os.path.join(
                        package_path, "resource", npy_name
                    )
                    try:
                        robot_posx = get_current_posx()[0]
                    except:
                        self.get_logger().warn("get_current_posx 실패로 재요청")
                        robot_posx = get_current_posx()[0]
                        time.sleep(0.3)
                    td_coord = self.transform_to_base(result, gripper2cam_path, robot_posx)

                    if td_coord[2] and sum(td_coord) != 0:
                        td_coord[2] += DEPTH_OFFSET 
                        td_coord[2] = max(td_coord[2], MIN_DEPTH)  # MIN_DEPTH: float = 2.0

                    target_pos = list(td_coord[:3]) + robot_posx[3:]
                    return target_pos,theta
            
            else:
                self.get_logger().warn(f"[시도 {attempt + 1}] 서비스 응답 없음. 재시도합니다.")
                attempt += 1
        self.get_logger().error(f"{max_attempts}회 시도 실패 - {target} 위치를 찾지 못했습니다.")
        return None, None
    

    def init_robot(self):
        JReady = [14.483, -3.664, 88.303, -0.704, 95.931, 16.779] #초기 작업 위치

        #posj([14.483, -3.664, 88.303, -0.704, 95.931, 16.779])
        movej(JReady, vel=VELOCITY, acc=ACC)
        gripper.open_gripper()
        #처음으로 돌아가는 방법???
        


    def pick_and_place_target(self, target_pos,target_theta):

        #target_pos와 target_theta가 들어오면 그냥 가는 거 

        # gripper.open_gripper()
        x,y,z = target_pos[0],target_pos[1],target_pos[2]
        rx,ry,rz = target_pos[3], target_pos[4], target_pos[5]

        # rz=target_theta
        
        movel([x,y,z,rx,ry,rz], vel=VELOCITY, acc=ACC)
        #movel(target_pos, vel=VELOCITY, acc=ACC)

        mwait()
        # gripper.close_gripper()

        # while gripper.get_status()[0]:
        #     time.sleep(0.5)
        # mwait()

        # gripper.open_gripper()
        # while gripper.get_status()[0]:
        #     time.sleep(0.5)


def main(args=None):
    node = RobotController()
    while rclpy.ok():
        node.robot_control()
    rclpy.shutdown()
    node.destroy_node()


if __name__ == "__main__":
    main()
