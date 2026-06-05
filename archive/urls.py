from django.urls import path
from . import views

app_name = 'archive'

urlpatterns = [
    path('', views.index, name='index'),
    path('sillokgwan/', views.sillokgwan, name='sillokgwan'),
    path('sillokgwan.html', views.sillokgwan, name='sillokgwan_html'),
    path('geumgirok/', views.geumgirok, name='geumgirok'),
    path('geumgirok.html', views.geumgirok, name='geumgirok_html'),
    path('chatbot/', views.sillokgwan, name='chatbot'),
    path('chatbot.html', views.sillokgwan, name='chatbot_html'),
    path('archive/', views.geumgirok, name='archive'),
    path('archive.html', views.geumgirok, name='archive_html'),
    path('list/', views.sillokgwan, name='list'),
    path('search/', views.sillokgwan, name='search'),
    path('taboos/', views.geumgirok, name='taboo_list'),
    path('taboos/today/', views.geumgirok, name='today_taboo'),
    path('taboos/<int:taboo_id>/', views.geumgirok, name='taboo_detail'),
    path('api/search/', views.sillok_search_api, name='sillok_search_api'),
]
