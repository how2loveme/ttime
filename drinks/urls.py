from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('menu/', views.menu_list, name='menu_list'),
    path('vote/<int:session_id>/', views.vote, name='vote'),
    path('vote/<int:session_id>/submit/', views.vote_submit, name='vote_submit'),
    path('vote/<int:session_id>/stats/', views.stats, name='stats'),
    path('vote/<int:session_id>/comment/', views.add_comment, name='add_comment'),
]
