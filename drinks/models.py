from django.db import models

class Category(models.Model):
    name = models.CharField(max_length=100, verbose_name='카테고리명')
    order = models.IntegerField(default=0, verbose_name='정렬순서')

    class Meta:
        ordering = ['order', 'name']
        verbose_name = '카테고리'
        verbose_name_plural = '카테고리 목록'

    def __str__(self):
        return self.name

class MenuItem(models.Model):
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='items', verbose_name='카테고리')
    name = models.CharField(max_length=200, verbose_name='메뉴명')
    price = models.IntegerField(default=0, verbose_name='가격(원)')
    image_url = models.URLField(blank=True, verbose_name='이미지URL')
    description = models.TextField(blank=True, verbose_name='설명')
    is_available = models.BooleanField(default=True, verbose_name='판매중')
    # 새로 추가된 인기메뉴 필드
    is_popular = models.BooleanField(default=False, verbose_name='인기메뉴')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['category__order', 'name']
        verbose_name = '메뉴'
        verbose_name_plural = '메뉴 목록'

    def __str__(self):
        return f"[{self.category.name}] {self.name}"

# --- 새로 추가된 팀원 모델 ---
class TeamMember(models.Model):
    name = models.CharField(max_length=50, verbose_name='이름')
    is_active = models.BooleanField(default=True, verbose_name='재직/참여중')

    class Meta:
        ordering = ['name']
        verbose_name = '팀원'
        verbose_name_plural = '팀원 목록'

    def __str__(self):
        return self.name

class VoteSession(models.Model):
    title = models.CharField(max_length=200, verbose_name='투표 제목')
    vote_date = models.DateField(verbose_name='티타임 날짜')
    is_active = models.BooleanField(default=True, verbose_name='투표 진행중')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-vote_date']
        verbose_name = '투표 세션'
        verbose_name_plural = '투표 세션 목록'

    def __str__(self):
        return f"{self.title} ({self.vote_date})"

    @property
    def total_votes(self):
        return self.votes.count()

class Vote(models.Model):
    session = models.ForeignKey(
        VoteSession, on_delete=models.CASCADE,
        related_name='votes', verbose_name='투표 세션'
    )
    # 기존 participant_name 대신 TeamMember 외래키 사용
    participant = models.ForeignKey(
        TeamMember, on_delete=models.CASCADE,
        related_name='votes', verbose_name='참여자'
    )
    menu_item = models.ForeignKey(
        MenuItem, on_delete=models.CASCADE,
        related_name='votes', verbose_name='선택 메뉴'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['session', 'participant']
        verbose_name = '투표'
        verbose_name_plural = '투표 목록'

    def __str__(self):
        return f"{self.participant.name} → {self.menu_item.name}"

class Comment(models.Model):
    session = models.ForeignKey(VoteSession, on_delete=models.CASCADE, related_name='comments', verbose_name='투표 세션')
    author = models.ForeignKey('TeamMember', on_delete=models.CASCADE, verbose_name='작성자')
    content = models.CharField(max_length=500, verbose_name='내용(옵션/댓글)')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']
        verbose_name = '댓글'
        verbose_name_plural = '댓글 목록'