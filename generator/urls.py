from django.urls import path

from . import views

app_name = 'generator'

urlpatterns = [
    path('storymaker/', views.goeijejoso, name='storymaker'),
    path('goeijejoso/', views.goeijejoso, name='goeijejoso'),
    path('generate/', views.generate_story_api, name='generate'),
]
