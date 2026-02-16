# -*- coding: utf-8 -*-
"""
News Engine v3.0 - Beast Mode (야수 모드)
- 5대장 뉴스 소스 (미국)
- 🔥 한국 뉴스 소스 대폭 확장 (네이버 속보, 매경, 한경, 서경)
- SEC 8-K
- curl_cffi 보안 우회
- KST 시간 처리
"""

import asyncio
import logging
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
import feedparser
import pytz
from difflib import SequenceMatcher
import re
from curl_cffi.requests import AsyncSession

from ai_brain_v3 import AIBrainV3
from config import Config

logger = logging.getLogger(__name__)

class NewsEngineV3:
    def __init__(self, ai_brain):
        self.ai = ai_brain
        self.seen_urls = set()
        self.seen_titles = []
        
        # Timezone
        self.kst = pytz.timezone('Asia/Seoul')
        
        # 🔥 v3.0: 뉴스 소스 대폭 확장
        self.sources = [
            # === 미국 뉴스 (5대장 + SEC) ===
            {
                'name': 'PR Newswire',
                'type': 'rss',
                'url': 'https://www.prnewswire.com/rss/news-releases-list.rss',
                'market': 'US'
            },
            {
                'name': 'GlobeNewswire',
                'type': 'rss',
                'url': 'https://www.globenewswire.com/RssFeed/subjectcode/15-allcategories/feedTitle/GlobeNewswire%20-%20All%20Categories',
                'market': 'US'
            },
            {
                'name': 'Business Wire',
                'type': 'html',
                'url': 'https://www.businesswire.com/portal/site/home/news/',
                'pattern': r'/news/home/\d+/',
                'market': 'US'
            },
            {
                'name': 'Benzinga',
                'type': 'html',
                'url': 'https://www.benzinga.com/news',
                'pattern': r'/news/\d+/',
                'market': 'US'
            },
            
            # === 🔥 한국 뉴스 소스 (v3.1.1 최종) ===
            {
                'name': '네이버 증권 속보',
                'type': 'naver_breaking',
                'url': 'https://finance.naver.com/news/news_list.naver?mode=LSS2D&section_id=101&section_id2=258',
                'market': 'KR'
            },
            {
                'name': '매일경제',
                'type': 'rss',
                'url': 'https://www.mk.co.kr/rss/30000001/',
                'market': 'KR'
            },
            {
                'name': '한국경제',
                'type': 'rss',
                'url': 'https://www.hankyung.com/feed/economy',
                'market': 'KR'
            },
            # 🔧 v3.1.1: 서울경제 완전 제거 (RSS 서비스 폐지됨)
        ]
        
        # SEC 8-K 공시
        self.sec_url = 'https://www.sec.gov/cgi-bin/browse-edgar?action=getcurrent&type=8-K&company=&dateb=&owner=include&start=0&count=100&output=atom'
        
        logger.info("📰 News Engine v3.0 Beast Mode 초기화")
    
    async def scan_all_sources(self):
        """모든 뉴스 소스 병렬 스캔 (curl_cffi)"""
        async with AsyncSession(impersonate="chrome110") as session:
            tasks = []
            
            for source in self.sources:
                if source['type'] == 'rss':
                    tasks.append(self._fetch_rss(session, source))
                elif source['type'] == 'html':
                    tasks.append(self._fetch_html(session, source))
                elif source['type'] == 'naver_breaking':
                    tasks.append(self._fetch_naver_breaking(session, source))
            
            tasks.append(self._fetch_sec(session))
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            news_list = []
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    source_name = self.sources[i]['name'] if i < len(self.sources) else 'SEC 8-K'
                    logger.error(f"{source_name} 스캔 오류: {result}")
                elif result:
                    news_list.extend(result)
            
            news_list.sort(key=lambda x: x.get('published_timestamp', 0), reverse=True)
            
            logger.info(f"📊 뉴스 수집: {len(news_list)}개 (미국 5대장 + 한국 3대장 + SEC)")
            return news_list
    
    async def _fetch_rss(self, session, source):
        """RSS 피드 스캔 (미국/한국 공통)"""
        items = []
        
        try:
            response = await session.get(source['url'], timeout=15)
            
            if response.status_code != 200:
                logger.warning(f"{source['name']} RSS 실패: {response.status_code}")
                # 🔧 v3.1: 404 등 에러 시에도 빈 리스트 반환하여 계속 진행
                return items
            
            # 🔧 v3.1: RSS 파싱 실패 시에도 계속 진행
            try:
                feed = feedparser.parse(response.text)
            except Exception as e:
                logger.warning(f"{source['name']} RSS 파싱 실패: {e}")
                return items
            
            if not feed.entries:
                logger.warning(f"{source['name']} 엔트리 없음")
                # 🔧 v3.1: 엔트리 없어도 빈 리스트 반환하여 계속 진행
                return items
            
            for entry in feed.entries[:20]:
                try:
                    title = entry.title
                    link = entry.link
                    
                    if self._is_duplicate(title, link):
                        continue
                    
                    pub_time = self._extract_rss_time(entry)
                    
                    age_hours = (datetime.now(self.kst) - pub_time).total_seconds() / 3600
                    if age_hours > 24:
                        continue
                    
                    if not self._passes_keyword_filter(title):
                        continue
                    
                    self._register_news(title, link)
                    
                    items.append({
                        'id': f"{source['name']}_{link}",
                        'title': title,
                        'url': link,
                        'source': source['name'],
                        'market': source['market'],
                        'type': 'news',
                        'timestamp': datetime.now(),
                        'published_timestamp': pub_time.timestamp(),
                        'published_time_kst': pub_time.strftime('%Y-%m-%d %H:%M:%S KST')
                    })
                    
                except Exception as e:
                    logger.debug(f"RSS 항목 오류: {e}")
                    continue
            
            logger.info(f"✅ {source['name']}: {len(items)}개")
            return items
            
        except Exception as e:
            logger.error(f"{source['name']} RSS 오류: {e}")
            return items
    
    async def _fetch_naver_breaking(self, session, source):
        """
        🔥 v3.0 신규: 네이버 증권 속보 크롤링
        - 특징주, 단독, 속보 우선
        """
        items = []
        
        try:
            response = await session.get(source['url'], timeout=15)
            
            if response.status_code != 200:
                logger.warning(f"{source['name']} 접근 실패: {response.status_code}")
                return items
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 뉴스 리스트
            news_items = soup.select('dl.newsList dd.articleSubject a')[:30]
            
            for item in news_items:
                try:
                    title = item.text.strip()
                    link = item.get('href', '')
                    
                    if not link.startswith('http'):
                        link = 'https://finance.naver.com' + link
                    
                    if self._is_duplicate(title, link):
                        continue
                    
                    # 🔥 특징주, 단독, 속보 우선 처리
                    is_priority = any(keyword in title for keyword in ['특징주', '단독', '속보', '긴급'])
                    
                    if not is_priority and not self._passes_keyword_filter(title):
                        continue
                    
                    pub_time = datetime.now(self.kst)
                    
                    self._register_news(title, link)
                    
                    # 우선도 높은 뉴스에 마킹
                    priority_tag = " 🔥" if is_priority else ""
                    
                    items.append({
                        'id': f"{source['name']}_{link}",
                        'title': title + priority_tag,
                        'url': link,
                        'source': source['name'],
                        'market': source['market'],
                        'type': 'news',
                        'timestamp': datetime.now(),
                        'published_timestamp': pub_time.timestamp(),
                        'published_time_kst': pub_time.strftime('%Y-%m-%d %H:%M:%S KST'),
                        'is_priority': is_priority
                    })
                    
                except Exception as e:
                    logger.debug(f"네이버 속보 항목 오류: {e}")
                    continue
            
            logger.info(f"✅ {source['name']}: {len(items)}개")
            return items
            
        except Exception as e:
            logger.error(f"{source['name']} 크롤링 오류: {e}")
            return items
    
    async def _fetch_html(self, session, source):
        """HTML 페이지 스크래핑 (Business Wire, Benzinga)"""
        items = []
        
        try:
            response = await session.get(source['url'], timeout=15)
            
            if response.status_code != 200:
                logger.warning(f"{source['name']} HTML 실패: {response.status_code}")
                return items
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Business Wire 특수 처리
            if source['name'] == 'Business Wire':
                news_items = soup.select('a.bwNewsList__link')[:20]
                
                for item in news_items:
                    try:
                        title = item.text.strip()
                        link = item.get('href', '')
                        
                        if not link.startswith('http'):
                            link = 'https://www.businesswire.com' + link
                        
                        if self._is_duplicate(title, link): continue
                        if not self._passes_keyword_filter(title): continue
                        
                        pub_time = datetime.now(self.kst)
                        
                        self._register_news(title, link)
                        
                        items.append({
                            'id': f"{source['name']}_{link}",
                            'title': title,
                            'url': link,
                            'source': source['name'],
                            'market': source['market'],
                            'type': 'news',
                            'timestamp': datetime.now(),
                            'published_timestamp': pub_time.timestamp(),
                            'published_time_kst': pub_time.strftime('%Y-%m-%d %H:%M:%S KST')
                        })
                    except Exception:
                        continue
                
                logger.info(f"✅ {source['name']}: {len(items)}개")
                return items

            # Benzinga 및 기타 일반 HTML 처리
            links = soup.find_all('a', href=re.compile(source['pattern']))
            
            for link_tag in links[:15]:
                try:
                    title = link_tag.get_text(strip=True)
                    link = link_tag.get('href')
                    
                    if not link.startswith('http'):
                        if source['name'] == 'Benzinga':
                            link = 'https://www.benzinga.com' + link
                    
                    if self._is_duplicate(title, link):
                        continue
                    
                    if not self._passes_keyword_filter(title):
                        continue
                    
                    pub_time = datetime.now(self.kst)
                    
                    self._register_news(title, link)
                    
                    items.append({
                        'id': f"{source['name']}_{link}",
                        'title': title,
                        'url': link,
                        'source': source['name'],
                        'market': source['market'],
                        'type': 'news',
                        'timestamp': datetime.now(),
                        'published_timestamp': pub_time.timestamp(),
                        'published_time_kst': pub_time.strftime('%Y-%m-%d %H:%M:%S KST')
                    })
                    
                except Exception as e:
                    logger.debug(f"HTML 링크 오류: {e}")
                    continue
            
            logger.info(f"✅ {source['name']}: {len(items)}개")
            return items
            
        except Exception as e:
            logger.error(f"{source['name']} HTML 오류: {e}")
            return items
    
    async def _fetch_sec(self, session):
        """SEC 8-K 공시 크롤링"""
        items = []
        
        try:
            headers = {'User-Agent': 'StockBot/3.0 (admin@stockbot.com)'}
            response = await session.get(self.sec_url, headers=headers, timeout=20)
            
            if response.status_code != 200:
                logger.warning(f"SEC 8-K 실패: {response.status_code}")
                return items
            
            soup = BeautifulSoup(response.text, 'xml')
            entries = soup.find_all('entry')
            
            for entry in entries[:30]:
                try:
                    title_tag = entry.find('title')
                    link_tag = entry.find('link')
                    updated_tag = entry.find('updated')
                    
                    if not title_tag or not link_tag:
                        continue
                    
                    title = title_tag.text.strip()
                    link = link_tag.get('href')
                    
                    title = f"[공시] {title}"
                    
                    if self._is_duplicate(title, link):
                        continue
                    
                    pub_time = self._extract_sec_time(updated_tag)
                    
                    age_hours = (datetime.now(self.kst) - pub_time).total_seconds() / 3600
                    if age_hours > 24:
                        continue
                    
                    if not self._passes_keyword_filter(title):
                        continue
                    
                    self._register_news(title, link)
                    
                    items.append({
                        'id': f"SEC_{link}",
                        'title': title,
                        'url': link,
                        'source': 'SEC 8-K',
                        'market': 'US',
                        'type': 'filing',
                        'timestamp': datetime.now(),
                        'published_timestamp': pub_time.timestamp(),
                        'published_time_kst': pub_time.strftime('%Y-%m-%d %H:%M:%S KST')
                    })
                    
                except Exception as e:
                    logger.debug(f"SEC 항목 오류: {e}")
                    continue
            
            logger.info(f"✅ SEC 8-K: {len(items)}개")
            return items
            
        except Exception as e:
            logger.error(f"SEC 8-K 오류: {e}")
            return items
    
    def _extract_rss_time(self, entry):
        """RSS 발간 시간 파싱 → KST"""
        try:
            if hasattr(entry, 'published_parsed') and entry.published_parsed:
                t = entry.published_parsed
                dt_naive = datetime(t.tm_year, t.tm_mon, t.tm_mday, t.tm_hour, t.tm_min, t.tm_sec)
                dt_kst = dt_naive + timedelta(hours=9)
                return self.kst.localize(dt_kst)
            
            if hasattr(entry, 'updated_parsed') and entry.updated_parsed:
                t = entry.updated_parsed
                dt_naive = datetime(t.tm_year, t.tm_mon, t.tm_mday, t.tm_hour, t.tm_min, t.tm_sec)
                dt_kst = dt_naive + timedelta(hours=9)
                return self.kst.localize(dt_kst)
                
        except Exception as e:
            logger.debug(f"RSS 시간 파싱 실패: {e}")
        
        return datetime.now(self.kst)
    
    def _extract_sec_time(self, updated_tag):
        """SEC 발간 시간 파싱 → KST"""
        try:
            if updated_tag:
                text = updated_tag.text.strip()
                dt_utc = datetime.fromisoformat(text.replace('Z', '+00:00'))
                dt_kst = dt_utc.astimezone(self.kst)
                return dt_kst
        except Exception as e:
            logger.debug(f"SEC 시간 파싱 실패: {e}")
        
        return datetime.now(self.kst)
    
    def _is_duplicate(self, title, url):
        """중복 체크 (URL + 제목 유사도)"""
        if url in self.seen_urls:
            return True
        
        for seen_title in self.seen_titles[-50:]:
            similarity = SequenceMatcher(None, title.lower(), seen_title.lower()).ratio()
            if similarity > 0.85:
                return True
        
        return False
    
    def _register_news(self, title, url):
        """뉴스 등록"""
        self.seen_urls.add(url)
        self.seen_titles.append(title)
        
        if len(self.seen_urls) > 2000:
            self.seen_urls.clear()
        if len(self.seen_titles) > 500:
            self.seen_titles = self.seen_titles[-250:]
    
    def _passes_keyword_filter(self, title):
        """키워드 필터 (Config 기반)"""
        title_upper = title.upper()
        
        # 악재 키워드 먼저 체크
        for negative in Config.NEGATIVE_KEYWORDS:
            if negative.upper() in title_upper:
                return False
        
        # 호재 키워드 체크
        for positive in Config.POSITIVE_KEYWORDS:
            if positive.upper() in title_upper:
                return True
        
        return False
