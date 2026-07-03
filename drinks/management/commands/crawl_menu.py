import re
import time
import requests
from bs4 import BeautifulSoup
from django.core.management.base import BaseCommand
from drinks.models import Category, MenuItem

BASE_URL = "https://composecoffee.com"
LIST_PATH = "/index.php"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
}


class Command(BaseCommand):
    help = '컴포즈커피 dispCafemenuGalleryList 기반 메뉴 크롤링'

    def add_arguments(self, parser):
        parser.add_argument('--fallback', action='store_true')

    def handle(self, *args, **options):
        try:
            self.crawl()
        except Exception as e:
            self.stderr.write(f"크롤링 실패: {e}")
            if options.get('fallback'):
                self.stdout.write("fallback 모드: 기존 DB 데이터 유지")
                return
            raise

    def get_soup(self, params):
        resp = requests.get(f"{BASE_URL}{LIST_PATH}", params=params,
                            headers=HEADERS, timeout=10)
        resp.raise_for_status()
        return BeautifulSoup(resp.text, 'html.parser')

    def get_categories(self):
        soup = self.get_soup({'mid': 'compose', 'act': 'dispCafemenuGalleryList'})
        filter_div = soup.select_one('.cafemenu-category-filter')
        categories = []
        for a_tag in filter_div.select('a.cafemenu-category-btn'):
            cat_srl = a_tag.get('data-category')
            name = a_tag.get_text(strip=True)
            if cat_srl and cat_srl != 'all' and name:
                categories.append({'srl': cat_srl, 'name': name})
        return categories

    def get_last_page(self, soup):
        pagination = soup.select_one('.pagination')
        if not pagination:
            return 1
        page_numbers = []
        for a_tag in pagination.select('a'):
            href = a_tag.get('href', '')
            match = re.search(r'page=(\d+)', href)
            if match:
                page_numbers.append(int(match.group(1)))
        return max(page_numbers) if page_numbers else 1

    def crawl(self):
        categories = self.get_categories()
        self.stdout.write(f"카테고리 {len(categories)}개 발견: {[c['name'] for c in categories]}")

        seen_names = set()

        for cat in categories:
            category_obj, _ = Category.objects.get_or_create(name=cat['name'])
            page = 1
            last_page = 1

            while page <= last_page:
                params = {
                    'mid': 'compose',
                    'act': 'dispCafemenuGalleryList',
                    'category_srl': cat['srl'],
                    'page': page,
                }
                soup = self.get_soup(params)

                if page == 1:
                    last_page = self.get_last_page(soup)

                items = soup.select('.cafemenu-menu-grid > a.cafemenu-menu-item')
                for item in items:
                    name_tag = item.select_one('.cafemenu-menu-name')
                    img_tag = item.select_one('.cafemenu-menu-image img')
                    if not name_tag:
                        continue

                    item_name = name_tag.get_text(strip=True)
                    img_src = img_tag.get('src', '') if img_tag else ''
                    img_url = img_src if img_src.startswith('http') else f"{BASE_URL}{img_src}"

                    seen_names.add(item_name)

                    MenuItem.objects.update_or_create(
                        name=item_name,
                        defaults={
                            'category': category_obj,
                            'image_url': img_url,
                            'is_available': True,
                        }
                    )

                self.stdout.write(f"[{cat['name']}] {page}/{last_page} 페이지 완료 ({len(items)}개)")
                page += 1
                time.sleep(0.3)  # 서버 부담 줄이기 위한 딜레이

        unavailable_count = MenuItem.objects.exclude(name__in=seen_names).update(is_available=False)
        self.stdout.write(
            f"크롤링 완료: 총 {len(seen_names)}개 메뉴 확인, "
            f"{unavailable_count}개 메뉴는 미사용 처리됨"
        )