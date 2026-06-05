from django.urls import path
from . import views

app_name = 'regions'

urlpatterns = [
    path('jidogam/', views.jidogam, name='jidogam'),
    path('regioninfo/', views.jidogam, name='regioninfo'),
    path('list/', views.jidogam, name='list'),
    path('<str:region_name>/', views.jidogam, name='detail'),
    path('api/query/', views.region_query_api, name='region_query_api'),
]
