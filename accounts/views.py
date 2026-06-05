from django.contrib.auth import logout as auth_logout
from django.shortcuts import redirect, render

def login(request):
    return render(request, 'accounts/login.html')


def signup(request):
    return render(request, 'accounts/register.html')


def register(request):
    return signup(request)


def logout(request):
    auth_logout(request)
    return redirect('accounts:login')


def mypage(request):
    return render(request, 'accounts/mypage.html')
