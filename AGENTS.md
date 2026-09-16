# Compose Vote Project

## Project Overview
Django-based 팀 티타임 음료 투표 시스템

## Project Structure
- Django 4.2.30
- PostgreSQL (production) / SQLite (development)
- Pipenv for dependency management

## Key Features
- 커피점별 메뉴 크롤링 (현재 컴포즈커피 지원)
- 팀원별 음료 투표 시스템
- 투표 결과 통계 및 댓글 기능
- 다중 커피점 지원

## Database Models
- **CoffeeShop**: 커피점 기본 정보 (상호명, 지점명, 웹사이트 등)
- **Category**: 커피점별 카테고리 (커피점 + 카테고리명 unique)
- **MenuItem**: 커피점별 메뉴 (커피점 + 메뉴명 unique)
- **VoteSession**: 투표 세션 (커피점별 투표)
- **Vote**: 개별 투표 (세션 + 참여자 unique)
- **TeamMember**: 팀원 정보
- **Comment**: 댓글/요청사항

## Important Model Relationships
- CoffeeShop → Category (1:N)
- CoffeeShop → MenuItem (1:N)
- CoffeeShop → VoteSession (1:N)
- Category → MenuItem (1:N)
- VoteSession → Vote (1:N)
- VoteSession → Comment (1:N)
- TeamMember → Vote (1:N)
- TeamMember → Comment (1:N)

## Development Commands
```bash
# 마이그레이션
pipenv run python manage.py makemigrations
pipenv run python manage.py migrate

# 서버 실행
pipenv run python manage.py runserver

# 메뉴 크롤링
pipenv run python manage.py crawl_menu
pipenv run python manage.py crawl_menu --coffee-shop <coffee_shop_id>

# Admin 접속
/admin/
```

## Environment Variables
- `DEBUG`: 개발 모드 (기본: 1)
- `USE_SQLITE`: SQLite 사용 여부 (기본: 1)
- `POSTGRES_HOST`: PostgreSQL 호스트 (프로덕션용)
- `POSTGRES_PORT`: PostgreSQL 포트 (기본: 5432)
- `POSTGRES_DB`: 데이터베이스 이름
- `POSTGRES_USER`: 데이터베이스 사용자
- `POSTGRES_PASSWORD`: 데이터베이스 비밀번호

## Key URLs
- `/`: 투표 세션 목록
- `/vote/<session_id>/`: 투표 페이지
- `/vote/<session_id>/stats/`: 투표 결과
- `/menu/`: 메뉴 목록
- `/admin/`: Django Admin

## Important Notes
- 로컬 개발 시 SQLite 사용 (`USE_SQLITE=1`)
- 프로덕션 시 PostgreSQL 사용
- 기존 데이터 마이그레이션 시 기본 커피점(컴포즈커피 신도림점) 자동 생성
- 커피점별로 메뉴와 카테고리가 분리됨
- 투표 세션 생성 시 반드시 커피점 선택 필요