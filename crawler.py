import requests
from bs4 import BeautifulSoup
import json
import os
from datetime import datetime

# 수집 데이터 저장 리스트
events = []

headers = {
    'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1'
}

def fetch_ppomppu_events():
    """뽐뿌 경품/이벤트 게시판 수집"""
    url = "https://www.ppomppu.co.kr/zboard/zboard.php?id=event"
    try:
        res = requests.get(url, headers=headers, timeout=10)
        res.encoding = 'euc-kr'
        soup = BeautifulSoup(res.text, 'html.parser')
        
        posts = soup.select('tr.list0, tr.list1')
        print(f"🔍 게시글 {len(posts)}개 발견, 분석 중...")
        
        for idx, post in enumerate(posts):
            title_tag = post.select_one('td.list_title a, a.list_title')
            if not title_tag:
                continue
                
            title = title_tag.text.strip()
            # 공지사항이나 짧은 글 제외
            if len(title) < 4 or "공지" in title:
                continue
                
            href = title_tag.get('href', '')
            link = f"https://www.ppomppu.co.kr/zboard/{href}" if not href.startswith('http') else href
            
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
    
    # 결과를 events.json 파일로 저장 (if문 안쪽으로 들여쓰기 포함해서 이동!)
    with open('events.json', 'w', encoding='utf-8') as f:
        json.dump(events, f, ensure_ascii=False, indent=2)
        
    print(f"✅ 총 {len(events)}개 이벤트 수집 완료!")

