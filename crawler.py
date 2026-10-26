import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
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

# 차단할 키워드 (1원 적립, 단순 출석, 단순 퀴즈 등 푼돈 이벤트 철저 차단)
EXCLUDE_KEYWORDS = [
    "종료", "마감", "품절", "완료", "당첨자", "발표", "공지", "규정", "질문", "후기", "삭제",
    "1원", "출석체크", "출첵", "룰렛", "티몬", "토스", "랜덤박스", "앱테크", "포인트적립"
]

# 🍯 경품·상품권 중심의 알짜 핵심 키워드 (이 중 하나라도 포함되어야 수집)
PRIZE_KEYWORDS = [
    "상품권", "기프티콘", "스타벅스", "스벅", "네이버페이", "네페", "신세계", "백화점", 
    "치킨", "피자", "버거", "커피", "아메리카노", "배달의민족", "배민", "요기요", 
    "올리브영", "문화상품권", "문상", "해피머니", "주유권", "경품", "추첨", "선착순", 
    "전원", "100%", "응모", "공모전", "체험단", "무료증정", "증정", "갤럭시", "아이폰"
]

def make_id(url):
    return "evt_" + hashlib.md5(url.encode('utf-8')).hexdigest()[:10]

def is_valid_prize_event(title, text_content=""):
    """푼돈 적립/출첵은 거르고, 확실한 경품/상품권 이벤트만 통과시킴"""
    combined = title + " " + text_content
    
    # 1. 제외 키워드(종료, 1원, 출첵 등)가 포함된 경우 즉시 차단
    if any(k in combined for k in EXCLUDE_KEYWORDS):
        return False
    if "[종료" in combined or "(종료" in combined or "종료됨" in combined:
        return False
    
    # 2. 과거 연도(20~25년) 글 차단
    if re.search(r'\b(20)?(20|21|22|23|24|25)[./-]', combined):
        return False

    # 3. 경품/상품권 핵심 키워드가 최소 1개 이상 포함되어야만 인정
    has_prize = any(k in combined for k in PRIZE_KEYWORDS)
    return has_prize

def extract_end_date(title):
    now = datetime.now()
    match = re.search(r'~\s*(\d{1,2})[./월]\s*(\d{1,2})', title)
    if match:
        month, day = int(match.group(1)), int(match.group(2))
        if 1 <= month <= 12 and 1 <= day <= 31:
            year = now.year + 1 if (now.month == 12 and month <= 2) else now.year
            return f"{year}-{month:02d}-{day:02d}"
    return "상시/본문참고"

def classify_event(title):
    category = "기업/금융"
    if any(k in title for k in ["치킨", "커피", "피자", "버거", "스타벅스", "스벅", "투썸", "메가커피", "배민", "요기요", "식당", "음료"]):
        category = "식음료/외식"
    elif any(k in title for k in ["쿠폰", "할인", "마트", "편의점", "쇼핑", "네이버페이", "네페", "무신사", "올리브영", "신세계", "상품권"]):
        category = "쇼핑/상품권"
    elif any(k in title for k in ["공공", "시청", "구청", "공사", "재단", "정부", "지자체", "공모전", "서포터즈", "박물관", "도서관"]):
        category = "공공/공모전"
    elif any(k in title for k in ["게임", "스팀", "플스", "닌텐도", "스위치", "엔비디아", "인텔", "갤럭시", "아이폰", "앱"]):
        category = "IT/기기"

    difficulty = "하"
    if any(k in title for k in ["서포터즈", "공모전", "영상", "글짓기", "리뷰", "체험단"]):
        difficulty = "상"
    elif any(k in title for k in ["인스타", "팔로우", "소문내기", "공유", "댓글", "인증"]):
        difficulty = "중"

    prize = "경품/상품권"
    for p in ["스타벅스", "네이버페이", "상품권", "신세계", "기프티콘", "치킨", "피자", "커피", "아메리카노", "문화상품권", "문상"]:
        if p in title:
            prize = p
            break

    # 상품권이나 확정 경품이 제목에 명시된 경우 무조건 '알짜'로 판별
    is_honey = True 
    return category, difficulty, prize, is_honey

def add_event(title, link, source, text_content=""):
    try:
        title = re.sub(r'\s+', ' ', title).strip()
        if len(title) < 5 or link in seen_links:
            return
        if not is_valid_prize_event(title, text_content):
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
    except Exception:
        pass

def fetch_ppomppu():
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
                row_text = post.get_text()
                title_tag = post.select_one('a.baseList-title, td.list_title a, a.list_title')
                if not title_tag:
                    continue
                title = title_tag.get_text(strip=True)
                href = title_tag.get('href', '')
                if not href or href.startswith('javascript'):
                    continue
                link = urljoin(url, href)
                add_event(title, link, "뽐뿌", row_text)
        except Exception as e:
            print(f"⚠️ 뽐뿌 수집 중 예외 발생: {e}")

def fetch_ruliweb():
    url = "https://bbs.ruliweb.com/market/board/1020"
    try:
        res = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(res.text, 'html.parser')
        posts = soup.select('tr.table_body')
        for post in posts:
            if 'notice' in post.get('class', []):
                continue
            row_text = post.get_text()
            title_tag = post.select_one('a.deco, a.subject_link')
            if not title_tag:
                continue
            title = title_tag.get_text(strip=True)
            link = title_tag.get('href', '').split('?')[0]
            if link:
                add_event(title, link, "루리웹", row_text)
    except Exception as e:
        print(f"⚠️ 루리웹 수집 중 예외 발생: {e}")

def fetch_clien():
    url = "https://www.clien.net/service/board/jirum"
    try:
        res = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(res.text, 'html.parser')
        posts = soup.select('div.list_item.symph_row')
        for post in posts:
            row_text = post.get_text()
            title_tag = post.select_one('span.list_subject a, a.list_subject')
            if not title_tag:
                continue
            title = title_tag.get_text(strip=True)
            href = title_tag.get('href', '')
            if href:
                link = urljoin("https://www.clien.net", href.split('?')[0])
                add_event(title, link, "클리앙", row_text)
    except Exception as e:
        print(f"⚠️ 클리앙 수집 중 예외 발생: {e}")

def fetch_coolenjoy():
    url = "https://coolenjoy.net/bbs/jirum"
    try:
        res = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(res.text, 'html.parser')
        posts = soup.select('td.td_subject a')
        for title_tag in posts:
            title = title_tag.get_text(strip=True)
            row_text = title_tag.parent.get_text() if title_tag.parent else ""
            href = title_tag.get('href', '')
            if href and 'jirum/' in href:
                add_event(title, href, "쿨엔조이", row_text)
    except Exception as e:
        print(f"⚠️ 쿨엔조이 수집 중 예외 발생: {e}")

if __name__ == "__main__":
    print("🚀 경품·상품권 집중형 스마트 크롤러 시작...")
    fetch_ppomppu()
    fetch_ruliweb()
    fetch_clien()
    fetch_coolenjoy()

    events.sort(key=lambda x: (not x.get("isHoney", False)))

    with open('events.json', 'w', encoding='utf-8') as f:
        json.dump(events, f, ensure_ascii=False, indent=2)

    print(f"✅ 총 {len(events)}개 알짜 경품/상품권 이벤트 수집 완료!")
