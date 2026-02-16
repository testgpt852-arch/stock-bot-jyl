# -*- coding: utf-8 -*-
"""
AI Brain v3.0 - Beast Mode (야수 모드)
- 🔥 페르소나 변경: 보수적 전략가 → 공격적 스캘퍼
- 프롬프트 개조: 안정성 무시, 텐버거 가능성 포착
- 관련주 찾기: 직접 수혜주 우선 (대형주 배제)
- Gemini 2.5 Flash 계열 사용 (사용자 제공 모델 목록 준수)
"""

from google import genai
from google.genai import types
import logging
import json
import re
from config import Config

logger = logging.getLogger(__name__)

class AIBrainV3:
    def __init__(self):
        self.api_key = Config.GEMINI_API_KEY
        
        if not self.api_key:
            raise ValueError("❌ GEMINI_API_KEY 필수!")
        
        self.client = genai.Client(api_key=self.api_key)
        
        # 🔥 v3.0: 사용자 제공 모델 목록 사용
        # Gemini 2.5 Flash, Gemini 2.5 Flash Lite, Gemini 3 Flash
        self.scanner_models = [
            'gemini-2.5-flash',          # 1순위
            'gemini-2.5-flash-lite',     # 백업
            'gemini-3-flash'             # 백업 (Preview)
        ]
        
        self.report_models = [
            'gemini-3-flash',            # 고성능
            'gemini-2.5-flash',          # 백업
            'gemini-2.5-flash-lite'      # 백업
        ]
        
        logger.info("🐺 AI Brain v3.0 Beast Mode 초기화")

    def _parse_json_safely(self, text):
        """
        AI 응답에서 JSON 데이터만 정밀하게 추출
        """
        try:
            if not text:
                return None

            # 1. 마크다운 코드 블록 제거
            text = re.sub(r'```json\s*', '', text)
            text = re.sub(r'```\s*', '', text)
            
            # 2. 가장 처음 '{' 와 가장 마지막 '}' 찾기
            start_idx = text.find('{')
            end_idx = text.rfind('}')
            
            if start_idx == -1 or end_idx == -1:
                return None
            
            # 3. 정확히 JSON 구간만 잘라냄
            json_str = text[start_idx : end_idx + 1]
            
            return json.loads(json_str)
        except Exception:
            return None
    
    async def quick_score(self, title, threshold=8.0):
        """
        🔥 v3.0 Beast Mode: 빠른 1차 필터 (제목만)
        - 보수적 관점 폐기
        - 8점 이상: 상한가 가능성 있는 확실한 호재
        """
        prompt = f"""
        너는 초단타 급등주 전문 스캘퍼다. 뉴스 제목만 보고 상한가 가능성을 0~10점으로 평가해라.
        
        제목: {title}
        
        평가 기준:
        - 8~10점: FDA 승인, M&A, 정부 계약, 최대주주 변경, 긴급 공시 등 확실한 호재
        - 5~7점: 임상 데이터, 파트너십, 실적 서프라이즈 등 중간 호재
        - 0~4점: 의견, 전망, 분석, 리포트 등 잡담
        
        ⚠️ 중요: 안정성 따지지 마라. 급등 가능성만 판단해라.
        
        JSON 형식:
        {{"score": 숫자}}
        """
        
        for model in self.scanner_models:
            try:
                config = types.GenerateContentConfig(
                    response_mime_type='application/json',
                    temperature=0.3
                )
                
                response = await self.client.aio.models.generate_content(
                    model=model,
                    contents=prompt,
                    config=config
                )
                
                result = self._parse_json_safely(response.text)
                
                if not result:
                    continue
                
                score = result.get('score', 0)
                return score >= threshold
                
            except Exception as e:
                logger.debug(f"[{model}] quick_score 실패: {e}")
                continue
        
        return False
    
    async def analyze_news_signal(self, news_item):
        """
        🔥 v3.0 Beast Mode: 상세 뉴스 분석 + 직접 수혜주 찾기
        - 대형주(삼성전자, 엔비디아) 추천 금지
        - 시총 작아도 직접적인 수혜주를 찾아내라
        - 뉴스에 종목명/티커 언급 시 무조건 1순위
        """
        prompt = f"""
        너는 초단타 급등주 전문 스캘퍼다. 이 뉴스를 분석해서 직접 수혜주를 찾아줘.
        
        제목: {news_item['title']}
        출처: {news_item.get('source', 'Unknown')}
        
        분석 요청:
        1. 급등 강도 0~10점 (8점 미만은 무시)
        2. 확실성: "confirmed" (승인/계약 완료) vs "uncertain" (예상/전망)
        3. 직접 수혜주 1등, 2등, 3등 (티커, 기업명, 이유)
        
        🔥 핵심 룰:
        - 뉴스에 종목명/티커가 명시되어 있다면 반드시 그 종목을 1순위로 잡아라
        - 대형주(삼성전자, SK하이닉스, 엔비디아, 애플, 마이크로소프트) 추천 금지
        - 시총이 작더라도 직접 수혜를 받는 종목을 찾아라
        - 관련주 찾기가 어렵다면 "UNKNOWN"으로 표시해라 (억지로 대형주 넣지 마라)
        
        예시:
        - "RIME Announces Partnership with Nvidia" → 1등: RIME (주인공), 2등: 물류/AI 관련주
        - "삼성바이오로직스, FDA 승인" → 1등: 삼성바이오로직스 (주인공)
        - "반도체 산업 전망 긍정적" → UNKNOWN (뉴스가 애매함)
        
        JSON 형식:
        {{
            "score": 0~10,
            "certainty": "confirmed" or "uncertain",
            "summary": "핵심 요약 1줄",
            "key_catalyst": "핵심 재료",
            "ticker_in_news": "뉴스에 명시된 종목명/티커 (없으면 null)",
            "recommendations": [
                {{
                    "rank": "1등 (대장주)",
                    "ticker": "종목코드",
                    "name": "회사명",
                    "reason": "수혜 이유"
                }},
                {{
                    "rank": "2등",
                    "ticker": "종목코드",
                    "name": "회사명",
                    "reason": "수혜 이유"
                }},
                {{
                    "rank": "3등",
                    "ticker": "종목코드",
                    "name": "회사명",
                    "reason": "수혜 이유"
                }}
            ],
            "risk_factors": ["리스크 1", "리스크 2"]
        }}
        
        ⚠️ 다시 강조: 뉴스에 종목이 명시되어 있다면 무조건 그 종목을 1순위로!
        """
        
        for model in self.report_models:
            try:
                config = types.GenerateContentConfig(
                    response_mime_type='application/json',
                    temperature=0.4
                )
                
                response = await self.client.aio.models.generate_content(
                    model=model,
                    contents=prompt,
                    config=config
                )
                
                result = self._parse_json_safely(response.text)
                
                if not result:
                    continue
                
                # 검증
                score = result.get('score', 0)
                if score < 7:
                    return None
                
                return result
                
            except Exception as e:
                logger.debug(f"[{model}] analyze_news_signal 실패: {e}")
                continue
        
        return None
    
    async def generate_daily_summary(self, signals):
        """
        일일 요약 리포트
        """
        if not signals:
            return "🐺 오늘은 사냥감이 없습니다. 내일을 기약합니다."
        
        top_signals = signals[:5]
        
        prompt = f"""
        너는 초단타 급등주 전문 스캘퍼다. 오늘의 핵심 이슈를 요약해줘.
        
        주요 시그널:
        {json.dumps(top_signals, ensure_ascii=False, indent=2)}
        
        요약 형식:
        1. 오늘의 핵심 테마 (2~3줄)
        2. 주목할 종목 TOP 3 (종목명 + 이유)
        3. 리스크 요인
        
        ⚠️ 스타일: 간결하고 공격적으로 (상한가 예측은 피하되, 급등 가능성은 언급)
        """
        
        for model in self.report_models:
            try:
                response = await self.client.aio.models.generate_content(
                    model=model,
                    contents=prompt
                )
                
                return response.text
                
            except Exception as e:
                logger.debug(f"[{model}] generate_daily_summary 실패: {e}")
                continue
        
        return "🐺 요약 생성 실패"
