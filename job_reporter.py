from __future__ import annotations

import argparse
import html as html_utils
import json
import os
import re
import sys
import textwrap
import time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from html.parser import HTMLParser
from pathlib import Path

try:
    from zoneinfo import ZoneInfo
except Exception:  # pragma: no cover - old Python fallback
    ZoneInfo = None


BASE_DIR = Path(__file__).resolve().parent
ENV_PATH = BASE_DIR / ".env"
LOG_DIR = BASE_DIR / "logs"

CHANNEL_TITLE = "프론트엔드 채용 리포트"
FALLBACK_CHAT_ID = ""
TELEGRAM_API = "https://api.telegram.org/bot{token}/{method}"
DEFAULT_SCHEDULE_HOUR = 10
DEFAULT_SCHEDULE_MINUTE = 0

DIRECT_FRONTEND_KEYWORDS = [
    "frontend",
    "front-end",
    "front end",
    "web frontend",
    "ui engineer",
    "react",
    "vue",
    "프론트엔드",
    "프론트 엔드",
    "웹프론트",
    "웹 프론트",
    "웹개발",
    "웹 개발",
    "FE 개발",
    "UI 개발자",
    "UI 개발",
]

RELATED_TECH_KEYWORDS = [
    "fullstack",
    "full-stack",
    "full stack",
    "web developer",
    "web engineer",
    "웹개발",
    "웹 개발",
    "웹서비스",
    "웹 서비스",
    "웹/앱",
    "웹앱",
    "모바일웹",
    "모바일 웹",
    "UI/UX",
    "서비스 개발",
    "플랫폼 개발",
    "채널 개발",
    "디지털채널",
    "인터넷뱅킹",
    "스마트뱅킹",
    "모바일뱅킹",
    "비대면 채널",
    "디지털 개발",
]

FRONTEND_KEYWORDS = DIRECT_FRONTEND_KEYWORDS + RELATED_TECH_KEYWORDS

TECH_STACK_PATTERNS = [
    ("JavaScript", r"(?<![\w])javascript(?![\w])"),
    ("TypeScript", r"(?<![\w])typescript(?![\w])"),
    ("HTML", r"(?<![\w])html(?:5)?(?![\w])"),
    ("React", r"(?<![\w])react(?:\.js|js)?(?![\w])"),
    ("Next.js", r"(?<![\w])next(?:\.js|js)(?![\w])"),
    ("Vue", r"(?<![\w])vue(?:\.js|js)?(?![\w])"),
    ("Nuxt", r"(?<![\w])nuxt(?:\.js|js)?(?![\w])"),
]

STRONG_FRONTEND_STACKS = {"React", "Next.js", "Vue", "Nuxt"}
FRONTEND_CONTEXT_KEYWORDS = [
    "frontend",
    "front-end",
    "front end",
    "프론트엔드",
    "프론트 엔드",
    "웹 개발",
    "웹개발",
    "web developer",
    "web engineer",
    "client-side",
    "browser",
    "ui engineer",
    "ui 개발",
]
NON_FRONTEND_TITLE_KEYWORDS = [
    "backend",
    "back-end",
    "백엔드",
    "cloud engineer",
    "devops",
    "sre",
    "infrastructure",
    "인프라",
    "data engineer",
    "데이터 엔지니어",
    "machine learning",
    "security engineer",
    "보안 엔지니어",
]

ROLE_TITLE_KEYWORDS = [
    "engineer",
    "developer",
    "software",
    "frontend",
    "front-end",
    "fullstack",
    "full-stack",
    "web",
    "개발",
    "엔지니어",
    "플랫폼",
    "서비스",
    "모바일",
    "앱",
    "디지털",
    "IT",
    "DX",
    "UI",
]

COMPANY_KO_NAMES = {
    "Samsung Careers": "삼성",
    "LG Careers": "LG",
    "SK Careers": "SK",
    "Hyundai Motor": "현대자동차",
    "Kia": "기아",
    "Hyundai Mobis": "현대모비스",
    "NAVER Careers": "네이버",
    "Kakao Careers": "카카오",
    "Coupang": "쿠팡",
    "LINE Careers": "라인",
    "Toss Careers": "토스",
    "Woowa Brothers": "우아한형제들",
    "Daangn": "당근",
    "Bucketplace": "버킷플레이스(오늘의집)",
    "Zigbang": "직방",
    "Yanolja": "야놀자",
    "KRAFTON": "크래프톤",
    "Nexon": "넥슨",
    "NCSoft": "엔씨소프트",
    "Netmarble": "넷마블",
    "Dunamu": "두나무",
    "MUSINSA": "무신사",
    "GS Group": "GS그룹",
    "GS Caltex": "GS칼텍스",
    "GS Retail": "GS리테일",
    "GS E&C": "GS건설",
    "HD Hyundai": "HD현대",
    "POSCO": "포스코",
    "Hanwha": "한화",
    "LS Group": "LS그룹",
    "LX Group": "LX그룹",
    "Kumho Petrochemical": "금호석유화학",
    "CJ Group": "CJ그룹",
    "Lotte Group": "롯데그룹",
    "Shinsegae I&C": "신세계아이앤씨",
    "Shinsegae Food": "신세계푸드",
    "AMOREPACIFIC": "아모레퍼시픽",
    "Celltrion": "셀트리온",
    "Doosan": "두산",
    "Hankook Tire": "한국타이어",
    "Korean Air": "대한항공",
    "Asiana Airlines": "아시아나항공",
    "KT Group": "KT그룹",
    "kt cloud": "케이티클라우드",
    "KB Financial Group": "KB금융그룹",
    "KB Kookmin Bank": "KB국민은행",
    "Shinhan Bank": "신한은행",
    "Shinhan Securities": "신한투자증권",
    "Hana TI": "하나금융티아이",
    "Woori Financial Group": "우리금융그룹",
    "Woori Bank": "우리은행",
    "Hana Bank": "하나은행",
    "IBK Industrial Bank of Korea": "IBK기업은행",
    "NH NongHyup Bank": "NH농협은행",
    "KDB Korea Development Bank": "KDB산업은행",
    "Korea Eximbank": "한국수출입은행",
    "Sh Suhyup Bank": "Sh수협은행",
    "BNK Busan Bank": "BNK부산은행",
    "BNK Kyongnam Bank": "BNK경남은행",
    "Kwangju Bank": "광주은행",
    "Jeonbuk Bank": "전북은행",
    "Jeju Bank": "제주은행",
    "KakaoBank": "카카오뱅크",
    "Kbank": "케이뱅크",
    "Toss Bank": "토스뱅크",
    "SC First Bank Korea": "SC제일은행",
    "Citi Korea": "한국씨티은행",
    "Mirae Asset Securities": "미래에셋증권",
    "NH Investment & Securities": "NH투자증권",
    "Korea Investment Securities": "한국투자증권",
    "Samsung Securities": "삼성증권",
    "KB Securities": "KB증권",
    "Hana Securities": "하나증권",
    "Kiwoom Securities": "키움증권",
    "Daishin Securities": "대신증권",
    "Meritz Securities": "메리츠증권",
    "Hanwha Investment & Securities": "한화투자증권",
    "Yuanta Securities Korea": "유안타증권",
    "LS Securities": "LS증권",
    "SK Securities": "SK증권",
    "IBK Securities": "IBK투자증권",
    "BNK Securities": "BNK투자증권",
    "Kakao Pay Securities": "카카오페이증권",
    "Toss Securities": "토스증권",
    "Eugene Investment & Securities": "유진투자증권",
    "Hyundai Motor Securities": "현대차증권",
    "Kyobo Securities": "교보증권",
    "Shinyoung Securities": "신영증권",
    "iM Securities": "iM증권",
    "Cape Investment & Securities": "케이프투자증권",
    "Hyundai E&C": "현대건설",
    "Hyundai Engineering": "현대엔지니어링",
    "DL E&C": "DL이앤씨",
    "Daewoo E&C": "대우건설",
    "SK ecoplant": "SK에코플랜트",
    "POSCO E&C": "포스코이앤씨",
    "Lotte E&C": "롯데건설",
    "HDC Hyundai Development Company": "HDC현대산업개발",
    "Kolon Global": "코오롱글로벌",
    "Hanwha Construction": "한화 건설부문",
    "Hoban Construction": "호반건설",
    "KCC Construction": "KCC건설",
    "SK hynix": "SK하이닉스",
    "LG Energy Solution": "LG에너지솔루션",
    "Samsung SDI": "삼성SDI",
    "Hanwha Aerospace": "한화에어로스페이스",
    "Hyundai Rotem": "현대로템",
    "Hyundai Steel": "현대제철",
    "Hyundai Glovis": "현대글로비스",
    "LS ELECTRIC": "LS일렉트릭",
    "LS Cable & System": "LS전선",
    "Hyosung Group": "효성그룹",
    "Doosan Enerbility": "두산에너빌리티",
}

JOB_CONTEXT_KEYWORDS = [
    "engineer",
    "developer",
    "software",
    "engineering",
    "개발자",
    "개발",
    "정규직",
    "계약직",
    "인턴",
    "경력",
    "신입",
    "모집",
    "채용",
]

PAGE_JOB_CONTEXT_KEYWORDS = [
    "정규직",
    "계약직",
    "인턴",
    "경력",
    "신입",
    "모집",
    "채용 완료",
    "지원기간",
    "application period",
]

COMPANIES = [
    # Major groups and tech platforms
    {
        "name": "Samsung Careers",
        "urls": ["https://www.samsungcareers.com/"],
    },
    {
        "name": "LG Careers",
        "urls": ["https://careers.lg.com/", "https://recruit.lg.com/"],
    },
    {
        "name": "SK Careers",
        "urls": ["https://www.skcareers.com/"],
    },
    {
        "name": "Hyundai Motor",
        "urls": ["https://talent.hyundai.com/", "https://talent.hyundai.com/apply/applyList.hc"],
    },
    {
        "name": "Kia",
        "urls": ["https://career.kia.com/job/jobs.kc"],
    },
    {
        "name": "Hyundai Mobis",
        "urls": ["https://careers.mobis.com/", "https://www.mobis.com/kr/aboutus/careers.do"],
    },
    {
        "name": "NAVER Careers",
        "urls": ["https://recruit.navercorp.com/", "https://recruit.navercorp.com/rcrt/list.do"],
    },
    {
        "name": "Kakao Careers",
        "urls": ["https://careers.kakao.com/jobs"],
    },
    {
        "name": "Coupang",
        "urls": ["https://www.coupang.jobs/kr/jobs/"],
    },
    {
        "name": "LINE Careers",
        "urls": ["https://careers.linecorp.com/jobs"],
    },
    {
        "name": "Toss Careers",
        "urls": ["https://toss.im/career/jobs"],
    },
    {
        "name": "Woowa Brothers",
        "urls": ["https://career.woowahan.com/jobs"],
    },
    {
        "name": "Daangn",
        "urls": ["https://team.daangn.com/jobs/"],
    },
    {
        "name": "Bucketplace",
        "urls": ["https://www.bucketplace.com/careers/"],
    },
    {
        "name": "Zigbang",
        "urls": ["https://career.zigbang.com/"],
    },
    {
        "name": "Yanolja",
        "urls": ["https://careers.yanolja.co/"],
    },
    {
        "name": "KRAFTON",
        "urls": ["https://krafton.com/careers/jobs/"],
    },
    {
        "name": "Nexon",
        "urls": ["https://careers.nexon.com/"],
    },
    {
        "name": "NCSoft",
        "urls": ["https://careers.ncsoft.com/", "https://m-careers.ncsoft.com/"],
    },
    {
        "name": "Netmarble",
        "urls": ["https://company.netmarble.com/rem/www/ko/recruit/recruitList"],
    },
    {
        "name": "Dunamu",
        "urls": ["https://www.dunamu.com/careers/jobs"],
    },
    {
        "name": "MUSINSA",
        "urls": ["https://www.musinsacareers.com/ko/home"],
    },
    # Refinery, energy, chemical, materials
    {
        "name": "GS Group",
        "urls": ["https://www.gs.co.kr/ko/career"],
    },
    {
        "name": "GS Caltex",
        "urls": ["https://recruit.gscaltex.com/"],
    },
    {
        "name": "GS EPS",
        "urls": ["https://gseps.recruiter.co.kr/", "https://www.gseps.com/contents.php?pno=146%3Fmid%3D24"],
    },
    {
        "name": "GS Retail",
        "urls": ["https://gsretail.recruiter.co.kr/career/home", "https://gsretail.recruiter.co.kr/career/job"],
    },
    {
        "name": "GS E&C",
        "urls": ["https://gsenc.recruiter.co.kr/career/home"],
    },
    {
        "name": "S-OIL",
        "urls": ["https://s-oil.recruiter.co.kr/career/home"],
    },
    {
        "name": "HD Hyundai",
        "urls": ["https://recruit.hd.com/en"],
    },
    {
        "name": "E1",
        "urls": ["https://e1.recruiter.co.kr/career/home", "https://e1.co.kr/ko/recruit/jobPostings"],
    },
    {
        "name": "POSCO",
        "urls": ["https://recruit.posco.com/"],
    },
    {
        "name": "Hanwha",
        "urls": ["https://www.hanwhain.com/", "https://www.hanwha.com/careers.do"],
    },
    {
        "name": "LS Group",
        "urls": ["https://www.lsholdings.com/ko/careers/recruitment-guide", "https://careers.lscablebiz.com/?locale=ko_KR"],
    },
    {
        "name": "LX Group",
        "urls": ["https://apply.lxcareers.com/", "https://apply.lxcareers.com/app/job/RetrieveJobNotices.rpi"],
    },
    {
        "name": "Kumho Petrochemical",
        "urls": ["https://recruit.kkpc.com/kkpcn.html", "https://recruit.kkpc.com/main/recruit/27_4/menu2_6.jsp"],
    },
    # Consumer, retail, logistics, manufacturing
    {
        "name": "CJ Group",
        "urls": ["https://recruit.cj.net/"],
    },
    {
        "name": "Lotte Group",
        "urls": ["https://recruit.lotte.co.kr/"],
    },
    {
        "name": "Shinsegae I&C",
        "urls": ["https://shinsegaeinc.recruiter.co.kr/career/home"],
    },
    {
        "name": "Shinsegae Food",
        "urls": ["https://www.shinsegaefood.com/recruit/notice_list.sf"],
    },
    {
        "name": "AMOREPACIFIC",
        "urls": ["https://careers.apgroup.com/", "https://careers.apgroup.com/search/"],
    },
    {
        "name": "Celltrion",
        "urls": ["https://recruit.celltrion.com/celltrion.html", "https://www.celltrion.com/en-us/careers/recruit/job"],
    },
    {
        "name": "Doosan",
        "urls": ["https://career.doosan.com/", "https://jobs.doosan.com/"],
    },
    {
        "name": "Hankook Tire",
        "urls": ["https://hankooktire.recruiter.co.kr/career/home", "https://www.hankooktire.com/kr/ko/company/career.html"],
    },
    {
        "name": "Korean Air",
        "urls": ["https://koreanair.recruiter.co.kr/career/home", "https://koreanair.recruiter.co.kr/career/apply"],
    },
    {
        "name": "Asiana Airlines",
        "urls": ["https://flyasiana.com/C/KR/KO/contents/cm201803220000730526"],
    },
    {
        "name": "KT Group",
        "urls": ["https://recruit.kt.com/", "https://recruit.kt.com/careers"],
    },
    {
        "name": "kt cloud",
        "urls": ["https://career.ktcloud.com/"],
    },
    {
        "name": "KT&G",
        "urls": ["https://www.ktng.com/career/recruit", "https://ktng.recruiter.co.kr/career/job"],
    },
    # Finance and financial tech employers with official hiring pages
    {
        "name": "KB Financial Group",
        "urls": ["https://careers.kbfg.com/"],
    },
    {
        "name": "KB Kookmin Bank",
        "urls": ["https://jobs.kbstar.com/?locale=ko_KR", "https://kbstar.careerlink.kr/"],
    },
    {
        "name": "Shinhan Bank",
        "urls": ["https://shinhan.recruiter.co.kr/career/jobs"],
    },
    {
        "name": "Shinhan Securities",
        "urls": ["https://recruit.shinhaninvest.com/"],
    },
    {
        "name": "Hana TI",
        "urls": ["https://hit.hanati.co.kr/en/career/recruitment"],
    },
    {
        "name": "Woori Investment Securities",
        "urls": ["https://www.wooriib.com/ir/en/employ/process.do"],
    },
    # Banks, internet banks, regional banks, and policy banks
    {
        "name": "Woori Financial Group",
        "urls": ["https://www.woorifg.com/kor/recruit/recruit-announcement/list.do"],
    },
    {
        "name": "Woori Bank",
        "urls": ["https://jrs.jobkorea.co.kr/wooribank", "https://recruit.incruit.com/wooribank/"],
    },
    {
        "name": "Hana Bank",
        "urls": ["https://hanabank.recruiter.co.kr/career/home", "https://hanabank.incruit.com/"],
    },
    {
        "name": "IBK Industrial Bank of Korea",
        "urls": ["https://ibk.incruit.com/"],
    },
    {
        "name": "NH NongHyup Bank",
        "urls": ["https://with.nonghyup.com/main.do", "https://jrs.jobkorea.co.kr/nhbank"],
    },
    {
        "name": "KDB Korea Development Bank",
        "urls": ["https://recruit.kdb.co.kr/", "https://kdb.incruit.com/hire/hirelist.asp"],
    },
    {
        "name": "Korea Eximbank",
        "urls": ["https://koreaexim.incruit.com/"],
    },
    {
        "name": "Sh Suhyup Bank",
        "urls": ["https://shbank.incruit.com/", "https://www.suhyup-bank.com/ib20/mnu/PBM01055"],
    },
    {
        "name": "BNK Busan Bank",
        "urls": ["https://busanbank.recruiter.co.kr/career/home", "https://www.busanbank.co.kr/ib20/mnu/BHPBKI443006001"],
    },
    {
        "name": "BNK Kyongnam Bank",
        "urls": ["https://knbank.recruiter.co.kr/career/home"],
    },
    {
        "name": "iM Bank",
        "urls": ["https://im.recruiter.co.kr/career/home"],
    },
    {
        "name": "Kwangju Bank",
        "urls": ["https://www.kjbank.com/ib20/mnu/BHPBKIF070200"],
    },
    {
        "name": "Jeonbuk Bank",
        "urls": ["https://jbbank.recruiter.co.kr/career/home"],
    },
    {
        "name": "Jeju Bank",
        "urls": ["https://jejubank.recruiter.co.kr/career/home"],
    },
    {
        "name": "KakaoBank",
        "urls": ["https://recruit.kakaobank.com/", "https://recruit.kakaobank.com/jobs"],
    },
    {
        "name": "Kbank",
        "urls": ["https://recruit.kbanknow.com/", "https://recruit.kbanknow.com/Recruit"],
    },
    {
        "name": "Toss Bank",
        "urls": ["https://toss.im/career/community/tossbank", "https://toss.im/career/jobs"],
    },
    {
        "name": "SC First Bank Korea",
        "urls": ["https://www.standardchartered.co.kr/np/kr/cms/cm/bi/RegularAdoption.jsp?menuId=HT02040200000000", "https://jobs.standardchartered.com/?locale=ko_KR"],
    },
    {
        "name": "Citi Korea",
        "urls": ["https://www.citibank.co.kr/HrdEmruCnts0102.act", "https://jobs.citi.com/location/south-korea-jobs/287/1835841/2"],
    },
    # Securities and investment firms
    {
        "name": "Mirae Asset Securities",
        "urls": ["https://career.miraeasset.com/"],
    },
    {
        "name": "NH Investment & Securities",
        "urls": ["https://nhqv.recruiter.co.kr/career/home", "https://nhqv.recruiter.co.kr/career/job"],
    },
    {
        "name": "Korea Investment Securities",
        "urls": ["https://recruit.truefriend.com/announcementList"],
    },
    {
        "name": "Samsung Securities",
        "urls": ["https://www.samsungcareers.com/subsid/detail/E40", "https://www.samsungsecurities.co.kr/kor/recruit/new_employee.do"],
    },
    {
        "name": "KB Securities",
        "urls": ["https://kbsec.career.greetinghr.com/ko/home", "https://careers.kbfg.com/"],
    },
    {
        "name": "Hana Securities",
        "urls": ["https://hanaw-recruit.com/"],
    },
    {
        "name": "Kiwoom Securities",
        "urls": ["https://www.kiwoom.com/h/ir/recruit/VJobOpeningView"],
    },
    {
        "name": "Daishin Securities",
        "urls": ["https://company.daishin.com/E5/MBoard/PType_Basic/Recruiting_Info/DW_Basic_List.aspx?boardseq=263"],
    },
    {
        "name": "Meritz Securities",
        "urls": ["https://imeritz.careerlink.kr/"],
    },
    {
        "name": "Hanwha Investment & Securities",
        "urls": ["https://recruit-hanwhawm.com/", "https://www.hanwhawm.com/main/main/index.cmd"],
    },
    {
        "name": "Yuanta Securities Korea",
        "urls": ["https://www.yuantakorea.com/", "https://www.yuantakorea.com/company/ko_outline.html"],
    },
    {
        "name": "LS Securities",
        "urls": ["https://ls-sec.recruiter.co.kr/app/jobnotice/list", "https://ir.ls-sec.co.kr/companykor/recruit/guide.jsp?board_no=160"],
    },
    {
        "name": "SK Securities",
        "urls": ["https://sks.recruiter.co.kr/"],
    },
    {
        "name": "IBK Securities",
        "urls": ["https://dware.intojob.co.kr/ibks.html", "https://recruit.ibks.com/cv/announces/ibks"],
    },
    {
        "name": "BNK Securities",
        "urls": ["https://careers.bnkfn.co.kr/ko/home", "https://careers.bnkfn.co.kr/ko/career"],
    },
    {
        "name": "Kakao Pay Securities",
        "urls": ["https://career.kakaopaysec.com/", "https://career.kakaopaysec.com/job_posting"],
    },
    {
        "name": "Toss Securities",
        "urls": ["https://toss.im/career/community/tosssecurities", "https://toss.im/career/jobs"],
    },
    {
        "name": "Eugene Investment & Securities",
        "urls": ["https://m.eugenefn.com/ci42r.do"],
    },
    {
        "name": "Hyundai Motor Securities",
        "urls": ["https://www.hmsec.com/company/main.do"],
    },
    {
        "name": "Kyobo Securities",
        "urls": ["https://recruit.iprovest.com/?page_id=7764"],
    },
    {
        "name": "Shinyoung Securities",
        "urls": ["https://shinrecruit.shinyoung.com/"],
    },
    {
        "name": "iM Securities",
        "urls": ["https://www.imfnsec.com/company_info/ci.jsp"],
    },
    {
        "name": "Cape Investment & Securities",
        "urls": ["https://www.capefn.com/jsp/web/ir/index.jsp"],
    },
    # Construction and engineering
    {
        "name": "Hyundai E&C",
        "urls": ["https://recruit.hdec.co.kr/"],
    },
    {
        "name": "Hyundai Engineering",
        "urls": ["https://m.hec.co.kr/ko/recruit/announcement", "https://hec.recruiter.co.kr/career/home"],
    },
    {
        "name": "DL E&C",
        "urls": ["https://www.dlenc.co.kr/careers/job/Recruit.do"],
    },
    {
        "name": "Daewoo E&C",
        "urls": ["https://recruit.daewooenc.com/"],
    },
    {
        "name": "SK ecoplant",
        "urls": ["https://recruit-skecoplant.com/"],
    },
    {
        "name": "POSCO E&C",
        "urls": ["https://poscoenc.careerlink.kr/", "https://www.poscoenc.com/ko/career/job_opening_list.aspx"],
    },
    {
        "name": "Lotte E&C",
        "urls": ["https://career.lottecon.co.kr/career/list", "https://mrecruit.lotte.co.kr/apply/announcement"],
    },
    {
        "name": "HDC Hyundai Development Company",
        "urls": ["https://recruit.incruit.com/hdc-dvp/job/", "https://www.hdc-dvp.com/mobile/recruitment/information.do"],
    },
    {
        "name": "Kolon Global",
        "urls": ["https://dream.kolon.com/", "https://www.kolonglobal.com/sub/recruitment01.php"],
    },
    {
        "name": "Hanwha Construction",
        "urls": ["https://recruit.hwenc.com", "https://m.hwenc.co.kr/recruit/notice/info.do"],
    },
    {
        "name": "Hoban Construction",
        "urls": ["https://www.ihoban.co.kr/recruit/recruit/web"],
    },
    {
        "name": "KCC Construction",
        "urls": ["https://www.kccworld.net/recruit/people.do"],
    },
    # Manufacturing, defense, logistics, and heavy industry
    {
        "name": "SK hynix",
        "urls": ["https://www.skhynix.com/careers/UI-FR-CR03/"],
    },
    {
        "name": "LG Energy Solution",
        "urls": ["https://www.lgensol.com/mobile/en/career/career-recruit-overseas", "https://careers.lg.com/"],
    },
    {
        "name": "Samsung SDI",
        "urls": ["https://www.samsungsdi.co.kr/career/employment-procedure.html", "https://www.samsungcareers.com/"],
    },
    {
        "name": "Hanwha Aerospace",
        "urls": ["https://m.hanwhaaerospace.com/eng/careers/recruit.do", "https://www.hanwhain.com/"],
    },
    {
        "name": "LIG Nex1 / Defense & Aerospace",
        "urls": ["https://ligdna.recruiter.co.kr/", "https://www.ligdefenseaerospace.com/people/jobsemp.do"],
    },
    {
        "name": "Hyundai Rotem",
        "urls": ["https://hyundai-rotem.recruiter.co.kr/career/home"],
    },
    {
        "name": "Hyundai Steel",
        "urls": ["https://hyundai-steel.recruiter.co.kr/career/home"],
    },
    {
        "name": "Hyundai Glovis",
        "urls": ["https://glovis.recruiter.co.kr/career/home"],
    },
    {
        "name": "LS ELECTRIC",
        "urls": ["https://lselectric.recruiter.co.kr/career/home", "https://www.ls-electric.com/ko/recruit/"],
    },
    {
        "name": "LS Cable & System",
        "urls": ["https://careers.lscablebiz.com/"],
    },
    {
        "name": "Hyosung Group",
        "urls": ["https://hyosung.recruiter.co.kr/"],
    },
    {
        "name": "Doosan Enerbility",
        "urls": ["https://career.doosan.com/dsp/sa/RecList.jsp", "https://www.doosanenerbility.com/kr/employment/recruitment"],
    },
]


@dataclass
class FetchStatus:
    company: str
    url: str
    ok: bool
    detail: str


@dataclass
class JobHit:
    company: str
    title: str
    url: str
    keyword: str
    category: str
    source_url: str
    snippet: str = ""
    deadline: str = ""
    match_basis: str = "공고명/목록"
    tech_stacks: list[str] = field(default_factory=list)


class LinkAndTextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.text_parts: list[str] = []
        self.links: list[dict[str, str]] = []
        self._active_links: list[dict[str, list[str] | str]] = []
        self.title_parts: list[str] = []
        self._in_title = False
        self._skip_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() in {"script", "style", "noscript", "template"}:
            self._skip_depth += 1
            return
        attrs_map = {key.lower(): value for key, value in attrs if value}
        if tag.lower() == "a" and attrs_map.get("href"):
            self._active_links.append({"href": attrs_map["href"], "parts": []})
        if tag.lower() == "title":
            self._in_title = True

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() in {"script", "style", "noscript", "template"} and self._skip_depth:
            self._skip_depth -= 1
            return
        if tag.lower() == "a" and self._active_links:
            link = self._active_links.pop()
            text = normalize_ws(" ".join(link["parts"]))  # type: ignore[arg-type]
            if text:
                self.links.append({"href": str(link["href"]), "text": text})
        if tag.lower() == "title":
            self._in_title = False

    def handle_data(self, data: str) -> None:
        if self._skip_depth:
            return
        if not data or not data.strip():
            return
        self.text_parts.append(data)
        if self._in_title:
            self.title_parts.append(data)
        for link in self._active_links:
            link["parts"].append(data)  # type: ignore[index,union-attr]

    @property
    def text(self) -> str:
        return normalize_ws(" ".join(self.text_parts))

    @property
    def title(self) -> str:
        return normalize_ws(" ".join(self.title_parts))


def normalize_ws(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def strip_html(value: str) -> str:
    without_scripts = re.sub(r"<(script|style|noscript|template)\b[^>]*>.*?</\1>", " ", value, flags=re.IGNORECASE | re.DOTALL)
    without_tags = re.sub(r"<[^>]+>", " ", without_scripts)
    return normalize_ws(html_utils.unescape(without_tags))


def find_tech_stacks(text: str) -> list[str]:
    stacks = [name for name, pattern in TECH_STACK_PATTERNS if re.search(pattern, text, re.IGNORECASE)]
    if "Next.js" not in stacks and re.search(r"(?<![\w])Next(?![\w])", text):
        stacks.append("Next.js")
    return stacks


def is_frontend_stack_match(title: str, detail_text: str, stacks: list[str]) -> bool:
    title_lower = title.lower()
    if any(keyword.lower() in title_lower for keyword in NON_FRONTEND_TITLE_KEYWORDS):
        return False
    if STRONG_FRONTEND_STACKS.intersection(stacks):
        return True
    combined = " ".join([title, detail_text])
    combined_lower = combined.lower()
    if any(keyword.lower() in title_lower for keyword in FRONTEND_CONTEXT_KEYWORDS):
        return True
    for stack in stacks:
        for match in re.finditer(re.escape(stack), combined, re.IGNORECASE):
            context = combined_lower[max(0, match.start() - 180) : match.end() + 180]
            if any(keyword.lower() in context for keyword in FRONTEND_CONTEXT_KEYWORDS):
                return True
    return False


def display_company_name(name: str) -> str:
    return COMPANY_KO_NAMES.get(name, name)


def looks_like_role_title(text: str) -> bool:
    lower = text.lower()
    return any(keyword.lower() in lower for keyword in ROLE_TITLE_KEYWORDS)


def is_allowed_detail_url(source_url: str, detail_url: str) -> bool:
    source_host = (urllib.parse.urlparse(source_url).hostname or "").lower()
    detail_host = (urllib.parse.urlparse(detail_url).hostname or "").lower()
    if not source_host or not detail_host:
        return False
    if source_host == detail_host or source_host.endswith(f".{detail_host}") or detail_host.endswith(f".{source_host}"):
        return True
    approved_hints = ("recruit", "career", "jobs", "jobkorea", "greetinghr", "incruit")
    return any(hint in detail_host for hint in approved_hints)


def load_env(path: Path) -> dict[str, str]:
    env: dict[str, str] = {}
    if not path.exists():
        return env
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        env[key.strip()] = value.strip().strip('"').strip("'")
    return env


def fetch_url(url: str, timeout: int = 18) -> tuple[str, str]:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 job-monitor/1.0 (+official-career-page-check)",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.7,en;q=0.6",
            "Accept-Encoding": "identity",
        },
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        content_type = response.headers.get("content-type", "")
        charset = response.headers.get_content_charset() or "utf-8"
        body = response.read().decode(charset, errors="replace")
    return body, content_type


def find_keyword(text: str) -> str | None:
    lower = text.lower()
    for keyword in FRONTEND_KEYWORDS:
        if keyword.lower() in lower:
            return keyword
    return None


def find_match(text: str) -> tuple[str, str] | None:
    lower = text.lower()
    for keyword in DIRECT_FRONTEND_KEYWORDS:
        if keyword.lower() in lower:
            return keyword, "직접 프론트엔드"
    stacks = find_tech_stacks(text)
    if stacks and is_frontend_stack_match(text, "", stacks):
        return stacks[0], "기술스택 일치"
    for keyword in RELATED_TECH_KEYWORDS:
        if keyword.lower() in lower:
            return keyword, "웹/디지털 관련"
    return None


def snippet_for(text: str, keyword: str, radius: int = 80) -> str:
    lower = text.lower()
    index = lower.find(keyword.lower())
    if index < 0:
        return ""
    start = max(index - radius, 0)
    end = min(index + len(keyword) + radius, len(text))
    prefix = "..." if start > 0 else ""
    suffix = "..." if end < len(text) else ""
    return prefix + text[start:end].strip() + suffix


def extract_deadline(text: str) -> str:
    compact = normalize_ws(text)
    if not compact:
        return ""

    permanent_status_patterns = [
        r"상시\s*채용",
        r"채용\s*시\s*마감",
        r"채용시\s*마감",
        r"수시\s*채용",
    ]
    for pattern in permanent_status_patterns:
        match = re.search(pattern, compact, re.IGNORECASE)
        if match:
            return normalize_ws(match.group(0))

    date = r"(?:20\d{2}[.\-/년]\s*)?\d{1,2}[.\-/월]\s*\d{1,2}(?:일)?(?:\s*\([^)]+\))?(?:\s*\d{1,2}:\d{2})?"
    range_match = re.search(rf"{date}\s*(?:~|–|-|부터)\s*{date}", compact)
    if range_match:
        return normalize_ws(range_match.group(0))

    until_match = re.search(rf"(?:~|마감일|접수마감|접수기간|기간)\s*[:：]?\s*{date}", compact)
    if until_match:
        return normalize_ws(until_match.group(0))

    status_patterns = [
        r"D\s*-\s*\d+",
        r"D\s*day",
        r"D\s*-\s*day",
        r"오늘\s*마감",
        r"접수\s*중",
        r"진행\s*중",
        r"모집\s*중",
        r"접수\s*마감",
        r"마감",
    ]
    for pattern in status_patterns:
        match = re.search(pattern, compact, re.IGNORECASE)
        if match:
            return normalize_ws(match.group(0))

    return ""


def normalize_date_value(value: object) -> str:
    if value is None:
        return ""
    text = normalize_ws(str(value))
    if not text:
        return ""
    date_match = re.search(r"20\d{2}-\d{1,2}-\d{1,2}(?:[T ]\d{1,2}:\d{2}(?::\d{2})?)?", text)
    if date_match:
        return date_match.group(0).replace("T", " ")
    return extract_deadline(text)


def iter_json_values(value: object):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from iter_json_values(child)
    elif isinstance(value, list):
        for child in value:
            yield from iter_json_values(child)


def iter_text_values(value: object):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for child in value.values():
            yield from iter_text_values(child)
    elif isinstance(value, list):
        for child in value:
            yield from iter_text_values(child)


def extract_job_text_from_json(value: object) -> str:
    job_text_keys = {
        "description",
        "jobdescription",
        "responsibilities",
        "qualifications",
        "skills",
        "techstack",
        "requirements",
        "preferredqualifications",
        "experienceRequirements".lower(),
    }
    parts: list[str] = []
    for item in iter_json_values(value):
        for key, child in item.items():
            normalized_key = re.sub(r"[^a-z]", "", str(key).lower())
            if normalized_key not in job_text_keys:
                continue
            parts.extend(str(text) for text in iter_text_values(child))
    return normalize_ws(" ".join(parts))[:200000]


def extract_job_detail_text(raw_html: str) -> str:
    parser = LinkAndTextParser()
    parser.feed(raw_html)
    parts = [parser.text]
    script_pattern = r"<script(?P<attrs>[^>]*)>(?P<body>.*?)</script>"
    for match in re.finditer(script_pattern, raw_html, flags=re.IGNORECASE | re.DOTALL):
        attrs = match.group("attrs")
        if not re.search(r"application/(?:ld\+)?json", attrs, re.IGNORECASE) and not re.search(
            r"id=[\"']__NEXT_DATA__[\"']", attrs, re.IGNORECASE
        ):
            continue
        try:
            parsed = json.loads(html_utils.unescape(match.group("body").strip()))
        except json.JSONDecodeError:
            continue
        structured_text = extract_job_text_from_json(parsed)
        if structured_text:
            parts.append(structured_text)
    return normalize_ws(" ".join(parts))


def extract_deadline_from_json(value: object) -> str:
    deadline_keys = {
        "validThrough",
        "valid_through",
        "deadline",
        "deadlineAt",
        "deadlineDate",
        "closeAt",
        "closedAt",
        "closingDate",
        "endDate",
        "dueDate",
        "expiresAt",
        "expirationDate",
        "recruitEndDate",
        "applyEndDate",
        "applicationEndDate",
        "receiptEndDate",
    }
    status_keys = {"employmentType", "jobStatus", "status", "recruitType"}
    for item in iter_json_values(value):
        for key in deadline_keys:
            if key in item:
                normalized = normalize_date_value(item.get(key))
                if normalized:
                    return f"마감일 {normalized}"
        for key in status_keys:
            if key in item:
                normalized = extract_deadline(str(item.get(key)))
                if normalized:
                    return normalized
    return ""


def extract_deadline_from_html_data(raw_html: str) -> str:
    for match in re.finditer(
        r"<script[^>]+type=[\"']application/ld\+json[\"'][^>]*>(.*?)</script>",
        raw_html,
        flags=re.IGNORECASE | re.DOTALL,
    ):
        data = html_utils.unescape(match.group(1).strip())
        try:
            parsed = json.loads(data)
        except json.JSONDecodeError:
            continue
        deadline = extract_deadline_from_json(parsed)
        if deadline:
            return deadline

    key_pattern = (
        r"(validThrough|deadline|deadlineAt|deadlineDate|closeAt|closingDate|endDate|dueDate|"
        r"expiresAt|expirationDate|recruitEndDate|applyEndDate|applicationEndDate|receiptEndDate)"
    )
    date_pattern = r"20\d{2}[-./]\d{1,2}[-./]\d{1,2}(?:[T ]\d{1,2}:\d{2}(?::\d{2})?)?"
    regex = rf"[\"']{key_pattern}[\"']\s*:\s*[\"']({date_pattern})[\"']"
    match = re.search(regex, raw_html, flags=re.IGNORECASE)
    if match:
        return f"마감일 {match.group(2).replace('T', ' ')}"

    return ""


def context_for_href(raw_html: str, href: str, radius: int = 900) -> str:
    if not href:
        return ""
    candidates = [href, html_utils.escape(href, quote=True), html_utils.escape(href, quote=False)]
    indices = [raw_html.find(candidate) for candidate in candidates if raw_html.find(candidate) >= 0]
    if not indices:
        return ""
    index = min(indices)
    start = max(0, index - radius)
    end = min(len(raw_html), index + radius)
    return strip_html(raw_html[start:end])


def extract_deadline_near_keyword(text: str, keyword: str) -> str:
    local = snippet_for(text, keyword, radius=220)
    return extract_deadline(local) or extract_deadline(text[:5000])


def enrich_hit(hit: JobHit) -> JobHit | None:
    deadline = extract_deadline(" ".join([hit.title, hit.snippet]))
    detail_failed = False
    detail_text = ""
    parsed = urllib.parse.urlparse(hit.url)
    if parsed.scheme in {"http", "https"}:
        try:
            html, _ = fetch_url(hit.url, timeout=12)
            deadline = deadline or extract_deadline_from_html_data(html)
            detail_text = extract_job_detail_text(html)
        except Exception:
            detail_failed = True

    if hit.category == "기술스택 후보":
        stacks = find_tech_stacks(detail_text)
        if not stacks or not is_frontend_stack_match(hit.title, detail_text, stacks):
            return None
        hit.category = "기술스택 일치"
        hit.keyword = ", ".join(stacks)
        hit.tech_stacks = stacks
        hit.match_basis = "상세 공고 기술스택"
        hit.snippet = snippet_for(detail_text, stacks[0], radius=110)
    else:
        stacks = find_tech_stacks(" ".join([hit.title, hit.snippet, detail_text]))
        hit.tech_stacks = stacks
        if hit.category == "기술스택 일치":
            hit.keyword = ", ".join(stacks) or hit.keyword
            hit.match_basis = "공고명 기술스택"

    deadline_keyword = hit.tech_stacks[0] if hit.tech_stacks else hit.keyword
    if detail_text:
        deadline = deadline or extract_deadline_near_keyword(detail_text, deadline_keyword)
    if deadline:
        hit.deadline = deadline
    elif detail_failed:
        hit.deadline = "공식 목록 미표기 / 상세 확인 실패"
    else:
        hit.deadline = "공식 페이지 미표기"
    return hit


def looks_like_job_context(text: str) -> bool:
    lower = text.lower()
    return any(keyword.lower() in lower for keyword in JOB_CONTEXT_KEYWORDS)


def looks_like_page_job_context(text: str) -> bool:
    lower = text.lower()
    return any(keyword.lower() in lower for keyword in PAGE_JOB_CONTEXT_KEYWORDS)


def scan_company(company: dict[str, object]) -> tuple[list[JobHit], list[FetchStatus]]:
    hits: list[JobHit] = []
    statuses: list[FetchStatus] = []
    name = str(company["name"])
    for url in company["urls"]:  # type: ignore[index]
        source_url = str(url)
        try:
            html, content_type = fetch_url(source_url)
        except Exception as exc:
            statuses.append(FetchStatus(name, source_url, False, f"{type(exc).__name__}: {exc}"))
            continue

        parser = LinkAndTextParser()
        parser.feed(html)
        page_text = parser.text
        statuses.append(FetchStatus(name, source_url, True, content_type or "ok"))

        seen_on_page: set[tuple[str, str]] = set()
        for link in parser.links:
            href = link["href"].strip()
            if href.startswith(("#", "javascript:", "mailto:", "tel:")):
                continue
            absolute_url = urllib.parse.urljoin(source_url, href)
            match = find_match(link["text"])
            if match and not looks_like_job_context(link["text"]):
                continue
            if not match and not (looks_like_role_title(link["text"]) and looks_like_job_context(link["text"])):
                continue
            if not match and not is_allowed_detail_url(source_url, absolute_url):
                continue
            keyword, category = match or ("", "기술스택 후보")
            title = normalize_ws(link["text"])[:140]
            context = context_for_href(html, href)
            key = (title.lower(), absolute_url)
            if key in seen_on_page:
                continue
            seen_on_page.add(key)
            hits.append(
                JobHit(
                    company=name,
                    title=title,
                    url=absolute_url,
                    keyword=keyword,
                    category=category,
                    source_url=source_url,
                    deadline=extract_deadline(" ".join([link["text"], context])),
                    tech_stacks=find_tech_stacks(link["text"]),
                )
            )

        match = find_match(page_text)
        keyword = match[0] if match else None
        category = match[1] if match else ""
        page_snippet = snippet_for(page_text, keyword) if keyword else ""
        if keyword and not seen_on_page and looks_like_page_job_context(page_snippet):
            hits.append(
                JobHit(
                    company=name,
                    title=parser.title or f"{name} 채용 페이지 키워드 매칭",
                    url=source_url,
                    keyword=keyword,
                    category=category,
                    source_url=source_url,
                    snippet=page_snippet,
                    deadline=extract_deadline_from_html_data(html) or extract_deadline_near_keyword(page_text, keyword),
                    tech_stacks=find_tech_stacks(page_snippet),
                )
            )

    return hits, statuses


def dedupe_hits(hits: list[JobHit]) -> list[JobHit]:
    deduped: list[JobHit] = []
    seen: set[tuple[str, str, str]] = set()
    for hit in hits:
        key = (hit.company.lower(), hit.title.lower(), hit.url, hit.category)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(hit)
    with ThreadPoolExecutor(max_workers=8) as executor:
        enriched = [hit for hit in executor.map(enrich_hit, deduped) if hit is not None]
    category_order = {"직접 프론트엔드": 0, "기술스택 일치": 1, "웹/디지털 관련": 2}
    return sorted(
        enriched,
        key=lambda hit: (category_order.get(hit.category, 9), hit.company.lower(), hit.title.lower()),
    )


def kst_timezone():
    if ZoneInfo:
        try:
            return ZoneInfo("Asia/Seoul")
        except Exception:
            pass
    return timezone(timedelta(hours=9), name="KST")


def now_kst() -> datetime:
    return datetime.now(kst_timezone())


def next_run_at(now: datetime, hour: int = DEFAULT_SCHEDULE_HOUR, minute: int = DEFAULT_SCHEDULE_MINUTE) -> datetime:
    target = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if target <= now:
        target += timedelta(days=1)
    return target


def build_report(hits: list[JobHit], statuses: list[FetchStatus]) -> str:
    timestamp = now_kst().strftime("%Y-%m-%d %H:%M KST")
    ok_count = sum(1 for status in statuses if status.ok)
    fail_count = len(statuses) - ok_count
    lines = [
        f"프론트엔드 채용 리포트 ({timestamp})",
        f"공식 채용 페이지 확인: {ok_count}개 URL 성공, {fail_count}개 URL 실패",
        "",
    ]

    if hits:
        direct_count = sum(1 for hit in hits if hit.category == "직접 프론트엔드")
        stack_count = sum(1 for hit in hits if hit.category == "기술스택 일치")
        related_count = len(hits) - direct_count - stack_count
        lines.append(f"프론트엔드/웹·디지털 관련 공고·페이지 {len(hits)}건")
        lines.append(f"- 직접 프론트엔드: {direct_count}건")
        lines.append(f"- 프론트엔드 기술스택 일치: {stack_count}건")
        lines.append(f"- 웹/디지털 관련: {related_count}건")
        for index, hit in enumerate(hits[:35], start=1):
            lines.extend(
                [
                    "",
                    f"{index}. {display_company_name(hit.company)}",
                    f"분류: {hit.category}",
                    f"공고/페이지: {hit.title}",
                    f"마감/상태: {hit.deadline or '확인 불가'}",
                    f"매칭 키워드: {hit.keyword}",
                    f"매칭 근거: {hit.match_basis}",
                    f"URL: {hit.url}",
                ]
            )
            if hit.tech_stacks:
                lines.append(f"확인된 기술스택: {', '.join(hit.tech_stacks)}")
            if hit.snippet:
                lines.append(f"본문 근거: {hit.snippet[:220]}")
        if len(hits) > 35:
            lines.append(f"\n그 외 {len(hits) - 35}건은 생략했습니다.")
    else:
        lines.append("오늘은 프론트엔드 키워드와 직접 매칭되는 새 공고/페이지를 찾지 못했습니다.")

    checked_companies = sorted({display_company_name(status.company) for status in statuses if status.ok})
    if checked_companies:
        lines.extend(["", "확인한 공식 채용 사이트:", ", ".join(checked_companies)])

    failures = [status for status in statuses if not status.ok]
    if failures:
        lines.append("")
        lines.append("접근 실패 URL:")
        for status in failures[:12]:
            lines.append(f"- {display_company_name(status.company)}: {status.url} ({status.detail[:140]})")
        if len(failures) > 12:
            lines.append(f"- 그 외 {len(failures) - 12}개")

    return "\n".join(lines)


def telegram_request(token: str, method: str, payload: dict[str, object]) -> dict[str, object]:
    url = TELEGRAM_API.format(token=token, method=method)
    data = urllib.parse.urlencode(payload).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        try:
            return json.loads(body)
        except json.JSONDecodeError:
            return {"ok": False, "description": body}


def discover_channel_chat_id(token: str) -> str | None:
    url = TELEGRAM_API.format(token=token, method="getUpdates")
    try:
        with urllib.request.urlopen(url, timeout=20) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except Exception:
        return None

    for update in payload.get("result", []):
        for key in ("channel_post", "my_chat_member", "message"):
            item = update.get(key)
            chat = item.get("chat") if isinstance(item, dict) else None
            if not isinstance(chat, dict):
                continue
            title = str(chat.get("title", ""))
            chat_id = chat.get("id")
            if chat_id and (CHANNEL_TITLE in title or chat.get("type") == "channel"):
                return str(chat_id)
    return None


def split_message(text: str, max_len: int = 3900) -> list[str]:
    if len(text) <= max_len:
        return [text]
    chunks: list[str] = []
    current: list[str] = []
    current_len = 0
    for paragraph in text.split("\n\n"):
        paragraph_len = len(paragraph) + 2
        if current and current_len + paragraph_len > max_len:
            chunks.append("\n\n".join(current))
            current = []
            current_len = 0
        current.append(paragraph)
        current_len += paragraph_len
    if current:
        chunks.append("\n\n".join(current))
    return chunks


def send_telegram_report(token: str, chat_id: str, report: str) -> tuple[bool, str]:
    last_description = ""
    for chunk in split_message(report):
        response = telegram_request(
            token,
            "sendMessage",
            {
                "chat_id": chat_id,
                "text": chunk,
                "disable_web_page_preview": "true",
            },
        )
        if not response.get("ok"):
            last_description = str(response.get("description", "unknown telegram error"))
            return False, last_description
    return True, "sent"


def collect_report(max_companies: int | None = None) -> tuple[str, list[JobHit], list[FetchStatus]]:
    companies = COMPANIES[:max_companies] if max_companies else COMPANIES
    all_hits: list[JobHit] = []
    all_statuses: list[FetchStatus] = []
    for company in companies:
        hits, statuses = scan_company(company)
        all_hits.extend(hits)
        all_statuses.extend(statuses)
        time.sleep(0.25)
    hits = dedupe_hits(all_hits)
    return build_report(hits, all_statuses), hits, all_statuses


def run_report_once(max_companies: int | None = None, dry_run: bool = False) -> int:
    env = load_env(ENV_PATH)
    token = env.get("TELEGRAM_KEY") or os.environ.get("TELEGRAM_KEY")
    chat_id = env.get("TELEGRAM_CHAT_ID") or os.environ.get("TELEGRAM_CHAT_ID") or FALLBACK_CHAT_ID

    report, _, _ = collect_report(max_companies)
    print(report)

    if dry_run:
        return 0

    if not token:
        print("TELEGRAM_KEY가 .env 또는 환경 변수에 없습니다.", file=sys.stderr)
        return 2

    if not chat_id:
        chat_id = discover_channel_chat_id(token) or ""
    if not chat_id:
        print("TELEGRAM_CHAT_ID가 .env 또는 환경 변수에 없습니다.", file=sys.stderr)
        return 2

    ok, detail = send_telegram_report(token, chat_id, report)
    if ok:
        print(f"Telegram report sent to chat_id {chat_id}.")
        return 0

    discovered_id = discover_channel_chat_id(token)
    if discovered_id and discovered_id != chat_id:
        ok, retry_detail = send_telegram_report(token, discovered_id, report)
        if ok:
            print(f"Telegram report sent to discovered chat_id {discovered_id}.")
            print(f"Add TELEGRAM_CHAT_ID={discovered_id} to automation/.env.")
            return 0
        detail = retry_detail

    print(
        textwrap.dedent(
            f"""
            Telegram 전송 실패: {detail}
            봇이 채널 '{CHANNEL_TITLE}'에 관리자 또는 게시 가능한 멤버로 추가되어 있는지 확인해주세요.
            확인된 chat_id가 있으면 automation/.env에 TELEGRAM_CHAT_ID=<chat_id>를 추가해주세요.
            """
        ).strip(),
        file=sys.stderr,
    )
    return 3


def run_schedule(max_companies: int | None, run_on_start: bool, hour: int, minute: int) -> int:
    if not (0 <= hour <= 23 and 0 <= minute <= 59):
        print("--schedule-hour는 0-23, --schedule-minute은 0-59 범위여야 합니다.", file=sys.stderr)
        return 2

    if run_on_start:
        print("Running startup report before entering schedule loop.", flush=True)
        run_report_once(max_companies=max_companies, dry_run=False)

    while True:
        now = now_kst()
        target = next_run_at(now, hour, minute)
        wait_seconds = max(0.0, (target - now).total_seconds())
        print(f"Next report scheduled at {target.strftime('%Y-%m-%d %H:%M:%S KST')}.", flush=True)

        while wait_seconds > 0:
            chunk = min(wait_seconds, 3600)
            time.sleep(chunk)
            wait_seconds -= chunk

        run_report_once(max_companies=max_companies, dry_run=False)


def main() -> int:
    parser = argparse.ArgumentParser(description="Send official frontend job report to Telegram.")
    parser.add_argument("--dry-run", action="store_true", help="Print the report without sending Telegram.")
    parser.add_argument("--max-companies", type=int, default=None, help="Limit company count for a quick smoke test.")
    parser.add_argument("--schedule", action="store_true", help="Keep running and send the report once a day.")
    parser.add_argument("--run-on-start", action="store_true", help="Send once immediately before waiting for the schedule.")
    parser.add_argument("--schedule-hour", type=int, default=DEFAULT_SCHEDULE_HOUR, help="KST hour for scheduled reports.")
    parser.add_argument("--schedule-minute", type=int, default=DEFAULT_SCHEDULE_MINUTE, help="KST minute for scheduled reports.")
    args = parser.parse_args()

    if args.schedule:
        return run_schedule(
            max_companies=args.max_companies,
            run_on_start=args.run_on_start,
            hour=args.schedule_hour,
            minute=args.schedule_minute,
        )

    return run_report_once(max_companies=args.max_companies, dry_run=args.dry_run)


if __name__ == "__main__":
    raise SystemExit(main())
