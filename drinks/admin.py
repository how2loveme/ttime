from django.contrib import admin
from django.utils.html import format_html
from .models import Category, MenuItem, VoteSession, Vote, TeamMember, Comment

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'order']
    ordering = ['order']

@admin.register(MenuItem)
class MenuItemAdmin(admin.ModelAdmin):
    # is_popular 추가
    list_display = ['name', 'category', 'is_available', 'is_popular', 'thumbnail']
    list_filter = ['category', 'is_available', 'is_popular']
    search_fields = ['name']
    # 관리자 리스트에서 바로 인기메뉴 체크박스 끄고 켤 수 있게 설정
    list_editable = ['is_available', 'is_popular']

    def thumbnail(self, obj):
        if obj.image_url:
            return format_html('<img src="{}" height="40"/>', obj.image_url)
        return '-'
    thumbnail.short_description = '이미지'

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
    list_display = ['title', 'vote_date', 'is_active', 'total_votes']
    list_editable = ['is_active']
    inlines = [VoteInline]

@admin.register(Vote)
class VoteAdmin(admin.ModelAdmin):
    list_display = ['participant', 'menu_item', 'session', 'created_at']
    list_filter = ['session']