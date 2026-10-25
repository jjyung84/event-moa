import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import json
from datetime import datetime

# 수집 데이터 저장 리스트
events = []

# PC 버전 HTML 구조를 받기 위해 Windows PC User-Agent 사용
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
    'Referer': 'https://www.ppomppu.co.kr/'
}

def fetch_ppomppu_events():
    """뽐뿌 경품/이벤트 게시판 수집"""
    url = "https://www.ppomppu.co.kr/zboard/zboard.php?id=event"
    try:
        res = requests.get(url, headers=headers, timeout=10)
        res.encoding = 'cp949'
        soup = BeautifulSoup(res.text, 'html.parser')
        
        # 개편된 뽐뿌 클래스(tr.baseList)와 기존 클래스 모두 탐색
        posts = soup.select('tr.baseList, tr.list0, tr.list1')
        print(f"🔍 게시글 {len(posts)}개 발견, 분석 중...")
        
        for idx, post in enumerate(posts):
            title_tag = post.select_one('a.baseList-title, td.list_title a, a.list_title')
            if not title_tag:
                continue
                
            title = title_tag.get_text(strip=True)
            
            # 공지사항이나 짧은 글 제외
            if len(title) < 4 or "공지" in title:
                continue
                
            href = title_tag.get('href', '')
            if not href or href.startswith('javascript'):
                continue
                
            # 상대 경로와 절대 경로를 안전하게 결합
            link = urljoin(url, href)
            
            # 카테고리 자동 태깅
            category = "기업/금융"
            if any(k in title for k in ["공공", "시청", "구청", "부", "공사", "재단", "정부", "지자체"]):
                category = "공공/정책"
            elif any(k in title for k in ["쿠폰", "할인", "마트", "편의점", "쇼핑", "배민", "요기요"]):
                category = "쇼핑/생활"

            # 난이도 자동 추론
            difficulty = "하"
            if any(k in title for k in ["퀴즈", "출석", "룰렛", "클릭"]):
                difficulty = "하"
            elif any(k in title for k in ["서포터즈", "공모전", "영상", "글짓기"]):
                difficulty = "상"
            elif any(k in title for k in ["인스타", "팔로우", "소문내기", "공유"]):
                difficulty = "중"

            events.append({
                "id": f"evt_{int(datetime.now().timestamp())}_{idx}",
                "title": title,
                "category": category,
                "type": "응모",
                "organizer": "자동수집",
                "prize": "게시물 참고",
                "endDate": datetime.now().strftime("%Y-%m-%d"),
                "difficulty": difficulty,
                "url": link,
                "views": 100 + (idx * 15),
                "completed": False,
                "favorite": False,
                "createdAt": datetime.now().strftime("%Y-%m-%d")
            })
            
    except Exception as e:
        print(f"❌ 수집 오류 발생: {e}")

if __name__ == "__main__":
    print("🚀 실시간 이벤트 자동 크롤러 시작...")
    fetch_ppomppu_events()
    
    # 결과를 events.json 파일로 저장
    with open('events.json', 'w', encoding='utf-8') as f:
        json.dump(events, f, ensure_ascii=False, indent=2)
        
    print(f"✅ 총 {len(events)}개 이벤트 수집 완료!")
