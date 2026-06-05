from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.csrf import ensure_csrf_cookie
import json
from .models import Bookmark

def signup_view(request):
    """Handles User Signup."""
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '').strip()
        
        if not username or not password:
            return render(request, 'accounts/signup.html', {'error': '아이디와 비밀번호를 입력해 주십시오.'})
        
        if User.objects.filter(username=username).exists():
            return render(request, 'accounts/signup.html', {'error': '이미 가입된 아이디입니다.'})
        
        # Create user and hash password automatically
        user = User.objects.create_user(username=username, password=password)
        login(request, user) # Auto login after signup
        return redirect('accounts:mygirok')
        
    return render(request, 'accounts/signup.html')

@ensure_csrf_cookie
def login_view(request):
    """Handles User Login."""
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '').strip()
        
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            # Redirect to where they came from or Mypage
            next_url = request.GET.get('next', 'accounts:mygirok')
            return redirect(next_url)
        else:
            return render(request, 'accounts/login.html', {'error': '인증 실패. 자격 증명을 확인하십시오.'})
            
    return render(request, 'accounts/login.html')

def logout_view(request):
    """Handles User Logout."""
    logout(request)
    return redirect('home')

@login_required(login_url='accounts:login')
def mygirok_view(request):
    """Renders user's bookmarked horror archive logs (Mypage)."""
    bookmarks = Bookmark.objects.filter(user=request.user)
    return render(request, 'accounts/mygirok.html', {'bookmarks': bookmarks})

def add_bookmark_api(request):
    """API endpoint to add a horror record to user bookmarks."""
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

