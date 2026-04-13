from django.contrib import admin
from django.utils.html import format_html
from .models import Category, MenuItem, VoteSession, Vote


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'order', 'item_count']
    ordering = ['order']

    def item_count(self, obj):
        return obj.items.count()
    item_count.short_description = '메뉴 수'


@admin.register(MenuItem)
class MenuItemAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'price_display', 'is_available', 'thumbnail']
    list_filter = ['category', 'is_available']
    search_fields = ['name']
    list_editable = ['is_available']

    def price_display(self, obj):
        return obj.price_display
    price_display.short_description = '가격'

    def thumbnail(self, obj):
        if obj.image_url:
            return format_html('<img src="{}" height="40"/>', obj.image_url)
        return '-'
    thumbnail.short_description = '이미지'


class VoteInline(admin.TabularInline):
    model = Vote
    extra = 0
    readonly_fields = ['participant_name', 'menu_item', 'created_at']


@admin.register(VoteSession)
class VoteSessionAdmin(admin.ModelAdmin):
    list_display = ['title', 'vote_date', 'is_active', 'total_votes']
    list_editable = ['is_active']
    inlines = [VoteInline]

    def total_votes(self, obj):
        return obj.total_votes
    total_votes.short_description = '참여자 수'


@admin.register(Vote)
class VoteAdmin(admin.ModelAdmin):
    list_display = ['participant_name', 'menu_item', 'session', 'created_at']
    list_filter = ['session']
    search_fields = ['participant_name']
