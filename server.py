import os
import json
import asyncio
import random
import re
from typing import Dict, List, Optional, Set
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
import uvicorn
import httpx
from dotenv import load_dotenv

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))

# .env 환경 변수 로드
load_dotenv(os.path.join(CURRENT_DIR, ".env"))

app = FastAPI(title="EduWord Chain Game Server")

# -------------------------------------------------------------
# 1. 두음법칙 (Initial Sound Rule) & 사전 검증 모듈
# -------------------------------------------------------------
def get_dueum_variants(char: str) -> List[str]:
    if not char:
        return []
    code = ord(char[0]) - 0xAC00
    if code < 0 or code > 11171:
        return [char]
    
    cho = code // 588
    jung = (code % 588) // 28
    jong = code % 28
    variants = [char]

    if cho == 5:  # ㄹ
        if jung in [2, 4, 7, 12, 17, 20]:  # ㅑ, ㅕ, ㅖ, ㅛ, ㅠ, ㅣ
            alt_code = 0xAC00 + (11 * 588) + (jung * 28) + jong
            variants.append(chr(alt_code))
        else:
            alt_code = 0xAC00 + (2 * 588) + (jung * 28) + jong
            variants.append(chr(alt_code))
    elif cho == 2:  # ㄴ
        if jung in [4, 12, 17, 20]:  # ㅕ, ㅛ, ㅠ, ㅣ
            alt_code = 0xAC00 + (11 * 588) + (jung * 28) + jong
            variants.append(chr(alt_code))

    return list(dict.fromkeys(variants))

# 표준국어대사전 검증용 단어 세트 로드 (서버 기동 시 메모리 상주)
DICTIONARY_FILE = os.path.join(CURRENT_DIR, "dictionary.json")
STANDARD_WORDS: Set[str] = set()

if os.path.exists(DICTIONARY_FILE):
    try:
        with open(DICTIONARY_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            STANDARD_WORDS = set(data)
            print(f"[Dictionary] Loaded {len(STANDARD_WORDS)} standard words from dictionary.json")
    except Exception as e:
        print(f"[Dictionary] Failed to load dictionary.json: {e}")

# fallback 기본 단어들 (사전 파일이 없거나 최소 보장용)
if not STANDARD_WORDS:
    DEFAULT_WORDS = [
        "가게","가격","가구","가기","가깝다","가늠","가락","가랑비","가래떡","가로수","가루","가마니","가면","가문","가뭄","가방","가수","가슴","가을","가입","가족","가죽","가축","가치","각계","각도","각본","간격","간결","간식","간장","간판","간호사","갈대","갈등","갈매기","갈비탕","갈색","감각","감격","감기","감나무","감독","감동","감사","감상","감소","감자","감정","감탄","갑옷","갑판","강낭콩","강단","강당","강도","강력","강변","강산","강아지","강좌","강철","강풍","강화","개구리","개나리","개막","개미","개발","개방","개성","개인","개최","거울","거인","거절","거품","건강","건물","건반","건설","검사","겨울","결과","결승","결정","결혼","경기","경찰","경찰관","계단","계란","계산기","계절","고구마","고기","고민","고양이","고을","고향","골목","곰팡이","공간","공기","공룡","공부","공원","공주","공책","과거","과목","과일","과자","과학","관광","관람","관심","관찰","광장","교과서","교문","교사","교실","교장","교탁","교통","구름","구슬","국가","국기","국물","국어","국화","군인","궁궐","귀걸이","규칙","그늘","그림","금붕어","기계","기념","기둥","기린","기쁨","기상","기억","기온","기운","기차","기차역","기초","기타","기회","김밥","김치","깃발","꼬마","꽃병","꽃씨","꽃잎","꿀벌",
        "나그네","나라","나무","나비","나팔","나침반","낙엽","낙타","낚시","날개","날씨","날짜","남극","남산","남쪽","낭만","낮잠","냄새","냉면","냉장고","너구리","노래","노래방","노을","노인","노트","노트북","녹음기","녹차","놀이터","농구","농구공","농담","농민","농부","농업","농촌","높이","눈사람","눈물","눈싸움","눈송이","뉴스","늑대","능력",
        "다람쥐","다리","다행","단어","단추","단풍","단풍나무","달걀","달력","달리기","달빛","담요","담임","답장","당근","대궐","대기","대낮","대나무","대답","대도시","대통령","대문","대한민국","도감","도구","도깨비","도덕","도로","도서관","도시","도시락","도자기","도장","도착","도토리","독감","독립","독서","독수리","돌고래","동굴","동네","동물","동물원","동생","동시","동아리","동요","동쪽","동치미","동화책","돼지","두뇌","두루미","두부","두통","뒷산","드라마","드레스","등대","등산",
        "라면","라디오","라일락","라켓","러시아","레몬","레슬링","레저","렌즈","로봇","로켓","루비","리듬","리본","리그","리더","리모컨",
        "마당","마술","마음","마을","마이크","마차","막내","막대기","만두","만세","만찬","만화책","말벌","말씀","망원경","머리","머리카락","먹이","메뉴","메달","메모지","메밀","메아리","며느리","면발","명령","명사","명산","명절","명작","모기","모래","모습","모양","모임","모자","목걸이","목련","목록","목소리","목수","목욕탕","목화","몸무게","무궁화","무당벌레","무더위","무대","무덤","무료","무릎","무사","무술","무용","무지개","문구점","문서","문장","문학","문제","물감","물결","물고기","물건","물놀이","물방울","물새","물수제비","물통","미술관","미소","미역국","미인","민들레","민속촌","민요","밀가루","밀짚모자",
        "바가지","바구니","바늘","바다","바둑","바둑판","바람","바람개비","바위","바지","바지락","박물관","박사","박수","반달","반지","반찬","발걸음","발목","발명가","발자국","발표","밤하늘","밥그릇","밥상","방과후","방망이","방송국","방울","방학","배경","배구","배꼽","배달","배려","배추김치","백과사전","백로","백설기","백조","백합","백화점","뱀장어","버섯","버드나무","버스","번호","벌레","벌집","범선","법원","베개","변화","별자리","별빛","별똥별","병아리","병원","보건소","보름달","보물","보리차","보석","보자기","보호","복도","복사기","복숭아","복지","볶음밥","봄날","봉사","봉선화","봉투","부모님","부엌","부채","북극곰","북소리","분필","불꽃놀이","불고기","비누","비둘기","비바람","비빔밥","비상구","비행기","빗방울","빙수","빛깔",
        "사과","사과나무","사건","사고","사다리","사람","사랑","사무실","사물함","사자","사자성어","사전","사진기","사촌","사탕","산골","산들바람","산맥","산소","산울림","산호","산토끼","살구","삼계탕","삼촌","상가","상금","상담","상상","상어","상자","상장","상품","새벽","새싹","색연필","색종이","생각","생물","생명","생선","생일","생활","서랍","서점","선물","선박","선배","선생님","선수","선율","선풍기","설경","설날","설탕","성공","성벽","성실","성적","세계","세수","세종대왕","소나무","소녀","소년","소방관","소방서","소설가","소식","소원","소음","소풍","손가락","손목","손수건","손수레","손톱","솔방울","송아지","송편","쇠고기","수건","수도","수련회","수박","수업","수영장","수저","수제비","수첩","수학","숙제","순간","순서","숲속","스마트폰","스케이트","스케치북","스푼","승리","시계","시골","시금치","시대","시민","시소","시인","시작","시장","시험","식기","식당","식빵","식사","식물원","식초","식혜","신문","신발","신발장","신비","신호등","실내화","실례","실수","실험실","심리학","심장",
        "아기","아내","아들","아름다움","아리랑","아시아","아이스크림","아침밥","악기","악수","안경","안개","안내소","안전","알림장","알파벳","암석","앞마당","애국가","야구","야구장","야자수","야채","약국","약속","약수터","양말","양념","양치","양파","어깨","어린이날","어머니","어부","얼굴","얼룩말","얼음","여름","여우","여행사","역사","역무원","역할","연구원","연극","연꽃","연못","연습장","연주회","연필","연필깎이","열기구","열매","열쇠","열차","염소","엽서","영국","영화관","영웅","예술가","예절","오리","오렌지","오솔길","오이","오징어","옥수수","온도계","온천","올챙이","옷걸이","옷장","옹달샘","와이파이","왕관","왕자","외국어","외할머니","외할아버지","요구르트","요리사","요정","욕실","용기","용돈","우산","우주선","우주인","우체국","우체통","우표","운동선수","운동장","운동화","원숭이","월드컵","위인전","유람선","유리창","유물","유성","유치원","육교","은메달","은방울꽃","은하수","음료수","음악가","음식점","응원","의견","의사","의자","이구아나","이글루","이름표","이메일","이모","이모티콘","이발소","이슬","이웃사촌","인간","인공지능","인기","인류","인사","인생","인쇄소","인어공주","인형","인터넷","일기예보","일기장","일본","일출","임금님","입구","입술","잎사귀",
        "자격증","자극","자금","자기소개","자동차","자랑","자루","자료","자립","자물쇠","자본주의","자부심","자석","자선단체","자신감","자연보호","자유","자작나무","자장면","자전거","자정","자존심","작곡가","작년","작품","잔디밭","잠자리","장갑","장난감","장독대","장마","장미꽃","장소","장수","장애물","재료","재미","저녁밥","저금통","저수지","전구","전기차","전망대","전설","전시회","전통","전화기","절약","젊음","점심시간","점수","접시","젓가락","정답","정류장","정리","정문","정성","정원","정직","제비","제주도","조개","조각상","조립","졸업식","종이접기","종착역","주머니","주민센터","주사위","주소","주스","주전자","죽순","줄넘기","중학교","지갑","지구촌","지남철","지도","지름길","지우개","지하철","지혜","진달래꽃","질문","질서","집안일","집게",
        "차례","차표","찬성","참나무","참새","참외","참치","채소","채송화","책가방","책꽂이","책상","책임","천둥","천문대","천사","천체","철새","철봉","철학","청개구리","청국장","청년","청소기","청소년","체육관","체조","초등학교","초등학생","초록색","초밥","초승달","초원","초콜릿","촛불","총각김치","추석","축구공","축구선수","축제","출구","출발","출석","충고","취미","치과","치마","치아","치즈","친구","친절","칠판","칫솔",
        "카드","카레","카메라","카네이션","카누","카페","칼국수","칼집","캐릭터","캠핑장","커피","커튼","컴퓨터","코끼리","코스모스","코알라","코트","콘서트","콩나물","콩국수","크레파스","크리스마스","키보드","킬로미터",
        "타악기","타이어","타조","탁구공","탁구채","탄산음료","탈출","탐험가","태극기","태권도","태양계","태풍","택배","택시","터널","터미널","테니스공","테이블","토끼","토마토","통나무","통신","통일","통장","투구","튜브","트럭","트럼펫","티셔츠","팀워크",
        "파도","파리","파스텔","파전","파일","팔레트","팔찌","팬더","팽이","팽이버섯","퍼즐","페이지","펜싱","편지봉투","포도주스","포스터","포크","폭포","표범","표어","풀잎","풍경","풍선","풍차","프린터","플루트","피아노","피자","필기도구","필통",
        "하나","하늘","하늘색","하마","하모니카","하천","학교","학부모","학생","학용품","학원","한국사","한글날","한복","한식","한옥","할머니","할아버지","항공기","해경","해녀","해달","해돋이","해산물","해안","해양","해질녘","해파리","해바라기","해풍","햄버거","햇살","햇빛","행복","행성","행운","향기","호두","호랑이","호박","호수","호텔","화가","화단","화분","화산","화성","화장실","화초","환영","활동","황금","황새","황사","회관","회색","회의","회전목마","효도","후식","훈련","휴대전화","휴식","휴일","휴지통","희망","희생","흰구름",
        "늘보","늘품","늘솔길","늘비","름봉","름료","곽란","곽지","곽밥","릇밥","릇들","듐석","튬석","슘석","늣치","늴리리","역사","역무원","역도","역할","역전","역사학","역지사지","유리","유성","유머","유람선","유행","유치원","유적","유기농","유령","양식","양초","양심","양호실","양파","여름","여자","여우","여행","여권","여유","요리","요일","요구르트","요람","요술","요정","요새"
    ]
    STANDARD_WORDS = set(DEFAULT_WORDS)

# -------------------------------------------------------------
# 1-1. 국립국어원 표준국어대사전 Open API 검증 모듈
# -------------------------------------------------------------
API_VERIFIED_WORDS_CACHE: Dict[str, bool] = {}

def get_korean_dict_api_key() -> str:
    """매 호출 시 .env 파일에서 최신 API 키를 읽어옵니다 (서버 재시작 없이 반영)."""
    load_dotenv(os.path.join(CURRENT_DIR, ".env"), override=True)
    return os.getenv("KOREAN_DICT_API_KEY", "").strip()

async def check_word_with_stdict_api(word: str) -> Optional[bool]:
    """
    국립국어원 표준국어대사전 Open API (https://stdict.korean.go.kr/api/search.do)
    - True: 국립국어원에 등재된 올바른 표준어
    - False: 국립국어원에 등재되지 않은 단어
    - None: API 키가 없거나 네트워크 오류 시 (로컬 사전 fallback)
    """
    if not word:
        return False

    # 1. 메모리 캐시 확인 (반복 검증 속도 최적화)
    if word in API_VERIFIED_WORDS_CACHE:
        return API_VERIFIED_WORDS_CACHE[word]

    # 2. 로컬 기본 표준어 세트에 이미 등록된 경우 즉시 인정
    if word in STANDARD_WORDS:
        API_VERIFIED_WORDS_CACHE[word] = True
        return True

    # 3. API 키 확인
    api_key = get_korean_dict_api_key()
    if not api_key or api_key == "YOUR_OPENAPI_KEY_HERE":
        return None  # API 키 미입력 시 None 반환 -> 로컬 사전 모드로 fallback

    url = "https://stdict.korean.go.kr/api/search.do"
    params = {
        "key": api_key,
        "q": word,
        "req_type": "json",
        "type_search": "search",
        "part": "word"
    }

    try:
        async with httpx.AsyncClient(timeout=3.5, verify=False) as client:
            resp = await client.get(url, params=params)
            if resp.status_code == 200:
                try:
                    data = resp.json()
                    channel = data.get("channel", {})
                    total = int(channel.get("total", 0))
                    items = channel.get("item", [])

                    # 검색된 표제어 중 특수문자, 하이픈 제거 후 정확 일치 검사
                    is_valid = False
                    for it in items:
                        clean_item_word = re.sub(r'[^가-힣]', '', it.get("word", ""))
                        if clean_item_word == word:
                            is_valid = True
                            break

                    if not is_valid and total > 0:
                        for it in items:
                            raw_w = it.get("word", "").replace("-", "").replace("^", "").strip()
                            if raw_w == word:
                                is_valid = True
                                break

                    API_VERIFIED_WORDS_CACHE[word] = is_valid
                    status_str = "✅ 국립국어원 등재 확인" if is_valid else "❌ 미등재"
                    print(f"[국립국어원 API] 단어 '{word}' 검증 결과: {status_str} (검색 {total}건)")
                    return is_valid
                except Exception as json_err:
                    print(f"[국립국어원 API] JSON 파싱 오류: {json_err}")
                    return None
            else:
                print(f"[국립국어원 API] HTTP {resp.status_code} 응답")
                return None
    except Exception as e:
        print(f"[국립국어원 API] 호출 예외 ({e}) -> 로컬 사전 대체")
        return None

AI_QUIZ_POOL = [
    {"word": "서울", "def": "대한민국의 수도이자 정치, 경제, 문화의 중심지인 특별시", "chosung": "ㅅ ㅇ", "len": 2},
    {"word": "인터넷", "def": "전 세계의 컴퓨터를 하나로 연결하여 정보를 주고받는 전 지구적 통신망", "chosung": "ㅇ ㅌ ㄴ", "len": 3},
    {"word": "지구", "def": "태양계의 세 번째 행성이며 물과 산소가 풍부하여 인류와 생명체가 살아가는 푸른 별", "chosung": "ㅈ ㄱ", "len": 2},
    {"word": "무지개", "def": "비가 온 뒤 햇빛이 물방울에 굴절되어 하늘에 나타나는 일곱 색깔의 아름다운 호", "chosung": "ㅁ ㅈ ㄱ", "len": 3},
    {"word": "도서관", "def": "수많은 책과 학습 자료를 모아 두어 누구나 읽거나 빌릴 수 있게 마련한 배움의 공간", "chosung": "ㄷ ㅅ ㄱ", "len": 3},
    {"word": "비행기", "def": "공기의 양력을 이용하여 하늘 높이 날아올라 사람과 짐을 싣고 빠르게 이동하는 항공기", "chosung": "ㅂ ㅎ ㄱ", "len": 3},
    {"word": "자전거", "def": "두 개의 바퀴를 사람이 발로 페달을 밟아 굴려서 움직이는 친환경 교통수단", "chosung": "ㅈ ㅈ ㄱ", "len": 3},
    {"word": "한글", "def": "세종대왕이 백성을 사랑하는 마음으로 창제한 우리나라 고유의 과학적인 문자", "chosung": "ㅎ ㄱ", "len": 2},
    {"word": "인공지능", "def": "인간의 학습과 추론 능력을 컴퓨터 알고리즘으로 구현하여 문제를 해결하는 첨단 기술", "chosung": "ㅇ ㄱ ㅈ ㄴ", "len": 4},
    {"word": "함박눈", "def": "겨울철에 눈송이가 크고 탐스럽게 엉겨서 펄펄 내리는 아름다운 눈", "chosung": "ㅎ ㅂ ㄴ", "len": 3},
    {"word": "우정", "def": "서로 깊이 신뢰하고 아끼며 함께 기쁨과 슬픔을 나누는 친구 사이의 따뜻한 정", "chosung": "ㅇ ㅈ", "len": 2},
    {"word": "바다", "def": "지구 표면의 대부분을 덮고 있는 거대하고 푸른 짠 물의 영역", "chosung": "ㅂ ㄷ", "len": 2},
    {"word": "선생님", "def": "학생들에게 지식과 바른 인성을 가르치고 이끌어 주는 존경받는 스승", "chosung": "ㅅ ㅅ ㄴ", "len": 3},
    {"word": "음악", "def": "박자, 가락, 음색을 조화롭게 엮어 사람의 사상과 감정을 표현하는 예술", "chosung": "ㅇ ㅇ", "len": 2}
]

# -------------------------------------------------------------
# 2. 반(Room) 모델 및 상태 관리
# -------------------------------------------------------------
class Player:
    def __init__(self, player_id: str, name: str, student_number: str = "", is_bot: bool = False):
        self.id = player_id
        self.name = name
        self.student_number = student_number or player_id
        self.score = 0
        self.combo = 0
        self.success_words: List[str] = []
        self.is_bot = is_bot

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "studentNumber": self.student_number,
            "score": self.score,
            "combo": self.combo,
            "successWords": self.success_words,
            "isBot": self.is_bot
        }

class GameRoom:
    def __init__(self, room_code: str):
        self.room_code = room_code
        self.stage = "LOBBY"  # LOBBY, QUIZ, PLAYING, FINISHED
        self.max_rounds = 5
        self.current_round = 1
        self.total_time_seconds = 300
        self.remaining_total_seconds = 300
        self.turn_time_seconds = 10
        self.remaining_turn_seconds = 10
        self.current_word = ""
        self.history: List[dict] = []
        self.used_words: List[str] = []
        self.players: List[Player] = []
        self.active_player_index = 0
        self.is_chance_mode = False
        self.quiz_data: Optional[dict] = None

        # WebSocket Connections
        self.teacher_ws: Optional[WebSocket] = None
        self.student_ws: Dict[str, WebSocket] = {}

        # Async Tasks
        self.turn_timer_task: Optional[asyncio.Task] = None
        self.total_timer_task: Optional[asyncio.Task] = None

    def to_state_dict(self):
        return {
            "roomCode": self.room_code,
            "stage": self.stage,
            "maxRounds": self.max_rounds,
            "currentRound": self.current_round,
            "totalTimeSeconds": self.total_time_seconds,
            "remainingTotalSeconds": self.remaining_total_seconds,
            "turnTimeSeconds": self.turn_time_seconds,
            "remainingTurnSeconds": self.remaining_turn_seconds,
            "currentWord": self.current_word,
            "history": self.history[:40],
            "usedWords": self.used_words,
            "players": [p.to_dict() for p in self.players],
            "activePlayerIndex": self.active_player_index,
            "isChanceMode": self.is_chance_mode,
            "quizData": self.quiz_data
        }

    async def broadcast_state(self):
        msg = {
            "type": "STATE_UPDATE",
            "state": self.to_state_dict()
        }
        await self.broadcast_json(msg)

    async def broadcast_json(self, msg: dict):
        text = json.dumps(msg, ensure_ascii=False)
        targets = []
        if self.teacher_ws:
            targets.append(self.teacher_ws)
        for ws in list(self.student_ws.values()):
            targets.append(ws)

        dead_ws = []
        for ws in targets:
            try:
                await ws.send_text(text)
            except Exception:
                dead_ws.append(ws)

        for dws in dead_ws:
            if dws == self.teacher_ws:
                self.teacher_ws = None
            for pid, sws in list(self.student_ws.items()):
                if sws == dws:
                    del self.student_ws[pid]

    def stop_timers(self):
        if self.turn_timer_task and not self.turn_timer_task.done():
            self.turn_timer_task.cancel()
            self.turn_timer_task = None
        if self.total_timer_task and not self.total_timer_task.done():
            self.total_timer_task.cancel()
            self.total_timer_task = None

    async def validate_word(self, word: str) -> dict:
        word = word.strip()
        if len(word) < 2:
            return {"valid": False, "reason": "글자 수는 2글자 이상이어야 합니다."}

        # 정규식 한글 확인
        if not re.fullmatch(r'^[가-힣]+$', word):
            return {"valid": False, "reason": "한글 단어만 입력할 수 있습니다."}

        # 이미 사용한 단어
        if word in self.used_words:
            return {"valid": False, "reason": f"'{word}'은(는) 이미 사용된 단어입니다."}

        # 첫 글자 일치 및 두음법칙 검사
        if self.current_word:
            last_char = self.current_word[-1]
            allowed_starts = get_dueum_variants(last_char)
            if word[0] not in allowed_starts:
                dueum_info = f" (두음법칙: {', '.join(allowed_starts)})" if len(allowed_starts) > 1 else ""
                return {"valid": False, "reason": f"'{last_char}'{dueum_info}(으)로 시작해야 합니다."}

        # 국립국어원 표준국어대사전 Open API 검증
        api_result = await check_word_with_stdict_api(word)
        if api_result is True:
            return {"valid": True, "reason": "국립국어원 표준국어대사전 등재 단어"}
        elif api_result is False:
            return {"valid": False, "reason": "국립국어원 표준국어대사전에 등재되지 않은 단어입니다."}
        else:
            # API 키 미설정 또는 네트워크 오류 시 로컬 사전 검증
            if word not in STANDARD_WORDS:
                return {"valid": False, "reason": "국립국어원 표준국어대사전에 등재되지 않은 단어입니다."}

        return {"valid": True, "reason": "올바른 단어"}

    def add_player(self, player_id: str, name: str, student_number: str, is_bot: bool = False) -> Player:
        for p in self.players:
            if p.id == player_id:
                p.name = name
                p.student_number = student_number
                return p
        new_player = Player(player_id, name, student_number, is_bot)
        self.players.append(new_player)
        return new_player

    def add_bots(self, count: int = 3):
        bot_pool = [
            ("10102", "이영희"),
            ("10103", "박지민"),
            ("10104", "최수호"),
            ("10105", "정다운"),
            ("10106", "강하늘")
        ]
        added = 0
        for bid, bname in bot_pool:
            if added >= count:
                break
            if not any(p.id == bid for p in self.players):
                self.add_player(bid, bname, bid, is_bot=True)
                added += 1

    async def start_quiz(self):
        self.stop_timers()
        self.stage = "QUIZ"
        self.quiz_data = random.choice(AI_QUIZ_POOL)
        self.current_round = 1
        self.history.clear()
        self.used_words.clear()
        for p in self.players:
            p.score = 0
            p.combo = 0
            p.success_words.clear()

        await self.broadcast_state()

        # 가상 학생 봇이 있을 경우 퀴즈 자동 정답 시뮬레이션
        bots = [p for p in self.players if p.is_bot]
        if bots:
            asyncio.create_task(self._bot_quiz_task(self.quiz_data["word"], bots))

    async def _bot_quiz_task(self, target_word: str, bots: List[Player]):
        delay = random.uniform(4.0, 7.0)
        await asyncio.sleep(delay)
        if self.stage == "QUIZ" and self.quiz_data and self.quiz_data.get("word") == target_word:
            lucky_bot = random.choice(bots)
            await self.solve_quiz(lucky_bot.id, target_word)

    async def solve_quiz(self, winner_id: str, word: str):
        if self.stage != "QUIZ":
            return

        winner = next((p for p in self.players if p.id == winner_id), None)
        if not winner:
            return

        # 승자를 1번 순서로 재배열
        others = [p for p in self.players if p.id != winner_id]
        self.players = [winner] + others
        self.active_player_index = 0

        winner.score += 10
        winner.success_words.append(word)
        self.current_word = word
        self.used_words.append(word)

        now_str = asyncio.get_event_loop().time()
        self.history.insert(0, {
            "player": winner.name,
            "studentNumber": winner.student_number,
            "word": word,
            "type": "quiz",
            "scoreChange": "+10점",
            "time": "퀴즈 우승"
        })

        self.stage = "PLAYING"
        await self.broadcast_state()
        self.start_game_timers()

    def start_game_timers(self):
        self.stop_timers()
        self.remaining_turn_seconds = 10
        self.is_chance_mode = False

        self.turn_timer_task = asyncio.create_task(self._run_turn_timer())
        if not self.total_timer_task or self.total_timer_task.done():
            self.total_timer_task = asyncio.create_task(self._run_total_timer())

        self._check_and_trigger_bot_turn()

    async def _run_total_timer(self):
        while self.remaining_total_seconds > 0 and self.stage == "PLAYING":
            await asyncio.sleep(1)
            self.remaining_total_seconds -= 1
        if self.stage == "PLAYING" and self.remaining_total_seconds <= 0:
            await self.finish_game()

    async def _run_turn_timer(self):
        while self.remaining_turn_seconds > 0 and self.stage == "PLAYING":
            await asyncio.sleep(1)
            self.remaining_turn_seconds -= 1
            await self.broadcast_state()

        if self.stage == "PLAYING" and self.remaining_turn_seconds <= 0:
            await self.handle_timeout()

    async def handle_timeout(self):
        if not self.is_chance_mode:
            # 턴 주자 -5점 감점 후 선착순 찬스 모드 진입
            active_player = self.players[self.active_player_index]
            active_player.score = max(0, active_player.score - 5)
            active_player.combo = 0

            self.history.insert(0, {
                "player": active_player.name,
                "studentNumber": active_player.student_number,
                "word": "시간 초과",
                "type": "fail",
                "scoreChange": "-5점",
                "time": "초과"
            })

            self.is_chance_mode = True
            self.remaining_turn_seconds = 10
            await self.broadcast_state()

            # 봇 찬스 시뮬레이션
            self._simulate_bot_chance()

            # 찬스 모드 카운트다운
            self.turn_timer_task = asyncio.create_task(self._run_chance_timer())
        else:
            await self.handle_chance_timeout()

    async def _run_chance_timer(self):
        while self.remaining_turn_seconds > 0 and self.stage == "PLAYING" and self.is_chance_mode:
            await asyncio.sleep(1)
            self.remaining_turn_seconds -= 1
            await self.broadcast_state()

        if self.stage == "PLAYING" and self.is_chance_mode and self.remaining_turn_seconds <= 0:
            await self.handle_chance_timeout()

    async def handle_chance_timeout(self):
        self.is_chance_mode = False
        # 아무도 입력 못했을 때 AI가 새로운 단어 제공
        fallback = random.choice(AI_QUIZ_POOL)["word"]
        self.current_word = fallback
        self.used_words.append(fallback)

        self.history.insert(0, {
            "player": "AI 진행자",
            "studentNumber": "",
            "word": f"새 제시어: {fallback}",
            "type": "combo",
            "scoreChange": "새출발",
            "time": "찬스종료"
        })

        await self.advance_turn()

    async def advance_turn(self):
        self.active_player_index = (self.active_player_index + 1) % len(self.players)
        if self.active_player_index == 0:
            self.current_round += 1
            if self.current_round > self.max_rounds:
                await self.finish_game()
                return

        self.is_chance_mode = False
        self.remaining_turn_seconds = 10
        await self.broadcast_state()
        self.start_game_timers()

    async def submit_word(self, player_id: str, raw_word: str):
        word = raw_word.strip()
        if self.stage == "QUIZ":
            if self.quiz_data and word == self.quiz_data["word"]:
                await self.solve_quiz(player_id, word)
            return

        if self.stage != "PLAYING":
            return

        p_idx = next((i for i, p in enumerate(self.players) if p.id == player_id), -1)
        if p_idx == -1:
            return
        player = self.players[p_idx]

        # 찬스 모드가 아닐 때는 현재 차례인 학생만 정답 제출 가능
        if not self.is_chance_mode and p_idx != self.active_player_index:
            return

        val = await self.validate_word(word)
        if not val["valid"]:
            # 오답 감점 -5점
            player.score = max(0, player.score - 5)
            player.combo = 0
            self.history.insert(0, {
                "player": player.name,
                "studentNumber": player.student_number,
                "word": f"{word} ({val['reason']})",
                "type": "fail",
                "scoreChange": "-5점",
                "time": "오답"
            })
            await self.broadcast_state()
            return

        # 정답 인정
        if self.turn_timer_task and not self.turn_timer_task.done():
            self.turn_timer_task.cancel()

        points = 10
        player.combo += 1
        combo_bonus = False
        if player.combo >= 2:
            points += 3
            combo_bonus = True

        player.score += points
        player.success_words.append(word)
        self.used_words.append(word)
        self.current_word = word

        self.history.insert(0, {
            "player": player.name,
            "studentNumber": player.student_number,
            "word": word,
            "type": "combo" if combo_bonus else "success",
            "scoreChange": f"+{points}점" + (" 🔥콤보!" if combo_bonus else ""),
            "time": "정답"
        })

        await self.advance_turn()

    def _check_and_trigger_bot_turn(self):
        if self.stage != "PLAYING" or self.is_chance_mode:
            return
        current = self.players[self.active_player_index]
        if not current.is_bot:
            return

        asyncio.create_task(self._bot_turn_task(current))

    async def _bot_turn_task(self, bot_player: Player):
        think_time = random.uniform(2.5, 4.5)
        await asyncio.sleep(think_time)
        if (self.stage == "PLAYING" and not self.is_chance_mode 
            and self.players[self.active_player_index].id == bot_player.id):
            bot_word = self._generate_bot_word()
            if bot_word:
                await self.submit_word(bot_player.id, bot_word)

    def _simulate_bot_chance(self):
        bots = [p for p in self.players if p.is_bot]
        if not bots:
            return
        asyncio.create_task(self._bot_chance_task(bots))

    async def _bot_chance_task(self, bots: List[Player]):
        delay = random.uniform(3.0, 6.0)
        await asyncio.sleep(delay)
        if self.stage == "PLAYING" and self.is_chance_mode:
            lucky_bot = random.choice(bots)
            bot_word = self._generate_bot_word()
            if bot_word:
                await self.submit_word(lucky_bot.id, bot_word)

    def _generate_bot_word(self) -> Optional[str]:
        if not self.current_word:
            return None
        last_char = self.current_word[-1]
        allowed = get_dueum_variants(last_char)

        candidates = [
            w for w in STANDARD_WORDS 
            if w[0] in allowed and w not in self.used_words and len(w) >= 2
        ]
        if candidates:
            return random.choice(candidates)
        return None

    async def finish_game(self):
        self.stop_timers()
        self.stage = "FINISHED"
        await self.broadcast_state()

    def reset_room(self, new_code: str):
        self.stop_timers()
        self.room_code = new_code
        self.stage = "LOBBY"
        self.current_round = 1
        self.remaining_total_seconds = self.total_time_seconds
        self.history.clear()
        self.used_words.clear()
        for p in self.players:
            p.score = 0
            p.combo = 0
            p.success_words.clear()


# -------------------------------------------------------------
# 3. 전체 반(Room) 매니저 & 파일 영구 저장소
# -------------------------------------------------------------
ROOM_CODE_FILE = os.path.join(CURRENT_DIR, "room_code.txt")

def save_active_room_code(code: str):
    """선생님이 개설한 4자리 방 번호를 파일(room_code.txt)에 저장"""
    try:
        with open(ROOM_CODE_FILE, "w", encoding="utf-8") as f:
            f.write(code.strip())
        print(f"[Room File] 방 번호 파일 저장 완료: {code} ({ROOM_CODE_FILE})")
    except Exception as e:
        print(f"[Room File Error] 방 번호 파일 저장 실패: {e}")

def get_saved_room_code() -> Optional[str]:
    """파일(room_code.txt)에서 현재 활성화된 선생님 방 번호 읽기"""
    if os.path.exists(ROOM_CODE_FILE):
        try:
            with open(ROOM_CODE_FILE, "r", encoding="utf-8") as f:
                code = f.read().strip()
                if len(code) == 4 and code.isdigit():
                    return code
        except Exception as e:
            print(f"[Room File Error] 방 번호 파일 읽기 실패: {e}")
    return None

ROOMS: Dict[str, GameRoom] = {}

def get_or_create_room(room_code: str) -> GameRoom:
    if room_code not in ROOMS:
        ROOMS[room_code] = GameRoom(room_code)
    return ROOMS[room_code]

def generate_random_4digit_code() -> str:
    while True:
        code = str(random.randint(1000, 9999))
        if code not in ROOMS:
            return code

# 서버 기동 시 기존 저장된 방 번호가 있으면 사전 등록
_saved_init_code = get_saved_room_code()
if _saved_init_code:
    get_or_create_room(_saved_init_code)
    print(f"[Room File] 기존 파일에서 선생님 방 번호 복원 완료: {_saved_init_code}")


# -------------------------------------------------------------
# 4. REST API & Static 파일 라우팅
# -------------------------------------------------------------
@app.get("/")
async def serve_index():
    index_file = os.path.join(CURRENT_DIR, "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file, media_type="text/html")
    return {"message": "index.html not found"}

class RoomCreateRequest(BaseModel):
    teacher_id: str
    teacher_pw: str

@app.post("/api/create-room")
async def api_create_room(req: RoomCreateRequest):
    if req.teacher_id != "t1" or req.teacher_pw != "t1":
        raise HTTPException(status_code=401, detail="교사 인증 실패 (ID: t1, PW: t1)")
    new_code = generate_random_4digit_code()
    room = get_or_create_room(new_code)
    save_active_room_code(new_code)
    return {"room_code": new_code, "status": "ok"}

@app.get("/api/rooms/active")
async def api_get_active_room():
    """선생님이 개설하여 파일(room_code.txt)에 저장된 활성 방 번호 반환"""
    saved = get_saved_room_code()
    if saved and saved not in ROOMS:
        get_or_create_room(saved)
    return {"room_code": saved, "exists": bool(saved)}

@app.get("/api/rooms/{room_code}/check")
async def api_check_room(room_code: str):
    """학생이 입력한 방 번호가 선생님 파일의 방 번호 또는 메모리 방과 일치하는지 매칭 검증"""
    saved = get_saved_room_code()
    exists = (saved is not None and room_code == saved) or (room_code in ROOMS)
    return {
        "exists": exists,
        "room_code": room_code,
        "active_room_code": saved
    }


# -------------------------------------------------------------
# 5. 실시간 WebSocket 엔드포인트
# -------------------------------------------------------------
@app.websocket("/ws/{room_code}")
async def websocket_game_endpoint(websocket: WebSocket, room_code: str):
    await websocket.accept()
    room = get_or_create_room(room_code)

    player_id: Optional[str] = None
    is_teacher: bool = False

    try:
        # 최초 연결 시 방의 최신 상태 전송
        await websocket.send_text(json.dumps({
            "type": "STATE_UPDATE",
            "state": room.to_state_dict()
        }, ensure_ascii=False))

        while True:
            text = await websocket.receive_text()
            try:
                data = json.loads(text)
            except Exception:
                continue

            msg_type = data.get("type")

            # A. 교사 인증 & 방 등록
            if msg_type == "TEACHER_CONNECT":
                t_id = data.get("teacherId")
                t_pw = data.get("teacherPw")
                if t_id == "t1" and t_pw == "t1":
                    room.teacher_ws = websocket
                    is_teacher = True
                    save_active_room_code(room_code)
                    await room.broadcast_state()

            # B. 학생 방 입장 등록
            elif msg_type == "STUDENT_JOIN":
                p_id = str(data.get("id", "")).strip()
                p_name = str(data.get("name", "")).strip()
                p_num = str(data.get("studentNumber", "")).strip() or p_id

                if p_id and p_name:
                    player_id = p_id
                    room.student_ws[player_id] = websocket
                    room.add_player(player_id, p_name, p_num, is_bot=False)
                    await room.broadcast_state()

            # C. 교사 설정 변경
            elif msg_type == "UPDATE_SETTINGS" and is_teacher:
                rounds = int(data.get("maxRounds", 5))
                mins = int(data.get("totalMinutes", 5))
                room.max_rounds = rounds
                room.total_time_seconds = mins * 60
                room.remaining_total_seconds = room.total_time_seconds
                await room.broadcast_state()

            # D. 가상 봇 추가
            elif msg_type == "ADD_BOTS" and is_teacher:
                count = int(data.get("count", 3))
                room.add_bots(count)
                await room.broadcast_state()

            # E. 게임 시작 (AI 퀴즈 단계)
            elif msg_type == "START_GAME" and is_teacher:
                if len(room.players) >= 2:
                    await room.start_quiz()

            # F. 단어 제출 (학생 or 퀴즈 정답)
            elif msg_type == "SUBMIT_WORD":
                s_id = data.get("playerId") or player_id
                word = data.get("word", "")
                if s_id and word:
                    await room.submit_word(s_id, word)

            # G. 게임 조기 종료 (교사)
            elif msg_type == "END_GAME" and is_teacher:
                await room.finish_game()

            # H. 방 리셋 및 새 방 번호 발급 (교사)
            elif msg_type == "RESET_ROOM" and is_teacher:
                new_c = generate_random_4digit_code()
                room.reset_room(new_c)
                # 룸 맵 키 갱신
                ROOMS[new_c] = room
                if room_code in ROOMS:
                    del ROOMS[room_code]
                room_code = new_c
                save_active_room_code(new_c)
                await room.broadcast_state()

    except WebSocketDisconnect:
        pass
    except Exception as e:
        print(f"[WebSocket Error] {e}")
    finally:
        if is_teacher and room.teacher_ws == websocket:
            room.teacher_ws = None
        if player_id and player_id in room.student_ws:
            del room.student_ws[player_id]


if __name__ == "__main__":
    print("=" * 60)
    print("🌿 에듀워드 파이썬 소켓 게임 서버 (FastAPI + WebSocket)")
    print("👉 접속 주소: http://localhost:8000 또는 http://<내_컴퓨터_IP>:8000")
    
    dict_key = get_korean_dict_api_key()
    if dict_key and dict_key != "YOUR_OPENAPI_KEY_HERE":
        masked_key = dict_key[:6] + "*" * (max(0, len(dict_key) - 6))
        print(f"📡 국립국어원 표준국어대사전 Open API: 연동 활성화 (인증키: {masked_key})")
    else:
        print("💡 국립국어원 Open API 키가 설정되지 않았습니다.")
        print("   -> .env 파일의 KOREAN_DICT_API_KEY 항목에 인증키를 입력하시면")
        print("      실시간 50만 표준어 검사가 즉시 연동됩니다! (현재는 로컬 사전 모드)")
    port = int(os.environ.get("PORT", 8000))
    print(f"👉 접속 포트: {port}")
    print("=" * 60)
    uvicorn.run(app, host="0.0.0.0", port=port)

