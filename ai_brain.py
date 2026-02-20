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

        # 🆕 뉴스 분석 전용 (Gemma 우선 → Gemini 쿼터 절약)
        # analyze_news_signal 전용: Gemma가 충분히 강력하고 무제한
        self.news_models = [
            'gemma-3-27b-it',           # 무제한 쿼터 (24시간 뉴스 분석)
            'gemma-3-12b-it',           # 백업
            'gemini-2.5-flash-lite',    # 최후 백업
        ]

        # /analyze 명령어 전용 (Gemini 고성능)
        self.report_models = [
            'gemini-3-flash-preview',   # 고성능 (/analyze 전용)
            'gemini-2.5-flash',         # 백업
            'gemma-3-27b-it',           # 최후 백업
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
            # Gemma: 텍스트 모드 (JSON 버그 우회) + temperature 고정
            coro = asyncio.to_thread(
                self.client.models.generate_content,
                model=model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.3,  # 일관성 확보 (기본값 ~1.0 방지)
                ),
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
        ⚠️ DEPRECATED: AI 호출 방식의 1차 필터 (비효율 → 사용 중단)
        현재는 Config.keyword_score() 순수 코드 방식으로 대체됨.
        이 함수는 하위 호환성을 위해 유지하지만 호출되지 않음.

        구버전 동작:
        🔥 v3.0 Beast Mode + 강화: 빠른 1차 필터 (제목만)
        ⚡ M&A/자금조달 키워드 감지 시 무조건 9-10점
        """
        prompt = f"""
        너는 초단타 급등주 전문 스캘퍼다. 뉴스 제목만 보고 상한가 가능성을 0~10점으로 평가해라.
        
        제목: {title}
        
        ══════════════════════════════════════
        ⚠️ 최우선 규칙 (이 키워드 있으면 무조건 9-10점):
        ══════════════════════════════════════
        [영어 M&A]
        "acquisition", "merger", "acquired", "merge", "buyout", "takeover",
        "tender offer", "definitive agreement", "going private", "take private"
        
        [한국어 M&A/지배구조]
        "인수합의", "인수완료", "합병완료", "경영권 인수", "최대주주 변경",
        "경영권 분쟁", "적대적 M&A", "공개매수"
        
        [영어 자금조달/계약]
        "$100M", "$200M", "$500M", "$1B", "private placement", "raises",
        "contract win", "contract award", "awarded contract", "major contract"
        
        [한국어 계약/수주]
        "대규모 수주", "공급 계약", "납품 계약", "독점 공급", "수출 계약",
        "정부 계약", "최대 수주", "역대 최대 계약"
        
        [영어 바이오]
        "fda approval", "fda approved", "fda clearance", "breakthrough designation",
        "phase 3 success", "primary endpoint met", "positive topline"
        
        [한국어 바이오]
        "임상 성공", "FDA 승인", "허가 획득", "신약 허가"
        
        ══════════════════════════════════════
        ⚠️ 악재 감지 시 무조건 0-2점:
        ══════════════════════════════════════
        "유상증자" (단, "유상증자 철회/취소"는 9점!),
        "상장폐지", "관리종목", "감자", "파산", "bankruptcy",
        "delisting", "going concern", "class action", "fda rejection",
        "crl", "clinical hold", "failed to meet", "recall",
        "investigation", "securities fraud", "reverse split"
        
        ══════════════════════════════════════
        일반 평가 기준:
        ══════════════════════════════════════
        - 8점: FDA 승인, 정부 계약 완료, 대형 파트너십 (NVIDIA/MS 등)
        - 7점: 임상 긍정적 데이터, 중형 계약, 실적 서프라이즈
        - 5~6점: 소규모 제휴, 제품 출시, 소형 계약
        - 3~4점: 의견, 전망, 분석 리포트
        - 0~2점: 악재 키워드 또는 명백한 노이즈
        
        JSON 형식:
        {{"score": 숫자, "reason": "판단 근거 한 줄"}}
        """

        for model in self.scanner_models:
            try:
                text = await self._generate(model, prompt, use_json_mode=True, timeout=_SCANNER_TIMEOUT)
                result = self._parse_json_safely(text)
                if not result:
                    logger.debug(f"[{model}] quick_score JSON 파싱 실패")
                    continue
                score = result.get('score', 0)
                reason = result.get('reason', '')
                logger.debug(f"[{model}] quick_score → {score}점 | {reason}")
                return score >= threshold
            except asyncio.TimeoutError:
                logger.warning(f"⏱️ [{model}] quick_score 타임아웃 ({_SCANNER_TIMEOUT}s) → 다음 모델")
                continue
            except Exception as e:
                logger.debug(f"[{model}] quick_score 실패: {e}")
                continue

        return False

    async def analyze_news_signal(self, news_item, min_score: int = 7):
        """
        🔥 v3.0 Beast Mode + 강화: 상세 뉴스 분석 + 티커 정확도 향상
        ✅ top_ticker: 1등 대장주 티커를 별도 키로 반환
        🎯 티커 정확도: 본문에서 명확히 추출, 추측 금지, NASDAQ 심볼 형식 검증
        🆕 news_models (Gemma) 전용: Gemini 쿼터 절약 → /analyze 전용
        🆕 min_score: 소스 신뢰도 기반 threshold (telegram_bot에서 전달)
        """
        # 🔧 SEC 공시 등에서 미리 추출된 회사명 활용
        company_hint = news_item.get('company_name', '').strip()
        company_hint_line = f"\n공시 회사명 (확정): {company_hint}" if company_hint else ""

        # 본문 추출 (최대 600자)
        content_raw = news_item.get('content', news_item.get('body', ''))
        content_line = f"\n본문: {content_raw[:600]}" if content_raw else ""

        prompt = f"""
        너는 주식 트레이딩 전문가다. 이 뉴스를 깊이 분석해서 수혜주를 찾아줘.
        
        제목: {news_item['title']}
        출처: {news_item.get('source', 'Unknown')}{company_hint_line}{content_line}
        
        ══════════════════════════════════════
        ⛔ 절대 금지 (위반 시 시스템 오류로 간주):
        ══════════════════════════════════════
        1. 본문/제목에 명시되지 않은 기업을 '수혜주'로 추천하지 마라.
        2. 특히 아래 기업들은 뉴스와 직접 관련(계약·지분·파트너십·공식 언급)이 없으면 절대 추천 금지:
           - SOOP (067160): 스트리밍 플랫폼. 관련 없는 뉴스에 반복적으로 나옴 → 철저히 금지
           - 애경산업 (018250): 화장품 ODM. 미용 관련이어도 직접 언급 없으면 금지
           - 미래에셋증권 (006800): 증권사. 금융 뉴스라도 직접 관련 없으면 금지
        3. 삼성전자 (005930)는 반도체·스마트폰·가전 분야 기업임. 삼성화재·삼성증권 등 다른 삼성 계열사와 혼동 금지.
        4. 미국 기업 뉴스에서 한국 종목을 간접수혜로 추천하지 마라.
           - "A가 B에 부품을 납품하므로 A가 수혜" 같은 6단계 논리 금지
           - 한국 종목은 뉴스에 한국 기업이 명시적으로 언급된 경우에만 추천
        5. 관련 수혜주가 없으면 recommendations를 빈 리스트([])로 반환해라. 억지로 채우지 마라.
        5. "AI 관련", "K-뷰티 관련" 같은 막연한 이유로 연관 없는 기업을 넣지 마라.
        
        ⛔ 뒷북 방지:
        - "상한가", "신고가 경신", "무더기 상한가", "폭등 마감" 등 이미 결과가 나온 뉴스 → score 0점
        - 스캘핑 봇은 "오르기 전" 재료를 찾는다
        
        ⛔ 저품질 뉴스 필터:
        - 교육 과정 홍보, 행사 안내, 비영리재단 프로그램, 세무/회계 소프트웨어 출시 → score 1~3점
        - 비상장 소기업 제품 출시 보도자료 (수혜 상장사 없음) → score 2~4점
        - 주가 직접 영향 없는 홍보성 보도자료 → score 3점 이하
        ══════════════════════════════════════
        
        분석 가이드:
        1. 회사명: 뉴스 제목/본문에서 정확히 추출. UNKNOWN 금지.
        2. 티커:
           - 한국: 6자리 숫자만. 확실히 아는 경우에만 사용. 모르면 반드시 "비상장"
           - 주요 한국 티커: 삼성전자=005930, 삼성화재=000810, 삼성증권=016360,
             LG화학=051910, SK하이닉스=000660, SOOP=067160, 애경산업=018250,
             한국콜마=161890, 두산에너빌리티=034020, 미래에셋증권=006800
           - 미국: 정확한 심볼만. 모르면 "비상장"
        3. 점수:
           - 9~10점: M&A 확정, FDA 승인, 대규모 수주 확정
           - 7~8점: 임상 성공, 실적 서프라이즈, 구체적 파트너십
           - 4~6점: 제품 출시, 소규모 계약, 간접 테마
           - 0~3점: 홍보성, 뒷북, 저품질
        
        JSON 형식:
        {{
            "score": 0~10 정수,
            "certainty": "confirmed" or "uncertain",
            "news_reliability": "high" or "medium" or "low",
            "summary": "핵심 요약 1줄",
            "key_catalyst": "핵심 재료",
            "surge_timing": "단기(당일~3일)" or "중기(1~2주)" or "없음",
            "ticker_in_news": "뉴스에 명시된 티커 (없으면 null)",
            "top_ticker": "가장 큰 수혜주 1개 티커 (확실한 경우만, 불확실하면 null)",
            "recommendations": [
                {{
                    "rank": "1등",
                    "ticker": "확실한 티커 (모르면 비상장)",
                    "name": "실제 회사명 (UNKNOWN 금지)",
                    "benefit_type": "직접수혜" or "간접수혜",
                    "reason": "본문 근거 구체적 이유 (20자 이상)"
                }}
            ]
        }}
        """

        for model in self.news_models:
            try:
                logger.info(f"🤖 [{model}] 뉴스 분석 시작...")
                text = await self._generate(model, prompt, use_json_mode=True, timeout=_REPORT_TIMEOUT)
                result = self._parse_json_safely(text)
                if not result:
                    logger.warning(f"❌ [{model}] JSON 파싱 실패")
                    continue

                score = result.get('score', 0)
                logger.info(f"✅ [{model}] 분석 성공 → 점수: {score}/10")

                # 🆕 min_score: 소스 신뢰도 기반 threshold 적용
                if score < min_score:
                    logger.debug(f"⏭️ [{model}] 점수 부족 ({score} < {min_score}) → 스킵")
                    return None

                # top_ticker 정규화
                top_ticker = result.get('top_ticker', '')
                if not top_ticker or top_ticker.lower() in ('null', 'unknown', ''):
                    result['top_ticker'] = None
                else:
                    result['top_ticker'] = top_ticker.strip()

                # 🚫 환각 필터: 본문/제목에 없는 SOOP/애경산업/삼성전자 등 제거
                news_text = (news_item['title'] + ' ' + content_raw).upper()
                # 미국 뉴스 여부 확인
                is_us_news = news_item.get('market', 'US') == 'US'

                HALLUCINATION_GUARD = {
                    # 한국 환각 빈도 높은 종목: 본문에 없으면 무조건 제거
                    '067160': 'SOOP',
                    '018250': '애경',
                    '006800': '미래에셋',
                    # 삼성전자: 미국 뉴스에서 특히 자주 환각으로 나옴
                    '005930': '삼성',
                    # 기타 자주 환각되는 대형주
                    '000660': 'SK하이닉스',
                    '051910': 'LG화학',
                    '035420': 'NAVER',
                }
                filtered_recs = []
                for rec in result.get('recommendations', []):
                    ticker = rec.get('ticker', '').strip()
                    name   = rec.get('name', '').strip()

                    # 회사명 UNKNOWN 방어
                    if (not name or name.upper() in ('UNKNOWN', 'UNKNOWN COMPANY', '')) and company_hint:
                        if rec.get('rank', '').startswith('1'):
                            rec['name'] = company_hint

                    # 🚫 미국 뉴스에서 한국 6자리 종목코드 추천 → 거의 항상 환각
                    if is_us_news and ticker.isdigit() and len(ticker) == 6:
                        logger.warning(f"🚫 미국뉴스에서 한국주 추천: {name}({ticker}) → 제거")
                        continue

                    # 환각 체크: 해당 기업 이름이 본문에 없으면 제거
                    guard_name = HALLUCINATION_GUARD.get(ticker)
                    if guard_name and guard_name not in news_text:
                        logger.warning(f"🚫 환각 필터: {name}({ticker}) 본문에 없음 → 제거")
                        continue

                    # reason 너무 짧으면 제거 (환각 추천은 이유가 막연함)
                    if len(rec.get('reason', '')) < 10:
                        continue

                    filtered_recs.append(rec)

                result['recommendations'] = filtered_recs

                # top_ticker도 환각 필터 적용
                tt = result.get('top_ticker')
                if tt:
                    # 미국 뉴스에서 한국 6자리 코드
                    if is_us_news and tt.isdigit() and len(tt) == 6:
                        logger.warning(f"🚫 top_ticker 미국뉴스 한국주: {tt} 제거")
                        result['top_ticker'] = None
                    else:
                        guard_name = HALLUCINATION_GUARD.get(tt)
                        if guard_name and guard_name not in news_text:
                            logger.warning(f"🚫 top_ticker 환각: {tt} 제거")
                            result['top_ticker'] = None

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
        너는 초단타 급등주 전문 스캘퍼다. 오늘의 핵심 이슈를 분석해서 요약해줘.

        주요 시그널:
        {json.dumps(top_signals, ensure_ascii=False, indent=2)}

        ══════════════════════════════════════
        분석 요청:
        ══════════════════════════════════════
        1. 오늘의 핵심 테마 (2~3줄)
           - 시그널들 사이에 공통 테마나 연결고리가 있는가?
           - 오늘 시장에서 가장 주목받을 섹터는?

        2. 주목할 종목 TOP 3
           - 종목명 + 티커 + 한 줄 이유
           - 직접 수혜 종목 우선 선정

        3. 내일 주목할 이벤트/촉매
           - 오늘 뉴스의 후속 반응으로 내일 움직일 종목이나 섹터
           - 예정된 발표, 실적, 이벤트 등

        4. 리스크 요인 (간단히)

        ⚠️ 스타일: 간결하고 직접적으로. 추측은 "가능성" 표현 사용.
        """

        for model in self.report_models:
            try:
                # 요약은 텍스트 그대로 반환 (JSON 불필요)
                coro = asyncio.to_thread(
                    self.client.models.generate_content,
                    model=model,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        temperature=0.3,
                    ),
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

    async def analyze_stock_on_demand(self, ticker_name: str, symbol: str, info: dict) -> str:
        """
        /analyze 명령어 전용: 종목 심층 분석
        yfinance info + AI 지식을 결합해서 텍스트 리포트 반환
        """
        # info에서 가져올 수 있는 기본 정보
        sector      = info.get('sector', '알 수 없음')
        industry    = info.get('industry', '알 수 없음')
        market_cap  = info.get('marketCap', 0)
        pe_ratio    = info.get('trailingPE', None)
        description = info.get('longBusinessSummary', '')[:300] if info.get('longBusinessSummary') else ''

        cap_str = f"{market_cap/1e12:.1f}조원" if market_cap > 1e12 else \
                  f"{market_cap/1e8:.0f}억원" if market_cap > 1e8 else \
                  f"${market_cap/1e9:.1f}B" if market_cap > 1e9 else "미확인"

        prompt = f"""
        너는 주식 전문 애널리스트다. 다음 종목을 종합적으로 분석해줘.

        종목명: {ticker_name}
        심볼: {symbol}
        섹터: {sector}
        업종: {industry}
        시가총액: {cap_str}
        {f"PER: {pe_ratio:.1f}" if pe_ratio else ""}
        {f"사업 개요: {description}" if description else ""}

        ══════════════════════════════════════
        분석 항목 (반드시 포함):
        ══════════════════════════════════════
        1. 📌 종목 핵심 요약 (2~3줄)
           - 이 회사가 뭘 하는 곳인지
           - 현재 시장 포지션

        2. 🔥 현재 주목 이유
           - 최근 이슈나 테마가 있는가?
           - 업황은 좋은가 나쁜가?

        3. 📈 단기 급등 가능성 (0~10점)
           - 점수와 근거

        4. ⚠️ 주요 리스크
           - 2~3가지 간결하게

        5. 💡 투자 포인트 한 줄 요약

        ⚠️ 스타일: 간결하고 실용적으로. 모르면 솔직하게 "정보 부족"이라고 해라.
        투자 권유가 아닌 정보 제공임을 마지막에 한 줄 명시.
        """

        for model in self.report_models:
            try:
                coro = asyncio.to_thread(
                    self.client.models.generate_content,
                    model=model,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        temperature=0.3,
                    ),
                )
                response = await asyncio.wait_for(coro, timeout=_REPORT_TIMEOUT)
                return response.text
            except asyncio.TimeoutError:
                logger.warning(f"⏱️ [{model}] analyze_stock_on_demand 타임아웃 → 다음 모델")
                continue
            except Exception as e:
                logger.warning(f"❌ [{model}] analyze_stock_on_demand 실패: {e}")
                continue

        return None


# Backward compatibility
AIBrain = AIBrainV3
