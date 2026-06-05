from django.urls import path
from . import views

app_name = 'post'

urlpatterns = [
    path('witness/', views.mokgyeokgirok_view, name='witness_board'),
    path('api/create/', views.post_create_api, name='post_create_api'),
    path('api/list/', views.post_list_api, name='post_list_api'),
    path('api/detail/<int:post_id>/', views.post_detail_api, name='post_detail_api'),
    path('api/like/<int:post_id>/', views.post_like_api, name='post_like_api'),
    path('api/edit/<int:post_id>/', views.post_edit_api, name='post_edit_api'),
    path('api/delete/<int:post_id>/', views.post_delete_api, name='post_delete_api'),
]
