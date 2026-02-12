# -*- coding: utf-8 -*-
"""
Predictor Engine v2.2 - 완전체
- DART API (한국 공시)
- SEC Form 4 (미국 내부자)
- SEC 13D/13G (고래 추적)
- 중복 방지 완벽
"""

import asyncio
import logging
from datetime import datetime, timedelta
import aiohttp
from bs4 import BeautifulSoup
import re
import urllib.parse
import yfinance as yf
from config import Config

logger = logging.getLogger(__name__)

class PredictorEngineV2_2:
    def __init__(self):
        # DART API (한국)
        self.dart_api_url = "https://opendart.fss.or.kr/api/list.xml"
        self.dart_api_key = Config.DART_API_KEY
        
        # SEC (미국)
        self.sec_form4_url = "https://www.sec.gov/cgi-bin/browse-edgar"
        self.sec_13d_url = "https://www.sec.gov/cgi-bin/browse-edgar"
        self.sec_company_tickers = "https://www.sec.gov/files/company_tickers.json"
        
        # 중복 방지
        self.seen_dart = set()
        self.seen_form4 = set()
        self.seen_13d = set()
        
        # CIK → 티커 매핑
        self.cik_to_ticker = {}
        self.code_cache = {}
        
        # 유명 투자자 (한국)
        self.famous_kr_whales = {
            '국민연금': '🐋 국민연금공단',
            '미래에셋': '🐋 미래에셋자산운용',
            '삼성생명': '🐋 삼성생명보험',
            'KB자산': '🐋 KB자산운용',
            '한국투자': '🐋 한국투자신탁',
        }
        
        # 유명 고래 (미국) - 40명
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
        
        logger.info("🔮 Predictor Engine v2.2 초기화")
    
    async def generate_daily_report(self, market='KR'):
        """
        아침/저녁 리포트
        """
        today = datetime.now().date()
        
        report = {
            'date': today,
            'market': market,
            'hot_stocks': [],
            'events_today': [],
            'risks': []
        }
        
        if market == 'KR':
            # DART 공시
            dart_signals = await self.scan_dart_filings(days=3)
            if dart_signals:
                report['hot_stocks'].extend(dart_signals)
                
                insider_count = sum(1 for s in dart_signals if s['signal_type'] == 'insider_buy')
                ownership_count = sum(1 for s in dart_signals if s['signal_type'] == 'ownership_increase')
                
                if insider_count > 0:
                    report['events_today'].append(f"내부자 매수: {insider_count}건")
                if ownership_count > 0:
                    report['events_today'].append(f"지분 공시: {ownership_count}건")
        
        else:  # US
            # SEC Form 4
            form4_signals = await self.scan_sec_form4(hours=24)
            if form4_signals:
                report['hot_stocks'].extend(form4_signals)
                report['events_today'].append(f"내부자 매수: {len(form4_signals)}건")
            
            # SEC 13D/13G (고래)
            whale_signals = await self.scan_sec_13d(hours=24)
            if whale_signals:
                report['hot_stocks'].extend(whale_signals)
                report['events_today'].append(f"고래 지분 공시: {len(whale_signals)}건")
        
        # 중복 제거
        report['hot_stocks'] = self._deduplicate_and_rank(report['hot_stocks'])
        
        # 리스크 체크
        report['risks'] = await self.check_market_risks(market)
        
        return report
    
    async def scan_dart_filings(self, days=3):
        """한국 DART 공시 (기존 검증됨 + 급등주 로직 강화)"""
        signals = []
        
        if not self.dart_api_key or len(self.dart_api_key) < 10:
            logger.warning("⚠️ DART API 키 없음")
            return signals
        
        try:
            params = {
                'crtfc_key': self.dart_api_key,
                'page_no': '1',
                'page_count': '50'
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(self.dart_api_url, params=params, timeout=10) as response:
                    if response.status != 200:
                        return signals
                    
                    xml = await response.text()
                    soup = BeautifulSoup(xml, 'xml')
                    
                    status = soup.find('status')
                    if status and status.text != '000':
                        return signals
                    
                    items = soup.find_all('list')
                    
                    for item in items:
                        try:
                            corp_name = item.find('corp_name').text
                            report_nm = item.find('report_nm').text
                            rcept_no = item.find('rcept_no').text
                            rcept_dt = item.find('rcept_dt').text
                            
                            if rcept_no in self.seen_dart:
                                continue
                            
                            filing_date = datetime.strptime(rcept_dt, '%Y%m%d').date()
                            if filing_date < (datetime.now().date() - timedelta(days=days)):
                                continue
                            
                            # 공시 분류
                            signal_type = None
                            confidence = 0.5
                            expected_impact = ''
                            is_negative = False
                            
                            if '임원' in report_nm or '주요주주특정증권' in report_nm:
                                signal_type = 'insider_buy'
                                confidence = 0.75
                                expected_impact = '+10~30%'
                                reason = '👔 내부자 매수'
                            elif '대량보유' in report_nm:
                                signal_type = 'ownership_increase'
                                confidence = 0.80
                                expected_impact = '+15~40%'
                                reason = '🐋 대량보유 신고 (5%+)'
                            elif '단일판매' in report_nm or '공급계약' in report_nm:
                                signal_type = 'contract'
                                confidence = 0.70
                                expected_impact = '+10~25%'
                                reason = '📜 대규모 계약'
                            
                            # 🔥 [NEW] 실적 대박 공시 (에스코넥/뉴인텍 사례)
                            elif '매출액' in report_nm or '손익구조' in report_nm:
                                signal_type = 'earnings_surprise'
                                confidence = 0.85
                                expected_impact = '+15~30%'
                                reason = '💰 실적 대박 (손익구조 변동)'
                            elif '잠정실적' in report_nm:
                                signal_type = 'earnings_provisional'
                                confidence = 0.80
                                expected_impact = '+10~20%'
                                reason = '📊 잠정 실적 발표'
                                
                            elif '주식교환' in report_nm or '합병' in report_nm:
                                signal_type = 'merger'
                                confidence = 0.85
                                expected_impact = '+20~50%'
                                reason = '🤝 M&A 공시'
                            elif '무상증자' in report_nm:
                                signal_type = 'bonus_issue'
                                confidence = 0.75
                                expected_impact = '+10~30%'
                                reason = '🎁 무상증자'
                            elif '공개매수' in report_nm:
                                signal_type = 'tender_offer'
                                confidence = 0.90
                                expected_impact = '+25~60%'
                                reason = '💰 공개매수'
                            
                            # 🔥 [NEW] 유상증자 정밀 분석 (케이바이오 사례)
                            elif '유상증자' in report_nm:
                                if '제3자배정' in report_nm or '3자배정' in report_nm:
                                    # 3자배정은 호재! (큰손 유입)
                                    signal_type = '3rd_party_allocation'
                                    confidence = 0.85
                                    expected_impact = '+15~30% (상한가 후보)'
                                    reason = '🚀 제3자배정 유상증자 (신규 자금/주주)'
                                    is_negative = False
                                else:
                                    # 일반 주주배정은 악재
                                    signal_type = 'dilution'
                                    is_negative = True
                                    reason = '⚠️ 주주배정 유상증자 (주가 희석)'

                            # 🔥 [NEW] 최대주주 변경 (플루토스 사례)
                            elif '최대주주변경' in report_nm or '주식양수도' in report_nm:
                                signal_type = 'ownership_change'
                                confidence = 0.90
                                expected_impact = '+20~30% (경영권 프리미엄)'
                                reason = '👑 최대주주 변경 (경영권 매각)'

                            elif '전환사채' in report_nm or 'CB' in report_nm:
                                signal_type = 'cb_issue'
                                is_negative = True
                                reason = '⚠️ CB 발행'
                            elif '감자' in report_nm:
                                signal_type = 'reverse_split'
                                is_negative = True
                                reason = '🚨 감자 (극악재)'
                            else:
                                continue
                            
                            # 종목 코드 매핑
                            stock_code = await self._get_stock_code_kr(corp_name, session)
                            ticker = stock_code if stock_code else "UNKNOWN"
                            
                            # 유명 투자자
                            whale_name = None
                            if not is_negative:
                                for whale_key, whale_desc in self.famous_kr_whales.items():
                                    if whale_key in corp_name:
                                        whale_name = whale_desc
                                        confidence = min(confidence + 0.1, 0.95)
                                        break
                            
                            self.seen_dart.add(rcept_no)
                            
                            filing_url = f"http://dart.fss.or.kr/dsaf001/main.do?rcpNo={rcept_no}"
                            
                            signals.append({
                                'ticker': ticker,
                                'name': corp_name,
                                'signal_type': signal_type,
                                'event_date': filing_date,
                                'confidence': confidence,
                                'expected_impact': expected_impact,
                                'reason': f"{whale_name}\n{reason}" if whale_name else reason,
                                'filing_id': rcept_no,  # 🆕 중복 체크용
                                'market': 'KR',  # 🆕 시장 구분
                                'details': {
                                    'report_name': report_nm,
                                    'filing_url': filing_url,
                                    'is_negative': is_negative
                                }
                            })
                            
                            logger.info(f"📋 DART: {corp_name} - {reason}")
                            
                        except Exception as e:
                            logger.debug(f"DART 항목 오류: {e}")
                            continue
                    
                    if len(self.seen_dart) > 1000:
                        self.seen_dart.clear()
            
            logger.info(f"✅ DART: {len(signals)}건")
            return signals
            
        except Exception as e:
            logger.error(f"DART 오류: {e}")
            return signals
    
    async def scan_sec_form4(self, hours=24):
        """미국 SEC Form 4 (기존 검증됨)"""
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
            
            headers = {'User-Agent': 'Mozilla/5.0 (PredictorBot/2.2)'}
            
            async with aiohttp.ClientSession() as session:
                async with session.get(self.sec_form4_url, params=params, headers=headers, timeout=15) as response:
                    if response.status != 200:
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
                                'filing_id': link,  # 🆕 중복 체크용
                                'market': 'US',  # 🆕 시장 구분
                                'details': {
                                    'filing_url': link,
                                    'transaction_type': transaction_type
                                }
                            })
                            
                            logger.info(f"👔 Form 4: {ticker} 매수")
                            
                        except Exception as e:
                            logger.debug(f"Form 4 오류: {e}")
                            continue
                    
                    if len(self.seen_form4) > 500:
                        self.seen_form4.clear()
            
            logger.info(f"✅ Form 4: {len(signals)}건")
            return signals
            
        except Exception as e:
            logger.error(f"Form 4 오류: {e}")
            return signals
    
    async def scan_sec_13d(self, hours=24):
        """미국 SEC 13D/13G (고래 추적)"""
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
                                'filing_id': link,  # 🆕 중복 체크용
                                'market': 'US',  # 🆕 시장 구분
                                'details': {
                                    'filing_url': link,
                                    'whale_name': whale_name,
                                    'form_type': form_type
                                }
                            })
                            
                            logger.info(f"🐋 13D: {final_symbol} - {form_type}")
                            
                        except Exception as e:
                            logger.debug(f"13D 오류: {e}")
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
    
    async def _get_stock_code_kr(self, company_name, session):
        """한국 종목 코드"""
        if company_name in self.code_cache:
            return self.code_cache[company_name]
        
        try:
            encoded = urllib.parse.quote(company_name)
            url = f"https://finance.naver.com/search/searchList.naver?query={encoded}"
            
            async with session.get(url, timeout=5) as response:
                if response.status != 200:
                    return None
                
                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')
                
                result = soup.select_one('table.tbl_search tr td.tit a')
                if not result:
                    return None
                
                href = result.get('href', '')
                code_match = re.search(r'code=(\d{6})', href)
                
                if code_match:
                    code = code_match.group(1)
                    self.code_cache[company_name] = code
                    return code
        except:
            pass
        
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
        중복 제거 & 순위 - 수정 (제미나이 검증)
        
        핵심: "회사 이름이 다르면 다른 놈이다!"
        - UNKNOWN 티커도 회사명으로 구분
        - 진짜 같은 회사의 여러 공시만 합침
        """
        unique_map = {}
        
        for signal in signals:
            ticker = signal.get('ticker', 'UNKNOWN')
            name = signal.get('name', 'Unknown')
            filing_id = signal.get('filing_id', '')
            
            # 🔥 핵심 로직: UNKNOWN이면 회사명으로 구분!
            if ticker == 'UNKNOWN' or not ticker:
                unique_key = f"UNKNOWN_{name}"
            else:
                unique_key = ticker
            
            # 고유 ID = unique_key + filing_id
            # (같은 회사의 서로 다른 공시는 분리)
            signal_id = f"{unique_key}_{filing_id}"
            
            # 진짜 중복(=같은 공시)만 제외
            if signal_id not in unique_map:
                unique_map[signal_id] = signal
            # 같은 signal_id면 건너뜀 (이미 추가됨)
        
        # 신뢰도 순 정렬
        ranked = sorted(
            unique_map.values(),
            key=lambda x: x.get('confidence', 0),
            reverse=True
        )
        
        return ranked[:10]  # TOP 10
