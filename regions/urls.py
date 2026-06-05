from django.urls import path
from . import views

app_name = 'regions'

urlpatterns = [
    path('regioninfo/', views.regioninfo, name='regioninfo'),
    path('list/', views.regioninfo, name='list'),
    path('api/query/', views.region_query_api, name='region_query_api'),
    path('api/list/', views.region_list_api, name='region_list_api'),
    path('api/cities/', views.city_list_api, name='city_list_api'),
    path('api/story/', views.story_detail_api, name='story_detail_api'),
]
