# 🚀 빠른 시작 가이드 (5분 안에!)

## Step 1: API 키 발급 (2분)

### 1.1 Telegram Bot
```
1. Telegram 앱 열기
2. @BotFather 검색
3. /newbot 입력
4. 봇 이름 입력: "Stock Alert Bot"
5. 봇 아이디 입력: "stock_alert_123_bot"
6. 토큰 받기: 1234567890:ABC...
```

### 1.2 Chat ID
```
1. @userinfobot 검색
2. 메시지 보내기
3. ID 받기: 123456789
```

### 1.3 Gemini AI
```
1. https://ai.google.dev/ 접속
2. "Get API Key" 클릭
3. 구글 로그인
4. 키 생성: AIza...
```

### 1.4 DART API
```
1. https://opendart.fss.or.kr/ 접속
2. 회원가입 (2분)
3. API 인증키 신청
4. 즉시 발급!
```

---

## Step 2: 설정 (1분)

```bash
# 1. .env 파일 생성
cp .env.example .env

# 2. 편집
nano .env
```

**.env 파일:**
```
TELEGRAM_TOKEN=1234567890:ABC...  ← Step 1.1
TELEGRAM_CHAT_ID=123456789         ← Step 1.2
GEMINI_API_KEY=AIza...             ← Step 1.3
DART_API_KEY=your_dart_key         ← Step 1.4
```

**저장:** `Ctrl+O` → `Enter` → `Ctrl+X`

---

## Step 3: 실행 (1분)

```bash
# 한 줄로 끝!
chmod +x start.sh && ./start.sh
```

---

## Step 4: 확인

### Telegram에 메시지 도착!
```
🚀 조기경보 시스템 v2.2 시작!

✅ AI Brain v2.2 (3개 모델)
✅ News Engine v2.2 (6개 소스)
✅ Momentum Tracker v2.2
✅ Predictor Engine v2.2 (고래 추적)

승률 80% 목표!
```

---

## Step 5: 명령어 테스트

```
/start   → 봇 시작 확인
/help    → 도움말
/report  → 즉시 리포트
```

---

## 트러블슈팅

### 문제 1: ModuleNotFoundError
```bash
# 해결
pip install -r requirements.txt
```

### 문제 2: DART API 오류
```
# .env 확인
cat .env | grep DART

# 키 재확인
# https://opendart.fss.or.kr/
```

### 문제 3: 봇 응답 없음
```
# Chat ID 확인
# @userinfobot에서 다시 받기
```

---

## Railway 배포 (보너스)

```bash
# 1. Railway CLI 설치
npm i -g @railway/cli

# 2. 로그인
railway login

# 3. 프로젝트 생성
railway init

# 4. 환경변수 설정
railway variables set TELEGRAM_TOKEN=xxx
railway variables set TELEGRAM_CHAT_ID=xxx
railway variables set GEMINI_API_KEY=xxx
railway variables set DART_API_KEY=xxx

# 5. 배포
railway up

# 6. 로그 확인
railway logs
```

---

## 다음 단계

1. **WHITE_PAPER.md 읽기** (필독!)
2. **첫 알림 기다리기** (30초~5분)
3. **승률 추적하기** (80% 목표)
4. **수익 내기!** 🚀

---

**남들보다 30초 빠르게, 1년에 1억!**
