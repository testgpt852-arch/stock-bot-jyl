# -*- coding: utf-8 -*-
"""
Predictor Engine (Production) - Beast Mode (야수 모드)
- 🔥 DART 공시 완전 제거 (경량화)
- SEC Form 4 (미국 내부자 매수)
- SEC 13D/13G (고래 추적)
- 중복 방지 완벽
"""

import asyncio
import logging
from datetime import datetime, timedelta
import aiohttp
from bs4 import BeautifulSoup
import re
import yfinance as yf

logger = logging.getLogger(__name__)

class PredictorEngine:
    def __init__(self):
        # 🔥 v3.0: DART API 완전 제거
        # SEC (미국)만 유지
        self.sec_form4_url = "https://www.sec.gov/cgi-bin/browse-edgar"
        self.sec_13d_url = "https://www.sec.gov/cgi-bin/browse-edgar"
        self.sec_company_tickers = "https://www.sec.gov/files/company_tickers.json"
        
        # 중복 방지 (SEC만)
        self.seen_form4 = set()
        self.seen_13d = set()
        
        # CIK → 티커 매핑
        self.cik_to_ticker = {}
        
        # 🐋 유명 고래 (미국) - 40명
        self.famous_us_whales = {
            'ICAHN': '👑 Carl Icahn',
            'ACKMAN': '👑 Bill Ackman (Pershing)',
            'EINHORN': '👑 David Einhorn',
            'BERKSHIRE': '🏆 Warren Buffett',
            'GATES': '🏆 Bill Gates',
            'SOROS': '🏆 George Soros',
            'STARBOARD': '⚔️ Starboard Value',
            'ELLIOTT': '⚔️ Elliott Management',
            'THIRD POINT': '⚔️ Third Point',
            'PERSHING': '⚔️ Pershing Square',
            'VALUEACT': '⚔️ ValueAct',
            'JANA': '⚔️ JANA Partners',
            'BLACKROCK': '🏦 BlackRock',
            'VANGUARD': '🏦 Vanguard',
            'STATE STREET': '🏦 State Street',
            'FIDELITY': '🏦 Fidelity',
            'GOLDMAN': '🏦 Goldman Sachs',
            'GOLDMAN SACHS': '🏦 Goldman Sachs',
            'MORGAN STANLEY': '🏦 Morgan Stanley',
            'JP MORGAN': '🏦 JP Morgan',
            'JPMORGAN': '🏦 JP Morgan',
            'CITADEL': '🤖 Citadel',
            'RENAISSANCE': '🤖 Renaissance Tech',
            'BRIDGEWATER': '🤖 Bridgewater',
            'TWO SIGMA': '🤖 Two Sigma',
            'DE SHAW': '🤖 D.E. Shaw',
            'MILLENNIUM': '🤖 Millennium',
            'SOFTBANK': '🇯🇵 SoftBank (손정의)',
            'BAUPOST': '💎 Baupost',
            'APPALOOSA': '💎 Appaloosa',
            'GREENLIGHT': '💎 Greenlight',
            'LONE PINE': '💎 Lone Pine',
        }
        
        logger.info("🔮 Predictor Engine (Production) Beast Mode 초기화 (SEC Only)")
    
    async def generate_daily_report(self, market='US'):
        """
        아침/저녁 리포트 (간소화)
        v3.0: SEC 공시만 포함
        """
        today = datetime.now().date()
        
        report = {
            'date': today,
            'market': market,
            'hot_stocks': [],
            'events_today': [],
            'risks': []
        }
        
        if market == 'US':
            # SEC Form 4 + 13D/13G
            form4_signals = await self.scan_sec_form4(hours=24)
            filing_13d = await self.scan_sec_13d(hours=24)
            
            all_signals = form4_signals + filing_13d
            report['events_today'] = self._deduplicate_and_rank(all_signals)
            
            # 리스크 체크
            report['risks'] = await self.check_market_risks('US')
        
        logger.info(f"📊 일일 리포트: {len(report['events_today'])}건")
        return report
    
    async def scan_sec_form4(self, hours=24):
        """
        미국 SEC Form 4 (내부자 거래)
        v3.0: 기존 로직 유지
        """
        signals = []
        
        try:
            params = {
                'action': 'getcurrent',
                'type': '4',
                'company': '',
                'dateb': '',
                'owner': 'include',
                'start': '0',
                'count': '100',
                'output': 'atom'
            }
            
            headers = {'User-Agent': 'Mozilla/5.0 (PredictorBot/3.0)'}
            
            async with aiohttp.ClientSession() as session:
                async with session.get(self.sec_form4_url, params=params, headers=headers, timeout=15) as response:
                    if response.status != 200:
                        logger.warning(f"Form 4 접근 실패: {response.status}")
                        return signals
                    
                    xml = await response.text()
                    soup = BeautifulSoup(xml, 'xml')
                    entries = soup.find_all('entry')[:40]
                    
                    for entry in entries:
                        try:
                            title = entry.find('title').text
                            link = entry.find('link')['href']
                            updated = entry.find('updated').text
                            
                            if link in self.seen_form4:
                                continue
                            
                            filing_time = datetime.fromisoformat(updated.replace('Z', '+00:00'))
                            now = datetime.now(filing_time.tzinfo)
                            
                            if (now - filing_time).total_seconds() > hours * 3600:
                                continue
                            
                            ticker_match = re.search(r'\(([A-Z]{1,5})\)', title)
                            if not ticker_match:
                                continue
                            
                            ticker = ticker_match.group(1)
                            
                            # 매수/매도 구분
                            transaction_type = await self._parse_form4_type(link, session)
                            
                            if transaction_type != 'BUY':
                                continue
                            
                            self.seen_form4.add(link)
                            
                            signals.append({
                                'ticker': ticker,
                                'name': ticker,
                                'signal_type': 'insider_buy',
                                'event_date': filing_time.date(),
                                'confidence': 0.80,
                                'expected_impact': '+10~30%',
                                'reason': '👔 임원 매수 (Form 4)',
                                'filing_id': link,
                                'market': 'US',
                                'details': {
                                    'filing_url': link,
                                    'transaction_type': transaction_type
                                }
                            })
                            
                            logger.info(f"👔 Form 4: {ticker} 매수")
                            
                        except Exception as e:
                            logger.debug(f"Form 4 항목 오류: {e}")
                            continue
                    
                    if len(self.seen_form4) > 500:
                        self.seen_form4.clear()
            
            logger.info(f"✅ Form 4: {len(signals)}건")
            return signals
            
        except Exception as e:
            logger.error(f"Form 4 오류: {e}")
            return signals
    
    async def scan_sec_13d(self, hours=24):
        """
        미국 SEC 13D/13G (고래 추적)
        v3.0: 기존 로직 유지
        """
        signals = []
        
        try:
            # CIK 매핑 로드 (최초 1회)
            if not self.cik_to_ticker:
                await self._load_sec_mappings()
            
            params = {
                'action': 'getcurrent',
                'type': '',
                'company': '',
                'dateb': '',
                'owner': 'include',
                'start': '0',
                'count': '100',
                'output': 'atom'
            }
            
            headers = {
                'User-Agent': 'StockAlertBot admin@stockbot.com',
                'Accept-Encoding': 'gzip, deflate',
                'Host': 'www.sec.gov'
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(self.sec_13d_url, params=params, headers=headers, timeout=20) as response:
                    if response.status != 200:
                        logger.warning(f"13D/13G 접근 실패: {response.status}")
                        return signals
                    
                    xml = await response.text()
                    soup = BeautifulSoup(xml, 'xml')
                    entries = soup.find_all('entry')[:50]
                    
                    for entry in entries:
                        try:
                            title = entry.find('title').text
                            link = entry.find('link')['href']
                            updated = entry.find('updated').text
                            
                            summary_tag = entry.find('summary')
                            summary = summary_tag.text if summary_tag else ''
                            
                            if link in self.seen_13d:
                                continue
                            
                            try:
                                filing_time = datetime.fromisoformat(updated.replace('Z', '+00:00'))
                            except:
                                filing_time = datetime.now()
                            
                            now = datetime.now(filing_time.tzinfo if filing_time.tzinfo else None)
                            if (now - filing_time).total_seconds() > hours * 3600:
                                continue
                            
                            # 13D/13G 필터
                            form_type = None
                            priority = 0
                            
                            upper_title = title.upper()
                            
                            if "SC 13D/A" in upper_title:
                                form_type = "🔥 SC 13D/A (지분 변경)"
                                priority = 9
                            elif "SC 13D" in upper_title:
                                form_type = "🚨 SC 13D (5%+ 공격적 투자)"
                                priority = 10
                            elif "SC 13G/A" in upper_title:
                                form_type = "📈 SC 13G/A (지분 변경)"
                                priority = 6
                            elif "SC 13G" in upper_title:
                                form_type = "📊 SC 13G (5%+ 단순 투자)"
                                priority = 7
                            else:
                                continue
                            
                            # 티커 추출
                            ticker = await self._extract_ticker_multi(title, summary, link, session)
                            final_symbol = ticker if ticker else "UNKNOWN"
                            
                            # 고래 확인
                            whale_name = None
                            for whale_key, whale_desc in self.famous_us_whales.items():
                                if whale_key in title.upper() or whale_key in summary.upper():
                                    whale_name = whale_desc
                                    priority += 3
                                    break
                            
                            self.seen_13d.add(link)
                            
                            trigger_msg = form_type
                            if whale_name:
                                trigger_msg = f"{whale_name}\n{form_type}"
                            
                            signals.append({
                                'ticker': final_symbol,
                                'name': final_symbol,
                                'signal_type': 'whale_alert',
                                'event_date': filing_time.date(),
                                'confidence': 0.85,
                                'expected_impact': '+15~50%',
                                'reason': trigger_msg,
                                'filing_id': link,
                                'market': 'US',
                                'details': {
                                    'filing_url': link,
                                    'whale_name': whale_name,
                                    'form_type': form_type
                                }
                            })
                            
                            logger.info(f"🐋 13D: {final_symbol} - {form_type}")
                            
                        except Exception as e:
                            logger.debug(f"13D 항목 오류: {e}")
                            continue
                    
                    if len(self.seen_13d) > 1000:
                        self.seen_13d.clear()
            
            logger.info(f"✅ 13D/13G: {len(signals)}건")
            return signals
            
        except Exception as e:
            logger.error(f"13D/13G 오류: {e}")
            return signals
    
    async def _load_sec_mappings(self):
        """SEC CIK → 티커 매핑"""
        try:
            headers = {'User-Agent': 'StockAlertBot admin@stockbot.com'}
            
            async with aiohttp.ClientSession() as session:
                async with session.get(self.sec_company_tickers, headers=headers, timeout=15) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        for company in data.values():
                            cik = str(company['cik_str']).zfill(10)
                            ticker = company['ticker']
                            self.cik_to_ticker[cik] = ticker
                        
                        logger.info(f"✅ SEC 매핑: {len(self.cik_to_ticker)}개")
                    
        except Exception as e:
            logger.error(f"SEC 매핑 오류: {e}")
    
    async def _extract_ticker_multi(self, title, summary, link, session):
        """다중 전략 티커 추출"""
        # 전략 1: CIK
        cik_match = re.search(r'\((\d{10})\)', title)
        if not cik_match:
            cik_match = re.search(r'\((\d{7,10})\)', title)
        
        if cik_match:
            cik = cik_match.group(1).zfill(10)
            ticker = self.cik_to_ticker.get(cik)
            if ticker:
                return ticker
        
        # 전략 2: URL CIK
        if link:
            url_cik_match = re.search(r'/data/(\d+)/', link)
            if url_cik_match:
                cik = url_cik_match.group(1).zfill(10)
                ticker = self.cik_to_ticker.get(cik)
                if ticker:
                    return ticker
        
        # 전략 3: 괄호 티커
        ticker_match = re.search(r'\(([A-Z]{1,5})\)', title)
        if ticker_match:
            return ticker_match.group(1)
        
        return None
    
    async def _parse_form4_type(self, filing_url, session):
        """Form 4 매수/매도 구분"""
        try:
            async with session.get(filing_url, timeout=5) as response:
                if response.status != 200:
                    return 'UNKNOWN'
                
                xml_text = await response.text()
                
                if '<transactionCode>P</transactionCode>' in xml_text:
                    return 'BUY'
                elif '<transactionCode>S</transactionCode>' in xml_text:
                    return 'SELL'
                else:
                    return 'UNKNOWN'
        except:
            return 'UNKNOWN'
    
    async def check_market_risks(self, market):
        """리스크 체크"""
        risks = []
        
        try:
            if market == 'US':
                vix = yf.Ticker('^VIX')
                vix_hist = vix.history(period='1d')
                
                if not vix_hist.empty:
                    vix_value = vix_hist['Close'].iloc[-1]
                    if vix_value > 30:
                        risks.append(f"⚠️ VIX 고공행진 ({vix_value:.1f})")
                    elif vix_value > 20:
                        risks.append(f"📊 VIX 상승 ({vix_value:.1f})")
                
                sp500 = yf.Ticker('^GSPC')
                sp_hist = sp500.history(period='5d')
                
                if len(sp_hist) >= 2:
                    change = ((sp_hist['Close'].iloc[-1] - sp_hist['Close'].iloc[-2]) / sp_hist['Close'].iloc[-2]) * 100
                    if change < -2:
                        risks.append(f"🔴 S&P 500 급락 ({change:.1f}%)")
            
            elif market == 'KR':
                kospi = yf.Ticker('^KS11')
                kospi_hist = kospi.history(period='5d')
                
                if len(kospi_hist) >= 2:
                    change = ((kospi_hist['Close'].iloc[-1] - kospi_hist['Close'].iloc[-2]) / kospi_hist['Close'].iloc[-2]) * 100
                    if change < -2:
                        risks.append(f"🔴 KOSPI 급락 ({change:.1f}%)")
        
        except Exception as e:
            logger.debug(f"리스크 체크 오류: {e}")
        
        return risks
    
    def _deduplicate_and_rank(self, signals):
        """
        중복 제거 & 순위
        """
        unique_map = {}
        
        for signal in signals:
            ticker = signal.get('ticker', 'UNKNOWN')
            name = signal.get('name', 'Unknown')
            filing_id = signal.get('filing_id', '')
            
            # UNKNOWN이면 회사명으로 구분
            if ticker == 'UNKNOWN' or not ticker:
                unique_key = f"UNKNOWN_{name}"
            else:
                unique_key = ticker
            
            # 고유 ID = unique_key + filing_id
            signal_id = f"{unique_key}_{filing_id}"
            
            # 진짜 중복(=같은 공시)만 제외
            if signal_id not in unique_map:
                unique_map[signal_id] = signal
        
        # 신뢰도 순 정렬
        ranked = sorted(
            unique_map.values(),
            key=lambda x: x.get('confidence', 0),
            reverse=True
        )
        
        return ranked[:10]  # TOP 10
