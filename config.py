# -*- coding: utf-8 -*-
"""
Config v3.0 - Beast Mode (야수 모드)
- 키워드 전략 전면 개편: 섹터별 세분화
- 한국 테마 대폭 강화
- RIME 사례 반영 (AI/물류 효율화)
"""

import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # API Keys
    TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
    TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
    GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
    FINNHUB_API_KEY = os.getenv('FINNHUB_API_KEY')  # 선택사항
    ALPHA_VANTAGE_KEY = os.getenv('ALPHA_VANTAGE_KEY')  # 선택사항
    DART_API_KEY = os.getenv('DART_API_KEY')  # v3.0에서는 사용 안 함
    
    @classmethod
    def validate(cls):
        required = ['TELEGRAM_TOKEN', 'TELEGRAM_CHAT_ID', 'GEMINI_API_KEY']
        missing = [k for k in required if not getattr(cls, k)]
        if missing: raise ValueError(f"누락된 API 키: {missing}")
    
    # 🔥 v3.0 Beast Mode 필터 설정
    MIN_MARKET_CAP = 1_000_000  # 시총 100만 달러 이상 (초소형주 포함)
    MAX_MARKET_CAP = 100_000_000_000  # 1000억 달러 미만 (대형주/ETF 제외)
    
    MIN_PRICE = 0.1  # 0.1달러 이상 (페니스탁 포함)
    MAX_PRICE = 100.0  # 100달러 이하
    
    MIN_VOLUME_INCREASE = 500  # 거래량 5배 이상 (급등 초기 포착)
    MIN_PRICE_CHANGE = 10.0  # 10% 이상 상승
    MIN_AI_SCORE = 7  # AI 점수 7점 이상
    
    # 🚨 POSITIVE_OVERRIDE - 악재 키워드보다 먼저 체크 (최우선 호재)
    # "유상증자 철회" 같은 케이스: 악재 키워드(유상증자)를 포함하지만 실제론 강한 호재
    POSITIVE_OVERRIDE = [
        # 악재 철회/취소 → 강한 호재
        '유상증자 철회', '유상증자 취소', '유상증자 백지화',
        '전환사채 상환', '전환사채 조기상환', '전환사채 취소',
        '감자 철회', '감자 취소',
        '거래정지 해제', '상장폐지 취소', '관리종목 해제',

        # 자사주 관련 (긍정)
        '자사주 소각', '자사주 매입', '자사주 취득',

        # 무상증자 (주주 환원 → 호재)
        '무상증자',

        # 영어 악재 철회
        'offering withdrawn', 'offering cancelled', 'offering terminated',
        'reverse split cancelled', 'reverse split withdrawn',
    ]

    # 🎯 v3.0 POSITIVE KEYWORDS - 섹터별 세분화 + 한국 테마 + RIME 반영
    POSITIVE_KEYWORDS = [
        # ===================================================================
        # 🧬 1. 바이오/헬스케어 (35% - 여전히 가장 강력)
        # ===================================================================
        
        # FDA/규제 승인
        'fda approval', 'fda approved', 'fda clearance', 'fda grants',
        'regulatory approval', 'marketing authorization', 'ce mark',
        'surprise fda nod', 'unexpected approval', 'breakthrough designation',
        
        # 임상 성공
        'clinical trial', 'phase 3', 'phase 2', 'phase 1',
        'primary endpoint met', 'statistically significant', 'superior efficacy',
        'positive data', 'positive results', 'met primary endpoint',
        'trial success', 'successful trial', 'pivotal trial',
        'positive top-line', 'positive topline', 'top-line data', 'topline results',
        'proof-of-concept', 'proof of concept', 'poc trial', 'poc study',
        'achieved primary endpoint', 'primary endpoint achieved',
        
        # 임상 결과 지표
        'durable response', 'sustained response', 'complete response', 'partial response',
        'objective response rate', 'orr', 'progression-free survival', 'pfs',
        'overall survival', 'os improvement', 'disease control rate',
        
        # 희귀질환/특수 지위
        'orphan drug', 'breakthrough therapy', 'fast track', 'priority review',
        'accelerated approval', 'rare disease', 'first-in-class', 'best-in-class',
        'expanded access', 'compassionate use', 'emergency use authorization', 'eua',
        
        # 라이센싱/제휴
        'licensing agreement', 'license deal', 'global rights', 'exclusive license',
        'milestone payment', 'investigational new drug', 'ind clearance', 'ind application',
        'rolling submission', 'rolling review', 'complete response letter lifted', 'crl lifted',
        'advisory committee', 'adcom positive', 'label expansion', 'indication expansion',
        
        # 적응증
        'moderate-to-severe', 'moderate to severe', 'severe', 'refractory', 'resistant',
        'advanced stage', 'metastatic', 'late-stage', 'late stage',
        
        # 질환 종류
        'atopic dermatitis', 'psoriasis', 'eczema', 'cancer', 'oncology', 'tumor',
        'alzheimer', 'parkinson', 'diabetes', 'cardiovascular', 'heart failure',
        
        # 대형 제약사 파트너십
        'pfizer partnership', 'roche collaboration', 'novartis agreement', 'merck deal',
        'jnj partnership', 'bristol myers', 'gilead', 'abbvie', 'amgen',
        'opt-in rights', 'option agreement', 'co-commercialization', 'royalty agreement',
        
        # ===================================================================
        # 🤝 2. M&A (25% - 즉각 급등)
        # ===================================================================
        'merger', 'acquisition', 'buyout', 'takeover', 'tender offer', 'all-cash offer',
        'acquired by', 'to be acquired', 'agrees to acquire', 'definitive agreement',
        'merger agreement', 'going private', 'take private',
        
        # QNCX 사례 반영
        'exploring strategic alternatives', 'explore strategic alternatives',
        'strategic alternative', 'reviewing strategic alternatives', 'strategic review',
        'strategic process', 'sale process', 'exploring sale', 'potential sale',
        'explore sale', 'financial advisor', 'exclusive financial advisor',
        'engaged as financial advisor', 'engaged as exclusive', 'lifesci capital',
        'investment bank', 'piper sandler', 'stifel', 'jefferies',
        
        # ===================================================================
        # 🤖 3. AI/반도체/테크 (20% - RIME 사례 반영)
        # ===================================================================
        
        # AI 핵심 키워드
        'artificial intelligence', 'ai partnership', 'ai platform', 'ai technology',
        'machine learning', 'deep learning', 'neural network', 'llm', 'large language model',
        'generative ai', 'ai model', 'ai chip', 'ai accelerator', 'ai inference',
        
        # 엔비디아/대형 테크 파트너십
        'nvidia partnership', 'nvidia isaac', 'nvidia collaboration', 'nvidia platform',
        'microsoft partnership', 'google partnership', 'amazon partnership',
        'openai', 'anthropic', 'meta ai', 'tesla partnership',
        
        # 반도체/칩셋
        'semiconductor', 'chip', 'chipset', 'processor', 'gpu', 'asic', 'fpga',
        'advanced packaging', '3nm', '2nm', 'euv', 'high bandwidth memory', 'hbm',
        
        # 효율성/성능 개선 (RIME 사례)
        'efficiency', 'cost reduction', 'platform launch', 'record high',
        'operational efficiency', 'optimization', 'automation', 'productivity gain',
        'faster processing', 'lower latency', 'improved performance',
        
        # 소프트웨어/플랫폼
        'saas', 'platform as a service', 'cloud platform', 'enterprise software',
        'digital transformation', 'api integration', 'subscription model',
        
        # ===================================================================
        # 🔋 4. 2차전지/에너지 (15%)
        # ===================================================================
        'battery', 'lithium', 'solid-state battery', 'energy storage', 'ev battery',
        'cathode', 'anode', 'electrolyte', 'battery cell', 'battery pack',
        'gigafactory', 'battery plant', 'capacity expansion',
        'charging', 'fast charging', 'wireless charging',
        'renewable energy', 'solar', 'wind power', 'hydrogen', 'fuel cell',
        'energy efficiency', 'carbon neutral', 'net zero', 'sustainability',
        
        # ===================================================================
        # 🤖 5. 로봇/스마트팩토리/물류 (10%)
        # ===================================================================
        'robotics', 'robot', 'automation', 'warehouse automation', 'logistics',
        'supply chain', 'fulfillment', 'autonomous', 'drone delivery',
        'smart factory', 'industry 4.0', 'iot', 'edge computing',
        'predictive maintenance', 'digital twin',
        
        # ===================================================================
        # 🚀 6. 방산/우주/국가안보 (10%)
        # ===================================================================
        'defense', 'defense contract', 'military', 'aerospace', 'space',
        'satellite', 'rocket', 'missile', 'drone', 'uav',
        'national security', 'pentagon', 'dod contract', 'navy', 'air force',
        'government contract', 'awarded contract', 'contract win', 'contract award',
        
        # ===================================================================
        # 🔬 7. 양자컴퓨팅/미래기술 (5%)
        # ===================================================================
        'quantum', 'quantum computing', 'quantum chip', 'qubit',
        'superconductor', 'photonics', 'nanotechnology',
        '6g', 'next-generation', 'breakthrough technology',
        
        # ===================================================================
        # 🏛️ 8. 정부/정책/보조금 (5%)
        # ===================================================================
        'government stake', 'sovereign investment', 'strategic resource',
        'subsidy', 'grant awarded', 'government funding', 'infrastructure bill',
        'chips act', 'inflation reduction act', 'tariff exemption',
        'critical minerals', 'rare earth', 'supply chain security',
        
        # ===================================================================
        # 💰 9. IPO/SPAC (5%)
        # ===================================================================
        'ipo', 'initial public offering', 'debut', 'spac merger',
        'business combination', 'merger completion', 'de-spac',
        'nasdaq debut', 'nyse debut', 'oversubscribed', 'upsized offering',
        
        # ===================================================================
        # 📊 10. 실적 서프라이즈 (5%)
        # ===================================================================
        'earnings beat', 'revenue beat', 'guidance raised', 'upgraded guidance',
        'record revenue', 'record earnings', 'record sales', 'blowout quarter',
        'massive beat', 'raised outlook', 'unexpected profit', 'surprise profit',
        
        # ===================================================================
        # 🌐 11. 무역/정책 (5%)
        # ===================================================================
        'tariff', 'trade policy', 'import ban', 'china ban',
        'alternative supplier', 'supply chain shift', 'reshoring',
        'friend-shoring', 'decoupling',
        
        # ===================================================================
        # 💎 12. 암호화폐/블록체인 (5%)
        # ===================================================================
        'bitcoin', 'ethereum', 'crypto', 'blockchain', 'web3',
        'bitcoin treasury', 'ethereum treasury', 'crypto strategy',
        'nft', 'defi', 'decentralized', 'vitalik buterin',
        
        # ===================================================================
        # 🇰🇷 13. 한국 키워드 (20% - 대폭 강화!)
        # ===================================================================

        # 기본 호재
        '승인', '허가', '인증', '수주', '계약', '특허', '개발', '출시',
        '임상', '성공', '합병', '인수', 'M&A', '제휴', '협력',
        '정부 계약', '국방', '방산', '수출', '수주',
        '흑자전환', '실적', '개선', '신약', '신제품',

        # 🔥 한국 특화 테마 (국장만의 특징)
        '경영권 분쟁', '경영권 방어', '우호지분', '적대적 M&A',
        '무상증자', '액면분할', '액면병합', '주식배당',
        '자사주', '자사주 소각', '자사주 매입',
        '유상증자 철회', '전환사채 상환',

        # 🔥 급등 직결 시그널
        '상한가', '급등', '품절주', '공급부족',
        '사상 최대', '사상 최고', '역대 최대', '역대 최고',
        '최대 실적', '최대 수주', '최대 계약',
        '어닝서프라이즈', '컨센서스 상회', '예상 상회',
        '흑자 전환', '적자 탈출', '턴어라운드',
        '대규모 수주', '공급 계약', '납품 계약', '독점 공급',

        # 정치/인맥 테마
        '대통령', '장관', '여당', '야당', '정책', '특위',
        '국회의원', '의원 관련주', '정치테마',

        # 상장 관련
        '신규상장', '재상장', '합병상장',
        '스팩', '스팩 합병', '스팩 대상',

        # 산업 육성/지원
        'K-칩스법', '반도체 지원', '배터리 지원',
        '소부장', '소재부품장비', '국가전략기술',

        # 실적/재무
        '영업이익 증가', '매출 증가', '실적 개선',

        # 테마/이슈
        '북한', '남북경협', '개성공단', '금강산',
        '올림픽', '월드컵', '엑스포', 'K-방산',
        '원자력', '원전', 'SMR', '소형모듈원전',
        '2차전지', '전기차', '수소차', '친환경차',
    ]
    
    # 🚫 v3.0 NEGATIVE KEYWORDS - 노이즈 대폭 강화
    NEGATIVE_KEYWORDS = [
        # ===================================================================
        # 💀 1. 자금 조달 (희석)
        # ===================================================================
        'offering', 'direct offering', 'public offering', 'registered direct offering',
        'shelf offering', 'secondary offering', 'follow-on offering',
        'at-the-market offering', 'atm offering', 'dilution', 'dilutive',
        'share issuance', 'stock issuance', 'warrant exercise',
        'rights offering', 'pipe offering', 'convertible note',
        
        # ===================================================================
        # 🪦 2. 기업 존속 위험
        # ===================================================================
        'bankruptcy', 'chapter 11', 'chapter 7', 'delisting',
        'nasdaq delisting', 'deficiency notice', 'going concern',
        'substantial doubt', 'wind down', 'liquidation', 'restructuring',
        
        # ===================================================================
        # ⚖️ 3. 법적/규제 리스크
        # ===================================================================
        'investigation', 'sec investigation', 'doj investigation',
        'lawsuit', 'class action', 'securities fraud', 'subpoena',
        'criminal charges', 'recall', 'product recall', 'safety recall',
        'warning letter', 'fda warning', 'crl', 'complete response letter',
        'rejected', 'denial', 'failed to meet', 'clinical hold',
        
        # ===================================================================
        # 🔄 4. 주식 구조 악재
        # ===================================================================
        'reverse split', 'reverse stock split', 'stock split',
        'share consolidation',
        
        # ===================================================================
        # ⏸️ 5. 거래 중단
        # ===================================================================
        'suspended', 'trading halt', 'halted', 'circuit breaker',
        'volatility halt',
        
        # ===================================================================
        # 📰 6. 의견/전망 (노이즈) - 🔥 대폭 강화
        # ===================================================================
        'analyst says', 'analyst ratings', 'analyst opinion', 'analyst note',
        'price target', 'upgraded', 'downgraded', 'maintained',
        'opinion', 'preview', 'outlook', 'forecast', 'prediction',
        'summary', 'recap', 'market wrap', 'market update',
        'why it moved', 'what to watch', 'what happened', 'explainer',
        
        # 노이즈성 컨텐츠
        'stock movers', 'pre-market', 'after-hours', 'morning brief',
        'market watch', 'stock alert', 'penny stock', 'meme stock',
        'stock to watch', 'stocks to buy', 'top picks',
        'sponsored', 'advertisement', 'paid promotion',
        
        # 정기 업데이트
        'investor presentation', 'roadshow', 'quarterly update',
        'monthly update', 'business update', 'corporate update',
        'conference call', 'webcast', 'earnings call',
        'to host', 'will host', 'to present', 'will present',
        
        # SEC 정기 보고서 (8-K는 제외)
        'files 10-k', 'files 10-q', 'files 20-f',
        'annual report', 'quarterly report', 'form 10-k', 'form 10-q',
        
        # ===================================================================
        # 🐻 7. 공매도
        # ===================================================================
        'short seller', 'short report', 'short interest',
        'hindenburg', 'citron', 'muddy waters', 'grizzly research',
        'white diamond', 'bonitas', 'culper',
        
        # ===================================================================
        # 🇰🇷 8. 한국 악재
        # ===================================================================
        '루머', '추정', '전망', '예상', '관측',
        '적자', '소송', '유상증자', '감자', '자본잠식',
        '거래정지', '상장폐지', '관리종목', '투자유의',
        '분식회계', '횡령', '배임', '검찰', '조사',
        '하락', '폭락', '급락', '매도',

        # 🔥 추가: 오버행/물량 악재
        '보호예수 해제', '오버행', '블록딜', '대량 매도',
        '전환청구', '전환권 행사', '워런트 행사',

        # 🔥 추가: 노이즈성 뉴스
        '분기 실적 발표 일정', '실적 발표 예정', '실적 발표 일정',
        '주주총회 소집', '주주총회 안내', '배당 기준일',
        '공시 안내', '정정 공시',
    ]

    # ──────────────────────────────────────────────────────────
    # 🆕 키워드 점수 테이블 (quick_score AI 호출 대체)
    # 뉴스 제목에서 가장 높은 점수의 키워드를 찾아 반환
    # 소스별 threshold와 함께 사용: score >= threshold 시 AI 분석 진행
    # ──────────────────────────────────────────────────────────
    KEYWORD_SCORES = {
        # ── 10점: M&A 확정 (즉각 급등) ──────────────────────
        'acquisition':          10, 'acquired by':          10,
        'to be acquired':       10, 'agrees to acquire':    10,
        'definitive agreement': 10, 'merger agreement':     10,
        'buyout':               10, 'takeover':             10,
        'tender offer':         10, 'all-cash offer':       10,
        'going private':        10, 'take private':         10,
        'merger':               10,
        '인수합의':             10, '인수완료':             10,
        '인수 합의':            10, '인수 완료':            10,   # 띄어쓰기 변형
        '합병완료':             10, '합병 완료':            10,   # 띄어쓰기 변형
        '경영권 인수':          10, '최대주주 변경':        10,
        '공개매수':             10,

        # ── 9점: FDA 승인, 대형 계약 확정 ───────────────────
        'fda approval':         9, 'fda approved':          9,
        'fda clearance':        9, 'fda grants':            9,
        'breakthrough designation': 9,
        'primary endpoint met': 9, 'met primary endpoint':  9,
        'meets primary endpoint': 9, 'endpoint met':        9,
        'achieved primary endpoint': 9,
        'positive topline':     9, 'positive top-line':     9,
        'positive data':        9, 'positive results':      9,
        'contract win':         9, 'contract award':        9,
        'awarded contract':     9, 'dod contract':          9,
        '대규모 수주':          9, '독점 공급':             9,
        '경영권 분쟁':          9, '역대 최대 계약':        9,
        '최대 수주':            9, '최대 계약':             9,

        # ── 8점: 임상 3상, 전략 대안 탐색, 주주환원 ─────────
        'phase 3':              8, 'pivotal trial':         8,
        'trial success':        8, 'successful trial':      8,
        'exploring strategic alternatives': 8,
        'explore strategic alternatives':   8,
        'strategic review':     8, 'strategic alternative': 8,
        'sale process':         8, 'exploring sale':        8,
        'potential sale':       8,
        'nvidia partnership':   8, 'microsoft partnership': 8,
        'google partnership':   8, 'amazon partnership':    8,
        'major contract':       8, 'government contract':   8,
        '무상증자':             8, '자사주 소각':           8,
        '흑자전환':             8, '흑자 전환':             8,
        '상한가':               8, '사상 최대':             8,
        '사상 최고':            8, '역대 최대':             8,
        '역대 최고':            8, '어닝서프라이즈':        8,

        # ── 7점: 파트너십, 임상 2상, 중형 계약 ──────────────
        'partnership':          7, 'collaboration':         7,
        'license deal':         7, 'licensing agreement':   7,
        'milestone payment':    7, 'exclusive license':     7,
        'phase 2':              7, 'clinical trial':        7,
        'nvidia':               7, 'openai':                7,
        'raises':               7, 'private placement':     7,
        'grant awarded':        7, 'government funding':    7,
        'spac merger':          7, 'business combination':  7,
        'merger completion':    7, 'de-spac':               7,
        'earnings beat':        7, 'revenue beat':          7,
        'guidance raised':      7, 'record revenue':        7,
        'record earnings':      7, 'blowout quarter':       7,
        '수주':                 7, '계약':                  7,
        '합의':                 7,   # 인수 합의, 협의 합의 등 한국 M&A 변형 포괄
        '특허':                 7, '임상 성공':             7,
        '흑자':                 7, '급등':                  7,
        '컨센서스 상회':        7, '예상 상회':             7,
        '턴어라운드':           7, '최대 실적':             7,

        # ── 6점: 제품 출시, AI 플랫폼 (신뢰 소스에서만 통과) ─
        'launches':             6, 'launch':                6,
        'ai platform':          6, 'platform launch':       6,
        'agentic ai':           6, 'generative ai':         6,
        'artificial intelligence': 6, 'ai technology':      6,
        'ai model':             6, 'ai chip':               6,
        'automation':           6, 'api integration':       6,
        'api launch':           6, 'saas':                  6,
        'cloud platform':       6, 'digital transformation': 6,
        'semiconductor':        6, 'chip':                  6,
        'ipo':                  6, 'nasdaq debut':          6,
        'nyse debut':           6, 'initial public offering': 6,
        'bitcoin':              6, 'ethereum':              6,
        'crypto':               6, 'blockchain':            6,
        '신규상장':             6, '재상장':                6,
        '합병상장':             6, '스팩 합병':             6,
        '영업이익 증가':        6, '매출 증가':             6,
        '실적 개선':            6,
    }

    # ── 소스별 threshold (낮을수록 더 많은 뉴스 통과) ────────
    # 공식 보도자료 배포 서비스 (기업이 직접 올림 → 루머 없음) → 6점
    # 편집 기사 혼재 소스 → 7점
    # 속보/루머 가능성 소스 → 8점
    SOURCE_THRESHOLD = {
        'PR Newswire':      6.0,
        'GlobeNewswire':    6.0,
        'Business Wire':    6.0,
        'SEC 8-K':          6.0,
        'Benzinga':         7.0,
        '매일경제':         7.0,
        '한국경제':         7.0,
        '네이버 증권 속보': 8.0,
    }

    @classmethod
    def keyword_score(cls, title: str) -> float:
        """
        🆕 AI 없이 순수 키워드로 뉴스 긴급도 점수 계산 (0~10)
        우선순위:
          1. POSITIVE_OVERRIDE → 9점 고정 (악재 철회 케이스)
          2. KEYWORD_SCORES    → 해당 키워드의 정의된 점수
          3. POSITIVE_KEYWORDS → 5점 (기본 호재, 키워드 점수 미정의)
          4. 없음              → 0점
        """
        title_lower = title.lower()

        # 1순위: POSITIVE_OVERRIDE (악재 철회 → 항상 강한 호재)
        for kw in cls.POSITIVE_OVERRIDE:
            if kw.lower() in title_lower:
                return 9.0

        # 2순위: KEYWORD_SCORES (긴 키워드 먼저 체크 → 정확도 향상)
        best_score = 0.0
        for kw, score in sorted(cls.KEYWORD_SCORES.items(),
                                 key=lambda x: len(x[0]), reverse=True):
            if kw.lower() in title_lower and score > best_score:
                best_score = float(score)

        if best_score > 0:
            return best_score

        # 3순위: 기본 POSITIVE_KEYWORDS (점수 정의 안 된 키워드)
        for kw in cls.POSITIVE_KEYWORDS:
            if kw.lower() in title_lower:
                return 5.0

        return 0.0

    # Reddit 설정 (선택사항)
    REDDIT_MIN_MENTIONS = 10
    REDDIT_SUBREDDITS = ['wallstreetbets', 'stocks', 'investing', 'pennystocks']
    
    # 🔥 v3.0 Beast Mode 설정
    BEAST_MODE = True  # 야수 모드 활성화
    ENABLE_MICRO_CAPS = True  # 초소형주 포함
    ENABLE_PENNY_STOCKS = True  # 페니스탁 포함
    AGGRESSIVE_SCANNING = True  # 공격적 스캐닝

try:
    Config.validate()
except ValueError as e:
    print(f"⚠️ 설정 오류: {e}")
