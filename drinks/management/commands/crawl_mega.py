# drinks/management/commands/crawl_mega.py
import requests
from bs4 import BeautifulSoup
from django.core.management.base import BaseCommand
from drinks.models import Category, MenuItem

BASE_URL = "https://www.mega-mgccoffee.com/menu/"
AJAX_URL = "https://www.mega-mgccoffee.com/menu/menu.php"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
BRAND = "mega"


class Command(BaseCommand):
    help = '메가커피 음료 메뉴 크롤링'

    def handle(self, *args, **options):
        seen_names = set()
        categories = self.get_categories()
        self.stdout.write(f"카테고리 {len(categories)}개 발견")

        for cat in categories:
            category_obj, _ = Category.objects.get_or_create(brand=BRAND, name=cat['name'], defaults={'order': cat['order']})
            items = self.get_items(cat)
            for it in items:
                seen_names.add(it['name'])
                MenuItem.objects.update_or_create(
                    category=category_obj, name=it['name'],
                    defaults={'image_url': it['image_url'], 'is_available': True}
                )
            self.stdout.write(f"[{cat['name']}] {len(items)}개 완료")

        unavailable = MenuItem.objects.filter(category__brand=BRAND) \
            .exclude(name__in=seen_names).update(is_available=False)
        self.stdout.write(f"메가 크롤링 완료: {len(seen_names)}개 확인, {unavailable}개 미사용 처리")

    def get_categories(self):
        res = requests.get(BASE_URL, params={"menu_category1": 1, "menu_category2": 1}, headers=HEADERS, timeout=10)
        soup = BeautifulSoup(res.text, "html.parser")
        wrap = soup.select_one("div.list_checkbox_wrap")
        categories = []
        for label in wrap.select(".checkbox_wrap.list_checkbox label.checkbox"):
            checkbox = label.select_one("input[name='list_checkbox']")
            text = label.select_one(".checkbox_text")
            if checkbox and text:
                categories.append({"id": checkbox.get("value"), "name": text.get_text(strip=True), "order": int(checkbox.get("value"))})
        return categories

    def _last_page(self, soup):
        last = soup.select_one("li.board_page_last a.board_page_link")
        return int(last["data-page"]) if last and last.get("data-page") else 1

    def get_items(self, category):
        items = []
        params = {"menu_category1": 1, "menu_category2": 1, "category": category["id"], "list_checkbox_all": ""}
        res = requests.get(BASE_URL, params=params, headers=HEADERS, timeout=10)
        soup = BeautifulSoup(res.text, "html.parser")
        last_page = self._last_page(soup)

        for page in range(1, last_page + 1):
            page_soup = soup if page == 1 else BeautifulSoup(
                requests.get(AJAX_URL, params={**params, "page": page}, headers=HEADERS, timeout=10).text, "html.parser"
            )
            # 변경: id 중복 대응 - 모든 menu_list 후보 중 li를 가진 것을 선택
            candidates = page_soup.find_all(id="menu_list")
            target_ul = next((ul for ul in candidates if ul.select("li")), None)
            if not target_ul:
                continue

            for li in target_ul.select("li"):
                name_tag = li.select_one(".cont_text_inner.text_wrap.cont_text_title b")
                img_tag = li.select_one(".cont_gallery_list_img img")
                if name_tag and img_tag:
                    items.append({"name": name_tag.get_text(strip=True), "image_url": img_tag.get("src")})
        return items