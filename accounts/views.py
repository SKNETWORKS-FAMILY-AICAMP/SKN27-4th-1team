from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.csrf import ensure_csrf_cookie
import json
from .forms import LoginForm, SignupForm
from .models import Bookmark
from . import services


def _first_form_error(form):
    errors = form.errors.get("__all__") or next(iter(form.errors.values()), None)
    if not errors:
        return "입력값을 확인해 주십시오."
    return errors[0]


def _safe_next_url(request, fallback_name="accounts:mygirok"):
    next_url = request.POST.get("next") or request.GET.get("next")
    if next_url and url_has_allowed_host_and_scheme(
        url=next_url,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return next_url
    return reverse(fallback_name)


@ensure_csrf_cookie
def signup(request):
    initial_next = request.GET.get("next", "")
    if request.method == 'POST':
        form = SignupForm(request.POST)
        if form.is_valid():
            services.signup_user(form.cleaned_data)
            services.login_user(
                request,
                form.cleaned_data["username"],
                form.cleaned_data["password"],
            )
            return redirect(_safe_next_url(request))

        return render(request, 'accounts/signup.html', {
            'form': form,
            'error': _first_form_error(form),
            'next': request.POST.get('next', ''),
        })

    return render(request, 'accounts/signup.html', {
        'form': SignupForm(initial={'next': initial_next}),
        'next': initial_next,
    })


def register(request):
    return signup(request)


@ensure_csrf_cookie
def login(request):
    initial_next = request.GET.get("next", "")
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            user = services.login_user(
                request,
                form.cleaned_data["username"],
                form.cleaned_data["password"],
            )
            if user is not None:
                return redirect(_safe_next_url(request))

        error = _first_form_error(form) if not form.is_valid() else '인증 실패. 자격 증명을 확인하십시오.'
        return render(request, 'accounts/login.html', {
            'form': form,
            'error': error,
            'next': request.POST.get('next', ''),
        })

    return render(request, 'accounts/login.html', {
        'form': LoginForm(initial={'next': initial_next}),
        'next': initial_next,
    })


def logout(request):
    services.logout_user(request)
    return redirect('home')


@login_required(login_url='accounts:login')
def mypage(request):
    bookmarks = services.list_external_bookmarks(request.user)
    factory_bookmarks = [item for item in bookmarks if item.horror_type != 'Witness']
    witness_bookmarks = [item for item in bookmarks if item.horror_type == 'Witness']
    generated_bookmarks = services.list_generated_story_bookmarks(request.user)
    post_bookmarks = services.list_post_bookmarks(request.user)
    profile = services.get_user_profile(request.user)

    try:
        from generator.services import list_user_generated_stories
        generated_stories = list_user_generated_stories(request.user)
    except (ImportError, AttributeError):
        generated_stories = []

    try:
        from post.services import list_user_posts
        user_posts = list_user_posts(request.user)
    except (ImportError, AttributeError):
        user_posts = []

    return render(request, 'accounts/mygirok.html', {
        'profile': profile,
        'bookmarks': bookmarks,
        'factory_bookmarks': factory_bookmarks,
        'witness_bookmarks': witness_bookmarks,
        'generated_bookmarks': generated_bookmarks,
        'post_bookmarks': post_bookmarks,
        'generated_stories': generated_stories,
        'user_posts': user_posts,
    })


def add_bookmark_api(request):
    if not request.user.is_authenticated:
        return JsonResponse({'status': 'error', 'message': '로그인이 필요합니다.'}, status=401)

    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Invalid method.'}, status=400)

    try:
        data = json.loads(request.body)
        horror_id = data.get('horror_id', '').strip()
        horror_title = data.get('horror_title', '').strip()
        horror_type = data.get('horror_type', 'Story').strip()

        if not horror_id or not horror_title:
            return JsonResponse({'status': 'error', 'message': '필수 데이터가 누락되었습니다.'}, status=400)

        bookmark, created = Bookmark.objects.get_or_create(
            user=request.user,
            horror_id=horror_id,
            defaults={
                'horror_title': horror_title,
                'horror_type': horror_type
            }
        )

        if not created:
            return JsonResponse({'status': 'exists', 'message': '이미 보관함에 보관된 기록입니다.'})

        return JsonResponse({'status': 'success', 'message': '보관함에 성공적으로 추가되었습니다.'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
