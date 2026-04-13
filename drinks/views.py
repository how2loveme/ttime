from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.db.models import Count
from .models import VoteSession, MenuItem, Vote, Category


def index(request):
    """메인 페이지: 진행 중인 투표 세션 목록"""
    active_sessions = VoteSession.objects.filter(is_active=True)
    past_sessions = VoteSession.objects.filter(is_active=False)[:5]
    return render(request, 'drinks/index.html', {
        'active_sessions': active_sessions,
        'past_sessions': past_sessions,
    })


def menu_list(request):
    """전체 메뉴 목록"""
    categories = Category.objects.prefetch_related('items').all()
    return render(request, 'drinks/menu_list.html', {'categories': categories})


def vote(request, session_id):
    """투표 페이지: 메뉴 선택"""
    session = get_object_or_404(VoteSession, pk=session_id)

    if not session.is_active:
        messages.warning(request, '이미 종료된 투표입니다.')
        return redirect('index')

    # 이미 투표했는지 확인 (이름 기반)
    already_voted_name = request.session.get(f'voted_{session_id}')
    existing_vote = None
    if already_voted_name:
        existing_vote = Vote.objects.filter(
            session=session, participant_name=already_voted_name
        ).select_related('menu_item').first()

    categories = Category.objects.prefetch_related(
        'items'
    ).filter(items__is_available=True).distinct()

    return render(request, 'drinks/vote.html', {
        'session': session,
        'categories': categories,
        'existing_vote': existing_vote,
        'already_voted_name': already_voted_name,
    })


def vote_submit(request, session_id):
    """투표 제출 처리"""
    if request.method != 'POST':
        return redirect('vote', session_id=session_id)

    session = get_object_or_404(VoteSession, pk=session_id, is_active=True)
    participant_name = request.POST.get('participant_name', '').strip()
    menu_item_id = request.POST.get('menu_item_id')

    if not participant_name:
        messages.error(request, '이름을 입력해주세요.')
        return redirect('vote', session_id=session_id)

    if not menu_item_id:
        messages.error(request, '음료를 선택해주세요.')
        return redirect('vote', session_id=session_id)

    menu_item = get_object_or_404(MenuItem, pk=menu_item_id, is_available=True)

    # 중복 투표 처리: 같은 이름이면 업데이트
    vote_obj, created = Vote.objects.update_or_create(
        session=session,
        participant_name=participant_name,
        defaults={'menu_item': menu_item}
    )

    request.session[f'voted_{session_id}'] = participant_name

    if created:
        messages.success(request, f'"{menu_item.name}" 을(를) 선택했습니다! 🎉')
    else:
        messages.info(request, f'"{menu_item.name}" 으로 변경되었습니다.')

    return redirect('vote', session_id=session_id)


def stats(request, session_id):
    """투표 통계 페이지"""
    session = get_object_or_404(VoteSession, pk=session_id)

    vote_counts = (
        Vote.objects.filter(session=session)
        .values('menu_item__name', 'menu_item__category__name', 'menu_item__price')
        .annotate(count=Count('id'))
        .order_by('-count')
    )

    all_votes = Vote.objects.filter(session=session).select_related(
        'menu_item', 'menu_item__category'
    ).order_by('participant_name')

    total = session.total_votes

    results = []
    for item in vote_counts:
        results.append({
            'name': item['menu_item__name'],
            'category': item['menu_item__category__name'],
            'price': item['menu_item__price'],
            'count': item['count'],
            'percent': round(item['count'] / total * 100) if total else 0,
        })

    return render(request, 'drinks/stats.html', {
        'session': session,
        'results': results,
        'all_votes': all_votes,
        'total': total,
    })
