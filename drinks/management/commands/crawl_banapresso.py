import requests
from django.core.management.base import BaseCommand
from drinks.models import Category, MenuItem, CoffeeShop

BASE_URL = "https://order.banapresso.com/query"
# 음료가 아닌 카테고리 (크롤링/표시 제외)
EXCLUDED_CATEGORIES = {'디저트', 'MD'}
MENU_QUERY = "91D8843AB9D3C73B28F1043252C574AF"  # 메뉴 목록
TEMP_QUERY = "2FFF7D3419C25631E50AE5510EDAAB0D"  # HOT/ICE 판매 메뉴 ID
MENU_PARAMS = {"f_code": 200000, "f_code_sub": 65600}  # f_code_sub=65600: 신도림점
TEMP_TYPES = ('HOT', 'ICE')
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

    def get_temp_item_ids(self):
        # HOT/ICE별 판매 메뉴 ID 수집 (row[0]이 상품 ID)
        temp_ids = {}
        for temp in TEMP_TYPES:
            data = self.post_query(
                TEMP_QUERY,
                {"nFCode": 200000, "filter": temp}
            )
            temp_ids[temp] = {row[0] for row in data.get('rows', [])}
        return temp_ids

    def get_menu_items(self, rows, temp_ids):
        # 인덱스 매핑 (응답 columns 메타데이터 기준):
        # 0(nItem): 상품 ID / 1(sItemDivision): 한글 카테고리명 / 4(sItem): 한글 메뉴명
        # 10(sImageUrl): ICE 이미지 / 11(sImageUrlSub): HOT 이미지
        # 18(nCharge): 기본 가격 / 19(nDefaultChargeHot): HOT 가격 / 20(nDefaultChargeIce): ICE 가격
        # 27(bSoldOut): 품절 / 28(bSellOutHot): HOT 품절 / 29(bSellOutIce): ICE 품절
        categories = []
        menu_items = []
        for row in rows:
            if len(row) < 30:
                continue

            item_id = row[0]
            category_name = row[1]
            menu_name = (row[4] or '').strip()

            # 디저트, MD 카테고리 제외
            if not category_name or not menu_name or category_name in EXCLUDED_CATEGORIES:
                continue

            for temp in TEMP_TYPES:
                # HOT/ICE 판매 목록에 없으면 해당 온도 메뉴는 등록하지 않음
                if item_id not in temp_ids[temp]:
                    continue

                if category_name not in categories:
                    categories.append(category_name)

                if temp == 'HOT':
                    image_url = row[11] or row[10]
                    price = row[19] or row[18]
                    is_sold_out = row[27] == 1 or row[28] == 1
                else:
                    image_url = row[10] or row[11]
                    price = row[20] or row[18]
                    is_sold_out = row[27] == 1 or row[29] == 1

                menu_items.append({
                    'category': category_name,
                    'name': f"[{temp}] {menu_name}",
                    'image_url': image_url or '',
                    'price': price or 0,
                    'is_sold_out': is_sold_out
                })

        return categories, menu_items

    def crawl(self):
        # 메뉴 데이터 수집
        menu_data = self.post_query(MENU_QUERY, MENU_PARAMS)
        rows = menu_data.get('rows', [])

        # HOT/ICE 판매 메뉴 ID 수집
        temp_ids = self.get_temp_item_ids()
        self.stdout.write(
            f"HOT {len(temp_ids['HOT'])}개 / ICE {len(temp_ids['ICE'])}개 판매 메뉴 ID 확인"
        )

        # 메뉴를 [HOT]/[ICE]로 분리
        categories, menu_items = self.get_menu_items(rows, temp_ids)
        self.stdout.write(f"카테고리 {len(categories)}개, 메뉴 {len(menu_items)}개 발견: {categories}")

        # 카테고리 등록
        category_map = {}
        for i, cat_name in enumerate(categories):
            category_obj, _ = Category.objects.update_or_create(
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
            price = item['price']
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
                        'price': price,
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