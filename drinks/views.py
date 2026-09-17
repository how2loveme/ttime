from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.db.models import Count
from django.db import models
from .models import VoteSession, MenuItem, Vote, Category, TeamMember, Comment, CoffeeShop
from types import SimpleNamespace

def index(request):
    active_sessions = VoteSession.objects.filter(is_active=True)
    past_sessions = VoteSession.objects.filter(is_active=False)[:5]
    return render(request, 'drinks/index.html', {
        'active_sessions': active_sessions,
        'past_sessions': past_sessions,
    })

def menu_list(request):
    coffee_shops = CoffeeShop.objects.filter(is_active=True).prefetch_related(
        models.Prefetch(
            'categories',
            queryset=Category.objects.prefetch_related(
                models.Prefetch('items', queryset=MenuItem.objects.filter(is_available=True).order_by('name'))
            )
        )
    )
    return render(request, 'drinks/menu_list.html', {'coffee_shops': coffee_shops})

def vote(request, session_id):
    session = get_object_or_404(VoteSession, pk=session_id)
    if not session.is_active:
        messages.warning(request, '이미 종료된 투표입니다.')
        return redirect('index')

    team_members = TeamMember.objects.filter(is_active=True)
    voted_member_id = request.session.get(f'voted_{session_id}')
    existing_vote = None
    if voted_member_id:
        existing_vote = Vote.objects.filter(
            session=session, participant_id=voted_member_id
        ).select_related('menu_item', 'participant').first()

    # 해당 커피점의 카테고리와 메뉴만 필터링
    categories = list(Category.objects.filter(
        coffee_shop=session.coffee_shop
    ).prefetch_related(
        models.Prefetch(
            'items',
            queryset=MenuItem.objects.filter(coffee_shop=session.coffee_shop, is_available=True)
        )
    ).filter(items__isnull=False).distinct())

    # 인기메뉴: 해당 커피점의 is_popular=True인 메뉴들로 가상 카테고리 구성
    popular_qs = MenuItem.objects.filter(
        is_popular=True, is_available=True, coffee_shop=session.coffee_shop
    )
    if popular_qs.exists():
        popular_category = SimpleNamespace(
            id='popular',
            name='🔥 인기메뉴',
            items=SimpleNamespace(all=lambda: popular_qs)
        )
        categories.insert(0, popular_category)

    return render(request, 'drinks/vote.html', {
        'session': session,
        'categories': categories,
        'team_members': team_members,
        'existing_vote': existing_vote,
    })

def vote_submit(request, session_id):
    if request.method != 'POST':
        return redirect('vote', session_id=session_id)

    session = get_object_or_404(VoteSession, pk=session_id, is_active=True)
    participant_id = request.POST.get('participant_id')
    menu_item_id = request.POST.get('menu_item_id')

    if not participant_id or not menu_item_id:
        messages.error(request, '팀원 이름과 음료를 모두 선택해주세요.')
        return redirect('vote', session_id=session_id)

    participant = get_object_or_404(TeamMember, pk=participant_id, is_active=True)
    menu_item = get_object_or_404(MenuItem, pk=menu_item_id, is_available=True, coffee_shop=session.coffee_shop)

    vote_obj, created = Vote.objects.update_or_create(
        session=session, participant=participant, defaults={'menu_item': menu_item}
    )
    request.session[f'voted_{session_id}'] = participant.id

    if created:
        messages.success(request, f'[{participant.name}] 님, "{menu_item.name}" 선택 완료! 🎉')
    else:
        messages.info(request, f'[{participant.name}] 님, "{menu_item.name}"(으)로 변경되었습니다.')

    # 투표 후 stats(결과창) 페이지로 즉시 이동
    return redirect('stats', session_id=session_id)

def stats(request, session_id):
    session = get_object_or_404(VoteSession, pk=session_id)

    # 해당 커피점의 메뉴만 필터링하여 투표 결과 계산
    vote_counts = Vote.objects.filter(
        session=session,
        menu_item__coffee_shop=session.coffee_shop
    ).values('menu_item__name', 'menu_item__category__name').annotate(count=Count('id')).order_by('-count')

    all_votes = Vote.objects.filter(session=session).select_related('menu_item', 'participant').order_by('participant__name')

    total = session.total_votes
    results = [{'name': item['menu_item__name'], 'category': item['menu_item__category__name'], 'count': item['count'], 'percent': round(item['count'] / total * 100) if total else 0} for item in vote_counts]

    comments = Comment.objects.filter(session=session).select_related('author')
    team_members = TeamMember.objects.filter(is_active=True)
    voted_member_id = request.session.get(f'voted_{session_id}')

    voted_member_ids = all_votes.values_list('participant_id', flat=True)
    unvoted_members = TeamMember.objects.filter(is_active=True).exclude(id__in=voted_member_ids).order_by('name')

    return render(request, 'drinks/stats.html', {
        'session': session, 'results': results, 'all_votes': all_votes, 'total': total,
        'comments': comments, 'team_members': team_members, 'voted_member_id': voted_member_id,
        'unvoted_members': unvoted_members, # 템플릿으로 전달
    })

# 새로 추가된 댓글 처리 View
def add_comment(request, session_id):
    if request.method == 'POST':
        author_id = request.POST.get('author_id')
        content = request.POST.get('content')
        if author_id and content:
            author = get_object_or_404(TeamMember, pk=author_id)
            session_obj = get_object_or_404(VoteSession, pk=session_id)
            Comment.objects.create(session=session_obj, author=author, content=content)
            messages.success(request, '댓글/요청사항이 등록되었습니다.')
    return redirect('stats', session_id=session_id)