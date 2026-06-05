from django.urls import path

from . import views

app_name = 'archive'

urlpatterns = [
    path('', views.index, name='index'),
    path('chatbot/', views.sillokgwan, name='chatbot'),
    path('archive/', views.geumgirok, name='archive'),
    path('sillokgwan/', views.sillokgwan, name='sillokgwan'),
    path('list/', views.sillokgwan, name='list'),
    path('search/', views.sillokgwan, name='search'),
    path('geumgirok/', views.geumgirok, name='geumgirok'),
    path('taboos/', views.geumgirok, name='taboo_list'),
    path('taboos/today/', views.geumgirok, name='today_taboo'),
    path('taboos/<int:taboo_id>/', views.geumgirok, name='taboo_detail'),
]
