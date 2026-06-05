from django.urls import path

from . import views

app_name = 'regions'

urlpatterns = [
    path('regioninfo/', views.jidogam, name='regioninfo'),
    path('jidogam/', views.jidogam, name='jidogam'),
    path('list/', views.jidogam, name='list'),
    path('<str:region_name>/', views.jidogam, name='detail'),
]
