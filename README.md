# ☕ 컴포즈 티타임 투표 시스템

컴포즈커피 신도림점 메뉴 기반 팀 음료 투표 앱입니다.

## 로컬 실행

```bash
# 1. 가상환경 & 의존성
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# 2. DB 초기화 + 메뉴 크롤링
python manage.py migrate
python manage.py crawl_menu --fallback   # 크롤링 실패 시 기본 데이터 사용

# 3. 관리자 계정 생성
python manage.py createsuperuser

# 4. 서버 실행
python manage.py runserver
```

## Docker 실행

```bash
docker-compose up -d
```
- 웹: http://localhost:8000
- 관리자: http://localhost:8000/admin

## 투표 세션 만들기

1. `/admin` 접속 → 로그인
2. **투표 세션** → **추가** 클릭
3. 제목, 티타임 날짜 입력 → 저장
4. 팀원들에게 `/vote/<id>/` URL 공유

## 크롤링 옵션

```bash
python manage.py crawl_menu             # 홈페이지 크롤링 시도 후 fallback
python manage.py crawl_menu --fallback  # fallback 데이터 바로 사용
python manage.py crawl_menu --clear     # 기존 삭제 후 재저장
```

> **참고**: composecoffee.com이 SPA(React)로 구성된 경우
> requests 크롤링이 실패할 수 있습니다.
> 이 경우 `--fallback` 옵션으로 내장 메뉴를 사용하거나,
> Selenium/Playwright로 크롤러를 확장하세요.
