# drinks/management/commands/crawl_mammoth.py
import requests
from bs4 import BeautifulSoup
from django.core.management.base import BaseCommand
from drinks.models import Category, MenuItem

LIST_URL = "https://mmthcoffee.com/sub/menu/list.html"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
BRAND = "mammoth"
EXCLUDED = {"푸드", "MD"}


class Command(BaseCommand):
    help = '매머드익스프레스 음료 메뉴 크롤링'

    def handle(self, *args, **options):
        soup = self.get_soup()
        seen_names = set()

        for idx, cate_div in enumerate(soup.select("div.sub_con div.cate"), start=1):
            title_tag = cate_div.select_one(".c_tit strong")
            if not title_tag:
                continue
            name = title_tag.get_text(strip=True)
            if name in EXCLUDED:
                continue

            category_obj, _ = Category.objects.get_or_create(brand=BRAND, name=name, defaults={'order': idx})
            items = self.get_items(cate_div)
            for it in items:
                seen_names.add(it['name'])
                MenuItem.objects.update_or_create(
                    category=category_obj, name=it['name'],
                    defaults={'image_url': it['image_url'], 'is_available': True}
                )
            self.stdout.write(f"[{name}] {len(items)}개 완료")

        unavailable = MenuItem.objects.filter(category__brand=BRAND) \
            .exclude(name__in=seen_names).update(is_available=False)
        self.stdout.write(f"매머드 크롤링 완료: {len(seen_names)}개 확인, {unavailable}개 미사용 처리")

    def get_soup(self):
        res = requests.get(LIST_URL, headers=HEADERS, timeout=10)
        res.raise_for_status()
        return BeautifulSoup(res.text, "html.parser")

    def get_items(self, cate_div):
        items = []
        for li in cate_div.select("ul.clear > li"):
            name_tag = li.select_one(".txt_wrap strong")
            img_tag = li.select_one(".img_wrap img")
            if name_tag and img_tag:
                items.append({
                    "name": name_tag.get_text(strip=True),
                    "image_url": requests.compat.urljoin(LIST_URL, img_tag.get("src")),
                })
        return items