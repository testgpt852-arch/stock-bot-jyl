# -*- coding: utf-8 -*-
"""
Momentum Tracker v3.1 - 제미나이 검증 반영 (완전체)
- 🔥 Yahoo Finance 스크래핑 폐기 → Finviz + yfinance 조합
- 이중 스캔 모드: 뉴스 종목 1분 / 시장 전체 10분
- 랜덤 User-Agent + 랜덤 지연 (Anti-Ban)
- 동적 종목 추가 (뉴스 연동)
"""

import asyncio
import aiohttp
import logging
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
import yfinance as yf
import re
import random
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

class MomentumTrackerV3_1:
    def __init__(self):
        # 한국 소스
        self.kr_surge_url = "https://finance.naver.com/sise/sise_quant.naver"
        self.program_url = "https://finance.naver.com/sise/programDeal.naver"
        self.theme_url = "https://finance.naver.com/sise/theme.naver"
        
        # 🔥 v3.1: Yahoo 대신 Finviz 사용 (HTML 구조 안정적)
        self.us_gainers_url = "https://finviz.com/screener.ashx?v=111&s=ta_topgainers"
        
        # 🔥 v3.1: 동적 종목 리스트 (뉴스에서 포착된 종목)
        self.dynamic_tickers_us = set()  # 미국
        self.dynamic_tickers_kr = set()  # 한국
        
        # 중복 방지
        self.seen_surge = set()
        self.seen_program = set()
        self.seen_theme = set()
        
        # Beast Mode 필터
        self.min_volume_ratio = 5.0
        self.min_price_change = 10.0
        self.max_market_cap_kr = 1_000_000
        self.max_market_cap_us = 100_000_000_000
        
        # 🔥 v3.1: User-Agent 풀 (차단 방지)
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edge/120.0.0.0',
            'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:121.0) Gecko/20100101 Firefox/121.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:121.0) Gecko/20100101 Firefox/121.0',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0',
        ]
        
        logger.info("🐺 Momentum Tracker v3.1 완전체 초기화")
    
    def _get_random_headers(self):
        """🔥 v3.1: 랜덤 User-Agent (차단 방지)"""
        return {
            'User-Agent': random.choice(self.user_agents),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        }
    
    async def _random_delay(self, base_seconds=1.0, jitter=0.5):
        """🔥 v3.1: 랜덤 지연 (Anti-Ban)"""
        delay = base_seconds + random.uniform(-jitter, jitter)
        await asyncio.sleep(max(0.1, delay))
    
    def add_dynamic_ticker(self, ticker, market='US'):
        """
        🔥 v3.1: 뉴스에서 포착된 종목 동적 추가
        이 종목들은 1분 주기로 집중 감시
        """
        if market == 'US':
            self.dynamic_tickers_us.add(ticker.upper())
            logger.info(f"➕ 동적 종목 추가 (US): {ticker}")
        else:
            self.dynamic_tickers_kr.add(ticker)
            logger.info(f"➕ 동적 종목 추가 (KR): {ticker}")
        
        # 리스트 크기 제한 (메모리 관리)
        if len(self.dynamic_tickers_us) > 50:
            self.dynamic_tickers_us.pop()
        if len(self.dynamic_tickers_kr) > 50:
            self.dynamic_tickers_kr.pop()
    
    async def scan_momentum(self, market='KR', mode='full'):
        """
        🔥 v3.1: 이중 스캔 모드
        - mode='dynamic': 뉴스 종목만 (1분 주기)
        - mode='full': 시장 전체 스캔 (10분 주기)
        """
        signals = []
        
        if market == 'KR':
            if mode == 'dynamic':
                # 동적 종목만 빠르게 체크
                if self.dynamic_tickers_kr:
                    dynamic_signals = await self._scan_dynamic_kr()
                    signals.extend(dynamic_signals)
            else:
                # 전체 스캔
                surge_signals = await self._scan_realtime_surge_kr()
                signals.extend(surge_signals)
                
                program_signals = await self._scan_program()
                signals.extend(program_signals)
                
                theme_signals = await self._scan_theme()
                signals.extend(theme_signals)
        
        else:  # US
            if mode == 'dynamic':
                # 동적 종목만 빠르게 체크
                if self.dynamic_tickers_us:
                    dynamic_signals = await self._scan_dynamic_us()
                    signals.extend(dynamic_signals)
            else:
                # 전체 스캔
                surge_signals = await self._scan_realtime_surge_us()
                signals.extend(surge_signals)
        
        logger.info(f"🐺 모멘텀 [{market}][{mode}]: {len(signals)}개")
        return signals
    
    async def _scan_dynamic_us(self):
        """🔥 v3.1: 뉴스 종목 빠른 체크 (1분 주기)"""
        signals = []
        
        for ticker in list(self.dynamic_tickers_us):
            try:
                await self._random_delay(0.5, 0.2)  # 0.3~0.7초 랜덤
                
                stock = await asyncio.to_thread(yf.Ticker, ticker)
                hist = stock.history(period='5d')
                
                if hist.empty or len(hist) < 2:
                    continue
                
                current = hist['Close'].iloc[-1]
                prev = hist['Close'].iloc[-2]
                change_pct = ((current - prev) / prev) * 100
                
                volume = hist['Volume'].iloc[-1]
                avg_volume = hist['Volume'][:-1].mean()
                volume_ratio = volume / avg_volume if avg_volume > 0 else 0
                
                # 급등 체크
                if change_pct >= self.min_price_change and volume_ratio >= self.min_volume_ratio:
                    alert_key = f"{ticker}_{datetime.now().date()}"
                    if alert_key not in self.seen_surge:
                        self.seen_surge.add(alert_key)
                        
                        signals.append({
                            'ticker': ticker,
                            'name': ticker,
                            'market': 'US',
                            'price': current,
                            'change_percent': change_pct,
                            'volume_ratio': volume_ratio,
                            'signals': [f'Surge {change_pct:.1f}%', f'Volume {volume_ratio:.1f}x'],
                            'reason': f'🔥 뉴스 종목 급등 ({change_pct:.1f}%, {volume_ratio:.1f}배)',
                            'timestamp': datetime.now(),
                            'alert_type': 'dynamic_surge'
                        })
                        
                        logger.info(f"🔥 뉴스 종목 급등: {ticker} +{change_pct:.1f}%")
                
            except Exception as e:
                logger.debug(f"동적 종목 체크 오류 ({ticker}): {e}")
                continue
        
        return signals
    
    async def _scan_dynamic_kr(self):
        """🔥 v3.1: 한국 뉴스 종목 빠른 체크"""
        signals = []
        
        for code in list(self.dynamic_tickers_kr):
            try:
                await self._random_delay(0.5, 0.2)
                
                ticker_symbol = f"{code}.KS" if code.startswith('0') else f"{code}.KQ"
                stock = await asyncio.to_thread(yf.Ticker, ticker_symbol)
                hist = stock.history(period='5d')
                
                if hist.empty or len(hist) < 2:
                    continue
                
                current = hist['Close'].iloc[-1]
                prev = hist['Close'].iloc[-2]
                change_pct = ((current - prev) / prev) * 100
                
                volume = hist['Volume'].iloc[-1]
                avg_volume = hist['Volume'][:-1].mean()
                volume_ratio = volume / avg_volume if avg_volume > 0 else 0
                
                if change_pct >= self.min_price_change and volume_ratio >= self.min_volume_ratio:
                    alert_key = f"{code}_{datetime.now().date()}"
                    if alert_key not in self.seen_surge:
                        self.seen_surge.add(alert_key)
                        
                        info = stock.info
                        name = info.get('longName', code)
                        
                        signals.append({
                            'ticker': code,
                            'name': name,
                            'market': 'KR',
                            'price': current,
                            'change_percent': change_pct,
                            'volume_ratio': volume_ratio,
                            'signals': [f'급등 {change_pct:.1f}%', f'거래량 {volume_ratio:.1f}배'],
                            'reason': f'🔥 뉴스 종목 급등 ({change_pct:.1f}%, {volume_ratio:.1f}배)',
                            'timestamp': datetime.now(),
                            'alert_type': 'dynamic_surge'
                        })
                        
                        logger.info(f"🔥 뉴스 종목 급등: {name} +{change_pct:.1f}%")
                
            except Exception as e:
                logger.debug(f"동적 종목 체크 오류 ({code}): {e}")
                continue
        
        return signals
    
    async def _scan_realtime_surge_us(self):
        """
        🔥 v3.1.1: 다중 fallback 시스템
        1차: Finviz 스크래핑
        2차: Yahoo Finance screener
        3차: yfinance API 직접 조회
        """
        signals = []
        
        # === 1차 시도: Finviz ===
        try:
            logger.info("1차 시도: Finviz 급등주 스캔")
            signals = await self._scan_finviz()
            
            if signals:
                logger.info(f"✅ Finviz 성공: {len(signals)}개")
                return signals
            else:
                logger.warning("Finviz 결과 0개, Yahoo 시도")
                
        except Exception as e:
            logger.warning(f"Finviz 실패: {e}, Yahoo 시도")
        
        # === 2차 시도: Yahoo Finance ===
        try:
            logger.info("2차 시도: Yahoo Finance screener")
            signals = await self._scan_yahoo_screener()
            
            if signals:
                logger.info(f"✅ Yahoo 성공: {len(signals)}개")
                return signals
            else:
                logger.warning("Yahoo 결과 0개, yfinance API 시도")
                
        except Exception as e:
            logger.warning(f"Yahoo 실패: {e}, yfinance API 시도")
        
        # === 3차 시도: yfinance API ===
        try:
            logger.info("3차 시도: yfinance API")
            signals = await self._scan_yfinance_api()
            
            if signals:
                logger.info(f"✅ yfinance API 성공: {len(signals)}개")
            else:
                logger.error("⚠️ 모든 방법 실패: 미국 급등주 0개")
                
        except Exception as e:
            logger.error(f"yfinance API도 실패: {e}")
        
        return signals
    
    async def _scan_finviz(self):
        """1차: Finviz 스크래핑"""
        signals = []
    async def _scan_finviz(self):
        """1차: Finviz 스크래핑"""
        signals = []
        
        try:
            headers = self._get_random_headers()
            
            async with aiohttp.ClientSession() as session:
                await self._random_delay(1.0, 0.3)  # 0.7~1.3초
                
                async with session.get(self.us_gainers_url, headers=headers, timeout=15) as response:
                    if response.status != 200:
                        logger.warning(f"Finviz 접근 실패: {response.status}")
                        return signals
                    
                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')
                    
                    # 🔧 v3.1: Finviz 테이블 찾기 강화 (fallback)
                    # 방법 1: class="table-light"
                    table = soup.find('table', {'class': 'table-light'})
                    
                    # 방법 2: class 없이 첫 번째 큰 테이블
                    if not table:
                        tables = soup.find_all('table')
                        for t in tables:
                            rows = t.find_all('tr')
                            if len(rows) > 10:  # 최소 10개 행 이상
                                table = t
                                logger.info("Finviz 테이블 fallback 사용")
                                break
                    
                    # 방법 3: 모든 tr 태그 직접 검색
                    if not table:
                        all_rows = soup.find_all('tr')
                        if len(all_rows) > 10:
                            logger.info(f"Finviz 테이블 없음, 전체 tr 사용 ({len(all_rows)}개)")
                            # 임시 컨테이너 생성
                            from bs4 import Tag
                            table = Tag(name='table')
                            for row in all_rows:
                                table.append(row)
                        else:
                            logger.warning(f"Finviz 데이터 없음 (tr: {len(all_rows)}개)")
                            return signals
                    
                    rows = table.find_all('tr')[1:51]  # 헤더 제외, 상위 50개
                    
                    for row in rows:
                        try:
                            cols = row.find_all('td')
                            if len(cols) < 12:
                                continue
                            
                            # Ticker
                            ticker_elem = cols[1].find('a')
                            if not ticker_elem:
                                continue
                            ticker = ticker_elem.text.strip()
                            
                            # Company
                            name = cols[2].text.strip()
                            
                            # Price
                            price_text = cols[8].text.strip()
                            try:
                                price = float(price_text)
                            except:
                                continue
                            
                            # Change %
                            change_text = cols[10].text.strip().replace('%', '').replace('+', '')
                            try:
                                change_pct = float(change_text)
                            except:
                                continue
                            
                            # Volume
                            volume_text = cols[11].text.strip()
                            try:
                                if 'M' in volume_text:
                                    volume = float(volume_text.replace('M', '')) * 1_000_000
                                elif 'K' in volume_text:
                                    volume = float(volume_text.replace('K', '')) * 1_000
                                else:
                                    volume = float(volume_text.replace(',', ''))
                            except:
                                volume = 0
                            
                            # 필터: 10% 이상
                            if change_pct < self.min_price_change:
                                continue
                            
                            # yfinance로 추가 검증
                            await self._random_delay(0.3, 0.1)
                            
                            try:
                                stock = await asyncio.to_thread(yf.Ticker, ticker)
                                info = stock.info
                                hist = stock.history(period='5d')
                                
                                if hist.empty or len(hist) < 2:
                                    continue
                                
                                # 거래량 비율
                                current_volume = hist['Volume'].iloc[-1]
                                avg_volume = hist['Volume'][:-1].mean()
                                volume_ratio = current_volume / avg_volume if avg_volume > 0 else 0
                                
                                if volume_ratio < self.min_volume_ratio:
                                    continue
                                
                                # 시가총액 체크
                                market_cap = info.get('marketCap', 0)
                                if market_cap > self.max_market_cap_us:
                                    continue
                                
                                # ETF 제외
                                if info.get('quoteType') == 'ETF':
                                    continue
                                
                            except Exception as e:
                                logger.debug(f"{ticker} yfinance 검증 실패: {e}")
                                # 실패해도 Finviz 데이터만으로 일단 포함
                                if volume == 0:
                                    continue
                                volume_ratio = 0
                            
                            # 중복 체크
                            alert_key = f"{ticker}_{datetime.now().date()}"
                            if alert_key in self.seen_surge:
                                continue
                            
                            self.seen_surge.add(alert_key)
                            
                            signals.append({
                                'ticker': ticker,
                                'name': name,
                                'market': 'US',
                                'price': price,
                                'change_percent': change_pct,
                                'volume': volume,
                                'volume_ratio': volume_ratio if volume_ratio else 0,
                                'signals': [f'Surge {change_pct:.1f}%', f'Volume {volume_ratio:.1f}x' if volume_ratio else 'High Volume'],
                                'reason': f'🔥 Finviz 급등 포착 ({change_pct:.1f}%)',
                                'timestamp': datetime.now(),
                                'alert_type': 'realtime_surge'
                            })
                            
                            logger.info(f"🔥 US Surge (Finviz): {ticker} +{change_pct:.1f}%")
                            
                        except Exception as e:
                            logger.debug(f"Finviz 행 파싱 오류: {e}")
                            continue
            
        except Exception as e:
            logger.error(f"미국 급등 스캔 오류: {e}")
        
        return signals
    
    async def _scan_realtime_surge_kr(self):
        """한국 급등주 (v3.0 유지, User-Agent만 랜덤화)"""
        signals = []
        
        try:
            headers = self._get_random_headers()
            
            async with aiohttp.ClientSession() as session:
                await self._random_delay(1.0, 0.3)
                
                async with session.get(self.kr_surge_url, headers=headers, timeout=15) as response:
                    if response.status != 200:
                        logger.warning(f"한국 급등주 페이지 접근 실패: {response.status}")
                        return signals
                    
                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')
                    
                    rows = soup.select('table.type_2 tr')[2:52]
                    
                    for row in rows:
                        try:
                            cols = row.select('td')
                            if len(cols) < 11:
                                continue
                            
                            name_elem = cols[1].select_one('a')
                            if not name_elem:
                                continue
                            
                            name = name_elem.text.strip()
                            href = name_elem.get('href', '')
                            code_match = re.search(r'code=(\d+)', href)
                            if not code_match:
                                continue
                            
                            code = code_match.group(1)
                            
                            price_text = cols[2].text.strip().replace(',', '')
                            if not price_text.isdigit():
                                continue
                            price = int(price_text)
                            
                            change_text = cols[4].text.strip().replace('%', '').replace('+', '').replace('-', '')
                            if not change_text.replace('.', '', 1).isdigit():
                                continue
                            change_pct = float(change_text)
                            
                            volume_text = cols[6].text.strip().replace(',', '')
                            if not volume_text.isdigit():
                                continue
                            volume = int(volume_text)
                            
                            volume_ratio_text = cols[10].text.strip().replace('%', '').replace('+', '')
                            if not volume_ratio_text.replace('.', '', 1).isdigit():
                                continue
                            volume_ratio = float(volume_ratio_text) / 100.0 + 1.0
                            
                            # 필터
                            if volume_ratio < self.min_volume_ratio:
                                continue
                            
                            if change_pct < self.min_price_change:
                                continue
                            
                            # 시가총액 체크
                            try:
                                ticker_symbol = f"{code}.KS" if code.startswith('0') else f"{code}.KQ"
                                stock = await asyncio.to_thread(yf.Ticker, ticker_symbol)
                                info = stock.info
                                
                                market_cap = info.get('marketCap', 0)
                                if market_cap > 750_000_000:
                                    continue
                                
                                if info.get('quoteType') == 'ETF':
                                    continue
                                
                            except Exception as e:
                                logger.debug(f"{code} yfinance 체크 실패: {e}")
                            
                            alert_key = f"{code}_{datetime.now().date()}"
                            if alert_key in self.seen_surge:
                                continue
                            
                            self.seen_surge.add(alert_key)
                            
                            signals.append({
                                'ticker': code,
                                'name': name,
                                'market': 'KR',
                                'price': price,
                                'change_percent': change_pct,
                                'volume': volume,
                                'volume_ratio': volume_ratio,
                                'signals': [f'급등 {change_pct:.1f}%', f'거래량 {volume_ratio:.1f}배'],
                                'reason': f'🔥 실시간 급등 포착 ({change_pct:.1f}%, {volume_ratio:.1f}배)',
                                'timestamp': datetime.now(),
                                'alert_type': 'realtime_surge'
                            })
                            
                            logger.info(f"🔥 KR Surge: {name} +{change_pct:.1f}%")
                            
                        except Exception as e:
                            logger.debug(f"한국 급등주 파싱 오류: {e}")
                            continue
            
        except Exception as e:
            logger.error(f"한국 실시간 급등 스캔 오류: {e}")
        
        return signals
    
    async def _scan_program(self):
        """프로그램 매매 (User-Agent 랜덤화)"""
        signals = []
        
        try:
            headers = self._get_random_headers()
            
            async with aiohttp.ClientSession() as session:
                await self._random_delay(1.0, 0.3)
                
                async with session.get(self.program_url, headers=headers, timeout=10) as response:
                    if response.status != 200:
                        return signals
                    
                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')
                    rows = soup.select('table.type_1 tr')[2:32]
                    
                    for row in rows:
                        try:
                            cols = row.select('td')
                            if len(cols) < 7:
                                continue
                            
                            name_elem = cols[0].select_one('a')
                            if not name_elem:
                                continue
                            
                            name = name_elem.text.strip()
                            
                            href = name_elem.get('href', '')
                            code_match = re.search(r'code=(\d+)', href)
                            if not code_match:
                                continue
                            
                            code = code_match.group(1)
                            
                            buy_text = cols[5].text.strip().replace(',', '')
                            if not buy_text.replace('-', '', 1).isdigit():
                                continue
                            
                            buy_amount = int(buy_text)
                            
                            if buy_amount < 300:
                                continue
                            
                            alert_key = f"{code}_{datetime.now().date()}"
                            if alert_key in self.seen_program:
                                continue
                            
                            self.seen_program.add(alert_key)
                            
                            signals.append({
                                'ticker': code,
                                'name': name,
                                'market': 'KR',
                                'signal_type': 'program_buy',
                                'buy_amount': buy_amount,
                                'reason': f'💻 프로그램 순매수 ({buy_amount/100:.0f}억원)',
                                'timestamp': datetime.now(),
                                'alert_type': 'program'
                            })
                            
                            logger.info(f"💻 프로그램: {name} ({buy_amount/100}억)")
                            
                        except Exception:
                            continue
            
        except Exception as e:
            logger.error(f"프로그램 스캔 오류: {e}")
        
        return signals
    
    async def _scan_theme(self):
        """테마주 (User-Agent 랜덤화)"""
        signals = []
        
        try:
            headers = self._get_random_headers()
            
            async with aiohttp.ClientSession() as session:
                await self._random_delay(1.0, 0.3)
                
                async with session.get(self.theme_url, headers=headers, timeout=10) as response:
                    if response.status != 200:
                        return signals
                    
                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')
                    rows = soup.select('table.type_1 tr')[2:22]
                    
                    for row in rows:
                        try:
                            cols = row.select('td')
                            if len(cols) < 4:
                                continue
                            
                            theme_elem = cols[0].select_one('a')
                            if not theme_elem:
                                continue
                            
                            theme_name = theme_elem.text.strip()
                            
                            change_text = cols[2].text.strip().replace('%', '').replace('+', '')
                            if not change_text.replace('.', '', 1).replace('-', '', 1).isdigit():
                                continue
                            
                            change_pct = float(change_text)
                            
                            up_count_text = cols[3].text.strip().split('/')[0]
                            up_count = int(up_count_text) if up_count_text.isdigit() else 0
                            
                            if change_pct < 3.0 or up_count < 5:
                                continue
                            
                            alert_key = f"{theme_name}_{datetime.now().date()}"
                            if alert_key in self.seen_theme:
                                continue
                            
                            theme_detail_url = "https://finance.naver.com" + theme_elem.get('href', '')
                            
                            top3 = await self._get_theme_top3(theme_detail_url, session)
                            
                            if not top3:
                                continue
                            
                            self.seen_theme.add(alert_key)
                            
                            trigger_msg = f'🎨 테마 전체 급등 ({theme_name} +{change_pct:.1f}%)\n'
                            trigger_msg += f'👑 1위: {top3[0]["name"]} (+{top3[0]["change"]:.1f}%)\n'
                            if len(top3) > 1:
                                trigger_msg += f'🥈 2위: {top3[1]["name"]} (+{top3[1]["change"]:.1f}%)\n'
                            if len(top3) > 2:
                                trigger_msg += f'🥉 3위: {top3[2]["name"]} (+{top3[2]["change"]:.1f}%)'
                            
                            signals.append({
                                'ticker': top3[0]['code'],
                                'name': top3[0]['name'],
                                'market': 'KR',
                                'signal_type': 'theme_surge',
                                'theme_name': theme_name,
                                'top3': top3,
                                'reason': trigger_msg,
                                'timestamp': datetime.now(),
                                'alert_type': 'theme'
                            })
                            
                            logger.info(f"🎨 테마: {theme_name} (1위: {top3[0]['name']})")
                            
                        except Exception:
                            continue
            
        except Exception as e:
            logger.error(f"테마 스캔 오류: {e}")
        
        return signals
    
    async def _get_theme_top3(self, theme_url, session):
        """테마 내 1~3위"""
        try:
            await self._random_delay(0.5, 0.2)
            
            async with session.get(theme_url, timeout=5) as response:
                if response.status != 200:
                    return None
                
                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')
                rows = soup.select('table.type_5 tr')[2:20]
                
                stocks = []
                
                for row in rows:
                    try:
                        cols = row.select('td')
                        if len(cols) < 5:
                            continue
                        
                        name_elem = cols[0].select_one('a')
                        if not name_elem:
                            continue
                        
                        name = name_elem.text.strip()
                        
                        href = name_elem.get('href', '')
                        code_match = re.search(r'code=(\d+)', href)
                        if not code_match:
                            continue
                        
                        code = code_match.group(1)
                        
                        price_text = cols[1].text.strip().replace(',', '')
                        price = int(price_text) if price_text.isdigit() else 0
                        
                        change_text = cols[3].text.strip().replace('%', '').replace('+', '')
                        change = float(change_text) if change_text.replace('.', '', 1).replace('-', '', 1).isdigit() else 0
                        
                        if change <= 0:
                            continue
                        
                        stocks.append({
                            'name': name,
                            'code': code,
                            'price': price,
                            'change': change
                        })
                        
                    except:
                        continue
                
                stocks.sort(key=lambda x: x['change'], reverse=True)
                
                return stocks[:3] if len(stocks) >= 1 else None
                
        except Exception:
            return None
    
    def cleanup_alerts(self):
        """메모리 정리"""
        if len(self.seen_surge) > 1000:
            self.seen_surge.clear()
        if len(self.seen_program) > 1000:
            self.seen_program.clear()
        if len(self.seen_theme) > 1000:
            self.seen_theme.clear()
        
        # 동적 종목도 주기적으로 정리 (24시간 지난 것)
        # 여기서는 단순히 크기만 제한
        if len(self.dynamic_tickers_us) > 100:
            # 오래된 것부터 제거 (set이므로 임의로 pop)
            for _ in range(50):
                if self.dynamic_tickers_us:
                    self.dynamic_tickers_us.pop()
        
        if len(self.dynamic_tickers_kr) > 100:
            for _ in range(50):
                if self.dynamic_tickers_kr:
                    self.dynamic_tickers_kr.pop()
    
    async def _scan_yahoo_screener(self):
        """2차: Yahoo Finance screener (간단한 API 방식)"""
        signals = []
        
        try:
            headers = self._get_random_headers()
            
            # Yahoo Finance screener API (공개 엔드포인트)
            yahoo_url = "https://query1.finance.yahoo.com/v1/finance/screener"
            
            payload = {
                "size": 50,
                "offset": 0,
                "sortField": "percentchange",
                "sortType": "desc",
                "quoteType": "equity",
                "query": {
                    "operator": "and",
                    "operands": [
                        {"operator": "gt", "operands": ["percentchange", 10]},
                        {"operator": "gt", "operands": ["intradaymarketcap", 1000000]}
                    ]
                }
            }
            
            async with aiohttp.ClientSession() as session:
                await self._random_delay(1.0, 0.3)
                
                async with session.post(yahoo_url, json=payload, headers=headers, timeout=15) as response:
                    if response.status != 200:
                        logger.warning(f"Yahoo screener 실패: {response.status}")
                        return signals
                    
                    data = await response.json()
                    
                    quotes = data.get('finance', {}).get('result', [{}])[0].get('quotes', [])
                    
                    if not quotes:
                        logger.warning("Yahoo screener 결과 없음")
                        return signals
                    
                    logger.info(f"Yahoo screener: {len(quotes)}개 발견")
                    
                    for quote in quotes[:20]:  # 상위 20개
                        try:
                            ticker = quote.get('symbol', '')
                            name = quote.get('shortName', ticker)
                            price = quote.get('regularMarketPrice', 0)
                            change_pct = quote.get('regularMarketChangePercent', 0)
                            volume = quote.get('regularMarketVolume', 0)
                            avg_volume = quote.get('averageDailyVolume3Month', 0)
                            
                            if not ticker:
                                continue
                            
                            volume_ratio = volume / avg_volume if avg_volume > 0 else 0
                            
                            # 필터
                            if change_pct < self.min_price_change:
                                continue
                            
                            if volume_ratio < self.min_volume_ratio:
                                continue
                            
                            # 시가총액 체크
                            market_cap = quote.get('marketCap', 0)
                            if market_cap > self.max_market_cap_us:
                                continue
                            
                            # 중복 체크
                            alert_key = f"{ticker}_{datetime.now().date()}"
                            if alert_key in self.seen_surge:
                                continue
                            
                            self.seen_surge.add(alert_key)
                            
                            signals.append({
                                'ticker': ticker,
                                'name': name,
                                'market': 'US',
                                'price': price,
                                'change_percent': change_pct,
                                'volume': volume,
                                'volume_ratio': volume_ratio,
                                'signals': [f'Surge {change_pct:.1f}%', f'Volume {volume_ratio:.1f}x'],
                                'reason': f'🔥 Yahoo Screener 급등 ({change_pct:.1f}%)',
                                'timestamp': datetime.now(),
                                'alert_type': 'realtime_surge'
                            })
                            
                            logger.info(f"🔥 US Surge (Yahoo): {ticker} +{change_pct:.1f}%")
                            
                        except Exception as e:
                            logger.debug(f"Yahoo quote 파싱 오류: {e}")
                            continue
            
        except Exception as e:
            logger.error(f"Yahoo screener 오류: {e}")
        
        return signals
    
    async def _scan_yfinance_api(self):
        """3차: yfinance API로 직접 조회 (최후 수단)"""
        signals = []
        
        try:
            logger.info("yfinance API로 S&P 500 상위 종목 조회")
            
            # S&P 500 주요 종목들 (유동성 높은 상위 50개)
            sp500_tickers = [
                'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'TSLA', 'META', 'BRK.B', 'UNH', 'JNJ',
                'V', 'WMT', 'JPM', 'MA', 'PG', 'HD', 'CVX', 'MRK', 'ABBV', 'KO',
                'PEP', 'AVGO', 'COST', 'TMO', 'MCD', 'CSCO', 'ACN', 'DHR', 'VZ', 'ABT',
                'ADBE', 'NFLX', 'CRM', 'NKE', 'WFC', 'TXN', 'BMY', 'PM', 'NEE', 'UPS',
                'RTX', 'HON', 'ORCL', 'QCOM', 'IBM', 'AMD', 'INTC', 'BA', 'CAT', 'GE'
            ]
            
            for ticker in sp500_tickers[:30]:  # 상위 30개만 체크 (속도)
                try:
                    await self._random_delay(0.2, 0.1)  # 빠른 체크
                    
                    stock = await asyncio.to_thread(yf.Ticker, ticker)
                    hist = stock.history(period='5d')
                    
                    if hist.empty or len(hist) < 2:
                        continue
                    
                    current = hist['Close'].iloc[-1]
                    prev = hist['Close'].iloc[-2]
                    change_pct = ((current - prev) / prev) * 100
                    
                    volume = hist['Volume'].iloc[-1]
                    avg_volume = hist['Volume'][:-1].mean()
                    volume_ratio = volume / avg_volume if avg_volume > 0 else 0
                    
                    # 급등 체크
                    if change_pct >= self.min_price_change and volume_ratio >= self.min_volume_ratio:
                        alert_key = f"{ticker}_{datetime.now().date()}"
                        if alert_key not in self.seen_surge:
                            self.seen_surge.add(alert_key)
                            
                            info = stock.info
                            name = info.get('longName', ticker)
                            
                            signals.append({
                                'ticker': ticker,
                                'name': name,
                                'market': 'US',
                                'price': current,
                                'change_percent': change_pct,
                                'volume': volume,
                                'volume_ratio': volume_ratio,
                                'signals': [f'Surge {change_pct:.1f}%', f'Volume {volume_ratio:.1f}x'],
                                'reason': f'🔥 yfinance API 급등 ({change_pct:.1f}%)',
                                'timestamp': datetime.now(),
                                'alert_type': 'realtime_surge'
                            })
                            
                            logger.info(f"🔥 US Surge (yfinance): {ticker} +{change_pct:.1f}%")
                
                except Exception as e:
                    logger.debug(f"{ticker} yfinance 체크 오류: {e}")
                    continue
            
        except Exception as e:
            logger.error(f"yfinance API 오류: {e}")
        
        return signals
