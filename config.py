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

    # 🚫 LATE_KEYWORDS - 이미 주가에 반영된 뒷북 뉴스 즉시 차단
    # _passes_keyword_filter와 keyword_score 양쪽에서 적용
    LATE_KEYWORDS = [
        # 이미 오른 결과 (한국)
        '상한가', '무더기 상한가', '상한가 진입', '상한가 마감', '상한가 기록',
        '신고가', '역대 최고가', '52주 최고가', '신고가 경신', '신고가 행진',
        '급등 마감', '폭등 마감', '급등세 마감',            # '급등' 단독은 제외 (정상 기사 차단 위험)
        '마감 시황', '장마감', '장 마감', '오전장 시황', '오후장 시황',
        '증시 시황', '순환매', '순환매 장세',
        '특징주',           # 이미 15%+ 오른 뒤 나오는 기사
        '전일 대비', '전일대비',
        '랠리 마감', '상승 마감', '상승세 마감',
        # 이미 오른 결과 (미국)
        'closed higher', 'market close', 'end of day', 'closing bell',
        'new all-time high', 'new 52-week high', 'hits all-time high',
        'hits record high', 'stock surges', 'shares surge',
        'pre-market movers', 'after-hours movers',
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
        '정부 계약', '국방', '방산', '수출',
        '흑자전환', '실적', '개선', '신약', '신제품',

        # 🔥 한국 특화 테마 (국장만의 특징)
        '경영권 분쟁', '경영권 방어', '우호지분', '적대적 M&A',
        '무상증자', '액면분할', '액면병합', '주식배당',
        '자사주', '자사주 소각', '자사주 매입',
        '유상증자 철회', '전환사채 상환',

        # 🔥 급등 직결 시그널 (뒷북 아닌 것만)
        '사상 최대', '사상 최고', '역대 최대', '역대 최고',
        '최대 실적', '최대 수주', '최대 계약',
        '어닝서프라이즈', '컨센서스 상회', '예상 상회',
        '흑자 전환', '적자 탈출', '턴어라운드',
        '대규모 수주', '공급 계약', '납품 계약', '독점 공급',

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
    # 🚫 NEGATIVE_SCORES - 악재 강도별 마이너스 점수
    # keyword_score()에서 POSITIVE 점수에서 차감
    # -10 이하 → 즉시 차단 (POSITIVE_OVERRIDE 없으면 통과 불가)
    # ──────────────────────────────────────────────────────────
    NEGATIVE_SCORES = {
        # ── -10점: 즉시 차단 (치명적 악재) ──────────────────
        'bankruptcy':           -10, 'chapter 11':           -10,
        'chapter 7':            -10, 'liquidation':          -10,
        'securities fraud':     -10, 'criminal charges':     -10,
        'class action':         -10,
        'fda rejection':        -10, 'complete response letter': -10,
        'clinical hold':        -10, 'failed to meet':       -10,
        'hindenburg':           -10, 'citron':               -10,
        'muddy waters':         -10, 'grizzly research':     -10,
        'white diamond':        -10, 'bonitas':              -10,
        'culper':               -10,
        '파산':                 -10, '분식회계':             -10,
        '횡령':                 -10, '배임':                 -10,
        '자본잠식':             -10,

        # ── -8점: 강한 악재 ───────────────────────────────────
        'delisting':            -8, 'nasdaq delisting':      -8,
        'going concern':        -8, 'substantial doubt':     -8,
        'wind down':            -8, 'restructuring':         -8,
        'deficiency notice':    -8,
        'investigation':        -8, 'sec investigation':     -8,
        'doj investigation':    -8, 'subpoena':              -8,
        'lawsuit':              -8,
        'recall':               -8, 'product recall':        -8,
        'safety recall':        -8,
        'reverse split':        -8, 'reverse stock split':   -8,
        'share consolidation':  -8,
        'trading halt':         -8, 'halted':                -8,
        'suspended':            -8,
        'investor alert':       -8, 'law firm investigates': -8,
        'investigates claims':  -8, 'pomerantz':             -8,
        '상장폐지':             -8, '관리종목':              -8,
        '거래정지':             -8, '검찰':                  -8,
        '조사':                 -8,

        # ── -6점: 중간 악재 ───────────────────────────────────
        'crl':                  -6, 'warning letter':        -6,
        'fda warning':          -6, 'rejected':              -6,
        'denial':               -6,
        'short seller':         -6, 'short report':          -6,
        'dilution':             -6, 'dilutive':              -6,
        'share issuance':       -6, 'stock issuance':        -6,
        'warrant exercise':     -6, 'convertible note':      -6,
        'pipe offering':        -6,
        '유상증자':             -6, '감자':                  -6,
        '보호예수 해제':        -6, '오버행':                -6,
        '블록딜':               -6, '대량 매도':             -6,
        '전환청구':             -6, '전환권 행사':           -6,
        '워런트 행사':          -6, '소송':                  -6,
        '투자유의':             -6,

        # ── -4점: 약한 악재 / 노이즈성 ──────────────────────
        'offering':             -4, 'direct offering':       -4,
        'public offering':      -4, 'registered direct offering': -4,
        'secondary offering':   -4,
        'follow-on offering':   -4, 'shelf offering':        -4,
        'at-the-market offering': -4, 'atm offering':        -4,
        'rights offering':      -4,
        'stock split':          -4,
        'circuit breaker':      -4, 'volatility halt':       -4,
        'downgraded':           -4, 'upgraded':              -4,
        '폭락':                 -4, '급락':                  -4,
        '적자':                 -4,

        # ── -2점: 노이즈 (정기 업데이트 / 의견성) ────────────
        'analyst says':         -2, 'analyst ratings':       -2,
        'analyst opinion':      -2, 'analyst note':          -2,
        'price target':         -2, 'maintained':            -2,
        'opinion':              -2, 'preview':               -2,
        'outlook':              -2, 'forecast':              -2,
        'prediction':           -2, 'summary':               -2,
        'recap':                -2, 'market wrap':           -2,
        'market update':        -2,
        'why it moved':         -2, 'what to watch':         -2,
        'what happened':        -2, 'explainer':             -2,
        'investor presentation': -2, 'roadshow':             -2,
        'quarterly update':     -2, 'monthly update':        -2,
        'business update':      -2, 'corporate update':      -2,
        'conference call':      -2, 'webcast':               -2,
        'earnings call':        -2,
        'to host':              -2, 'will host':             -2,
        'to present':           -2, 'will present':          -2,
        'files 10-k':           -2, 'files 10-q':            -2,
        'files 20-f':           -2, 'annual report':         -2,
        'quarterly report':     -2, 'form 10-k':             -2,
        'form 10-q':            -2,
        'stock movers':         -2, 'pre-market':            -2,
        'after-hours':          -2, 'morning brief':         -2,
        'market watch':         -2, 'stock alert':           -2,
        'penny stock':          -2, 'meme stock':            -2,
        'stock to watch':       -2, 'stocks to buy':         -2,
        'top picks':            -2,
        'sponsored':            -2, 'advertisement':         -2,
        'paid promotion':       -2,
        'short interest':       -2,
        '루머':                 -2, '추정':                  -2,
        '전망':                 -2, '예상':                  -2,
        '관측':                 -2,
        '하락':                 -2, '매도':                  -2,
        '주주총회 소집':        -2, '주주총회 안내':         -2,
        '배당 기준일':          -2, '공시 안내':             -2,
        '정정 공시':            -2,
        '분기 실적 발표 일정':  -2, '실적 발표 예정':       -2,
        '실적 발표 일정':       -2,
    }

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
        '인수 합의':            10, '인수 완료':            10,
        '합병완료':             10, '합병 완료':            10,
        '경영권 인수':          10, '최대주주 변경':        10,
        '공개매수':             10,

        # ── 9점: FDA 승인, 임상 성공, 대형 계약 확정 ─────────
        'fda approval':         9, 'fda approved':          9,
        'fda clearance':        9, 'fda grants':            9,
        'regulatory approval':  9, 'marketing authorization': 9,
        'ce mark':              9,
        'surprise fda nod':     9, 'unexpected approval':   9,
        'breakthrough designation': 9,
        'primary endpoint met': 9, 'met primary endpoint':  9,
        'meets primary endpoint': 9, 'endpoint met':        9,
        'achieved primary endpoint': 9, 'primary endpoint achieved': 9,
        'positive topline':     9, 'positive top-line':     9,
        'top-line data':        9, 'topline results':       9,
        'positive data':        9, 'positive results':      9,
        'trial success':        9, 'successful trial':      9,
        'statistically significant': 9, 'superior efficacy': 9,
        'proof-of-concept':     9, 'proof of concept':      9,
        'poc trial':            9, 'poc study':             9,
        'adcom positive':       9, 'complete response letter lifted': 9,
        'crl lifted':           9,
        'contract win':         9, 'contract award':        9,
        'awarded contract':     9, 'dod contract':          9,
        '대규모 수주':          9, '독점 공급':             9,
        '경영권 분쟁':          9, '역대 최대 계약':        9,
        '최대 수주':            9, '최대 계약':             9,

        # ── 8점: 전략 대안, 대형 파트너십, 주주환원, 임상 지위 ─
        'phase 3':              8, 'pivotal trial':         8,
        'phase 2':              8,
        'orphan drug':          8, 'breakthrough therapy':  8,
        'fast track':           8, 'priority review':       8,
        'accelerated approval': 8, 'emergency use authorization': 8,
        'eua':                  8,
        'first-in-class':       8, 'best-in-class':         8,
        'expanded access':      8, 'compassionate use':     8,
        'rare disease':         8,
        'durable response':     8, 'sustained response':    8,
        'complete response':    8, 'overall survival':      8,
        'os improvement':       8, 'objective response rate': 8,
        # 'orr' 단독 제거: 'W2CoRRection' 같은 false positive 방지. 'objective response rate'(8점)으로 대체
        'pfizer partnership':   8, 'roche collaboration':   8,
        'novartis agreement':   8, 'merck deal':            8,
        'jnj partnership':      8, 'bristol myers':         8,
        'gilead':               8, 'abbvie':                8,
        'amgen':                8,
        'global rights':        8, 'exclusive license':     8,
        'opt-in rights':        8, 'co-commercialization':  8,
        'royalty agreement':    8,
        'exploring strategic alternatives': 8,
        'explore strategic alternatives':   8,
        'strategic review':     8, 'strategic alternative': 8,
        'reviewing strategic alternatives': 8, 'strategic process': 8,
        'sale process':         8, 'exploring sale':        8,
        'potential sale':       8, 'explore sale':          8,
        'financial advisor':    8, 'exclusive financial advisor': 8,
        'engaged as financial advisor': 8, 'engaged as exclusive': 8,
        'investment bank':      8, 'lifesci capital':       8,
        'piper sandler':        8, 'stifel':                8,
        'jefferies':            8,
        'nvidia partnership':   8, 'nvidia':                8,
        'nvidia isaac':         8, 'nvidia collaboration':  8,
        'nvidia platform':      8,
        'microsoft partnership': 8, 'google partnership':   8,
        'amazon partnership':   8, 'openai':                8,
        'anthropic':            8, 'meta ai':               8,
        'tesla partnership':    8,
        'major contract':       8, 'government contract':   8,
        'defense contract':     8, 'dod contract':          8,
        'pentagon':             8,
        '무상증자':             8, '자사주 소각':           8,
        '흑자전환':             8, '흑자 전환':             8,
        '상한가':               8, '사상 최대':             8,
        '사상 최고':            8, '역대 최대':             8,
        '역대 최고':            8, '어닝서프라이즈':        8,

        # ── 7점: 파트너십, 중형계약, 임상 데이터, 실적 서프라이즈 ─
        'partnership':          7, 'collaboration':         7,
        'license deal':         7, 'licensing agreement':   7,
        'milestone payment':    7,
        'investigational new drug': 7, 'ind clearance':     7,
        'ind application':      7, 'rolling submission':    7,
        'rolling review':       7, 'advisory committee':    7,
        'label expansion':      7, 'indication expansion':  7,
        'partial response':     7, 'progression-free survival': 7,
        'pfs':                  7, 'disease control rate':  7,
        'phase 1':              7, 'clinical trial':        7,
        'option agreement':     7,
        'ai partnership':       7, 'ai platform':           7,
        'machine learning':     7, 'deep learning':         7,
        'neural network':       7, 'llm':                   7,
        'large language model': 7, 'generative ai':         7,
        'ai model':             7, 'ai chip':               7,
        'ai accelerator':       7, 'ai inference':          7,
        'ai technology':        7,
        'chipset':              7, 'processor':             7,
        'gpu':                  7, 'asic':                  7,
        'fpga':                 7, 'advanced packaging':    7,
        '3nm':                  7, '2nm':                   7,
        'euv':                  7, 'high bandwidth memory': 7,
        'hbm':                  7, 'semiconductor':         7,
        'chip':                 7,
        'raises':               7, 'private placement':     7,
        'grant awarded':        7, 'government funding':    7,
        'subsidy':              7, 'infrastructure bill':   7,
        'chips act':            7, 'inflation reduction act': 7,
        'government stake':     7, 'sovereign investment':  7,
        'strategic resource':   7, 'tariff exemption':      7,
        'critical minerals':    7, 'rare earth':            7,
        'supply chain security': 7,
        'defense':              7, 'military':              7,
        'aerospace':            7, 'space':                 7,
        'satellite':            7, 'rocket':                7,
        'missile':              7, 'uav':                   7,
        'national security':    7, 'navy':                  7,
        'air force':            7,
        'spac merger':          7, 'business combination':  7,
        'merger completion':    7, 'de-spac':               7,
        'nasdaq debut':         7, 'nyse debut':            7,
        'oversubscribed':       7, 'upsized offering':      7,
        'earnings beat':        7, 'revenue beat':          7,
        'guidance raised':      7, 'upgraded guidance':     7,
        'record revenue':       7, 'record earnings':       7,
        'record sales':         7, 'blowout quarter':       7,
        'massive beat':         7, 'raised outlook':        7,
        'unexpected profit':    7, 'surprise profit':       7,
        'record high':          7,
        'solid-state battery':  7, 'ev battery':            7,
        'gigafactory':          7, 'battery plant':         7,
        'capacity expansion':   7, 'energy storage':        7,
        'quantum computing':    7, 'quantum chip':          7,
        'quantum':              7, 'qubit':                 7,
        'superconductor':       7, 'photonics':             7,
        'nanotechnology':       7, 'breakthrough technology': 7,
        '수주':                 7, '계약':                  7,
        '합의':                 7, '특허':                  7,
        '임상 성공':            7, '흑자':                  7,
        '급등':                 7, '컨센서스 상회':         7,
        '예상 상회':            7, '턴어라운드':            7,
        '최대 실적':            7,
        '인수':                 7, '합병':                  7,
        '제휴':                 7, '협력':                  7,
        '수출':                 7, '정부 계약':             7,
        '국방':                 7, '방산':                  7,
        'K-방산':               7,
        '신약':                 7, '신제품':                7,
        '임상':                 7, '성공':                  7,
        '허가':                 7, '승인':                  7,
        '인증':                 7,
        '경영권 방어':          7, '우호지분':              7,
        '적대적 M&A':           7, 'M&A':                   7,
        '품절주':               7, '공급부족':              7,
        '공급 계약':            7, '납품 계약':             7,
        '영업이익 증가':        7, '매출 증가':             7,
        '실적 개선':            7, '실적':                  7,
        '개선':                 7,
        'SMR':                  7, '소형모듈원전':          7,
        '원자력':               7, '원전':                  7,

        # ── 6점: 제품 출시, AI 런칭, 테마주, 에너지 (신뢰 소스에서 통과) ─
        'launches':             6, 'launch':                6,
        'platform launch':      6, 'agentic ai':            6,
        'artificial intelligence': 6, 'api integration':   6,
        'api launch':           6, 'saas':                  6,
        'platform as a service': 6, 'cloud platform':       6,
        'enterprise software':  6, 'digital transformation': 6,
        'subscription model':   6,
        'efficiency':           6, 'cost reduction':        6,
        'operational efficiency': 6, 'optimization':        6,
        'automation':           6, 'productivity gain':     6,
        'faster processing':    6, 'lower latency':         6,
        'improved performance': 6,
        'robotics':             6, 'robot':                 6,
        'warehouse automation': 6, 'logistics':             6,
        'supply chain':         6, 'fulfillment':           6,
        'autonomous':           6, 'drone delivery':        6,
        'smart factory':        6, 'industry 4.0':          6,
        'iot':                  6, 'edge computing':        6,
        'predictive maintenance': 6, 'digital twin':        6,
        'drone':                6,
        'battery':              6, 'lithium':               6,
        'cathode':              6, 'anode':                 6,
        'electrolyte':          6, 'battery cell':          6,
        'battery pack':         6,
        'charging':             6, 'fast charging':         6,
        'wireless charging':    6,
        'renewable energy':     6, 'solar':                 6,
        'wind power':           6, 'hydrogen':              6,
        'fuel cell':            6, 'energy efficiency':     6,
        'carbon neutral':       6, 'net zero':              6,
        'sustainability':       6,
        '6g':                   6, 'next-generation':       6,
        'tariff':               6, 'trade policy':          6,
        'import ban':           6, 'china ban':             6,
        'alternative supplier': 6, 'supply chain shift':    6,
        'reshoring':            6, 'friend-shoring':        6,
        'decoupling':           6,
        'bitcoin':              6, 'ethereum':              6,
        'crypto':               6, 'blockchain':            6,
        'web3':                 6, 'bitcoin treasury':      6,
        'ethereum treasury':    6, 'crypto strategy':       6,
        'nft':                  6, 'defi':                  6,
        'decentralized':        6, 'vitalik buterin':       6,
        'ipo':                  6, 'initial public offering': 6,
        'debut':                6, 'spac':                  6,
        '신규상장':             6, '재상장':                6,
        '합병상장':             6, '스팩 합병':             6,
        '스팩':                 6, '스팩 대상':             6,
        '2차전지':              6, '전기차':                6,
        '수소차':               6, '친환경차':              6,
        '개발':                 6, '출시':                  6,
        '자사주':               6, '액면분할':              6,
        '액면병합':             6, '주식배당':              6,
        '적자 탈출':            6,
        'K-칩스법':             6, '반도체 지원':           6,
        '배터리 지원':          6, '소부장':                6,
        '소재부품장비':         6, '국가전략기술':          6,

        # ── 5점: 테마/정치/이슈 (낮은 threshold 소스에서만 통과) ─
        'moderate-to-severe':   5, 'moderate to severe':   5,
        'severe':               5, 'refractory':           5,
        'resistant':            5, 'advanced stage':       5,
        'metastatic':           5, 'late-stage':           5,
        'late stage':           5,
        'atopic dermatitis':    5, 'psoriasis':            5,
        'eczema':               5, 'cancer':               5,
        'oncology':             5, 'tumor':                5,
        'alzheimer':            5, 'parkinson':            5,
        'diabetes':             5, 'cardiovascular':       5,
        'heart failure':        5,
        '대통령':               5, '장관':                 5,
        '여당':                 5, '야당':                 5,
        '정책':                 5, '특위':                 5,
        '국회의원':             5, '의원 관련주':           5,
        '정치테마':             5,
        '북한':                 5, '남북경협':             5,
        '개성공단':             5, '금강산':               5,
        '올림픽':               5, '월드컵':               5,
        '엑스포':               5,
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
        '네이버 증권 속보': 8.0,   # 루머/뒷북 위험 가장 높음 → 가장 엄격
    }

    @classmethod
    def keyword_score(cls, title: str) -> float:
        """
        🆕 AI 없이 순수 키워드로 뉴스 긴급도 점수 계산
        
        처리 순서:
          1. POSITIVE_OVERRIDE 체크 → 해당 시 9.0 즉시 반환 (악재 철회)
          2. NEGATIVE_SCORES 최악값 계산 (긴 키워드 우선)
          3. KEYWORD_SCORES 최고값 계산 (긴 키워드 우선)
          4. 순 점수 = 양수 점수 + 음수 패널티
             - 패널티 ≤ -8 이고 POSITIVE가 9 미만 → 0 반환 (즉시 차단)
             - 나머지 → max(0, 양수 + 패널티)
          5. 양수 키워드 없으면 → POSITIVE_KEYWORDS fallback (5점)
          6. 아무것도 없으면 → 0점
        """
        import logging as _logging
        _log = _logging.getLogger(__name__)
        title_lower = title.lower()

        # ── 1순위: POSITIVE_OVERRIDE (악재 철회 → 무조건 통과) ──
        for kw in cls.POSITIVE_OVERRIDE:
            if kw.lower() in title_lower:
                return 9.0

        # ── 2순위: LATE_KEYWORDS (뒷북 → 즉시 차단) ─────────────
        for kw in cls.LATE_KEYWORDS:
            if kw.lower() in title_lower:
                return 0.0

        # ── 3순위: NEGATIVE_SCORES 최악값 계산 ──────────────────
        worst_neg = 0.0
        for kw, penalty in sorted(cls.NEGATIVE_SCORES.items(),
                                   key=lambda x: len(x[0]), reverse=True):
            if kw.lower() in title_lower and penalty < worst_neg:
                worst_neg = float(penalty)

        # ── 3순위: KEYWORD_SCORES 최고값 계산 ───────────────────
        best_pos = 0.0
        for kw, score in sorted(cls.KEYWORD_SCORES.items(),
                                  key=lambda x: len(x[0]), reverse=True):
            if kw.lower() in title_lower and score > best_pos:
                best_pos = float(score)

        # ── 4순위: 순 점수 계산 ─────────────────────────────────
        if best_pos > 0:
            # 치명적 악재(-8 이하)이고 압도적 호재(9점 이상) 아니면 차단
            if worst_neg <= -8 and best_pos < 9:
                _log.debug(
                    f"🚫 악재 차단: pos={best_pos} neg={worst_neg} | {title[:50]}"
                )
                return 0.0
            net = best_pos + worst_neg
            return max(0.0, net)

        # ── 5순위: 기본 POSITIVE_KEYWORDS fallback ───────────────
        for kw in cls.POSITIVE_KEYWORDS:
            if kw.lower() in title_lower:
                # fallback도 악재 패널티 적용
                if worst_neg <= -8:
                    return 0.0
                return max(0.0, 5.0 + worst_neg)

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
