from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    path('signup/', views.signup_view, name='signup'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('mygirok/', views.mygirok_view, name='mygirok'),
    path('api/bookmark/add/', views.add_bookmark_api, name='add_bookmark_api'),
]

