from gtts import gTTS
import uuid
import socket
import time

def test_gtts_save():
    try:
        # 인터넷 연결 테스트
        socket.create_connection(("www.google.com", 80), timeout=5)
        print("✅ 인터넷 연결 확인됨")

        text = "수술 정보를 읽어드리겠습니다. .환자의 정보는 테디베어 암컷 10세  수술 정보는 위 내 이물에 의한 장폐색 의증 복강 절개 후 이물 제거 입니다"
        filename = f"./tts_output_{uuid.uuid4()}.mp3"
        print("🎤 gTTS 처리 시작")

        t0 = time.time()
        tts = gTTS(text=text, lang='ko')
        tts.save(filename)
        print(f"✅ MP3 저장 완료: {filename}")
        print(f"⏱️ 소요 시간: {time.time() - t0:.2f}초")

    except socket.timeout:
        print("❌ 인터넷 연결 실패 (timeout)")
    except Exception as e:
        print(f"❌ 오류 발생: {e}")

test_gtts_save()
