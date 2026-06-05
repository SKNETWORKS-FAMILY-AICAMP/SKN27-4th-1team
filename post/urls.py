from django.urls import path

from . import views

app_name = 'post'

urlpatterns = [
    path('community/', views.mokgyeokgirok, name='community'),
    path('mokgyeokgirok/', views.mokgyeokgirok, name='mokgyeokgirok'),
    path('list/', views.mokgyeokgirok, name='list'),
    path('create/', views.mokgyeokgirok, name='create'),
    path('<int:post_id>/', views.mokgyeokgirok, name='detail'),
    path('<int:post_id>/update/', views.mokgyeokgirok, name='update'),
    path('<int:post_id>/delete/', views.mokgyeokgirok, name='delete'),
]
