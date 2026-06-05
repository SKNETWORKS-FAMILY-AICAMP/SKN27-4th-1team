from django.urls import path
from . import views

app_name = 'archive'

urlpatterns = [
    path('sillokgwan/', views.sillokgwan_view, name='sillokgwan'),
    path('api/search/', views.sillok_search_api, name='sillok_search_api'),
]

