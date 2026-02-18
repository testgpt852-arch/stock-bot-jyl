# -*- coding: utf-8 -*-
"""
AI Brain v3.0 - Beast Mode + Production Enhancement
- 🔥 M&A/자금조달 무조건 9-10점 (필터링 방지)
- 🎯 티커 정확도 향상: 본문 정확 추출, 추측 금지, NASDAQ 심볼 형식 검증
- 🆕 Gemma 모델 이원화 + JSON 버그 수정
- 🔧 모델별 타임아웃 추가 (블로킹 방지)
"""

from google import genai
from google.genai import types
import asyncio
import logging
import json
import re
from config import Config

logger = logging.getLogger(__name__)

# 모델별 타임아웃 (초)
_SCANNER_TIMEOUT = 15   # quick_score: 빠른 1차 필터 → 15초
_REPORT_TIMEOUT  = 35   # analyze_news_signal: 상세 분석 → 35초
_SUMMARY_TIMEOUT = 40   # generate_daily_summary → 40초


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

    async def _generate(self, model_name, prompt, use_json_mode=True, timeout=35):
        """
        🆕 모델별 분기 호출 + 타임아웃 적용
        - Gemma: JSON mime_type 미지원 → 텍스트 모드 후 _parse_json_safely
        - Gemini: JSON 모드 직접 사용
        - timeout: 초과 시 asyncio.TimeoutError → 호출부에서 다음 모델로 fallback
        """
        is_gemma = model_name in self.gemma_models

        if is_gemma or not use_json_mode:
            # Gemma: 텍스트 모드 (JSON 버그 우회)
            coro = asyncio.to_thread(
                self.client.models.generate_content,
                model=model_name,
                contents=prompt,
            )
        else:
            # Gemini: JSON 모드
            coro = asyncio.to_thread(
                self.client.models.generate_content,
                model=model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type='application/json',
                    temperature=0.3,
                ),
            )

        # 🔧 타임아웃 적용: 초과 시 TimeoutError 발생 → 다음 모델로 넘어감
        response = await asyncio.wait_for(coro, timeout=timeout)
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
                text = await self._generate(model, prompt, use_json_mode=True, timeout=_SCANNER_TIMEOUT)
                result = self._parse_json_safely(text)
                if not result:
                    logger.debug(f"[{model}] quick_score JSON 파싱 실패")
                    continue
                score = result.get('score', 0)
                logger.debug(f"[{model}] quick_score → {score}점")
                return score >= threshold
            except asyncio.TimeoutError:
                logger.warning(f"⏱️ [{model}] quick_score 타임아웃 ({_SCANNER_TIMEOUT}s) → 다음 모델")
                continue
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
        # 🔧 SEC 공시 등에서 미리 추출된 회사명 활용
        company_hint = news_item.get('company_name', '').strip()
        company_hint_line = f"\n공시 회사명 (확정): {company_hint}" if company_hint else ""

        prompt = f"""
        너는 초단타 급등주 전문 스캘퍼다. 이 뉴스를 분석해서 직접 수혜주를 찾아줘.
        
        제목: {news_item['title']}
        출처: {news_item.get('source', 'Unknown')}{company_hint_line}
        
        ══════════════════════════════════════
        ⚠️ 핵심 규칙 (반드시 지켜라):
        ══════════════════════════════════════
        
        【회사명(name) 규칙】
        - 뉴스 제목 또는 "공시 회사명"에서 회사명이 확인되면 반드시 그 이름을 사용
        - 회사명은 절대 "UNKNOWN" 금지! 제목에서 반드시 추출할 것
        - 예: "[공시] 8-K - M Evo Global Acquisition Corp II (0002087361)" → name: "M Evo Global Acquisition Corp II"
        - 예: "공시 회사명 (확정): Tesla Inc." → name: "Tesla Inc."
        
        【티커(ticker) 규칙】
        - 티커는 "(NASDAQ: XXXX)" "(NYSE: XXXX)" 형식으로 명시된 경우에만 사용
        - 괄호 안 숫자(예: 0002087361)는 SEC CIK 번호이므로 절대 티커 아님!
        - 명시되지 않은 경우에만 "UNKNOWN" 사용 (회사명은 알아도 티커 모르면 UNKNOWN OK)
        
        【점수 규칙】
        - 9-10점: M&A, $50M+ 자금조달, 대형 파트너십, 8-K 공시 (M&A/자금조달 가능성)
        - 8점: FDA 승인, 계약 완료
        - 대형주(삼성전자, 엔비디아, 애플) 1등 추천 금지
        ══════════════════════════════════════
        
        분석 요청:
        1. 급등 강도 0~10점
        2. 확실성: "confirmed" (승인/계약 완료) vs "uncertain" (예상/전망)
        3. 수혜주 1등, 2등, 3등 (회사명 + 티커 + 이유)
        4. top_ticker: 1등 티커 (명시된 경우만, 아니면 UNKNOWN)
        
        티커 추출 예시:
        - "Auddia (NASDAQ: AUUD) Announces Merger" → ticker: "AUUD", name: "Auddia"
        - "[공시] 8-K - M Evo Global Acquisition Corp II (0002087361)" → ticker: "UNKNOWN", name: "M Evo Global Acquisition Corp II"
        - "반도체 산업 전망 긍정적" → ticker: "UNKNOWN", name: "관련 반도체 ETF"
        
        JSON 형식:
        {{
            "score": 0~10,
            "certainty": "confirmed" or "uncertain",
            "summary": "핵심 요약 1줄",
            "key_catalyst": "핵심 재료",
            "ticker_in_news": "뉴스에 명시된 티커 (없으면 null)",
            "top_ticker": "수혜주 1등 티커 (명시된 경우만, 아니면 UNKNOWN)",
            "recommendations": [
                {{
                    "rank": "1등 (대장주)",
                    "ticker": "종목코드 또는 UNKNOWN",
                    "name": "반드시 실제 회사명 기재 (UNKNOWN 절대 금지)",
                    "reason": "수혜 이유"
                }},
                {{
                    "rank": "2등",
                    "ticker": "종목코드 또는 UNKNOWN",
                    "name": "반드시 실제 회사명 기재",
                    "reason": "수혜 이유"
                }},
                {{
                    "rank": "3등",
                    "ticker": "종목코드 또는 UNKNOWN",
                    "name": "반드시 실제 회사명 기재",
                    "reason": "수혜 이유"
                }}
            ],
            "risk_factors": ["리스크 1", "리스크 2"]
        }}
        """

        for model in self.report_models:
            try:
                logger.info(f"🤖 [{model}] 뉴스 분석 시작...")
                text = await self._generate(model, prompt, use_json_mode=True, timeout=_REPORT_TIMEOUT)
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

                # recommendations의 티커 검증 + 회사명 UNKNOWN 방어
                for rec in result.get('recommendations', []):
                    # 티커 형식 검증
                    ticker = rec.get('ticker', '')
                    if ticker and ticker.upper() not in ('UNKNOWN', ''):
                        ticker_clean = ticker.strip().upper()
                        if not re.match(r'^[A-Z]{1,5}$', ticker_clean):
                            logger.warning(f"❌ 추천 티커 형식 오류: {ticker}")
                            rec['ticker'] = 'UNKNOWN'

                    # 🔧 회사명 UNKNOWN 방어: AI가 name을 UNKNOWN으로 반환한 경우
                    # company_hint(SEC 파싱 회사명)가 있으면 1등에 채워줌
                    name = rec.get('name', '')
                    if (not name or name.upper() in ('UNKNOWN', 'UNKNOWN COMPANY', '')) and company_hint:
                        if rec.get('rank', '').startswith('1'):
                            rec['name'] = company_hint
                            logger.info(f"🔧 1등 회사명 복원: {company_hint}")

                return result

            except asyncio.TimeoutError:
                logger.warning(f"⏱️ [{model}] 분석 타임아웃 ({_REPORT_TIMEOUT}s) → 다음 모델")
                continue
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
                coro = asyncio.to_thread(
                    self.client.models.generate_content,
                    model=model,
                    contents=prompt,
                )
                response = await asyncio.wait_for(coro, timeout=_SUMMARY_TIMEOUT)
                return response.text
            except asyncio.TimeoutError:
                logger.warning(f"⏱️ [{model}] 요약 타임아웃 ({_SUMMARY_TIMEOUT}s) → 다음 모델")
                continue
            except Exception as e:
                logger.debug(f"[{model}] generate_daily_summary 실패: {e}")
                continue

        return "🐺 요약 생성 실패"


# Backward compatibility
AIBrain = AIBrainV3
