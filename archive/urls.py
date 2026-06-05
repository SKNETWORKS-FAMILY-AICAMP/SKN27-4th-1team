from django.urls import path
from . import views

app_name = 'archive'

urlpatterns = [
    path('', views.index, name='index'),
    path('chatbot/', views.chatbot, name='chatbot'),
    path('archive/', views.archive, name='archive'),
    path('list/', views.chatbot, name='list'),
    path('search/', views.chatbot, name='search'),
    path('taboos/', views.archive, name='taboo_list'),
    path('taboos/today/', views.archive, name='today_taboo'),
    path('taboos/<int:taboo_id>/', views.archive, name='taboo_detail'),
    path('api/search/', views.sillok_search_api, name='sillok_search_api'),
    path('api/taboos/', views.taboo_list_api, name='taboo_list_api'),
    path('api/taboos/search/', views.taboo_search_api, name='taboo_search_api'),
    path('api/taboos/today/', views.today_taboo_api, name='today_taboo_api'),
    path('api/taboos/<int:taboo_id>/', views.taboo_detail_api, name='taboo_detail_api'),
]
