import requests
from bs4 import BeautifulSoup
from django.core.management.base import BaseCommand
from drinks.models import Category, MenuItem

FALLBACK_MENU = [
    ("커피", 1, [
        ("아이스 아메리카노", 2000), ("핫 아메리카노", 2000), ("카페라떼", 3000),
        ("바닐라라떼", 3500), ("카라멜마끼아또", 3500), ("돌체라떼", 3500),
        ("달고나라떼", 3500), ("카페모카", 3500), ("아인슈페너라떼", 3500),
        ("캡틴아메리카노", 2500),
    ]),
    ("더치커피", 2, [
        ("더치아메리카노", 2500), ("더치라떼", 3500), ("더치바닐라라떼", 4000),
    ]),
    ("논커피 라떼", 3, [
        ("초코라떼", 3500), ("더블초코라떼", 4000), ("말차라떼", 3500),
        ("고구마라떼", 3500), ("딸기라떼", 4000), ("망고라떼", 4000),
        ("흑임자라떼", 3500), ("팥라떼", 3500),
    ]),
    ("프라페", 4, [
        ("리얼초코자바칩프라페", 4500), ("그린티프라페", 4000),
        ("쿠키초코프라페", 4500), ("민트초코오레오프라페", 4500), ("딸기프라페", 4500),
    ]),
    ("스무디", 5, [
        ("요거트스무디", 4000), ("딸기요거트스무디", 4500),
        ("망고스무디", 4000), ("복숭아스무디", 4000),
    ]),
    ("밀크쉐이크", 6, [
        ("바닐라밀크쉐이크", 4000), ("초코밀크쉐이크", 4000),
        ("딸기밀크쉐이크", 4500), ("커피밀크쉐이크", 4000),
    ]),
    ("에이드", 7, [
        ("레몬에이드", 3500), ("자몽에이드", 3500), ("청포도에이드", 3500),
        ("복숭아에이드", 3500), ("딸기에이드", 4000),
    ]),
    ("티", 8, [
        ("복숭아아이스티", 2500), ("자몽허니블랙티", 3000),
        ("레몬티", 2500), ("캐모마일", 2500), ("얼그레이", 2500),
    ]),
    ("주스", 9, [
        ("오렌지주스", 3500), ("망고주스", 3500), ("자몽주스", 3500),
    ]),
]


def crawl_from_website():
    try:
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            )
        }
        resp = requests.get("https://composecoffee.com/menu", headers=headers, timeout=10)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "lxml")
        items = []
        menu_cards = soup.select(".menu-item, .item-card, li.item")
        for card in menu_cards:
            name_tag = card.select_one(".name, .title, h3, h4, strong")
            price_tag = card.select_one(".price, [class*=price]")
            img_tag = card.select_one("img")
            if name_tag and name_tag.get_text(strip=True):
                items.append({
                    "name": name_tag.get_text(strip=True),
                    "price": price_tag.get_text(strip=True) if price_tag else "0",
                    "image": img_tag["src"] if img_tag and img_tag.get("src") else "",
                })
        return items
    except Exception as e:
        print(f"  크롤링 실패: {e}")
        return []


class Command(BaseCommand):
    help = "컴포즈커피 메뉴를 크롤링하여 DB에 저장합니다."

    def add_arguments(self, parser):
        parser.add_argument("--fallback", action="store_true",
                            help="크롤링 없이 기본 메뉴 데이터를 바로 사용")
        parser.add_argument("--clear", action="store_true",
                            help="기존 메뉴 데이터 삭제 후 재저장")

    def handle(self, *args, **options):
        if options["clear"]:
            MenuItem.objects.all().delete()
            Category.objects.all().delete()
            self.stdout.write("기존 메뉴 데이터를 삭제했습니다.")

        if MenuItem.objects.exists() and not options["clear"]:
            self.stdout.write(self.style.WARNING(
                "이미 메뉴 데이터가 존재합니다. --clear 옵션으로 초기화 후 재실행하세요."))
            return

        crawled = []
        if not options["fallback"]:
            self.stdout.write("컴포즈커피 홈페이지 크롤링 시도 중...")
            crawled = crawl_from_website()
            if crawled:
                self.stdout.write(self.style.SUCCESS(f"  크롤링 성공: {len(crawled)}개 항목"))

        if not crawled:
            self.stdout.write("  -> 기본 메뉴 데이터(fallback)를 사용합니다.")
            self._save_fallback()
        else:
            self._save_crawled(crawled)

        total = MenuItem.objects.count()
        self.stdout.write(self.style.SUCCESS(f"완료! 총 {total}개 메뉴 저장됨."))

    def _save_fallback(self):
        for cat_name, order, items in FALLBACK_MENU:
            category, _ = Category.objects.get_or_create(
                name=cat_name, defaults={"order": order}
            )
            for menu_name, price in items:
                MenuItem.objects.get_or_create(
                    name=menu_name, category=category,
                    defaults={"price": price}
                )

    def _save_crawled(self, crawled_items):
        cat, _ = Category.objects.get_or_create(
            name="전체메뉴", defaults={"order": 0})
        for item in crawled_items:
            price_str = "".join(filter(str.isdigit, item.get("price", "0")))
            price = int(price_str) if price_str else 0
            MenuItem.objects.get_or_create(
                name=item["name"], category=cat,
                defaults={"price": price, "image_url": item.get("image", "")}
            )
