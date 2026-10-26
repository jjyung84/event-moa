import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import xml.etree.ElementTree as ET
import json
import re
import hashlib
from datetime import datetime

events = []
seen_links = set()

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
    'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7'
}

# 제외할 키워드 (종료/무관 게시글 차단)
EXCLUDE_KEYWORDS = ["종료", "마감", "품절", "완료", "당첨자", "발표", "공지", "규정", "질문", "후기"]

# 🍯 알짜 이벤트 판별 키워드
HONEY_KEYWORDS = [
    "기프티콘", "스타벅스", "스벅", "편의점", "CU", "GS25", "세븐일레븐",
    "100%", "전원", "무료", "출석", "퀴즈", "선착순", "네이버페이", "네페",
    "상품권", "치킨", "커피", "아메리카노", "바나나우유", "포인트", "적립금", "0원"
]


def make_id(url):
    """URL 기반 고유 ID 생성 (재수집 시에도 참여완료/즐겨찾기 유지)"""
    return "evt_" + hashlib.md5(url.encode('utf-8')).hexdigest()[:10]


def is_expired_title(title):
    """제목에 포함된 날짜(~M/D, ~M.D)를 분석해 이미 지난 이벤트인지 판별"""
    if any(k in title for k in EXCLUDE_KEYWORDS):
        return True

    now = datetime.now()
    match = re.search(r'~\s*(\d{1,2})[./월]\s*(\d{1,2})', title)
    if match:
        month, day = int(match.group(1)), int(match.group(2))
        if 1 <= month <= 12 and 1 <= day <= 31:
            try:
                end_dt = datetime(now.year, month, day, 23, 59, 59)
                if end_dt < now and not (now.month == 12 and month <= 2):
                    return True
            except ValueError:
                pass
    return False


def extract_end_date(title):
    """제목에서 마감일 추출 (없으면 상시/본문참고 반환)"""
    now = datetime.now()
    match = re.search(r'~\s*(\d{1,2})[./월]\s*(\d{1,2})', title)
    if match:
        month, day = int(match.group(1)), int(match.group(2))
        if 1 <= month <= 12 and 1 <= day <= 31:
            year = now.year + 1 if (now.month == 12 and month <= 2) else now.year
            return f"{year}-{month:02d}-{day:02d}"
    return "상시/본문참고"


def classify_event(title):
    """카테고리, 난이도, 경품, 알짜 여부 자동 분석"""
    category = "기업/금융"
    if any(k in title for k in ["치킨", "커피", "피자", "버거", "스타벅스", "스벅", "투썸", "메가커피", "배민", "요기요", "식당", "음료"]):
        category = "식음료/외식"
    elif any(k in title for k in ["쿠폰", "할인", "마트", "편의점", "쇼핑", "네이버페이", "네페", "무신사", "올리브영", "티몬", "지마켓", "옥션", "11번가"]):
        category = "쇼핑/생활"
    elif any(k in title for k in ["공공", "시청", "구청", "공사", "재단", "정부", "지자체", "공모전", "서포터즈", "박물관", "도서관"]):
        category = "공공/공모전"
    elif any(k in title for k in ["게임", "스팀", "플스", "닌텐도", "스위치", "엔비디아", "인텔", "갤럭시", "아이폰", "앱"]):
        category = "IT/게임"

    difficulty = "하"
    if any(k in title for k in ["서포터즈", "공모전", "영상", "글짓기", "리뷰", "체험단"]):
        difficulty = "상"
    elif any(k in title for k in ["인스타", "팔로우", "소문내기", "공유", "댓글", "구독", "인증"]):
        difficulty = "중"

    prize = "본문 참고"
    for p in ["스타벅스", "네이버페이", "상품권", "기프티콘", "치킨", "커피", "아메리카노", "포인트", "쿠폰", "무료"]:
        if p in title:
            prize = p
            break

    is_honey = any(k.lower() in title.lower() for k in HONEY_KEYWORDS)
    return category, difficulty, prize, is_honey


def add_event(title, link, source):
    """중복 및 유효성 검사 후 리스트에 추가"""
    title = re.sub(r'\s+', ' ', title).strip()
    if len(title) < 5 or link in seen_links:
        return
    if is_expired_title(title):
        return

    seen_links.add(link)
    category, difficulty, prize, is_honey = classify_event(title)
    end_date = extract_end_date(title)

    events.append({
        "id": make_id(link),
        "title": title,
        "source": source,
        "category": category,
        "difficulty": difficulty,
        "prize": prize,
        "isHoney": is_honey,
        "endDate": end_date,
        "url": link,
        "createdAt": datetime.now().strftime("%Y-%m-%d %H:%M")
    })


def fetch_ppomppu():
    """1. 뽐뿌 쿠폰/이벤트 게시판 수집"""
    urls = [
        "https://www.ppomppu.co.kr/zboard/zboard.php?id=coupon",
        "https://www.ppomppu.co.kr/zboard/zboard.php?id=event"
    ]
    for url in urls:
        try:
            res = requests.get(url, headers={**headers, 'Referer': 'https://www.ppomppu.co.kr/'}, timeout=10)
            res.encoding = 'cp949'
            soup = BeautifulSoup(res.text, 'html.parser')
            posts = soup.select('tr.baseList, tr.list0, tr.list1')

            for post in posts:
                if post.select_one('del, s, strike'):
                    continue
                date_text = post.get_text()
                if re.search(r'\b(1\d|2[0-5])/\d{2}/\d{2}\b', date_text):
                    continue

                title_tag = post.select_one('a.baseList-title, td.list_title a, a.list_title')
                if not title_tag:
                    continue
                title = title_tag.get_text(strip=True)
                href = title_tag.get('href', '')
                if not href or href.startswith('javascript'):
                    continue

                link = urljoin(url, href)
                add_event(title, link, "뽐뿌")
        except Exception as e:
            print(f"❌ 뽐뿌 수집 오류: {e}")


def fetch_ruliweb():
    """2. 루리웹 핫딜/이벤트 게시판 수집"""
    url = "https://bbs.ruliweb.com/market/board/1020"
    try:
        res = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(res.text, 'html.parser')
        posts = soup.select('tr.table_body')

        for post in posts:
            if 'notice' in post.get('class', []):
                continue
            title_tag = post.select_one('a.deco, a.subject_link')
            if not title_tag:
                continue
            title = title_tag.get_text(strip=True)
            link = title_tag.get('href', '').split('?')[0]
            if link:
                add_event(title, link, "루리웹")
    except Exception as e:
        print(f"❌ 루리웹 수집 오류: {e}")


def fetch_clien():
    """3. 클리앙 알뜰구매/이벤트 게시판 수집"""
    url = "https://www.clien.net/service/board/jirum"
    try:
        res = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(res.text, 'html.parser')
        posts = soup.select('div.list_item.symph_row')

        for post in posts:
            if post.select_one('span.icon_info'):
                info_txt = post.select_one('span.icon_info').get_text(strip=True)
                if info_txt in ["품절", "종료"]:
                    continue

            title_tag = post.select_one('span.list_subject a, a.list_subject')
            if not title_tag:
                continue
            title = title_tag.get_text(strip=True)
            href = title_tag.get('href', '')
            if href:
                link = urljoin("https://www.clien.net", href.split('?')[0])
                add_event(title, link, "클리앙")
    except Exception as e:
        print(f"❌ 클리앙 수집 오류: {e}")


def fetch_coolenjoy():
    """4. 쿨엔조이 지름/알뜰정보 수집"""
    url = "https://coolenjoy.net/bbs/jirum"
    try:
        res = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(res.text, '
