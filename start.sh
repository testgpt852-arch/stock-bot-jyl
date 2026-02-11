#!/bin/bash

echo "======================================"
echo "🚀 조기경보 시스템 v2.2 시작"
echo "======================================"

# 1. .env 확인
if [ ! -f .env ]; then
    echo "❌ .env 파일이 없습니다!"
    echo "📝 .env.example을 복사해서 .env를 만드세요:"
    echo "   cp .env.example .env"
    echo "   nano .env"
    exit 1
fi

# 2. Python 확인
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3가 설치되지 않았습니다!"
    exit 1
fi

# 3. venv 생성 (없으면)
if [ ! -d "venv" ]; then
    echo "📦 가상환경 생성 중..."
    python3 -m venv venv
fi

# 4. venv 활성화
echo "✅ 가상환경 활성화"
source venv/bin/activate

# 5. 패키지 설치
echo "📦 패키지 설치 중..."
pip install --upgrade pip
pip install -r requirements.txt

# 6. 봇 실행
echo "======================================"
echo "🤖 봇 실행 중..."
echo "======================================"
python3 main_v2_2.py
