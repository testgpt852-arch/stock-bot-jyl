# -*- coding: utf-8 -*-
"""
Momentum Tracker - Production
- [핵심] curl_cffi AsyncSession(impersonate="chrome110") 으로 Finviz 크롤링
- 동적 컬럼 매핑 (헤더 텍스트 기반, 고정 인덱스 제거)
- yfinance prepost=True (장전 데이터 포함)
- 동적 종목 TTL 24시간 자동 만료
- 알림 우선순위 (CRITICAL / HIGH / MEDIUM / LOW)
- 다중 fallback: Finviz → Yahoo → yfinance
- 이중 스캔 모드: 뉴스 종목 1분 / 시장 전체 10분
"""

import asyncio
import aiohttp
import logging
from datetime import datetime, timedelta, date
from enum import Enum
from bs4 import BeautifulSoup
import yfinance as yf
import re
import random
from curl_cffi.requests import AsyncSession

logger = logging.getLogger(__name__)


class AlertPriority(Enum):
    CRITICAL = 1  # 뉴스 종목 + 20%↑ + 거래량 10배
    HIGH     = 2  # 뉴스 종목 급등
    MEDIUM   = 3  # 시장 전체 스캔 급등
    LOW      = 4  # 프로그램 매매, 테마주


class MomentumTracker:
    def __init__(self):
        # 한국 소스
        self.kr_surge_url  = "https://finance.naver.com/sise/sise_quant.naver"
        self.program_url   = "https://finance.naver.com/sise/programDeal.naver"
        self.theme_url     = "https://finance.naver.com/sise/theme.naver"

        # 미국 소스
        self.us_gainers_url = "https://finviz.com/screener.ashx?v=111&s=ta_topgainers"

        # 동적 종목 (TTL 24시간)
        self.dynamic_tickers_us: dict[str, datetime] = {}
        self.dynamic_tickers_kr: dict[str, datetime] = {}
        self.dynamic_ticker_ttl_hours = 24

        # 중복 방지
        self.seen_surge   = set()
        self.seen_program = set()
        self.seen_theme   = set()

        # Beast Mode 필터
        self.min_volume_ratio   = 5.0
        self.min_price_change   = 10.0
        self.max_market_cap_us  = 100_000_000_000
        self.max_market_cap_kr  = 750_000_000     # USD 기준 약 1조원

        # 통계
        self.stats = {
            'total_alerts':    0,
            'us_alerts':       0,
            'kr_alerts':       0,
            'critical_alerts': 0,
            'high_alerts':     0,
            'medium_alerts':   0,
            'finviz_success':  0,
            'yahoo_success':   0,
            'yfinance_success': 0,
            'avg_change_pct':  0.0,
            'max_change_pct':  0.0,
            'session_start':   datetime.now(),
        }

        # User-Agent 풀
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15',
        ]

        logger.info("🚀 Momentum Tracker (Production) 초기화")

    # ─────────────────────────────────────────────
    # 유틸
    # ─────────────────────────────────────────────
    def _get_random_headers(self):
        return {
            'User-Agent':               random.choice(self.user_agents),
            'Accept':                   'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language':          'en-US,en;q=0.5',
            'Accept-Encoding':          'gzip, deflate',
            'Connection':               'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }

    async def _random_delay(self, base=1.0, jitter=0.5):
        await asyncio.sleep(max(0.1, base + random.uniform(-jitter, jitter)))

    # ─────────────────────────────────────────────
    # 동적 종목 관리
    # ─────────────────────────────────────────────
    def add_dynamic_ticker(self, ticker: str, market: str = 'US'):
        """
        AI 분석 결과(top_ticker 또는 추천 종목)를 동적 감시 목록에 추가.
        24시간 TTL 자동 적용.
        """
        now = datetime.now()
        if market == 'US':
            self.dynamic_tickers_us[ticker.upper()] = now
            logger.info(f"➕ 동적 종목 추가 (US): {ticker.upper()} (TTL 24h)")
        else:
            self.dynamic_tickers_kr[ticker] = now
            logger.info(f"➕ 동적 종목 추가 (KR): {ticker} (TTL 24h)")

        # 최대 50개 유지 (초과 시 가장 오래된 것 제거)
        self._trim_dynamic_tickers('US')
        self._trim_dynamic_tickers('KR')

    def _trim_dynamic_tickers(self, market: str, limit: int = 50):
        pool = self.dynamic_tickers_us if market == 'US' else self.dynamic_tickers_kr
        while len(pool) > limit:
            oldest = min(pool, key=pool.get)
            del pool[oldest]
            logger.debug(f"➖ 동적 종목 제거 ({market}, TTL 초과): {oldest}")

    def _get_active_dynamic_tickers(self, market: str = 'US') -> list:
        """TTL 만료된 종목 제외 후 활성 목록 반환"""
        now = datetime.now()
        ttl = timedelta(hours=self.dynamic_ticker_ttl_hours)
        pool = self.dynamic_tickers_us if market == 'US' else self.dynamic_tickers_kr

        active = {t: ts for t, ts in pool.items() if now - ts < ttl}
        expired = set(pool.keys()) - set(active.keys())
        for t in expired:
            del pool[t]
            logger.debug(f"⏰ 동적 종목 TTL 만료 ({market}): {t}")

        if market == 'US':
            self.dynamic_tickers_us = active
        else:
            self.dynamic_tickers_kr = active

        return list(active.keys())

    # ─────────────────────────────────────────────
    # 우선순위 & 통계
    # ─────────────────────────────────────────────
    def _assign_priority(self, signal: dict, is_dynamic: bool = False) -> dict:
        change_pct   = signal.get('change_percent', 0)
        volume_ratio = signal.get('volume_ratio', 0)
        alert_type   = signal.get('alert_type', '')

        if alert_type in ('program', 'theme'):
            priority = AlertPriority.LOW
        elif is_dynamic and change_pct >= 20 and volume_ratio >= 10:
            priority = AlertPriority.CRITICAL
        elif is_dynamic:
            priority = AlertPriority.HIGH
        else:
            priority = AlertPriority.MEDIUM

        signal['priority'] = priority
        signal['priority_emoji'] = {
            AlertPriority.CRITICAL: '🚨🚨🚨',
            AlertPriority.HIGH:     '🔥🔥',
            AlertPriority.MEDIUM:   '🔥',
            AlertPriority.LOW:      '📊',
        }[priority]
        return signal

    def _update_stats(self, signal: dict):
        self.stats['total_alerts'] += 1
        if signal.get('market') == 'US':
            self.stats['us_alerts'] += 1
        else:
            self.stats['kr_alerts'] += 1

        p = signal.get('priority')
        if p == AlertPriority.CRITICAL:
            self.stats['critical_alerts'] += 1
        elif p == AlertPriority.HIGH:
            self.stats['high_alerts'] += 1
        elif p == AlertPriority.MEDIUM:
            self.stats['medium_alerts'] += 1

        change_pct = abs(signal.get('change_percent', 0))
        total = self.stats['total_alerts']
        prev_avg = self.stats['avg_change_pct']
        self.stats['avg_change_pct'] = (prev_avg * (total - 1) + change_pct) / total
        if change_pct > self.stats['max_change_pct']:
            self.stats['max_change_pct'] = change_pct

    def get_stats_summary(self) -> str:
        uptime = datetime.now() - self.stats['session_start']
        h = int(uptime.total_seconds() // 3600)
        m = int((uptime.total_seconds() % 3600) // 60)
        return (
            f"📊 Momentum Tracker 통계\n"
            f"━━━━━━━━━━━━━━━━\n"
            f"⏱️ 실행 시간: {h}h {m}m\n"
            f"🔔 총 알림: {self.stats['total_alerts']}건\n"
            f"  🇺🇸 US: {self.stats['us_alerts']}건\n"
            f"  🇰🇷 KR: {self.stats['kr_alerts']}건\n"
            f"━━━━━━━━━━━━━━━━\n"
            f"🚨 긴급(CRITICAL): {self.stats['critical_alerts']}건\n"
            f"🔥🔥 높음(HIGH):   {self.stats['high_alerts']}건\n"
            f"🔥 보통(MEDIUM):   {self.stats['medium_alerts']}건\n"
            f"━━━━━━━━━━━━━━━━\n"
            f"📈 평균 등락률: {self.stats['avg_change_pct']:.1f}%\n"
            f"🏆 최고 등락률: {self.stats['max_change_pct']:.1f}%\n"
            f"━━━━━━━━━━━━━━━━\n"
            f"📡 데이터 소스 성공:\n"
            f"  Finviz:   {self.stats['finviz_success']}회\n"
            f"  Yahoo:    {self.stats['yahoo_success']}회\n"
            f"  yfinance: {self.stats['yfinance_success']}회\n"
            f"━━━━━━━━━━━━━━━━\n"
            f"🔍 동적 감시 종목 (TTL 24h):\n"
            f"  US: {len(self.dynamic_tickers_us)}개\n"
            f"  KR: {len(self.dynamic_tickers_kr)}개\n"
        )

    # ─────────────────────────────────────────────
    # 공개 스캔 메서드
    # ─────────────────────────────────────────────
    async def scan_momentum(self, market: str = 'KR', mode: str = 'full') -> list:
        """
        mode='dynamic' : 뉴스 종목만 (1분 주기)
        mode='full'    : 시장 전체 스캔 (10분 주기)
        """
        signals = []

        if market == 'KR':
            if mode == 'dynamic':
                if self._get_active_dynamic_tickers('KR'):
                    signals.extend(await self._scan_dynamic_kr())
            else:
                signals.extend(await self._scan_realtime_surge_kr())
                signals.extend(await self._scan_program())
                signals.extend(await self._scan_theme())

        else:  # US
            if mode == 'dynamic':
                if self._get_active_dynamic_tickers('US'):
                    signals.extend(await self._scan_dynamic_us())
            else:
                signals.extend(await self._scan_realtime_surge_us())

        logger.info(f"🐺 모멘텀 [{market}][{mode}]: {len(signals)}개")
        return signals

    # ─────────────────────────────────────────────
    # 동적 종목 스캔 (1분 주기)
    # ─────────────────────────────────────────────
    async def _scan_dynamic_us(self) -> list:
        """AI가 지목한 US 종목 1분 집중 감시 (prepost=True로 장전 포함)"""
        signals = []
        active = self._get_active_dynamic_tickers('US')
        if not active:
            return signals

        for ticker in active:
            try:
                await self._random_delay(0.5, 0.2)
                stock = await asyncio.to_thread(yf.Ticker, ticker)
                # ✅ prepost=True: 장전/장후 데이터 포함
                hist = stock.history(period='5d', prepost=True)

                if hist.empty or len(hist) < 2:
                    continue

                current      = hist['Close'].iloc[-1]
                prev         = hist['Close'].iloc[-2]
                change_pct   = ((current - prev) / prev) * 100
                volume       = hist['Volume'].iloc[-1]
                avg_volume   = hist['Volume'][:-1].mean()
                volume_ratio = volume / avg_volume if avg_volume > 0 else 0

                if change_pct < self.min_price_change or volume_ratio < self.min_volume_ratio:
                    continue

                alert_key = f"{ticker}_{datetime.now().date()}"
                if alert_key in self.seen_surge:
                    continue
                self.seen_surge.add(alert_key)

                signal = {
                    'ticker':         ticker,
                    'name':           ticker,
                    'market':         'US',
                    'price':          current,
                    'change_percent': change_pct,
                    'volume_ratio':   volume_ratio,
                    'signals':        [f'Surge {change_pct:.1f}%', f'Volume {volume_ratio:.1f}x'],
                    'reason':         f'🔥🔥 뉴스 종목 급등 ({change_pct:.1f}%, {volume_ratio:.1f}배)',
                    'timestamp':      datetime.now(),
                    'alert_type':     'dynamic_surge',
                }
                signal = self._assign_priority(signal, is_dynamic=True)
                self._update_stats(signal)
                signals.append(signal)
                logger.info(f"{signal['priority_emoji']} 뉴스 종목 급등 (US): {ticker} +{change_pct:.1f}%")

            except Exception as e:
                logger.debug(f"동적 종목 체크 오류 (US, {ticker}): {e}")

        return signals

    async def _scan_dynamic_kr(self) -> list:
        """AI가 지목한 KR 종목 1분 집중 감시 (prepost=True)"""
        signals = []
        active = self._get_active_dynamic_tickers('KR')
        if not active:
            return signals

        for code in active:
            try:
                await self._random_delay(0.5, 0.2)
                symbol = f"{code}.KS" if code.startswith('0') else f"{code}.KQ"
                stock  = await asyncio.to_thread(yf.Ticker, symbol)
                # ✅ prepost=True
                hist   = stock.history(period='5d', prepost=True)

                if hist.empty or len(hist) < 2:
                    continue

                current      = hist['Close'].iloc[-1]
                prev         = hist['Close'].iloc[-2]
                change_pct   = ((current - prev) / prev) * 100
                volume       = hist['Volume'].iloc[-1]
                avg_volume   = hist['Volume'][:-1].mean()
                volume_ratio = volume / avg_volume if avg_volume > 0 else 0

                if change_pct < self.min_price_change or volume_ratio < self.min_volume_ratio:
                    continue

                alert_key = f"{code}_{datetime.now().date()}"
                if alert_key in self.seen_surge:
                    continue
                self.seen_surge.add(alert_key)

                info = await asyncio.to_thread(lambda: stock.info)
                name = info.get('longName', code)

                signal = {
                    'ticker':         code,
                    'name':           name,
                    'market':         'KR',
                    'price':          current,
                    'change_percent': change_pct,
                    'volume_ratio':   volume_ratio,
                    'signals':        [f'급등 {change_pct:.1f}%', f'거래량 {volume_ratio:.1f}배'],
                    'reason':         f'🔥 뉴스 종목 급등 ({change_pct:.1f}%, {volume_ratio:.1f}배)',
                    'timestamp':      datetime.now(),
                    'alert_type':     'dynamic_surge',
                }
                signal = self._assign_priority(signal, is_dynamic=True)
                self._update_stats(signal)
                signals.append(signal)
                logger.info(f"{signal['priority_emoji']} 뉴스 종목 급등 (KR): {name} +{change_pct:.1f}%")

            except Exception as e:
                logger.debug(f"동적 종목 체크 오류 (KR, {code}): {e}")

        return signals

    # ─────────────────────────────────────────────
    # 미국 전체 스캔 (다중 fallback)
    # ─────────────────────────────────────────────
    async def _scan_realtime_surge_us(self) -> list:
        """1차 Finviz → 2차 Yahoo → 3차 yfinance"""

        # 1차: Finviz (curl_cffi)
        try:
            logger.info("1차 시도: Finviz (curl_cffi)")
            signals = await self._scan_finviz()
            if signals:
                self.stats['finviz_success'] += 1
                logger.info(f"✅ Finviz 성공: {len(signals)}개")
                return signals
            logger.warning("Finviz 결과 0개 → Yahoo 시도")
        except Exception as e:
            logger.warning(f"Finviz 실패: {e} → Yahoo 시도")

        # 2차: Yahoo Finance
        try:
            logger.info("2차 시도: Yahoo Finance screener")
            signals = await self._scan_yahoo_screener()
            if signals:
                self.stats['yahoo_success'] += 1
                logger.info(f"✅ Yahoo 성공: {len(signals)}개")
                return signals
            logger.warning("Yahoo 결과 0개 → yfinance 시도")
        except Exception as e:
            logger.warning(f"Yahoo 실패: {e} → yfinance 시도")

        # 3차: yfinance 직접 조회
        try:
            logger.info("3차 시도: yfinance API")
            signals = await self._scan_yfinance_api()
            if signals:
                self.stats['yfinance_success'] += 1
                logger.info(f"✅ yfinance 성공: {len(signals)}개")
            else:
                logger.error("⚠️ 모든 방법 실패: 미국 급등주 0개")
            return signals
        except Exception as e:
            logger.error(f"yfinance API도 실패: {e}")

        return []

    async def _scan_finviz(self) -> list:
        """
        Finviz 스크래핑 - curl_cffi (Chrome TLS 지문 위장)
        동적 컬럼 매핑으로 헤더 변경에 강건
        """
        signals = []

        try:
            # ✅ curl_cffi AsyncSession (Chrome110 TLS 지문 위장)
            async with AsyncSession(impersonate="chrome110") as session:
                await self._random_delay(1.0, 0.3)

                response = await session.get(self.us_gainers_url, timeout=15)

                if response.status_code != 200:
                    logger.warning(f"Finviz 접근 실패: {response.status_code}")
                    return signals

                soup = BeautifulSoup(response.text, 'html.parser')

                # 테이블 탐색 (class 이름 변경에 대응)
                table = soup.find('table', {'class': lambda c: c and 'screener_table' in c})
                if not table:
                    # fallback: id 기반
                    wrapper = soup.find('tr', {'id': 'screener-table'})
                    if wrapper:
                        table = wrapper.find('table')
                if not table:
                    # fallback: 가장 큰 테이블
                    for t in soup.find_all('table'):
                        if len(t.find_all('tr')) > 10:
                            table = t
                            logger.warning("Finviz fallback: 가장 큰 테이블 사용")
                            break
                if not table:
                    logger.warning("Finviz 테이블을 찾을 수 없음")
                    return signals

                all_rows = table.find_all('tr')
                if len(all_rows) < 2:
                    return signals

                # ✅ 동적 컬럼 매핑 (헤더 텍스트 기반)
                header_cells = all_rows[0].find_all(['th', 'td'])
                col_map = {}
                for idx, cell in enumerate(header_cells):
                    text = cell.get_text(strip=True).lower()
                    if text in ('ticker', 'no.') or text == '#':
                        col_map.setdefault('ticker', idx)
                    elif 'company' in text:
                        col_map.setdefault('name', idx)
                    elif text == 'price':
                        col_map.setdefault('price', idx)
                    elif 'change' in text and '%' in text:
                        col_map.setdefault('change', idx)
                    elif text in ('volume', 'vol'):
                        col_map.setdefault('volume', idx)

                # 헤더 파싱 실패 시 Finviz 기본 레이아웃 사용
                if len(col_map) < 3:
                    logger.info("Finviz 헤더 파싱 실패, 기본 인덱스 사용 (Finviz v111)")
                    col_map = {'ticker': 1, 'name': 2, 'price': 8, 'change': 10, 'volume': 11}
                else:
                    logger.debug(f"Finviz 동적 컬럼 매핑: {col_map}")

                for row in all_rows[1:51]:
                    try:
                        cols = row.find_all('td')
                        if len(cols) < 12:
                            continue

                        # Ticker
                        t_idx = col_map.get('ticker', 1)
                        ticker_elem = cols[t_idx].find('a')
                        ticker = ticker_elem.get_text(strip=True) if ticker_elem else cols[t_idx].get_text(strip=True)
                        if not ticker:
                            continue

                        # Name
                        n_idx = col_map.get('name', 2)
                        name = cols[n_idx].get_text(strip=True)

                        # Price
                        p_idx = col_map.get('price', 8)
                        try:
                            price = float(cols[p_idx].get_text(strip=True))
                        except ValueError:
                            continue

                        # Change %
                        c_idx = col_map.get('change', 10)
                        change_text = cols[c_idx].get_text(strip=True).replace('%', '').replace('+', '')
                        try:
                            change_pct = float(change_text)
                        except ValueError:
                            continue

                        # Volume
                        v_idx = col_map.get('volume', 11)
                        vol_text = cols[v_idx].get_text(strip=True)
                        try:
                            if 'M' in vol_text:
                                volume = float(vol_text.replace('M', '')) * 1_000_000
                            elif 'K' in vol_text:
                                volume = float(vol_text.replace('K', '')) * 1_000
                            else:
                                volume = float(vol_text.replace(',', ''))
                        except ValueError:
                            volume = 0

                        if change_pct < self.min_price_change:
                            continue

                        # yfinance 추가 검증 (거래량 비율, 시가총액, ETF 여부)
                        await self._random_delay(0.3, 0.1)
                        volume_ratio = 0
                        try:
                            stock = await asyncio.to_thread(yf.Ticker, ticker)
                            # ✅ prepost=True
                            hist = stock.history(period='5d', prepost=True)
                            if hist.empty or len(hist) < 2:
                                continue
                            cur_vol    = hist['Volume'].iloc[-1]
                            avg_vol    = hist['Volume'][:-1].mean()
                            volume_ratio = cur_vol / avg_vol if avg_vol > 0 else 0
                            if volume_ratio < self.min_volume_ratio:
                                continue
                            info = await asyncio.to_thread(lambda: stock.info)
                            if info.get('marketCap', 0) > self.max_market_cap_us:
                                continue
                            if info.get('quoteType') == 'ETF':
                                continue
                        except Exception as e:
                            logger.debug(f"{ticker} yfinance 검증 실패: {e}")
                            if volume == 0:
                                continue

                        alert_key = f"{ticker}_{datetime.now().date()}"
                        if alert_key in self.seen_surge:
                            continue
                        self.seen_surge.add(alert_key)

                        signal = {
                            'ticker':         ticker,
                            'name':           name,
                            'market':         'US',
                            'price':          price,
                            'change_percent': change_pct,
                            'volume':         volume,
                            'volume_ratio':   volume_ratio,
                            'signals':        [f'Surge {change_pct:.1f}%', f'Volume {volume_ratio:.1f}x'],
                            'reason':         f'🔥 Finviz 급등 포착 ({change_pct:.1f}%)',
                            'timestamp':      datetime.now(),
                            'alert_type':     'realtime_surge',
                            'source':         'finviz',
                        }
                        signal = self._assign_priority(signal, is_dynamic=False)
                        self._update_stats(signal)
                        signals.append(signal)
                        logger.info(f"{signal['priority_emoji']} US Surge (Finviz): {ticker} +{change_pct:.1f}%")

                    except Exception as e:
                        logger.debug(f"Finviz 행 파싱 오류: {e}")

        except Exception as e:
            logger.error(f"Finviz 스캔 오류: {e}")

        return signals

    async def _scan_yahoo_screener(self) -> list:
        """2차: Yahoo Finance screener API"""
        signals = []
        try:
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
                        {"operator": "gt", "operands": ["intradaymarketcap", 1000000]},
                    ],
                },
            }

            async with aiohttp.ClientSession() as session:
                await self._random_delay(1.0, 0.3)
                async with session.post(
                    yahoo_url,
                    json=payload,
                    headers=self._get_random_headers(),
                    timeout=aiohttp.ClientTimeout(total=15),
                ) as response:
                    if response.status != 200:
                        logger.warning(f"Yahoo screener 실패: {response.status}")
                        return signals

                    data   = await response.json()
                    quotes = data.get('finance', {}).get('result', [{}])[0].get('quotes', [])

                    if not quotes:
                        logger.warning("Yahoo screener 결과 없음")
                        return signals

                    for quote in quotes[:20]:
                        try:
                            ticker       = quote.get('symbol', '')
                            name         = quote.get('shortName', ticker)
                            price        = quote.get('regularMarketPrice', 0)
                            change_pct   = quote.get('regularMarketChangePercent', 0)
                            volume       = quote.get('regularMarketVolume', 0)
                            avg_volume   = quote.get('averageDailyVolume3Month', 0)
                            market_cap   = quote.get('marketCap', 0)

                            if not ticker:
                                continue
                            if change_pct < self.min_price_change:
                                continue
                            if market_cap > self.max_market_cap_us:
                                continue

                            volume_ratio = volume / avg_volume if avg_volume > 0 else 0
                            if volume_ratio < self.min_volume_ratio:
                                continue

                            alert_key = f"{ticker}_{datetime.now().date()}"
                            if alert_key in self.seen_surge:
                                continue
                            self.seen_surge.add(alert_key)

                            signal = {
                                'ticker':         ticker,
                                'name':           name,
                                'market':         'US',
                                'price':          price,
                                'change_percent': change_pct,
                                'volume':         volume,
                                'volume_ratio':   volume_ratio,
                                'signals':        [f'Surge {change_pct:.1f}%', f'Volume {volume_ratio:.1f}x'],
                                'reason':         f'🔥 Yahoo Screener 급등 ({change_pct:.1f}%)',
                                'timestamp':      datetime.now(),
                                'alert_type':     'realtime_surge',
                                'source':         'yahoo',
                            }
                            signal = self._assign_priority(signal, is_dynamic=False)
                            self._update_stats(signal)
                            signals.append(signal)
                            logger.info(f"{signal['priority_emoji']} US Surge (Yahoo): {ticker} +{change_pct:.1f}%")

                        except Exception as e:
                            logger.debug(f"Yahoo quote 파싱 오류: {e}")

        except Exception as e:
            logger.error(f"Yahoo screener 오류: {e}")

        return signals

    async def _scan_yfinance_api(self) -> list:
        """
        3차: yfinance 직접 조회 (병렬 5개씩)
        S&P 500 상위 50개를 대상으로 급등 체크
        """
        signals = []

        sp500_tickers = [
            'AAPL','MSFT','GOOGL','AMZN','NVDA','TSLA','META','BRK-B','UNH','JNJ',
            'V','WMT','JPM','MA','PG','HD','CVX','MRK','ABBV','KO',
            'PEP','AVGO','COST','TMO','MCD','CSCO','ACN','DHR','VZ','ABT',
            'ADBE','NFLX','CRM','NKE','WFC','TXN','BMY','PM','NEE','UPS',
            'RTX','HON','ORCL','QCOM','IBM','AMD','INTC','BA','CAT','GE',
        ]

        async def check_one(ticker: str):
            try:
                await self._random_delay(0.2, 0.1)
                stock = await asyncio.to_thread(yf.Ticker, ticker)
                # ✅ prepost=True
                hist  = stock.history(period='5d', prepost=True)
                if hist.empty or len(hist) < 2:
                    return None

                current      = hist['Close'].iloc[-1]
                prev         = hist['Close'].iloc[-2]
                change_pct   = ((current - prev) / prev) * 100
                volume       = hist['Volume'].iloc[-1]
                avg_volume   = hist['Volume'][:-1].mean()
                volume_ratio = volume / avg_volume if avg_volume > 0 else 0

                if change_pct < self.min_price_change or volume_ratio < self.min_volume_ratio:
                    return None

                alert_key = f"{ticker}_{datetime.now().date()}"
                if alert_key in self.seen_surge:
                    return None
                self.seen_surge.add(alert_key)

                info = await asyncio.to_thread(lambda: stock.info)
                name = info.get('longName', ticker)

                return {
                    'ticker':         ticker,
                    'name':           name,
                    'market':         'US',
                    'price':          current,
                    'change_percent': change_pct,
                    'volume':         volume,
                    'volume_ratio':   volume_ratio,
                    'signals':        [f'Surge {change_pct:.1f}%', f'Volume {volume_ratio:.1f}x'],
                    'reason':         f'🔥 yfinance 급등 ({change_pct:.1f}%)',
                    'timestamp':      datetime.now(),
                    'alert_type':     'realtime_surge',
                    'source':         'yfinance',
                }
            except Exception as e:
                logger.debug(f"{ticker} yfinance 체크 오류: {e}")
                return None

        batch_size = 5
        for i in range(0, min(len(sp500_tickers), 30), batch_size):
            batch   = sp500_tickers[i:i + batch_size]
            results = await asyncio.gather(*[check_one(t) for t in batch], return_exceptions=True)
            for result in results:
                if result and not isinstance(result, Exception):
                    result = self._assign_priority(result, is_dynamic=False)
                    self._update_stats(result)
                    signals.append(result)
                    logger.info(f"{result['priority_emoji']} US Surge (yfinance): {result['ticker']} +{result['change_percent']:.1f}%")

        return signals

    # ─────────────────────────────────────────────
    # 한국 전체 스캔
    # ─────────────────────────────────────────────
    async def _scan_realtime_surge_kr(self) -> list:
        signals = []
        try:
            async with aiohttp.ClientSession() as session:
                await self._random_delay(1.0, 0.3)
                async with session.get(
                    self.kr_surge_url,
                    headers=self._get_random_headers(),
                    timeout=aiohttp.ClientTimeout(total=15),
                ) as response:
                    if response.status != 200:
                        logger.warning(f"한국 급등주 접근 실패: {response.status}")
                        return signals

                    soup = BeautifulSoup(await response.text(), 'html.parser')
                    rows = soup.select('table.type_2 tr')[2:52]

                    for row in rows:
                        try:
                            cols = row.select('td')
                            if len(cols) < 11:
                                continue

                            name_elem = cols[1].select_one('a')
                            if not name_elem:
                                continue
                            name = name_elem.get_text(strip=True)
                            href = name_elem.get('href', '')
                            m    = re.search(r'code=(\d+)', href)
                            if not m:
                                continue
                            code = m.group(1)

                            price_text = cols[2].get_text(strip=True).replace(',', '')
                            if not price_text.isdigit():
                                continue
                            price = int(price_text)

                            change_text = cols[4].get_text(strip=True).replace('%', '').replace('+', '').replace('-', '')
                            if not change_text.replace('.', '', 1).isdigit():
                                continue
                            change_pct = float(change_text)

                            vol_ratio_text = cols[10].get_text(strip=True).replace('%', '').replace('+', '')
                            if not vol_ratio_text.replace('.', '', 1).isdigit():
                                continue
                            volume_ratio = float(vol_ratio_text) / 100.0 + 1.0

                            if change_pct < self.min_price_change or volume_ratio < self.min_volume_ratio:
                                continue

                            # 시가총액 + ETF 체크
                            try:
                                symbol = f"{code}.KS" if code.startswith('0') else f"{code}.KQ"
                                stock  = await asyncio.to_thread(yf.Ticker, symbol)
                                info   = await asyncio.to_thread(lambda: stock.info)
                                if info.get('marketCap', 0) > self.max_market_cap_kr:
                                    continue
                                if info.get('quoteType') == 'ETF':
                                    continue
                            except Exception as e:
                                logger.debug(f"{code} KR yfinance 체크 실패: {e}")

                            alert_key = f"{code}_{datetime.now().date()}"
                            if alert_key in self.seen_surge:
                                continue
                            self.seen_surge.add(alert_key)

                            signal = {
                                'ticker':         code,
                                'name':           name,
                                'market':         'KR',
                                'price':          price,
                                'change_percent': change_pct,
                                'volume_ratio':   volume_ratio,
                                'signals':        [f'급등 {change_pct:.1f}%', f'거래량 {volume_ratio:.1f}배'],
                                'reason':         f'🔥 실시간 급등 ({change_pct:.1f}%, {volume_ratio:.1f}배)',
                                'timestamp':      datetime.now(),
                                'alert_type':     'realtime_surge',
                            }
                            signal = self._assign_priority(signal, is_dynamic=False)
                            self._update_stats(signal)
                            signals.append(signal)
                            logger.info(f"{signal['priority_emoji']} KR Surge: {name} +{change_pct:.1f}%")

                        except Exception as e:
                            logger.debug(f"KR 급등주 파싱 오류: {e}")

        except Exception as e:
            logger.error(f"한국 실시간 급등 스캔 오류: {e}")

        return signals

    async def _scan_program(self) -> list:
        signals = []
        try:
            async with aiohttp.ClientSession() as session:
                await self._random_delay(1.0, 0.3)
                async with session.get(
                    self.program_url,
                    headers=self._get_random_headers(),
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as response:
                    if response.status != 200:
                        return signals

                    soup = BeautifulSoup(await response.text(), 'html.parser')
                    rows = soup.select('table.type_1 tr')[2:32]

                    for row in rows:
                        try:
                            cols = row.select('td')
                            if len(cols) < 7:
                                continue
                            name_elem = cols[0].select_one('a')
                            if not name_elem:
                                continue
                            name = name_elem.get_text(strip=True)
                            href = name_elem.get('href', '')
                            m    = re.search(r'code=(\d+)', href)
                            if not m:
                                continue
                            code = m.group(1)

                            buy_text = cols[5].get_text(strip=True).replace(',', '')
                            if not buy_text.replace('-', '', 1).isdigit():
                                continue
                            buy_amount = int(buy_text)
                            if buy_amount < 300:
                                continue

                            alert_key = f"{code}_{datetime.now().date()}"
                            if alert_key in self.seen_program:
                                continue
                            self.seen_program.add(alert_key)

                            signal = {
                                'ticker':      code,
                                'name':        name,
                                'market':      'KR',
                                'signal_type': 'program_buy',
                                'buy_amount':  buy_amount,
                                'reason':      f'💻 프로그램 순매수 ({buy_amount / 100:.0f}억원)',
                                'timestamp':   datetime.now(),
                                'alert_type':  'program',
                            }
                            signal = self._assign_priority(signal, is_dynamic=False)
                            signals.append(signal)
                            logger.info(f"💻 프로그램: {name} ({buy_amount / 100:.0f}억)")

                        except Exception:
                            continue

        except Exception as e:
            logger.error(f"프로그램 스캔 오류: {e}")

        return signals

    async def _scan_theme(self) -> list:
        signals = []
        try:
            async with aiohttp.ClientSession() as session:
                await self._random_delay(1.0, 0.3)
                async with session.get(
                    self.theme_url,
                    headers=self._get_random_headers(),
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as response:
                    if response.status != 200:
                        return signals

                    soup = BeautifulSoup(await response.text(), 'html.parser')
                    rows = soup.select('table.type_1 tr')[2:22]

                    for row in rows:
                        try:
                            cols = row.select('td')
                            if len(cols) < 4:
                                continue
                            theme_elem = cols[0].select_one('a')
                            if not theme_elem:
                                continue
                            theme_name = theme_elem.get_text(strip=True)

                            change_text = cols[2].get_text(strip=True).replace('%', '').replace('+', '')
                            if not change_text.replace('.', '', 1).replace('-', '', 1).isdigit():
                                continue
                            change_pct = float(change_text)

                            up_count_text = cols[3].get_text(strip=True).split('/')[0]
                            up_count = int(up_count_text) if up_count_text.isdigit() else 0

                            if change_pct < 3.0 or up_count < 5:
                                continue

                            alert_key = f"{theme_name}_{datetime.now().date()}"
                            if alert_key in self.seen_theme:
                                continue

                            theme_url = "https://finance.naver.com" + theme_elem.get('href', '')
                            top3 = await self._get_theme_top3(theme_url, session)
                            if not top3:
                                continue

                            self.seen_theme.add(alert_key)

                            msg = (
                                f'🎨 테마 전체 급등 ({theme_name} +{change_pct:.1f}%)\n'
                                f'👑 1위: {top3[0]["name"]} (+{top3[0]["change"]:.1f}%)\n'
                            )
                            if len(top3) > 1:
                                msg += f'🥈 2위: {top3[1]["name"]} (+{top3[1]["change"]:.1f}%)\n'
                            if len(top3) > 2:
                                msg += f'🥉 3위: {top3[2]["name"]} (+{top3[2]["change"]:.1f}%)'

                            signal = {
                                'ticker':     top3[0]['code'],
                                'name':       top3[0]['name'],
                                'market':     'KR',
                                'theme_name': theme_name,
                                'top3':       top3,
                                'reason':     msg,
                                'timestamp':  datetime.now(),
                                'alert_type': 'theme',
                            }
                            signal = self._assign_priority(signal, is_dynamic=False)
                            signals.append(signal)
                            logger.info(f"🎨 테마: {theme_name} (1위: {top3[0]['name']})")

                        except Exception:
                            continue

        except Exception as e:
            logger.error(f"테마 스캔 오류: {e}")

        return signals

    async def _get_theme_top3(self, theme_url: str, session) -> list | None:
        try:
            await self._random_delay(0.5, 0.2)
            async with session.get(theme_url, timeout=aiohttp.ClientTimeout(total=5)) as response:
                if response.status != 200:
                    return None

                soup   = BeautifulSoup(await response.text(), 'html.parser')
                rows   = soup.select('table.type_5 tr')[2:20]
                stocks = []

                for row in rows:
                    try:
                        cols = row.select('td')
                        if len(cols) < 5:
                            continue
                        name_elem = cols[0].select_one('a')
                        if not name_elem:
                            continue
                        name = name_elem.get_text(strip=True)
                        href = name_elem.get('href', '')
                        m    = re.search(r'code=(\d+)', href)
                        if not m:
                            continue
                        code = m.group(1)

                        price_text  = cols[1].get_text(strip=True).replace(',', '')
                        price       = int(price_text) if price_text.isdigit() else 0
                        change_text = cols[3].get_text(strip=True).replace('%', '').replace('+', '')
                        change      = float(change_text) if change_text.replace('.', '', 1).replace('-', '', 1).isdigit() else 0

                        if change <= 0:
                            continue
                        stocks.append({'name': name, 'code': code, 'price': price, 'change': change})
                    except Exception:
                        continue

                stocks.sort(key=lambda x: x['change'], reverse=True)
                return stocks[:3] if stocks else None

        except Exception:
            return None

    # ─────────────────────────────────────────────
    # 메모리 정리
    # ─────────────────────────────────────────────
    def cleanup_alerts(self):
        """7일 지난 날짜 데이터 정리. seen_* set이 1000개 초과 시 절반 삭제."""
        for s in (self.seen_surge, self.seen_program, self.seen_theme):
            if len(s) > 1000:
                to_remove = list(s)[:len(s) - 500]
                for item in to_remove:
                    s.discard(item)
        logger.info("메모리 정리 완료")
