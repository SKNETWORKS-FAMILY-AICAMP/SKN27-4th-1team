from django.urls import path
from . import views

app_name = 'regions'

urlpatterns = [
    path('jidogam/', views.jidogam, name='jidogam'),
    path('regioninfo/', views.jidogam, name='regioninfo'),
    path('list/', views.jidogam, name='list'),
    path('api/query/', views.region_query_api, name='region_query_api'),
    path('api/list/', views.region_list_api, name='region_list_api'),
    path('api/cities/', views.city_list_api, name='city_list_api'),
    path('api/story/', views.story_detail_api, name='story_detail_api'),
    path('<str:region_name>/', views.jidogam, name='detail'),
]
