# -*- coding: utf-8 -*-
"""
Momentum Tracker v2.2 - 완전체
- 급등주 감지
- 프로그램 매매 (3억+)
- 테마주 연쇄 상승 (1등, 2등, 3등)
- 중복 방지 완벽
"""

import asyncio
import aiohttp
import logging
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
import yfinance as yf
import re

logger = logging.getLogger(__name__)

class MomentumTrackerV2_2:
    def __init__(self):
        # 한국 소스
        self.program_url = "https://finance.naver.com/sise/programDeal.naver"
        self.theme_url = "https://finance.naver.com/sise/theme.naver"
        
        # 미국 종목
        self.us_watchlist = ['NVDA', 'TSLA', 'AAPL', 'MSFT', 'AMD', 'GOOGL', 'META', 'AMZN']
        
        # 한국 종목
        self.kr_watchlist = [
            ('005930', '삼성전자'),
            ('000660', 'SK하이닉스'),
            ('035420', 'NAVER'),
            ('005380', '현대차'),
            ('051910', 'LG화학'),
        ]
        
        # 중복 방지
        self.seen_surge = set()        # 급등 알림
        self.seen_program = set()      # 프로그램 매매
        self.seen_theme = set()        # 테마
        
        logger.info("📊 Momentum Tracker v2.2 초기화")
    
    async def scan_momentum(self, market='KR'):
        """모멘텀 스캔 (통합)"""
        signals = []
        
        if market == 'KR':
            # 1. 급등주
            surge_signals = await self._scan_surge_kr()
            signals.extend(surge_signals)
            
            # 2. 프로그램 매매
            program_signals = await self._scan_program()
            signals.extend(program_signals)
            
            # 3. 테마주
            theme_signals = await self._scan_theme()
            signals.extend(theme_signals)
        
        else:  # US
            surge_signals = await self._scan_surge_us()
            signals.extend(surge_signals)
        
        logger.info(f"📊 모멘텀: {len(signals)}개 ({market})")
        return signals
    
    async def _scan_surge_kr(self):
        """한국 급등주"""
        signals = []
        
        try:
            for code, name in self.kr_watchlist:
                try:
                    ticker = f"{code}.KS"
                    stock = await asyncio.to_thread(yf.Ticker, ticker)
                    
                    hist = stock.history(period='5d')
                    if hist.empty or len(hist) < 2:
                        continue
                    
                    current = hist['Close'].iloc[-1]
                    prev = hist['Close'].iloc[-2]
                    change_pct = ((current - prev) / prev) * 100
                    
                    volume = hist['Volume'].iloc[-1]
                    avg_volume = hist['Volume'].mean()
                    volume_ratio = volume / avg_volume if avg_volume > 0 else 0
                    
                    # 급등 조건
                    detected_signals = []
                    
                    if change_pct >= 5.0:
                        detected_signals.append('급등 5%+')
                    
                    if volume_ratio >= 3.0:
                        detected_signals.append('거래량폭증 3배+')
                    
                    # 연속 상승
                    if len(hist) >= 3:
                        consecutive = all(
                            hist['Close'].iloc[i] > hist['Close'].iloc[i-1]
                            for i in range(-3, 0)
                        )
                        if consecutive:
                            detected_signals.append('연속 상승 3일')
                    
                    # 52주 신고가
                    hist_1y = stock.history(period='1y')
                    if not hist_1y.empty:
                        high_52w = hist_1y['High'].max()
                        if current >= high_52w * 0.99:
                            detected_signals.append('52주 신고가')
                    
                    # 최소 2개 신호
                    if len(detected_signals) < 2:
                        continue
                    
                    # 중복 체크
                    alert_key = f"{code}_{datetime.now().date()}"
                    if alert_key in self.seen_surge:
                        continue
                    
                    self.seen_surge.add(alert_key)
                    
                    # 뉴스 역추적 (간소화)
                    reason = "시장 반응 (뉴스 확인 필요)"
                    
                    signals.append({
                        'ticker': code,
                        'name': name,
                        'market': 'KR',
                        'price': current,
                        'change_percent': change_pct,
                        'volume_ratio': volume_ratio,
                        'signals': detected_signals,
                        'reason': reason,
                        'timestamp': datetime.now()
                    })
                    
                    logger.info(f"🔥 급등: {name} +{change_pct:.1f}%")
                    
                except Exception as e:
                    logger.debug(f"{code} 스캔 오류: {e}")
                    continue
            
        except Exception as e:
            logger.error(f"한국 급등 스캔 오류: {e}")
        
        return signals
    
    async def _scan_surge_us(self):
        """미국 급등주"""
        signals = []
        
        try:
            for ticker in self.us_watchlist:
                try:
                    stock = await asyncio.to_thread(yf.Ticker, ticker)
                    
                    hist = stock.history(period='5d')
                    if hist.empty or len(hist) < 2:
                        continue
                    
                    current = hist['Close'].iloc[-1]
                    prev = hist['Close'].iloc[-2]
                    change_pct = ((current - prev) / prev) * 100
                    
                    volume = hist['Volume'].iloc[-1]
                    avg_volume = hist['Volume'].mean()
                    volume_ratio = volume / avg_volume if avg_volume > 0 else 0
                    
                    detected_signals = []
                    
                    if change_pct >= 5.0:
                        detected_signals.append('Surge 5%+')
                    
                    if volume_ratio >= 3.0:
                        detected_signals.append('Volume Explosion')
                    
                    if len(detected_signals) < 2:
                        continue
                    
                    alert_key = f"{ticker}_{datetime.now().date()}"
                    if alert_key in self.seen_surge:
                        continue
                    
                    self.seen_surge.add(alert_key)
                    
                    signals.append({
                        'ticker': ticker,
                        'name': ticker,
                        'market': 'US',
                        'price': current,
                        'change_percent': change_pct,
                        'volume_ratio': volume_ratio,
                        'signals': detected_signals,
                        'reason': "Market reaction (check news)",
                        'timestamp': datetime.now()
                    })
                    
                    logger.info(f"🔥 Surge: {ticker} +{change_pct:.1f}%")
                    
                except Exception as e:
                    logger.debug(f"{ticker} scan error: {e}")
                    continue
            
        except Exception as e:
            logger.error(f"US surge scan error: {e}")
        
        return signals
    
    async def _scan_program(self):
        """프로그램 매매 (중복 방지 추가)"""
        signals = []
        
        try:
            headers = {'User-Agent': 'Mozilla/5.0'}
            
            async with aiohttp.ClientSession() as session:
                async with session.get(self.program_url, headers=headers, timeout=10) as response:
                    if response.status != 200:
                        return signals
                    
                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')
                    
                    rows = soup.select('table.type_2 tr')[2:12]
                    
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
                            
                            if buy_amount < 300:  # 3억원
                                continue
                            
                            # 중복 체크
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
                                'timestamp': datetime.now()
                            })
                            
                            logger.info(f"💻 프로그램: {name} ({buy_amount/100}억)")
                            
                        except Exception:
                            continue
            
        except Exception as e:
            logger.error(f"프로그램 스캔 오류: {e}")
        
        return signals
    
    async def _scan_theme(self):
        """테마주 (1등, 2등, 3등 + 중복 방지)"""
        signals = []
        
        try:
            headers = {'User-Agent': 'Mozilla/5.0'}
            
            async with aiohttp.ClientSession() as session:
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
                            
                            # 중복 체크
                            alert_key = f"{theme_name}_{datetime.now().date()}"
                            if alert_key in self.seen_theme:
                                continue
                            
                            theme_detail_url = "https://finance.naver.com" + theme_elem.get('href', '')
                            
                            # 1~3위 추출
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
                                'timestamp': datetime.now()
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
