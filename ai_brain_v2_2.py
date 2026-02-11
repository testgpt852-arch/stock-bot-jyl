# -*- coding: utf-8 -*-
"""
AI Brain v2.2 - 완전체
- 다중 모델 fallback (3개)
- Gemma JSON 버그 대응
- 종목 없이 수혜주 찾기
"""

from google import genai
from google.genai import types
import logging
import json
import re
from config import Config

logger = logging.getLogger(__name__)

class AIBrainV2_2:
    def __init__(self):
        self.api_key = Config.GEMINI_API_KEY
        
        if not self.api_key:
            raise ValueError("❌ GEMINI_API_KEY 필수!")
        
        self.client = genai.Client(api_key=self.api_key)
        
        # 모델 전략 (기존 검증됨)
        self.scanner_models = [
            'gemma-3-27b-it',          # 무제한 쿼터 (1순위)
            'gemma-3-12b-it',          # 백업
            'gemini-2.5-flash-lite'    # 백업
        ]
        
        self.report_models = [
            'gemini-3-flash-preview',  # 고성능
            'gemini-2.5-flash',        # 백업
            'gemma-3-27b-it'
        ]
        
        # Gemma 모델 목록 (JSON 모드 미지원)
        self.gemma_models = {
            'gemma-3-27b-it',
            'gemma-3-12b-it',
            'gemma-3-4b-it'
        }
        
        logger.info("🤖 AI Brain v2.2 초기화")
    
    async def quick_score(self, title, threshold=8.0):
        """
        빠른 1차 필터 (제목만)
        """
        prompt = f"""
        뉴스 제목만 보고 투자 가치를 0~10점으로 평가해.
        
        제목: {title}
        
        8점 이상: FDA 승인, M&A, 정부 계약 등 확실한 호재
        7점 이하: 의견, 전망, 잡담
        
        JSON 형식:
        {{"score": 숫자}}
        """
        
        for model in self.scanner_models:
            try:
                is_gemma = model in self.gemma_models
                
                if is_gemma:
                    config = types.GenerateContentConfig(temperature=0.3)
                else:
                    config = types.GenerateContentConfig(
                        response_mime_type='application/json',
                        temperature=0.3
                    )
                
                response = await self.client.aio.models.generate_content(
                    model=model,
                    contents=prompt,
                    config=config
                )
                
                text = response.text
                
                if is_gemma or '```' in text:
                    text = re.sub(r'```json\n|```', '', text).strip()
                
                result = json.loads(text)
                score = result.get('score', 0)
                
                return score >= threshold
                
            except Exception as e:
                logger.debug(f"[{model}] quick_score 실패: {e}")
                continue
        
        return False
    
    async def analyze_news_signal(self, news_item):
        """
        상세 뉴스 분석 + 수혜주 찾기
        종목 없어도 OK!
        """
        prompt = f"""
        너는 글로벌 주식 전략가야. 이 뉴스를 분석해서 수혜주를 찾아줘.
        
        제목: {news_item['title']}
        출처: {news_item.get('source', 'Unknown')}
        
        분석 요청:
        1. 호재 강도 0~10점 (8점 미만은 잡담)
        2. 확실성: "confirmed" (승인됨, 계약됨) vs "uncertain" (예상, 전망)
        3. 수혜주 1등, 2등, 3등 (티커, 기업명, 이유)
        
        JSON 형식:
        {{
            "score": 0~10,
            "certainty": "confirmed" or "uncertain",
            "summary": "핵심 요약 1줄",
            "key_catalyst": "핵심 재료",
            "recommendations": [
                {{
                    "rank": "1등 (대장주)",
                    "ticker": "AAPL",
                    "name": "Apple",
                    "reason": "이유",
                    "confidence": 0.9,
                    "expected_return_30min": 5.0,
                    "expected_return_1day": 15.0
                }},
                {{"rank": "2등", ...}},
                {{"rank": "3등", ...}}
            ],
            "entry_timing": "immediate" or "wait_for_dip" or "avoid",
            "risk_factors": ["리스크1", "리스크2"]
        }}
        """
        
        for model in self.scanner_models:
            try:
                is_gemma = model in self.gemma_models
                
                if is_gemma:
                    config = types.GenerateContentConfig(temperature=0.5)
                else:
                    config = types.GenerateContentConfig(
                        response_mime_type='application/json',
                        temperature=0.5
                    )
                
                response = await self.client.aio.models.generate_content(
                    model=model,
                    contents=prompt,
                    config=config
                )
                
                text = response.text
                
                if is_gemma or '```' in text:
                    text = re.sub(r'```json\n|```', '', text).strip()
                
                result = json.loads(text)
                result['model_used'] = model
                
                return result
                
            except Exception as e:
                logger.warning(f"[{model}] analyze_news 실패: {e}")
                continue
        
        logger.error("❌ 모든 모델 분석 실패")
        return None
    
    async def analyze_stock_manual(self, stock_data):
        """
        /analyze 명령용 상세 분석
        """
        prompt = f"""
        종목 분석해줘.
        
        종목: {stock_data['name']} ({stock_data['symbol']})
        현재가: {stock_data['price']}
        변동률: {stock_data['change_percent']}%
        거래량: {stock_data['volume']}
        뉴스: {stock_data.get('title', '없음')}
        
        JSON 형식:
        {{
            "score": 0~10,
            "summary": "핵심 요약",
            "reasoning": "분석 근거",
            "recommendation": "Strong Buy/Buy/Hold/Sell",
            "risk_level": "Low/Medium/High",
            "entry_price": 숫자,
            "target_price": 숫자,
            "stop_loss": 숫자
        }}
        """
        
        for model in self.report_models:
            try:
                is_gemma = model in self.gemma_models
                
                if is_gemma:
                    config = types.GenerateContentConfig(temperature=0.7)
                else:
                    config = types.GenerateContentConfig(
                        response_mime_type='application/json',
                        temperature=0.7
                    )
                
                response = await self.client.aio.models.generate_content(
                    model=model,
                    contents=prompt,
                    config=config
                )
                
                text = response.text
                
                if is_gemma or '```' in text:
                    text = re.sub(r'```json\n|```', '', text).strip()
                
                result = json.loads(text)
                result['model_used'] = model
                
                return result
                
            except Exception as e:
                logger.warning(f"[{model}] analyze_stock 실패: {e}")
                continue
        
        return {
            "score": 0,
            "summary": "분석 실패",
            "reasoning": "API 오류",
            "risk_level": "Unknown",
            "model_used": "failed"
        }
