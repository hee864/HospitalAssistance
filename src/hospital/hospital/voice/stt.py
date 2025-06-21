from langchain.chat_models import ChatOpenAI
import openai
import sounddevice as sd
import scipy.io.wavfile as wav
import numpy as np
import tempfile
import os

class STT:
    def __init__(self, openai_api_key):
        self.openai_api_key = openai_api_key
        self.duration = 5  # seconds
        self.samplerate = 16000  # Whisper는 16kHz를 선호

    def speech2text(self):
        # 녹음 설정
        print("음성 녹음을 시작합니다. \n 5초 동안 말해주세요...")
        audio = sd.rec(int(self.duration * self.samplerate),
                       samplerate=self.samplerate, channels=1, dtype='int16')
        sd.wait()
        print("녹음 완료. gpt-4o-transcribe에 전송 중...")

        # 임시 WAV 파일 저장
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_wav:
            wav.write(temp_wav.name, self.samplerate, audio)

            # Whisper API 호출
        print("[DEBUG] Temp file saved:", temp_wav.name)
        print("[DEBUG] File exists:", os.path.exists(temp_wav.name))
        print("[DEBUG] API Key:", self.openai_api_key)

        try:
            with open(temp_wav.name, "rb") as f:
                print("[DEBUG] Whisper API 호출 시작")
                transcript = openai.Audio.transcribe(
                    model="gpt-4o-mini-transcribe",
                    file=f,
                    api_key=self.openai_api_key,
                    language="ko"
                )
                print("[DEBUG] Whisper 응답 수신 완료")
        except Exception as e:
            print("[ERROR] Whisper API 호출 실패:", e)
            raise

        print("STT 결과: ", transcript['text'])
        return transcript['text']