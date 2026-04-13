import time
import requests
from bs4 import BeautifulSoup
from django.core.management.base import BaseCommand
from drinks.models import Category, MenuItem

class Command(BaseCommand):
    help = '컴포즈커피 공식 홈페이지에서 실제 카테고리와 메뉴(페이징 포함)를 크롤링합니다.'

    def add_arguments(self, parser):
        parser.add_argument('--clear', action='store_true', help='기존 데이터 삭제 후 크롤링')

    def handle(self, *args, **options):
        if options['clear']:
            MenuItem.objects.all().delete()
            Category.objects.all().delete()
            self.stdout.write(self.style.SUCCESS('기존 데이터를 모두 삭제했습니다.'))

        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        base_url = 'https://composecoffee.com'

        self.stdout.write('홈페이지 접속 중...')
        resp = requests.get(f'{base_url}/menu', headers=headers, timeout=10)
        soup = BeautifulSoup(resp.text, 'html.parser')

        # 1. 카테고리 추출 (<ul class="nav nav-pills ...">)
        ul_tag = soup.find('ul', class_='nav nav-pills nav-sm nav-fill mb-5')
        if not ul_tag:
            self.stdout.write(self.style.ERROR('카테고리 영역을 찾을 수 없습니다.'))
            return

        categories = []
        # 투표와 무관한 디저트/MD/전체 탭은 제외
        exclude_cats = ['전체', '디저트', 'MD상품']

        for a_tag in ul_tag.find_all('a'):
            cat_name = a_tag.get_text(strip=True)
            if cat_name and cat_name not in exclude_cats:
                href = a_tag.get('href')
                if href:
                    cat_url = href if href.startswith('http') else base_url + href
                    categories.append((cat_name, cat_url))

        self.stdout.write(self.style.SUCCESS(f'총 {len(categories)}개의 음료 카테고리를 찾았습니다: {[c[0] for c in categories]}'))

        total_items = 0

        # 2. 카테고리별 메뉴 및 페이징 크롤링
        for order, (cat_name, cat_url) in enumerate(categories, start=1):
            self.stdout.write(f'\n[{cat_name}] 크롤링 시작...')
            category_obj, _ = Category.objects.get_or_create(name=cat_name, defaults={'order': order})

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

                # 음료 아이템 추출 (<div class="col-lg-3 col-md-4 col-sm-6 itemBox">)
                items = c_soup.find_all('div', class_=lambda c: c and 'itemBox' in c.split())

                if not items:
                    break

                for item in items:
                    # 메뉴명 추출 (h4 태그 등 텍스트 박스)
                    name_tag = item.find('h4') or item.find('span', class_='title')
                    if not name_tag:
                        # 특정 태그가 없으면 내부 텍스트 전체 가져오기
                        name_tag = item.find('div', class_='txtBox')

                    menu_name = name_tag.get_text(strip=True) if name_tag else ""
                    if not menu_name:
                        continue

                    # 이미지 추출
                    img_tag = item.find('img')
                    img_url = ''
                    if img_tag and img_tag.get('src'):
                        src = img_tag['src']
                        img_url = src if src.startswith('http') else base_url + src

                    # DB 저장
                    MenuItem.objects.get_or_create(
                        name=menu_name,
                        category=category_obj,
                        defaults={
                            'price': 0, # 공홈에는 가격 정보가 없으므로 0으로 세팅
                            'image_url': img_url
                        }
                    )
                    total_items += 1

                # 3. 페이징 처리 (<nav aria-label="Page navigation" class="mt-2">)
                nav_tag = c_soup.find('nav', class_='mt-2')
                if not nav_tag:
                    break # 페이지 네비게이션이 없으면 단일 페이지

                # 다음 페이지 링크(page=2, page=3...)가 있는지 검사
                next_page_str = f'page={page+1}'
                has_next = any(next_page_str in a.get('href', '') for a in nav_tag.find_all('a'))

                if has_next:
                    page += 1
                    time.sleep(0.5) # 서버 부하 방지를 위해 0.5초 대기
                else:
                    break

        self.stdout.write(self.style.SUCCESS(f'\n완료! 총 {total_items}개의 메뉴와 이미지를 성공적으로 저장했습니다.'))
        self.stdout.write(self.style.WARNING('※ 홈페이지에는 가격이 안 적혀있어 가격은 0원으로 저장됩니다. 필요한 경우 관리자(Admin)에서 수정하세요.'))