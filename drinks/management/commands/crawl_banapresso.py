import requests
from django.core.management.base import BaseCommand
from drinks.models import Category, MenuItem, CoffeeShop

BASE_URL = "https://order.banapresso.com/query"
# 음료가 아닌 카테고리 (크롤링/표시 제외)
EXCLUDED_CATEGORIES = {'디저트', 'MD'}
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Content-Type": "application/json"
}


class Command(BaseCommand):
    help = '바나프레소 API 기반 메뉴 크롤링'

    def add_arguments(self, parser):
        parser.add_argument('--coffee-shop', type=str, help='커피점 ID 또는 이름')

    def handle(self, *args, **options):
        try:
            # 커피점 파라미터 처리
            coffee_shop = options.get('coffee_shop')
            if coffee_shop:
                try:
                    # ID로 찾기 시도
                    self.coffee_shop = CoffeeShop.objects.get(id=coffee_shop)
                except (CoffeeShop.DoesNotExist, ValueError):
                    # 이름으로 찾기 시도
                    self.coffee_shop = CoffeeShop.objects.get(name__icontains=coffee_shop)
            else:
                # 기본 커피점 (바나프레소)
                self.coffee_shop, _ = CoffeeShop.objects.get_or_create(
                    name='바나프레소',
                    branch_name='',
                    defaults={
                        'website_url': 'https://order.banapresso.com',
                        'description': '바나프레소',
                        'is_active': True
                    }
                )

            self.stdout.write(f"크롤링 대상 커피점: {self.coffee_shop}")
            self.crawl()
        except Exception as e:
            self.stderr.write(f"크롤링 실패: {e}")
            raise

    def post_query(self, query, params):
        response = requests.post(
            BASE_URL,
            json={"query": query, "params": params},
            headers=HEADERS,
            timeout=10
        )
        response.raise_for_status()
        return response.json()

    def get_categories(self):
        # 메뉴 데이터에서 카테고리 추출 (이미 한글 카테고리명 사용)
        menu_data = self.post_query(
            "91D8843AB9D3C73B28F1043252C574AF",
            {"f_code": 200000, "f_code_sub": 65600}
        )

        categories = set()
        if 'rows' in menu_data:
            for row in menu_data['rows']:
                # 두번째 값이 한글 카테고리명
                if len(row) > 1 and row[1]:
                    category_name = row[1]
                    # 디저트, MD 카테고리 제외
                    if category_name not in EXCLUDED_CATEGORIES:
                        categories.add(category_name)

        return sorted(list(categories))

    def get_menu_items(self):
        # 메뉴 API 호출
        data = self.post_query(
            "91D8843AB9D3C73B28F1043252C574AF",
            {"f_code": 200000, "f_code_sub": 65600}
        )

        menu_items = []
        if 'rows' in data:
            for row in data['rows']:
                # 배열 길이 체크
                if len(row) < 49:
                    continue

                # 인덱스 매핑:
                # 1: 한글 카테고리명
                # 4: 한글 메뉴명
                # 11: 이미지 URL
                # 48: 품절여부 (1=품절, 0=정상)
                category_name = row[1] if len(row) > 1 else None
                menu_name = row[4] if len(row) > 4 else None
                image_url = row[10] if len(row) > 11 else None
                is_sold_out = row[29] == 1

                # 디저트, MD 카테고리 제외
                if category_name in EXCLUDED_CATEGORIES:
                    continue

                if category_name and menu_name:
                    menu_items.append({
                        'category': category_name,
                        'name': menu_name,
                        'image_url': image_url,
                        'is_sold_out': is_sold_out
                    })

        return menu_items

    def crawl(self):
        # 카테고리 수집
        categories = self.get_categories()
        self.stdout.write(f"카테고리 {len(categories)}개 발견: {categories}")

        # 메뉴 수집
        menu_items = self.get_menu_items()
        self.stdout.write(f"메뉴 {len(menu_items)}개 발견")

        # 카테고리 등록
        category_map = {}
        for i, cat_name in enumerate(categories):
            category_obj, _ = Category.objects.get_or_create(
                coffee_shop=self.coffee_shop,
                name=cat_name,
                defaults={'order': i}
            )
            category_map[cat_name] = category_obj

        # 메뉴 등록
        seen_names = set()
        for item in menu_items:
            category_name = item['category']
            menu_name = item['name']
            image_url = item['image_url']
            is_sold_out = item['is_sold_out']

            if category_name in category_map:
                category_obj = category_map[category_name]
                seen_names.add(menu_name)

                MenuItem.objects.update_or_create(
                    coffee_shop=self.coffee_shop,
                    name=menu_name,
                    defaults={
                        'category': category_obj,
                        'image_url': image_url,
                        'is_available': not is_sold_out,  # 품절이면 is_available=False
                    }
                )

        # 해당 커피점의 미사용 메뉴 처리
        unavailable_count = MenuItem.objects.filter(
            coffee_shop=self.coffee_shop
        ).exclude(name__in=seen_names).update(is_available=False)

        # 디저트/MD 등 제외 카테고리 정리: 투표 이력 없는 메뉴는 삭제, 있으면 미사용 처리
        excluded_qs = MenuItem.objects.filter(
            coffee_shop=self.coffee_shop,
            category__name__in=EXCLUDED_CATEGORIES
        )
        deleted_count = 0
        for item in excluded_qs:
            if item.votes.exists():
                item.is_available = False
                item.save(update_fields=['is_available'])
            else:
                item.delete()
                deleted_count += 1
        # 비어버린 제외 카테고리 삭제
        Category.objects.filter(
            coffee_shop=self.coffee_shop,
            name__in=EXCLUDED_CATEGORIES,
            items__isnull=True
        ).delete()

        self.stdout.write(
            f"크롤링 완료: 총 {len(seen_names)}개 메뉴 확인, "
            f"{unavailable_count}개 메뉴는 미사용 처리됨, "
            f"제외 카테고리 메뉴 {deleted_count}개 삭제됨"
        )