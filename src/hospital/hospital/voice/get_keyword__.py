# ros2 service call /get_keyword std_srvs/srv/Trigger "{}"

import os
import rclpy
import pyaudio
from rclpy.node import Node
import pyttsx3

from ament_index_python.packages import get_package_share_directory
from dotenv import load_dotenv
from langchain.chat_models import ChatOpenAI
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain

# from std_srvs.srv import Trigger
from hospital_interfaces.srv import ObjectTarget
from hospital.voice.MicController import MicController, MicConfig

from hospital.voice.wakeup_word import WakeupWord
from hospital.voice.stt import STT
import time
import datetime
from gtts import gTTS
from playsound import playsound
import uuid

############ Package Path & Environment Setting ############
current_dir = os.getcwd()
package_path = get_package_share_directory("hospital")

is_laod = load_dotenv(dotenv_path=os.path.join(f"{package_path}/resource/.env"))
print("===========================")
print("현재 작업 디렉토리 : ", os.getcwd())
print("package_path : ", package_path)
print("dotenv_path : ", os.path.join(package_path, "resource/.env"))
print("===========================")

openai_api_key = os.getenv("OPENAI_API_KEY")
# openai_api_key =r'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'

############ AI Processor ############
# class AIProcessor:
#     def __init__(self):



############ GetKeyword Node ############
class GetKeyword(Node):
    def __init__(self):
        self.engine = pyttsx3.init()
        self.engine.setProperty('rate', 150)  # 속도 조절 (기본값: 200)

        self.llm = ChatOpenAI(
            model="gpt-4o", temperature=0.5, openai_api_key=openai_api_key
        )

        prompt_content = """
            당신은 사용자의 문장에서 특정 도구와 목적지를 추출해야 합니다.
            또한 당신은 의료 보조 로봇이며 suction, scalpel,spray과 같은 의료 용어를 인식해야 합니다.
            suction, mess, spray는 명령어이며 이는 작업 도구인 suction, scalpel, spray를 정해진 목적지로 이동시키라는 명령어이다.
            목적지는 scar와  hands이다
            suction과 spray는 목적지가 scar 
            scalpel는 목적지가 hands
            아예 관련이 없는 경우에는 의료 기구로 억지로 넣지 않아도 돼


            <목표>
            - 문장에서 다음 리스트에 포함된 도구를 최대한 정확히 추출하세요.
            - 문장에 등장하는 도구의 목적지(어디로 옮기라고 했는지)도 함께 추출하세요.

            <도구 리스트>
            - suction, scalpel, spray, hammer, screwdriver, wrench, pos1, pos2, pos3

            <출력 형식>
            - 다음 형식을 반드시 따르세요: [도구1 도구2 ... / pos1 pos2 ...]
            - 도구와 위치는 각각 공백으로 구분
            - 도구가 없으면 앞쪽은 공백 없이 비우고, 목적지가 없으면 '/' 뒤는 공백 없이 비웁니다.
            - 도구와 목적지의 순서는 등장 순서를 따릅니다.

            <특수 규칙>
            - 명확한 도구 명칭이 없지만 문맥상 유추 가능한 경우(예: "못 박는 것" → hammer)는 리스트 내 항목으로 최대한 추론해 반환하세요.
            - 다수의 도구와 목적지가 동시에 등장할 경우 각각에 대해 정확히 매칭하여 순서대로 출력하세요.
            - 발음이 정확하지 않더라도 '석션', '셕션', '쎅션', '쎅쎤' 등은 suction으로 간주
            - 발음이 정확하지 않더라도 "메스", "매스", "멧스" 등은 mess로 간주
            - 스프레이와 비슷한 발음은 spray로 간주
            - 단어 하나 말하는 것은 suction, mess, spray 3개 중 하나로 인식
            - 수술 정보에 대해 말해달라는 것, 혹은 그것과 비슷하게 유추 가능한 경우는 수술정보로 간주하고 입력과 출력을 info로 해줘
            - "석션 시작해줘" 와 "석션"은 구분 해줘. "석션 시작해줘"는 결과가 tracking 이고 "suction"은 결과가 scar야 
            - 입력 / 출력 은 항상 1개만 가도록 해야 돼
            <예시>
            - 입력 : "suction"
            출력 : suction / scar

            - 입력 : "suction 시작해줘 "
            출력 : start / tracking
            -입력 : "suction 종료해줘"
            출력 : stop / tracking


            - 입력 : "mess"
            출력 : scalpel / hands

            - 입력 : "칼"
            출력 : scalpel / hands

            - 입력 : "spray"
            출력 : spray / scar

            - 입력: "hammer를 pos1에 가져다 놔"  
            출력: hammer / pos1

            - 입력: "왼쪽에 있는 해머와 wrench를 pos1에 넣어줘"  
            출력: hammer wrench / pos1

            - 입력: "왼쪽에 있는 hammer를줘"  
            출력: hammer /

            - 입력: "왼쪽에 있는 못 박을 수 있는것을 줘"  
            출력: hammer /

            - 입력: "hammer는 pos2에 두고 screwdriver는 pos1에 둬"  
            출력: hammer screwdriver / pos2 pos1

            - 입력: "수술정보"
            출력: info / info 

            <사용자 입력>
            "{user_input}"                
        """

        #수술정보=환자 정보, 진단명, 수술명, 수술일시 (현재 시간 받아서 )

        self.prompt_template = PromptTemplate(
            input_variables=["user_input"], template=prompt_content
        )
        self.lang_chain = LLMChain(llm=self.llm, prompt=self.prompt_template)
        self.stt = STT(openai_api_key=openai_api_key)


        super().__init__("get_keyword_node")
        # 오디오 설정
        mic_config = MicConfig(
            chunk=12000,
            rate=48000,
            channels=1,
            record_seconds=5,
            fmt=pyaudio.paInt16,
            device_index=10,
            buffer_size=24000,
        )
        self.mic_controller = MicController(config=mic_config)
        # self.ai_processor = AIProcessor()

        self.get_logger().info("MicRecorderNode initialized.")
        self.get_logger().info("wait for client's request...")

        ###서비스 서버 생성 || 클라이언트 : robot_control노드
        self.get_keyword_srv = self.create_service(
            ObjectTarget, "/get_keyword", self.get_keyword
        ) #요청올때마다 get_keyword함수 실행
        self.wakeup_word = WakeupWord(mic_config.buffer_size)

    def speak_text(self, text: str):
        print("speak_text함수 실행")
        print(type(text))
        
        self.engine.say(text)
        time.sleep(1.0)
        self.engine.runAndWait()
        print("speak_text 함수 실행 완료")

    def extract_keyword(self, output_message):
        response = self.lang_chain.invoke({"user_input": output_message})
        result = response["text"]
        print("==========================")
        print("응답 텍스트 : ",result)
        print("==========================")

        object, target = result.strip().split("/")
        
        

        object = object.split()
        target = target.split()

        print(f"llm's response: {object}")
        print(f"object: {object}")
        print(f"target: {target}")
        
        return object,target
    
    def get_keyword(self, request, response):  # 요청과 응답 객체를 받아야 함
        try:
            print("open stream")
            self.mic_controller.open_stream()
            self.wakeup_word.set_stream(self.mic_controller.stream)
        except OSError:
            self.get_logger().error("Error: Failed to open audio stream")
            self.get_logger().error("please check your device index")
           
        while rclpy.ok():
            
            self.get_logger().info('waiting for hello rokey ')
            while not self.wakeup_word.is_wakeup(): #여기서 소켓 으로 받아서 활성화 가능 트리거 하나 추가
                print('듣고 있는 중...')
                #여기서 헬로 로키 감지될 때까지 반복
                pass

            time.sleep(0.3)
            print('ready')  
            self.speak_text('I am ready')
            # STT --> Keword Extract --> Embedding
            ###여기서부터 수정
            output_message = self.stt.speech2text()
            # keyword = self.extract_keyword(output_message) # mess / 손
            extract_object, extract_target = self.extract_keyword(output_message)

            """
            -입력 : "suction 시작해줘 "
            출력 : start / tracking
            -입력 : "suction 종료해줘"
            출력 : stop / tracking
            """

            if len(extract_object)>=2 or len(extract_target)>=2: ###여기서 예외처리 해 뒀는데
                print("길이 예외 처리")
                continue
            #지금 무조건 리스트 하나만오게 햇는데
            extract_object=" ".join(extract_object) #문자열로 변환 시킴ㄴ
            extract_target=" ".join(extract_target)

            print("===========================================================")
            self.get_logger().info(f"send get_keyword service respone ")
            self.get_logger().info(f"object : {extract_object}, target : {extract_target}")
            print("===========================================================")
            
            # valid_commands=['scalpel','suction']
            command = ""  # 항상 초기화
            if extract_object=="info": #수술 정보에 대한 If문
                self.get_logger().info("수술 정보 요청 감지됨")
                try:
                    now = datetime.datetime.now()
                    current_time = now.strftime("%Y년 %m월 %d일 %p %I시 %M분").replace("AM", "오전").replace("PM", "오후")

                    with open(os.path.join(package_path, "resource", "surgery_info.txt"), "r", encoding="utf-8") as f:
                        info = f.read()

                    # 실제 TTS 생성 및 재생 (즉시)
                    from gtts import gTTS
                    import uuid
                    tmp_path = f"/tmp/{uuid.uuid4()}.mp3"
                    gTTS(text=f"현재 시간은 {current_time}입니다. {info}", lang='ko').save(tmp_path)
                    playsound(tmp_path)
                    os.remove(tmp_path)

                except Exception as e:
                    self.get_logger().error(f"수술정보 파일 읽기 실패: {e}")
                    

                continue  # 다시 "hello rokey" 대기
            # 조건 1: 'tracking'일 경우
            #suction start / tracking
            #지금 object는 stop , start
            #target = tracking

            elif extract_target=="tracking": #트래킹명령에 대한 if문
                ###옵젝에 따라 다르게
                if extract_object=="start":
                    print("트래킹 시작 명령 보냄")
                    command = "tracking_start"
                elif extract_object=="stop":
                    print("트래킹 종료 명령 보냄")
                    command= "tracking_stop"
                # self.speak_text(command)
            #  조건 2: 유효한 명령어 포함

            elif extract_object == "scalpel" or extract_object == "suction":
                print("메스  , 셕션 대답")
                # self.speak_text(extract_object)
                         
            elif extract_object == "spray":#스프레이는tts가 못 말하여 따로 뺌       
                print("spray 명령 받음")
                # self.speak_text("doing spray ")
                
            else: #이상한 명령 들어올때
                print("이상한 명령")
                self.speak_text("sorry speak again")
                self.get_logger().info("잘못된 명령어, 다시 시도합니다")
                time.sleep(0.5)
                continue  #  루프 계속 (응답 리턴 안 하고 반복)

            # 응답 설정 후 종료
            response.success = True
            response.object = extract_object
            response.target = extract_target
            response.commands = command #tracking_start, tracking_stop보냄

            return response
        
def main():
    rclpy.init()
    node = GetKeyword()
    print(f"[DEBUG] .env loaded: {is_laod}")
    print(f"[DEBUG] OPENAI_API_KEY: {openai_api_key}")

    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == "__main__":
    main()
