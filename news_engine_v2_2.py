# -*- coding: utf-8 -*-
"""
News Engine v2.2 - v3.0 업그레이드 (호환성 유지)
- 파일명: v2_2 (호환성)
- 내용물: v3.0 (최신)
- 5대장 뉴스 소스 + SEC 8-K
- curl_cffi 보안 우회
- KST 시간 처리
- AI 모델명 추적
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

from ai_brain_v2_2 import AIBrainV2_2
from config import Config

logger = logging.getLogger(__name__)

class NewsEngineV2_2:  # 🔥 클래스명 v2_2 유지!
    def __init__(self, ai_brain):
        self.ai = ai_brain
        self.seen_urls = set()
        self.seen_titles = []
        
        # Timezone
        self.kst = pytz.timezone('Asia/Seoul')
        
        # 🆕 5대장 뉴스 소스 + SEC 8-K (v3.0)
        self.sources = [
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
        ]
        
        # SEC 8-K 공시
        self.sec_url = 'https://www.sec.gov/cgi-bin/browse-edgar?action=getcurrent&type=8-K&company=&dateb=&owner=include&start=0&count=100&output=atom'
        
        logger.info("📰 News Engine v2.2 (v3.0 업그레이드) 초기화")
    
    async def scan_all_sources(self):
        """모든 뉴스 소스 병렬 스캔 (curl_cffi)"""
        async with AsyncSession(impersonate="chrome110") as session:
            tasks = []
            
            for source in self.sources:
                if source['type'] == 'rss':
                    tasks.append(self._fetch_rss(session, source))
                elif source['type'] == 'html':
                    tasks.append(self._fetch_html(session, source))
            
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
            
            logger.info(f"📊 뉴스 수집: {len(news_list)}개 (5대장 + SEC)")
            return news_list
    
    async def _fetch_rss(self, session, source):
        """RSS 피드 스캔"""
        items = []
        
        try:
            response = await session.get(source['url'], timeout=15)
            
            if response.status_code != 200:
                logger.warning(f"{source['name']} RSS 실패: {response.status_code}")
                return items
            
            feed = feedparser.parse(response.text)
            
            if not feed.entries:
                logger.warning(f"{source['name']} 엔트리 없음")
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
    
    async def _fetch_html(self, session, source):
        """HTML 크롤링 (Golden Logic)"""
        items = []
        
        try:
            headers = {'Referer': 'https://www.google.com/'}
            response = await session.get(source['url'], headers=headers, timeout=15)
            
            if response.status_code != 200:
                logger.warning(f"{source['name']} HTML 실패: {response.status_code}")
                return items
            
            soup = BeautifulSoup(response.text, 'lxml')
            links = soup.find_all('a', href=re.compile(source['pattern']))
            
            for link_tag in links[:15]:
                try:
                    title = link_tag.get_text(strip=True)
                    link = link_tag.get('href')
                    
                    if not link.startswith('http'):
                        if source['name'] == 'Business Wire':
                            link = 'https://www.businesswire.com' + link
                        elif source['name'] == 'Benzinga':
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
        """SEC XML updated 시간 파싱 → KST"""
        try:
            if updated_tag:
                time_str = updated_tag.text.strip()
                
                if time_str.endswith('Z'):
                    time_str = time_str.replace('Z', '+00:00')
                
                dt = datetime.fromisoformat(time_str)
                dt_kst = dt.astimezone(self.kst)
                
                return dt_kst
                
        except Exception as e:
            logger.debug(f"SEC 시간 파싱 실패: {e}")
        
        return datetime.now(self.kst)
    
    def _is_duplicate(self, title, url):
        """중복 체크"""
        if url in self.seen_urls:
            return True
        
        for seen_title in self.seen_titles:
            if SequenceMatcher(None, title, seen_title).ratio() > 0.85:
                return True
        
        return False
    
    def _register_news(self, title, url):
        """중복 방지 등록"""
        self.seen_urls.add(url)
        self.seen_titles.append(title)
        
        if len(self.seen_titles) > 100:
            self.seen_titles.pop(0)
    
    def _passes_keyword_filter(self, title):
        """키워드 필터"""
        title_lower = title.lower()
        
        has_positive = any(kw in title_lower for kw in Config.POSITIVE_KEYWORDS)
        has_negative = any(kw in title_lower for kw in Config.NEGATIVE_KEYWORDS)
        
        return has_positive and not has_negative
    
    async def process_news(self, news_item):
        """뉴스 처리 파이프라인 (SEC 공시 최적화)"""
        try:
            is_filing = news_item.get('type') == 'filing'
            
            threshold = 7.5 if is_filing else 8.0
            is_promising = await self.ai.quick_score(news_item['title'], threshold=threshold)
            
            if not is_promising:
                return None
            
            analysis = await self.ai.analyze_news_signal(news_item)
            
            if not analysis:
                return None
            
            if is_filing and analysis['score'] < 9.5:
                analysis['score'] = min(analysis['score'] + 0.5, 10.0)
                logger.info(f"📋 공시 점수 보정: {analysis['score']}")
            
            min_score = 8.0 if is_filing else 8.5
            if analysis['score'] < min_score:
                return None
            
            verified = await self.verify_signals(analysis, news_item)
            
            if not verified:
                return None
            
            return {
                'news': news_item,
                'analysis': analysis,
                'verified': True,
                'verification_details': verified,
                'model_used': analysis.get('model_used', 'unknown'),
                'is_filing': is_filing,
                'timestamp': datetime.now()
            }
            
        except Exception as e:
            logger.error(f"뉴스 처리 오류: {e}")
            return None
    
    async def verify_signals(self, analysis, news_item):
        """3중 검증"""
        verification = {
            'ai_score': analysis['score'],
            'checks_passed': [],
            'total_score': 0
        }
        
        if analysis['score'] >= 9.0:
            verification['total_score'] += 50
            verification['checks_passed'].append('AI 초고점수')
        elif analysis['score'] >= 8.5:
            verification['total_score'] += 40
            verification['checks_passed'].append('AI 고점수')
        else:
            return None
        
        if analysis.get('certainty') == 'confirmed':
            verification['total_score'] += 15
            verification['checks_passed'].append('확정 뉴스')
        
        if news_item.get('type') == 'filing':
            verification['total_score'] += 10
            verification['checks_passed'].append('SEC 공식 공시')
        
        verification['total_score'] += 10
        verification['checks_passed'].append('시장 분석')
        
        news_type = self._classify_news_type(news_item['title'])
        pattern_score = {
            'approval': 25,
            'earnings': 20,
            'contract': 20,
            'government': 15,
            'product': 15,
            'other': 5
        }.get(news_type, 5)
        
        verification['total_score'] += pattern_score
        verification['checks_passed'].append(f'타입: {news_type}')
        
        if verification['total_score'] >= 80:
            return verification
        else:
            return None
    
    def _classify_news_type(self, title):
        """뉴스 타입 분류"""
        title_lower = title.lower()
        
        keywords = {
            'approval': ['승인', 'approval', 'approved', 'fda'],
            'earnings': ['실적', 'earnings', '영업이익'],
            'contract': ['계약', 'contract', '수주'],
            'government': ['정부', 'government', 'subsidy'],
            'product': ['출시', 'launch', 'product'],
        }
        
        for news_type, words in keywords.items():
            if any(word in title_lower for word in words):
                return news_type
        
        return 'other'
    
    def cleanup_old_news(self):
        """메모리 정리"""
        if len(self.seen_urls) > 1000:
            self.seen_urls = set(list(self.seen_urls)[-500:])
        if len(self.seen_titles) > 100:
            self.seen_titles = self.seen_titles[-50:]
