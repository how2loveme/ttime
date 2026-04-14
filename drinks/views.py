from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.db.models import Count
from .models import VoteSession, MenuItem, Vote, Category, TeamMember, Comment

def index(request):
    active_sessions = VoteSession.objects.filter(is_active=True)
    past_sessions = VoteSession.objects.filter(is_active=False)[:5]
    return render(request, 'drinks/index.html', {
        'active_sessions': active_sessions,
        'past_sessions': past_sessions,
    })

def menu_list(request):
    categories = Category.objects.prefetch_related('items').all()
    return render(request, 'drinks/menu_list.html', {'categories': categories})

def vote(request, session_id):
    session = get_object_or_404(VoteSession, pk=session_id)
    if not session.is_active:
        messages.warning(request, '이미 종료된 투표입니다.')
        return redirect('index')

    team_members = TeamMember.objects.filter(is_active=True)
    voted_member_id = request.session.get(f'voted_{session_id}')
    existing_vote = None
    if voted_member_id:
        existing_vote = Vote.objects.filter(session=session, participant_id=voted_member_id).select_related('menu_item', 'participant').first()

    categories = Category.objects.prefetch_related('items').filter(items__is_available=True).distinct()

    # 인기메뉴 필터링해서 가져오기
    popular_items = MenuItem.objects.filter(is_popular=True, is_available=True)

    return render(request, 'drinks/vote.html', {
        'session': session,
        'categories': categories,
        'team_members': team_members,
        'existing_vote': existing_vote,
        'popular_items': popular_items, # 템플릿으로 전달
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
    menu_item = get_object_or_404(MenuItem, pk=menu_item_id, is_available=True)

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
    vote_counts = Vote.objects.filter(session=session).values('menu_item__name', 'menu_item__category__name').annotate(count=Count('id')).order_by('-count')
    all_votes = Vote.objects.filter(session=session).select_related('menu_item', 'participant').order_by('participant__name')

    total = session.total_votes
    results = [{'name': item['menu_item__name'], 'category': item['menu_item__category__name'], 'count': item['count'], 'percent': round(item['count'] / total * 100) if total else 0} for item in vote_counts]

    # 댓글 시스템을 위한 데이터
    comments = Comment.objects.filter(session=session).select_related('author')
    team_members = TeamMember.objects.filter(is_active=True)
    voted_member_id = request.session.get(f'voted_{session_id}') # 방금 투표한 사람 (자동 선택용)

    return render(request, 'drinks/stats.html', {
        'session': session, 'results': results, 'all_votes': all_votes, 'total': total,
        'comments': comments, 'team_members': team_members, 'voted_member_id': voted_member_id
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