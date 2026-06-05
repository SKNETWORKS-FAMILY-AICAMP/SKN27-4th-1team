from django.urls import path
from . import views

app_name = 'regions'

urlpatterns = [
    path('jidogam/', views.jidogam_view, name='jidogam'),
    path('api/query/', views.region_query_api, name='region_query_api'),
]

