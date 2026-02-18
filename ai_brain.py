# -*- coding: utf-8 -*-
"""
AI Brain v3.0 - Beast Mode + Production Enhancement
- 🔥 M&A/자금조달 무조건 9-10점 (필터링 방지)
- 🎯 티커 정확도 향상: 본문 정확 추출, 추측 금지, NASDAQ 심볼 형식 검증
- 🆕 Gemma 모델 이원화 + JSON 버그 수정
"""

from google import genai
from google.genai import types
import asyncio
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

        # 🆕 이원화 전략 (Gemma 무제한 쿼터 → 24시간 감시)
        self.scanner_models = [
            'gemma-3-27b-it',           # 무제한 쿼터 (24시간 감시)
            'gemma-3-12b-it',
            'gemini-2.5-flash-lite',    # 백업
        ]

        self.report_models = [
            'gemini-3-flash-preview',   # 고성능 (/analyze 전용)
            'gemini-2.5-flash',         # 백업
            'gemma-3-27b-it',
        ]

        # 🆕 Gemma 모델 목록 (JSON mime_type 미지원 → 텍스트 모드로 처리)
        self.gemma_models = {'gemma-3-27b-it', 'gemma-3-12b-it', 'gemma-3-4b-it'}

        logger.info("🐺 AI Brain v3.0 Beast Mode 초기화 (Gemma 이원화 적용)")

    def _parse_json_safely(self, text):
        """AI 응답에서 JSON 정밀 추출 (마크다운 + 중괄호 파싱)"""
        try:
            if not text:
                return None
            # 마크다운 코드블록 제거
            text = re.sub(r'```json\s*', '', text)
            text = re.sub(r'```\s*', '', text)
            # 중괄호 범위 추출
            start_idx = text.find('{')
            end_idx = text.rfind('}')
            if start_idx == -1 or end_idx == -1:
                return None
            return json.loads(text[start_idx:end_idx + 1])
        except Exception:
            return None

    async def _generate(self, model_name, prompt, use_json_mode=True):
        """
        🆕 모델별 분기 호출
        - Gemma: JSON mime_type 미지원 → 텍스트 모드 후 _parse_json_safely
        - Gemini: JSON 모드 직접 사용
        """
        is_gemma = model_name in self.gemma_models

        if is_gemma or not use_json_mode:
            # Gemma: 텍스트 모드 (JSON 버그 우회)
            response = await asyncio.to_thread(
                self.client.models.generate_content,
                model=model_name,
                contents=prompt,
            )
        else:
            # Gemini: JSON 모드
            response = await asyncio.to_thread(
                self.client.models.generate_content,
                model=model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type='application/json',
                    temperature=0.3,
                ),
            )

        return response.text

    async def quick_score(self, title, threshold=8.0):
        """
        🔥 v3.0 Beast Mode + 강화: 빠른 1차 필터 (제목만)
        ⚡ M&A/자금조달 키워드 감지 시 무조건 9-10점
        """
        prompt = f"""
        너는 초단타 급등주 전문 스캘퍼다. 뉴스 제목만 보고 상한가 가능성을 0~10점으로 평가해라.
        
        제목: {title}
        
        ⚠️ 최우선 규칙 (이 키워드 있으면 무조건 9-10점):
        - M&A: "acquisition", "merger", "acquired", "merge"
        - 자금조달: "$100M", "$200M", "private placement", "financing", "raises"
        - 파트너십: "partnership with [대형 기업]", "collaboration with [유명 기업]"
        
        평가 기준:
        - 9~10점: M&A, 대규모 자금조달($50M+), 대형 파트너십 (NVIDIA, Microsoft 등)
        - 8점: FDA 승인, 정부 계약, 최대주주 변경
        - 5~7점: 임상 데이터, 중소형 파트너십, 실적 서프라이즈
        - 0~4점: 의견, 전망, 분석, 리포트
        
        JSON 형식:
        {{"score": 숫자}}
        """

        for model in self.scanner_models:
            try:
                text = await self._generate(model, prompt, use_json_mode=True)
                result = self._parse_json_safely(text)
                if not result:
                    logger.debug(f"[{model}] quick_score JSON 파싱 실패")
                    continue
                score = result.get('score', 0)
                logger.debug(f"[{model}] quick_score → {score}점")
                return score >= threshold
            except Exception as e:
                logger.debug(f"[{model}] quick_score 실패: {e}")
                continue

        return False

    async def analyze_news_signal(self, news_item):
        """
        🔥 v3.0 Beast Mode + 강화: 상세 뉴스 분석 + 티커 정확도 향상
        ✅ top_ticker: 1등 대장주 티커를 별도 키로 반환
        🎯 티커 정확도: 본문에서 명확히 추출, 추측 금지, NASDAQ 심볼 형식 검증
        """
        prompt = f"""
        너는 초단타 급등주 전문 스캘퍼다. 이 뉴스를 분석해서 직접 수혜주를 찾아줘.
        
        제목: {news_item['title']}
        출처: {news_item.get('source', 'Unknown')}
        
        ⚠️ 최우선 규칙:
        1. M&A/자금조달 뉴스는 무조건 9-10점
        2. 티커는 뉴스 본문에 명시된 것만 사용 (추측 금지!)
        3. 티커 형식: 1~5자 영문 대문자 (예: AAPL, TSLA, NVDA)
        4. 뉴스에 티커가 없으면 "UNKNOWN" 입력
        
        분석 요청:
        1. 급등 강도 0~10점
           - 9-10점: M&A, $50M+ 자금조달, 대형 파트너십
           - 8점: FDA 승인, 계약 완료
        2. 확실성: "confirmed" (승인/계약 완료) vs "uncertain" (예상/전망)
        3. 직접 수혜주 1등, 2등, 3등 (티커, 기업명, 이유)
        4. top_ticker: 수혜주 1등의 티커 (가장 확실한 대장주)
        
        🔥 티커 추출 규칙 (매우 중요!):
        - 뉴스 제목에 "(NASDAQ: TSLA)" 같은 표기가 있으면 그대로 사용
        - 뉴스 본문에 "Tesla Inc. (NASDAQ: TSLA)" 같은 명시가 있으면 추출
        - 확실하지 않으면 무조건 "UNKNOWN" (틀린 티커보다 낫다!)
        - 대형주(삼성전자, 엔비디아, 애플) 추천 금지
        
        예시:
        - "Auddia (NASDAQ: AUUD) Announces Merger" → top_ticker: "AUUD"
        - "Sensei Biotherapeutics (NASDAQ: SNSE)" → top_ticker: "SNSE"
        - "Rackspace Technology (NASDAQ: RXT)" → top_ticker: "RXT"
        - "반도체 산업 전망 긍정적" → top_ticker: "UNKNOWN"
        
        JSON 형식:
        {{
            "score": 0~10,
            "certainty": "confirmed" or "uncertain",
            "summary": "핵심 요약 1줄",
            "key_catalyst": "핵심 재료",
            "ticker_in_news": "뉴스에 명시된 종목명/티커 (없으면 null)",
            "top_ticker": "수혜주 1등 티커 (확실한 경우만, 아니면 UNKNOWN)",
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
        
        ⚠️ 다시 강조: 
        - M&A/자금조달은 무조건 9-10점!
        - 티커는 본문에 명시된 것만! 추측 절대 금지!
        - 확실하지 않으면 "UNKNOWN" 입력!
        """

        for model in self.report_models:
            try:
                logger.info(f"🤖 [{model}] 뉴스 분석 시작...")
                text = await self._generate(model, prompt, use_json_mode=True)
                result = self._parse_json_safely(text)
                if not result:
                    logger.warning(f"❌ [{model}] JSON 파싱 실패")
                    continue

                score = result.get('score', 0)
                logger.info(f"✅ [{model}] 분석 성공 → 점수: {score}/10")

                if score < 7:
                    return None

                # top_ticker 정규화 + 형식 검증
                top_ticker = result.get('top_ticker', 'UNKNOWN')
                if not top_ticker or top_ticker.lower() in ('null', 'unknown', ''):
                    result['top_ticker'] = None
                else:
                    ticker_clean = top_ticker.strip().upper()
                    if re.match(r'^[A-Z]{1,5}$', ticker_clean):
                        result['top_ticker'] = ticker_clean
                    else:
                        logger.warning(f"❌ 잘못된 티커 형식: {top_ticker} → UNKNOWN")
                        result['top_ticker'] = None

                # recommendations의 티커도 검증
                for rec in result.get('recommendations', []):
                    ticker = rec.get('ticker', '')
                    if ticker and ticker.upper() not in ('UNKNOWN', ''):
                        ticker_clean = ticker.strip().upper()
                        if not re.match(r'^[A-Z]{1,5}$', ticker_clean):
                            logger.warning(f"❌ 추천 티커 형식 오류: {ticker}")
                            rec['ticker'] = 'UNKNOWN'

                return result

            except Exception as e:
                logger.warning(f"❌ [{model}] analyze_news_signal 실패: {e}")
                continue

        return None

    async def generate_daily_summary(self, signals):
        """일일 요약 리포트"""
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
                # 요약은 텍스트 그대로 반환 (JSON 불필요)
                response = await asyncio.to_thread(
                    self.client.models.generate_content,
                    model=model,
                    contents=prompt,
                )
                return response.text
            except Exception as e:
                logger.debug(f"[{model}] generate_daily_summary 실패: {e}")
                continue

        return "🐺 요약 생성 실패"


# Backward compatibility
AIBrain = AIBrainV3