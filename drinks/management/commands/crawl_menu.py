import time
import requests
from bs4 import BeautifulSoup
from django.core.management.base import BaseCommand
from drinks.models import Category, MenuItem


class Command(BaseCommand):
    help = '컴포즈커피 공식 홈페이지에서 실제 카테고리와 메뉴(페이징 포함)를 크롤링합니다.'

    def handle(self, *args, **options):
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        base_url = 'https://composecoffee.com'

        self.stdout.write('홈페이지 접속 중...')
        resp = requests.get(f'{base_url}/menu', headers=headers, timeout=10)
        soup = BeautifulSoup(resp.text, 'html.parser')

        # 1. 카테고리 추출
        ul_tag = soup.find('ul', class_='nav nav-pills nav-sm nav-fill mb-5')
        if not ul_tag:
            self.stdout.write(self.style.ERROR('카테고리 영역을 찾을 수 없습니다.'))
            return

        categories = []
        exclude_cats = ['전체', '디저트', 'MD상품']

        for a_tag in ul_tag.find_all('a'):
            cat_name = a_tag.get_text(strip=True)
            if cat_name and cat_name not in exclude_cats:
                href = a_tag.get('href')
                if href:
                    cat_url = href if href.startswith('http') else base_url + href
                    categories.append((cat_name, cat_url))

        self.stdout.write(self.style.SUCCESS(
            f'총 {len(categories)}개의 음료 카테고리: {[c[0] for c in categories]}'
        ))

        # ── 핵심 변경 ①: 이번 크롤링에서 수집된 메뉴명을 담을 Set ──────────
        crawled_names = set()
        total_added = 0
        total_updated = 0

        # 2. 카테고리별 메뉴 및 페이징 크롤링
        for order, (cat_name, cat_url) in enumerate(categories, start=1):
            self.stdout.write(f'\n[{cat_name}] 크롤링 시작...')
            category_obj, _ = Category.objects.get_or_create(
                name=cat_name, defaults={'order': order}
            )

            page = 1
            while True:
                target_url = f"{cat_url}?page={page}"
                self.stdout.write(f'  - 페이지 {page} 요청 중...')

                try:
                    c_resp = requests.get(target_url, headers=headers, timeout=10)
                    c_soup = BeautifulSoup(c_resp.text, 'html.parser')
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f'통신 오류: {e}'))
                    break

                items = c_soup.find_all('div', class_=lambda c: c and 'itemBox' in c.split())
                if not items:
                    break

                for item in items:
                    name_tag = item.find('h4') or item.find('span', class_='title')
                    if not name_tag:
                        name_tag = item.find('div', class_='txtBox')

                    menu_name = name_tag.get_text(strip=True) if name_tag else ""
                    if not menu_name:
                        continue

                    img_tag = item.find('img')
                    img_url = ''
                    if img_tag and img_tag.get('src'):
                        src = img_tag['src']
                        img_url = src if src.startswith('http') else base_url + src

                    # ── 핵심 변경 ②: get_or_create → Upsert 처리 ──────────
                    crawled_names.add(menu_name)
                    existing = MenuItem.objects.filter(name=menu_name).first()

                    if existing:
                        # 기존 메뉴: 이미지/카테고리 최신화, 미사용이었다면 복구
                        changed = False
                        if existing.image_url != img_url:
                            existing.image_url = img_url
                            changed = True
                        if existing.category != category_obj:
                            existing.category = category_obj
                            changed = True
                        if not existing.is_available:
                            existing.is_available = True
                            changed = True
                        if changed:
                            existing.save()
                            total_updated += 1
                    else:
                        # 새 메뉴: 추가
                        MenuItem.objects.create(
                            category=category_obj,
                            name=menu_name,
                            price=0,
                            image_url=img_url,
                            is_available=True,
                        )
                        total_added += 1
                    # ────────────────────────────────────────────────────────

                # 3. 페이징 처리
                nav_tag = c_soup.find('nav', class_='mt-2')
                if not nav_tag:
                    break

                next_page_str = f'page={page + 1}'
                has_next = any(
                    next_page_str in a.get('href', '') for a in nav_tag.find_all('a')
                )

                if has_next:
                    page += 1
                    time.sleep(0.5)
                else:
                    break

        # ── 핵심 변경 ③: 크롤링에서 사라진 메뉴 → 미사용 처리 ──────────────
        disappeared = MenuItem.objects.filter(
            is_available=True
        ).exclude(name__in=crawled_names)
        disappeared_count = disappeared.count()
        disappeared.update(is_available=False)
        # ────────────────────────────────────────────────────────────────────

        self.stdout.write(self.style.SUCCESS(
            f'\n완료! [추가] {total_added}개 / [수정] {total_updated}개 / [미사용] {disappeared_count}개'
        ))
        self.stdout.write(self.style.WARNING(
            '※ 홈페이지에는 가격이 안 적혀있어 0원으로 저장됩니다. 필요한 경우 관리자(Admin)에서 수정하세요.'
        ))