from django.contrib import admin
from django.utils.html import format_html
from django.urls import path
from django.core.management import call_command
from django.shortcuts import redirect
from django.contrib import messages
from .models import CoffeeShop, Category, MenuItem, VoteSession, Vote, TeamMember, Comment

@admin.register(CoffeeShop)
class CoffeeShopAdmin(admin.ModelAdmin):
    list_display = ['name', 'branch_name', 'is_active', 'created_at']
    list_filter = ['is_active']
    search_fields = ['name', 'branch_name']
    list_editable = ['is_active']

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['coffee_shop', 'name', 'order']
    list_filter = ['coffee_shop']
    ordering = ['coffee_shop', 'order']

@admin.register(MenuItem)
class MenuItemAdmin(admin.ModelAdmin):
    # 아까 만든 커스텀 템플릿 연결
    change_list_template = "admin/drinks/menuitem/change_list.html"

    list_display = ['coffee_shop', 'name', 'category', 'is_available', 'is_popular', 'thumbnail']
    list_filter = ['coffee_shop', 'category', 'is_available', 'is_popular']
    search_fields = ['name']
    list_editable = ['is_available', 'is_popular']

    def thumbnail(self, obj):
        if obj.image_url:
            return format_html('<img src="{}" height="40"/>', obj.image_url)
        return '-'
    thumbnail.short_description = '이미지'

    # 버튼 클릭 시 실행될 URL 추가
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('update-menu/', self.admin_site.admin_view(self.update_menu_view), name='update_menu'),
            path('update-menu/<int:coffee_shop_id>/', self.admin_site.admin_view(self.update_menu_view), name='update_menu_coffee_shop'),
            path('update-banapresso/', self.admin_site.admin_view(self.update_banapresso_view), name='update_banapresso'),
            path('update-banapresso/<int:coffee_shop_id>/', self.admin_site.admin_view(self.update_banapresso_view), name='update_banapresso_coffee_shop'),
        ]
        return custom_urls + urls

    # 크롤링 실행 로직
    def update_menu_view(self, request, coffee_shop_id=None):
        try:
            # 커피점 ID가 있으면 해당 커피점만 크롤링
            if coffee_shop_id:
                call_command('crawl_menu', '--coffee-shop', str(coffee_shop_id))
                self.message_user(request, f"✅ 커피점 ID {coffee_shop_id} 메뉴 크롤링 및 업데이트가 완료되었습니다!", level=messages.SUCCESS)
            else:
                # 기본 크롤링 (컴포즈커피 신도림점)
                call_command('crawl_menu')
                self.message_user(request, "✅ 메뉴 크롤링 및 업데이트가 완료되었습니다!", level=messages.SUCCESS)
        except Exception as e:
            self.message_user(request, f"❌ 크롤링 중 오류가 발생했습니다: {e}", level=messages.ERROR)

        return redirect('..')  # 다시 메뉴 목록으로 돌아감

    # 바나프레소 크롤링 실행 로직
    def update_banapresso_view(self, request, coffee_shop_id=None):
        try:
            # 커피점 ID가 있으면 해당 커피점만 크롤링
            if coffee_shop_id:
                call_command('crawl_banapresso', '--coffee-shop', str(coffee_shop_id))
                self.message_user(request, f"✅ 커피점 ID {coffee_shop_id} 바나프레소 메뉴 크롤링 및 업데이트가 완료되었습니다!", level=messages.SUCCESS)
            else:
                # 기본 바나프레소 크롤링
                call_command('crawl_banapresso')
                self.message_user(request, "✅ 바나프레소 메뉴 크롤링 및 업데이트가 완료되었습니다!", level=messages.SUCCESS)
        except Exception as e:
            self.message_user(request, f"❌ 바나프레소 크롤링 중 오류가 발생했습니다: {e}", level=messages.ERROR)

        return redirect('..')  # 다시 메뉴 목록으로 돌아감

@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ['author', 'content', 'session', 'created_at']
    list_filter = ['session']

@admin.register(TeamMember)
class TeamMemberAdmin(admin.ModelAdmin):
    list_display = ['name', 'is_active']
    list_editable = ['is_active']
    search_fields = ['name']

class VoteInline(admin.TabularInline):
    model = Vote
    extra = 0
    readonly_fields = ['participant', 'menu_item', 'created_at']

@admin.register(VoteSession)
class VoteSessionAdmin(admin.ModelAdmin):
    list_display = ['coffee_shop', 'title', 'vote_date', 'is_active', 'total_votes']
    list_filter = ['coffee_shop', 'is_active']
    list_editable = ['is_active']
    inlines = [VoteInline]

@admin.register(Vote)
class VoteAdmin(admin.ModelAdmin):
    list_display = ['participant', 'menu_item', 'session', 'created_at']
    list_filter = ['session']