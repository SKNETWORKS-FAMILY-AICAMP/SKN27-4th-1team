from django.urls import path
from . import views

app_name = 'post'

urlpatterns = [
    path('witness/', views.mokgyeokgirok_view, name='witness_board'),
    path('api/create/', views.post_create_api, name='post_create_api'),
    path('api/detail/<int:post_id>/', views.post_detail_api, name='post_detail_api'),
    path('api/like/<int:post_id>/', views.post_like_api, name='post_like_api'),
]

