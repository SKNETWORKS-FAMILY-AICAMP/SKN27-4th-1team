from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    path('signup/', views.signup, name='signup'),
    path('login/', views.login, name='login'),
    path('logout/', views.logout, name='logout'),
    path('delete/', views.delete_account, name='delete_account'),
    path('mypage/', views.mypage, name='mypage'),
    path('api/bookmark/add/', views.add_bookmark_api, name='add_bookmark_api'),
]
