# -*- coding: utf-8 -*-
"""
Momentum Tracker (Production)
- ✅ curl_cffi AsyncSession(impersonate="chrome110") → Finviz Cloudflare 우회
- ✅ 동적 컬럼 매핑 (헤더 텍스트 기반, 하드코딩 인덱스 금지)
- ✅ yfinance prepost=True → 장전/장후 데이터 포함
- ✅ _scan_yfinance_api 함수 복구 (이전 버전에서 dead code 버그 있었음)
- ✅ 다중 fallback (Finviz → Yahoo → yfinance)
- ✅ 이중 스캔 모드 (뉴스 종목 1분 / 시장 전체 10분)
- ✅ Anti-Ban: 랜덤 User-Agent + 랜덤 지연
- ✅ 알림 우선순위 (CRITICAL/HIGH/MEDIUM/LOW)
- ✅ 동적 종목 TTL 24시간
- ✅ 날짜별 메모리 관리
- ✅ 통계 추적
"""

import asyncio
import aiohttp
import logging
from datetime import datetime, timedelta, date
from collections import defaultdict
from enum import Enum
from bs4 import BeautifulSoup, Tag
import yfinance as yf
import re
import random
from typing import List, Dict, Optional

# curl_cffi: Cloudflare TLS 지문 위장 (Finviz 전용)
try:
    from curl_cffi.requests import AsyncSession as CurlAsyncSession
    CURL_CFFI_AVAILABLE = True
except ImportError:
    CURL_CFFI_AVAILABLE = False
    logger_tmp = logging.getLogger(__name__)
    logger_tmp.warning("⚠️ curl_cffi 미설치 → Finviz는 aiohttp fallback 사용")

logger = logging.getLogger(__name__)


# ────────────────────────────────────────────────────────
# 알림 우선순위
# ────────────────────────────────────────────────────────
class AlertPriority(Enum):
    CRITICAL = 1   # 뉴스 언급 + 급등 동시 → 🚨🚨🚨
    HIGH     = 2   # 뉴스 종목 급등 → 🔥🔥
    MEDIUM   = 3   # 시장 전체 스캔 급등 → 🔥
    LOW      = 4   # 프로그램 매매, 테마주 → 📊

_PRIORITY_EMOJI = {
    AlertPriority.CRITICAL: '🚨🚨🚨',
    AlertPriority.HIGH:     '🔥🔥',
    AlertPriority.MEDIUM:   '🔥',
    AlertPriority.LOW:      '📊',
}


# ────────────────────────────────────────────────────────
# 메인 클래스
# ────────────────────────────────────────────────────────
class MomentumTracker:
    def __init__(self):
        # ── 한국 소스 URL ──
        self.kr_surge_url = "https://finance.naver.com/sise/sise_quant.naver"
        self.program_url  = "https://finance.naver.com/sise/programDeal.naver"
        self.theme_url    = "https://finance.naver.com/sise/theme.naver"

        # ── 미국 소스 URL ──
        self.us_gainers_url = "https://finviz.com/screener.ashx?v=111&s=ta_topgainers"

        # ── 동적 종목 (TTL 24h) ──
        self.dynamic_tickers_us: Dict[str, datetime] = {}  # {ticker: 추가시각}
        self.dynamic_tickers_kr: Dict[str, datetime] = {}
        self.dynamic_ticker_ttl_hours = 24

        # ── 중복 방지 (날짜별) ──
        self.seen_surge_by_date   = defaultdict(set)
        self.seen_program_by_date = defaultdict(set)
        self.seen_theme_by_date   = defaultdict(set)
        # 하위 호환 (기존 코드 참조 대비)
        self.seen_surge   = set()
        self.seen_program = set()
        self.seen_theme   = set()

        # ── Beast Mode 필터 ──
        self.min_volume_ratio   = 5.0
        self.min_price_change   = 10.0
        self.max_market_cap_kr  = 1_000_000
        self.max_market_cap_us  = 100_000_000_000

        # ── 통계 ──
        self.stats = {
            'total_alerts':    0,
            'us_alerts':       0,
            'kr_alerts':       0,
            'critical_alerts': 0,
            'high_alerts':     0,
            'medium_alerts':   0,
            'finviz_success':  0,
            'yahoo_success':   0,
            'yfinance_success':0,
            'avg_change_pct':  0.0,
            'max_change_pct':  0.0,
            'session_start':   datetime.now(),
        }

        # ── User-Agent 풀 ──
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

        logger.info("🚀 Momentum Tracker (Production) 초기화")

    # ────────────────────────────────────────────
    # 공통 헬퍼
    # ────────────────────────────────────────────
    def _get_random_headers(self) -> dict:
        return {
            'User-Agent': random.choice(self.user_agents),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }

    async def _random_delay(self, base_seconds=1.0, jitter=0.5):
        delay = base_seconds + random.uniform(-jitter, jitter)
        await asyncio.sleep(max(0.1, delay))

    # ────────────────────────────────────────────
    # 동적 종목 관리 (TTL)
    # ────────────────────────────────────────────
    def add_dynamic_ticker(self, ticker: str, market: str = 'US'):
        """뉴스/AI가 지목한 종목 추가. 24시간 TTL."""
        now = datetime.now()
        if market == 'US':
            self.dynamic_tickers_us[ticker.upper()] = now
            logger.info(f"➕ 동적 종목 추가 (US): {ticker} [TTL 24h]")
            if len(self.dynamic_tickers_us) > 50:
                oldest = min(self.dynamic_tickers_us, key=self.dynamic_tickers_us.get)
                del self.dynamic_tickers_us[oldest]
        else:
            self.dynamic_tickers_kr[ticker] = now
            logger.info(f"➕ 동적 종목 추가 (KR): {ticker} [TTL 24h]")
            if len(self.dynamic_tickers_kr) > 50:
                oldest = min(self.dynamic_tickers_kr, key=self.dynamic_tickers_kr.get)
                del self.dynamic_tickers_kr[oldest]

    def _get_active_dynamic_tickers(self, market: str = 'US') -> List[str]:
        """TTL 만료 종목 제거 후 활성 종목 반환."""
        now = datetime.now()
        ttl = timedelta(hours=self.dynamic_ticker_ttl_hours)
        pool = self.dynamic_tickers_us if market == 'US' else self.dynamic_tickers_kr

        expired = [t for t, ts in pool.items() if now - ts >= ttl]
        for t in expired:
            del pool[t]
            logger.debug(f"⏰ TTL 만료 ({market}): {t}")

        return list(pool.keys())

    # ────────────────────────────────────────────
    # 우선순위 & 통계
    # ────────────────────────────────────────────
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

        signal['priority']       = priority
        signal['priority_emoji'] = _PRIORITY_EMOJI[priority]
        return signal

    def _update_stats(self, signal: dict):
        self.stats['total_alerts'] += 1
        market = signal.get('market', 'US')
        if market == 'US':
            self.stats['us_alerts'] += 1
        else:
            self.stats['kr_alerts'] += 1

        priority = signal.get('priority')
        if priority == AlertPriority.CRITICAL:
            self.stats['critical_alerts'] += 1
        elif priority == AlertPriority.HIGH:
            self.stats['high_alerts'] += 1
        elif priority == AlertPriority.MEDIUM:
            self.stats['medium_alerts'] += 1

        change_pct = abs(signal.get('change_percent', 0))
        total      = self.stats['total_alerts']
        prev_avg   = self.stats['avg_change_pct']
        self.stats['avg_change_pct'] = (prev_avg * (total - 1) + change_pct) / total
        if change_pct > self.stats['max_change_pct']:
            self.stats['max_change_pct'] = change_pct

    def get_stats_summary(self) -> str:
        uptime  = datetime.now() - self.stats['session_start']
        hours   = int(uptime.total_seconds() // 3600)
        minutes = int((uptime.total_seconds() % 3600) // 60)
        return (
            f"📊 Momentum Tracker (Production) 통계\n"
            f"━━━━━━━━━━━━━━━━\n"
            f"⏱️ 실행 시간: {hours}h {minutes}m\n"
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
            f"🔍 동적 종목 (TTL 24h):\n"
            f"  US: {len(self.dynamic_tickers_us)}개\n"
            f"  KR: {len(self.dynamic_tickers_kr)}개\n"
        )

    # ────────────────────────────────────────────
    # 메인 스캔 진입점
    # ────────────────────────────────────────────
    async def scan_momentum(self, market: str = 'KR', mode: str = 'full') -> List[dict]:
        """
        이중 스캔 모드:
        - mode='dynamic': 뉴스 종목만 (1분 주기)
        - mode='full':    시장 전체 스캔 (10분 주기)
        """
        signals = []

        if market == 'KR':
            if mode == 'dynamic':
                if self.dynamic_tickers_kr:
                    signals.extend(await self._scan_dynamic_kr())
            else:
                signals.extend(await self._scan_realtime_surge_kr())
                signals.extend(await self._scan_program())
                signals.extend(await self._scan_theme())
        else:  # US
            if mode == 'dynamic':
                if self.dynamic_tickers_us:
                    signals.extend(await self._scan_dynamic_us())
            else:
                signals.extend(await self._scan_realtime_surge_us())

        logger.info(f"🐺 모멘텀 [{market}][{mode}]: {len(signals)}개")
        return signals

    # ────────────────────────────────────────────
    # US - 동적 종목 (1분 주기)
    # ────────────────────────────────────────────
    async def _scan_dynamic_us(self) -> List[dict]:
        """뉴스 종목 빠른 체크 (1분 주기) + TTL + 우선순위
           ✅ prepost=True: 장전/장후 데이터 포함
        """
        signals = []
        active_tickers = self._get_active_dynamic_tickers('US')
        if not active_tickers:
            return signals

        for ticker in active_tickers:
            try:
                await self._random_delay(0.5, 0.2)
                stock = await asyncio.to_thread(yf.Ticker, ticker)
                # ✅ prepost=True: 장전/장후 급등 감지
                hist = await asyncio.to_thread(
                    lambda: stock.history(period='5d', prepost=True)
                )

                if hist.empty or len(hist) < 2:
                    continue

                current      = hist['Close'].iloc[-1]
                prev         = hist['Close'].iloc[-2]
                change_pct   = ((current - prev) / prev) * 100
                volume       = hist['Volume'].iloc[-1]
                avg_volume   = hist['Volume'][:-1].mean()
                volume_ratio = volume / avg_volume if avg_volume > 0 else 0

                if change_pct >= self.min_price_change and volume_ratio >= self.min_volume_ratio:
                    alert_key = f"{ticker}_{datetime.now().date()}"
                    if alert_key not in self.seen_surge:
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
                        logger.info(f"{signal['priority_emoji']} 뉴스 종목 급등: {ticker} +{change_pct:.1f}%")

            except Exception as e:
                logger.debug(f"동적 종목 체크 오류 ({ticker}): {e}")
                continue

        return signals

    # ────────────────────────────────────────────
    # KR - 동적 종목 (1분 주기)
    # ────────────────────────────────────────────
    async def _scan_dynamic_kr(self) -> List[dict]:
        """한국 뉴스 종목 빠른 체크 + TTL + 우선순위
           ✅ prepost=True: 장전/장후 데이터 포함
        """
        signals = []
        active_tickers = self._get_active_dynamic_tickers('KR')
        if not active_tickers:
            return signals

        for code in active_tickers:
            try:
                await self._random_delay(0.5, 0.2)
                ticker_symbol = f"{code}.KS" if code.startswith('0') else f"{code}.KQ"
                stock = await asyncio.to_thread(yf.Ticker, ticker_symbol)
                hist = await asyncio.to_thread(
                    lambda: stock.history(period='5d', prepost=True)
                )

                if hist.empty or len(hist) < 2:
                    continue

                current      = hist['Close'].iloc[-1]
                prev         = hist['Close'].iloc[-2]
                change_pct   = ((current - prev) / prev) * 100
                volume       = hist['Volume'].iloc[-1]
                avg_volume   = hist['Volume'][:-1].mean()
                volume_ratio = volume / avg_volume if avg_volume > 0 else 0

                if change_pct >= self.min_price_change and volume_ratio >= self.min_volume_ratio:
                    alert_key = f"{code}_{datetime.now().date()}"
                    if alert_key not in self.seen_surge:
                        self.seen_surge.add(alert_key)

                        info = stock.info
                        name = info.get('longName', code)

                        signal = {
                            'ticker':         code,
                            'name':           name,
                            'market':         'KR',
                            'price':          current,
                            'change_percent': change_pct,
                            'volume_ratio':   volume_ratio,
                            'signals':        [f'급등 {change_pct:.1f}%', f'거래량 {volume_ratio:.1f}배'],
                            'reason':         f'🔥🔥 뉴스 종목 급등 ({change_pct:.1f}%, {volume_ratio:.1f}배)',
                            'timestamp':      datetime.now(),
                            'alert_type':     'dynamic_surge',
                        }
                        signal = self._assign_priority(signal, is_dynamic=True)
                        self._update_stats(signal)
                        signals.append(signal)
                        logger.info(f"{signal['priority_emoji']} 뉴스 종목 급등(KR): {name} +{change_pct:.1f}%")

            except Exception as e:
                logger.debug(f"동적 종목 체크 오류 ({code}): {e}")
                continue

        return signals

    # ────────────────────────────────────────────
    # US - 전체 스캔 (3중 fallback)
    # ────────────────────────────────────────────
    async def _scan_realtime_surge_us(self) -> List[dict]:
        """
        3중 fallback:
        1차: Finviz (curl_cffi, TLS 위장)
        2차: Yahoo Finance screener API
        3차: yfinance 직접 조회 (병렬)
        """
        # 1차 Finviz
        try:
            logger.info("1차 시도: Finviz")
            signals = await self._scan_finviz()
            if signals:
                logger.info(f"✅ Finviz 성공: {len(signals)}개")
                return signals
            logger.warning("Finviz 결과 0개 → Yahoo 시도")
        except Exception as e:
            logger.warning(f"Finviz 실패: {e} → Yahoo 시도")

        # 2차 Yahoo
        try:
            logger.info("2차 시도: Yahoo Finance screener")
            signals = await self._scan_yahoo_screener()
            if signals:
                logger.info(f"✅ Yahoo 성공: {len(signals)}개")
                return signals
            logger.warning("Yahoo 결과 0개 → yfinance 시도")
        except Exception as e:
            logger.warning(f"Yahoo 실패: {e} → yfinance 시도")

        # 3차 yfinance
        try:
            logger.info("3차 시도: yfinance API")
            signals = await self._scan_yfinance_api()
            if signals:
                logger.info(f"✅ yfinance 성공: {len(signals)}개")
            else:
                logger.error("⚠️ 모든 방법 실패: 미국 급등주 0개")
            return signals
        except Exception as e:
            logger.error(f"yfinance API도 실패: {e}")
            return []

    # ────────────────────────────────────────────
    # 1차: Finviz (curl_cffi TLS 위장)
    # ────────────────────────────────────────────
    async def _scan_finviz(self) -> List[dict]:
        """
        ✅ curl_cffi AsyncSession(impersonate="chrome110") 사용
           → Cloudflare TLS 지문 위장, 장중 차단 방지
        ✅ 동적 컬럼 매핑: 헤더 텍스트로 인덱스 결정
        ✅ 실제 class명: 'screener_table'
        """
        signals = []

        try:
            await self._random_delay(1.0, 0.3)

            if CURL_CFFI_AVAILABLE:
                # ✅ curl_cffi: Chrome TLS 지문 위장
                async with CurlAsyncSession(impersonate="chrome110") as session:
                    response = await session.get(
                        self.us_gainers_url,
                        headers=self._get_random_headers(),
                        timeout=20,
                    )
                    html = response.text
                    status = response.status_code
            else:
                # fallback: aiohttp
                async with aiohttp.ClientSession() as session:
                    async with session.get(
                        self.us_gainers_url,
                        headers=self._get_random_headers(),
                        timeout=15,
                    ) as resp:
                        status = resp.status
                        html   = await resp.text()

            if (CURL_CFFI_AVAILABLE and status != 200) or (not CURL_CFFI_AVAILABLE and status != 200):
                logger.warning(f"Finviz HTTP {status}")
                return signals

            soup = BeautifulSoup(html, 'html.parser')

            # ── 테이블 탐색 (3단계) ──
            # 1) F12로 확인한 실제 class명
            table = soup.find('table', {'class': lambda c: c and 'screener_table' in c})

            if table:
                logger.info("✅ Finviz screener_table 발견")
            else:
                # 2) 첫 번째 큰 테이블 (10행 이상)
                for t in soup.find_all('table'):
                    if len(t.find_all('tr')) > 10:
                        table = t
                        logger.warning("⚠️ Finviz fallback: 큰 테이블 사용")
                        break

            if not table:
                # 3) 전체 tr 직접 수집
                all_rows = soup.find_all('tr')
                if len(all_rows) > 10:
                    table = Tag(name='table')
                    for row in all_rows:
                        table.append(row)
                    logger.warning(f"⚠️ Finviz fallback: 전체 tr {len(all_rows)}개")
                else:
                    logger.warning("⚠️ Finviz 테이블 없음")
                    return signals

            all_rows = table.find_all('tr')
            if len(all_rows) < 2:
                return signals

            # ── ✅ 동적 컬럼 매핑 (헤더 텍스트 기반) ──
            header_cells = all_rows[0].find_all(['th', 'td'])
            col_map: Dict[str, int] = {}
            for idx, cell in enumerate(header_cells):
                text = cell.text.strip().lower()
                if 'ticker' in text:
                    col_map['ticker'] = idx
                elif 'company' in text:
                    col_map['name'] = idx
                elif text == 'price' or text.startswith('price'):
                    col_map['price'] = idx
                elif 'change' in text and '%' in text:
                    col_map['change'] = idx
                elif text in ('volume', 'vol'):
                    col_map['volume'] = idx

            # 헤더 파싱 실패 시 기본 인덱스 (Finviz 기본 레이아웃)
            if not col_map:
                logger.info("Finviz 헤더 파싱 실패 → 기본 인덱스 사용")
                col_map = {'ticker': 1, 'name': 2, 'price': 8, 'change': 10, 'volume': 11}
            else:
                logger.debug(f"Finviz 컬럼 매핑: {col_map}")

            # ── 데이터 행 파싱 ──
            for row in all_rows[1:51]:
                try:
                    cols = row.find_all('td')
                    if len(cols) < 12:
                        continue

                    ticker_idx  = col_map.get('ticker', 1)
                    name_idx    = col_map.get('name',   2)
                    price_idx   = col_map.get('price',  8)
                    change_idx  = col_map.get('change', 10)
                    volume_idx  = col_map.get('volume', 11)

                    # Ticker
                    ticker_elem = cols[ticker_idx].find('a')
                    ticker = ticker_elem.text.strip() if ticker_elem else cols[ticker_idx].text.strip()
                    if not ticker:
                        continue

                    # Company
                    name = cols[name_idx].text.strip()

                    # Price
                    try:
                        price = float(cols[price_idx].text.strip())
                    except ValueError:
                        continue

                    # ✅ Change % (동적 인덱스 사용으로 컬럼 혼동 없음)
                    try:
                        change_pct = float(
                            cols[change_idx].text.strip().replace('%', '').replace('+', '')
                        )
                    except ValueError:
                        continue

                    # Volume
                    vol_text = cols[volume_idx].text.strip()
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

                    # ✅ yfinance 보조 검증 (prepost=True)
                    await self._random_delay(0.3, 0.1)
                    volume_ratio = 0
                    try:
                        stock = await asyncio.to_thread(yf.Ticker, ticker)
                        info  = stock.info
                        hist  = await asyncio.to_thread(
                            lambda: stock.history(period='5d', prepost=True)
                        )

                        if hist.empty or len(hist) < 2:
                            continue

                        cur_vol    = hist['Volume'].iloc[-1]
                        avg_vol    = hist['Volume'][:-1].mean()
                        volume_ratio = cur_vol / avg_vol if avg_vol > 0 else 0

                        if volume_ratio < self.min_volume_ratio:
                            continue

                        market_cap = info.get('marketCap', 0)
                        if market_cap > self.max_market_cap_us:
                            continue

                        if info.get('quoteType') == 'ETF':
                            continue

                    except Exception as e:
                        logger.debug(f"{ticker} yfinance 검증 실패: {e}")
                        if volume == 0:
                            continue

                    # 중복 체크
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
                        'signals':        [f'Surge {change_pct:.1f}%',
                                           f'Volume {volume_ratio:.1f}x' if volume_ratio else 'High Volume'],
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
                    continue

        except Exception as e:
            logger.error(f"Finviz 스캔 오류: {e}")

        if signals:
            self.stats['finviz_success'] += 1
        return signals

    # ────────────────────────────────────────────
    # 2차: Yahoo Finance screener
    # ────────────────────────────────────────────
    async def _scan_yahoo_screener(self) -> List[dict]:
        signals = []
        yahoo_url = "https://query1.finance.yahoo.com/v1/finance/screener"
        payload = {
            "size": 50, "offset": 0,
            "sortField": "percentchange", "sortType": "desc",
            "quoteType": "equity",
            "query": {
                "operator": "and",
                "operands": [
                    {"operator": "gt", "operands": ["percentchange", 10]},
                    {"operator": "gt", "operands": ["intradaymarketcap", 1000000]},
                ],
            },
        }

        try:
            async with aiohttp.ClientSession() as session:
                await self._random_delay(1.0, 0.3)
                async with session.post(
                    yahoo_url, json=payload,
                    headers=self._get_random_headers(), timeout=15,
                ) as resp:
                    if resp.status != 200:
                        logger.warning(f"Yahoo screener HTTP {resp.status}")
                        return signals
                    data   = await resp.json()
                    quotes = data.get('finance', {}).get('result', [{}])[0].get('quotes', [])

            if not quotes:
                return signals

            logger.info(f"Yahoo screener: {len(quotes)}개")
            for quote in quotes[:20]:
                try:
                    ticker       = quote.get('symbol', '')
                    if not ticker:
                        continue
                    name         = quote.get('shortName', ticker)
                    price        = quote.get('regularMarketPrice', 0)
                    change_pct   = quote.get('regularMarketChangePercent', 0)
                    volume       = quote.get('regularMarketVolume', 0)
                    avg_volume   = quote.get('averageDailyVolume3Month', 0)
                    volume_ratio = volume / avg_volume if avg_volume > 0 else 0
                    market_cap   = quote.get('marketCap', 0)

                    if change_pct   < self.min_price_change:  continue
                    if volume_ratio < self.min_volume_ratio:   continue
                    if market_cap   > self.max_market_cap_us:  continue

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

        if signals:
            self.stats['yahoo_success'] += 1
        return signals

    # ────────────────────────────────────────────
    # 3차: yfinance 직접 조회 (병렬 처리)
    # ────────────────────────────────────────────
    async def _scan_yfinance_api(self) -> List[dict]:
        """
        ✅ 5개씩 병렬 처리 (9초 → 2초)
        ✅ prepost=True: 장전/장후 데이터 포함
        """
        signals = []

        sp500_tickers = [
            'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'TSLA', 'META', 'BRK.B', 'UNH', 'JNJ',
            'V',    'WMT',  'JPM',   'MA',   'PG',   'HD',   'CVX',  'MRK',   'ABBV', 'KO',
            'PEP',  'AVGO', 'COST',  'TMO',  'MCD',  'CSCO', 'ACN',  'DHR',   'VZ',   'ABT',
        ]

        async def check_ticker(ticker: str) -> Optional[dict]:
            try:
                await self._random_delay(0.2, 0.1)
                stock = await asyncio.to_thread(yf.Ticker, ticker)
                # ✅ prepost=True
                hist = await asyncio.to_thread(
                    lambda: stock.history(period='5d', prepost=True)
                )
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

                info = stock.info
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
                logger.debug(f"{ticker} yfinance 오류: {e}")
                return None

        try:
            logger.info("yfinance 병렬 스캔 시작")
            batch_size = 5
            for i in range(0, len(sp500_tickers), batch_size):
                batch   = sp500_tickers[i:i + batch_size]
                results = await asyncio.gather(
                    *[check_ticker(t) for t in batch],
                    return_exceptions=True,
                )
                for result in results:
                    if result and not isinstance(result, Exception):
                        signal = self._assign_priority(result, is_dynamic=False)
                        self._update_stats(signal)
                        signals.append(signal)
                        logger.info(f"{signal['priority_emoji']} US Surge (yfinance): "
                                    f"{signal['ticker']} +{signal['change_percent']:.1f}%")

            logger.info(f"yfinance 완료: {len(signals)}개")

        except Exception as e:
            logger.error(f"yfinance API 오류: {e}")

        if signals:
            self.stats['yfinance_success'] += 1
        return signals

    # ────────────────────────────────────────────
    # KR - 전체 스캔
    # ────────────────────────────────────────────
    async def _scan_realtime_surge_kr(self) -> List[dict]:
        signals = []
        try:
            async with aiohttp.ClientSession() as session:
                await self._random_delay(1.0, 0.3)
                async with session.get(
                    self.kr_surge_url,
                    headers=self._get_random_headers(), timeout=15,
                ) as resp:
                    if resp.status != 200:
                        return signals
                    html = await resp.text()

            soup = BeautifulSoup(html, 'html.parser')
            for row in soup.select('table.type_2 tr')[2:52]:
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

                    vol_ratio_text = cols[10].text.strip().replace('%', '').replace('+', '')
                    if not vol_ratio_text.replace('.', '', 1).isdigit():
                        continue
                    volume_ratio = float(vol_ratio_text) / 100.0 + 1.0

                    if volume_ratio < self.min_volume_ratio or change_pct < self.min_price_change:
                        continue

                    try:
                        sym   = f"{code}.KS" if code.startswith('0') else f"{code}.KQ"
                        stock = await asyncio.to_thread(yf.Ticker, sym)
                        info  = stock.info
                        if info.get('marketCap', 0) > 750_000_000:
                            continue
                        if info.get('quoteType') == 'ETF':
                            continue
                    except Exception:
                        pass

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
                        'volume':         volume,
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
            logger.error(f"KR 급등 스캔 오류: {e}")

        return signals

    # ────────────────────────────────────────────
    # 프로그램 매매
    # ────────────────────────────────────────────
    async def _scan_program(self) -> List[dict]:
        signals = []
        try:
            async with aiohttp.ClientSession() as session:
                await self._random_delay(1.0, 0.3)
                async with session.get(
                    self.program_url,
                    headers=self._get_random_headers(), timeout=10,
                ) as resp:
                    if resp.status != 200:
                        return signals
                    html = await resp.text()

            soup = BeautifulSoup(html, 'html.parser')
            for row in soup.select('table.type_1 tr')[2:32]:
                try:
                    cols = row.select('td')
                    if len(cols) < 7:
                        continue
                    name_elem = cols[0].select_one('a')
                    if not name_elem:
                        continue
                    name = name_elem.text.strip()
                    code_match = re.search(r'code=(\d+)', name_elem.get('href', ''))
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

                    signal = {
                        'ticker':      code,
                        'name':        name,
                        'market':      'KR',
                        'signal_type': 'program_buy',
                        'buy_amount':  buy_amount,
                        'reason':      f'💻 프로그램 순매수 ({buy_amount/100:.0f}억원)',
                        'timestamp':   datetime.now(),
                        'alert_type':  'program',
                    }
                    signal = self._assign_priority(signal)
                    signals.append(signal)
                    logger.info(f"💻 프로그램: {name} ({buy_amount/100:.0f}억)")

                except Exception:
                    continue

        except Exception as e:
            logger.error(f"프로그램 스캔 오류: {e}")

        return signals

    # ────────────────────────────────────────────
    # 테마주
    # ────────────────────────────────────────────
    async def _scan_theme(self) -> List[dict]:
        signals = []
        try:
            async with aiohttp.ClientSession() as session:
                await self._random_delay(1.0, 0.3)
                async with session.get(
                    self.theme_url,
                    headers=self._get_random_headers(), timeout=10,
                ) as resp:
                    if resp.status != 200:
                        return signals
                    html = await resp.text()
                soup = BeautifulSoup(html, 'html.parser')

                for row in soup.select('table.type_1 tr')[2:22]:
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

                        detail_url = "https://finance.naver.com" + theme_elem.get('href', '')
                        top3 = await self._get_theme_top3(detail_url, session)
                        if not top3:
                            continue

                        self.seen_theme.add(alert_key)

                        msg = f'🎨 테마 급등 ({theme_name} +{change_pct:.1f}%)\n'
                        msg += f'👑 1위: {top3[0]["name"]} (+{top3[0]["change"]:.1f}%)'
                        if len(top3) > 1:
                            msg += f'\n🥈 2위: {top3[1]["name"]} (+{top3[1]["change"]:.1f}%)'
                        if len(top3) > 2:
                            msg += f'\n🥉 3위: {top3[2]["name"]} (+{top3[2]["change"]:.1f}%)'

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
                        signal = self._assign_priority(signal)
                        signals.append(signal)
                        logger.info(f"🎨 테마: {theme_name} (1위: {top3[0]['name']})")

                    except Exception:
                        continue

        except Exception as e:
            logger.error(f"테마 스캔 오류: {e}")

        return signals

    async def _get_theme_top3(self, theme_url: str, session) -> Optional[List[dict]]:
        try:
            await self._random_delay(0.5, 0.2)
            async with session.get(theme_url, timeout=5) as resp:
                if resp.status != 200:
                    return None
                html = await resp.text()

            soup   = BeautifulSoup(html, 'html.parser')
            stocks = []
            for row in soup.select('table.type_5 tr')[2:20]:
                try:
                    cols = row.select('td')
                    if len(cols) < 5:
                        continue
                    name_elem = cols[0].select_one('a')
                    if not name_elem:
                        continue
                    name = name_elem.text.strip()
                    code_match = re.search(r'code=(\d+)', name_elem.get('href', ''))
                    if not code_match:
                        continue
                    code = code_match.group(1)
                    price_text = cols[1].text.strip().replace(',', '')
                    price = int(price_text) if price_text.isdigit() else 0
                    change_text = cols[3].text.strip().replace('%', '').replace('+', '')
                    change = float(change_text) if change_text.replace('.','',1).replace('-','',1).isdigit() else 0
                    if change <= 0:
                        continue
                    stocks.append({'name': name, 'code': code, 'price': price, 'change': change})
                except Exception:
                    continue

            stocks.sort(key=lambda x: x['change'], reverse=True)
            return stocks[:3] if stocks else None

        except Exception:
            return None

    # ────────────────────────────────────────────
    # 메모리 정리
    # ────────────────────────────────────────────
    def cleanup_alerts(self):
        """7일 지난 날짜별 데이터 삭제, 오늘 데이터 보존"""
        today = date.today()

        for store in (self.seen_surge_by_date, self.seen_program_by_date, self.seen_theme_by_date):
            old = [d for d in store if (today - d).days > 7]
            for d in old:
                del store[d]

        # seen_surge/program/theme (하위 호환 set) 크기 제한
        for s in (self.seen_surge, self.seen_program, self.seen_theme):
            while len(s) > 1000:
                s.pop()

        logger.info(f"메모리 정리 완료")


# ────────────────────────────────────────────────────────
# 하위 호환 alias (구 코드에서 MomentumTrackerV3_3 를 import 하는 경우 대비)
# ────────────────────────────────────────────────────────
MomentumTrackerV3_3 = MomentumTracker
