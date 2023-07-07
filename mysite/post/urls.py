from django.urls import path
from . import views


app_name = 'post'
urlpatterns = [
    path('post_create/', views.PostCreateView.as_view(), name='post_create'),
    path('search/', views.SearchPostListView.as_view(), name='search'),
    path('replies/', views.ReplyPostListView.as_view(), name='replies'),
    path('status/<int:pk>/', views.PostStatusView.as_view(), name='status'),
    path('reply/<int:pk>/', views.reply_create_view, name='reply'),
    path('repost/<int:pk>/', views.repost_create_view, name='repost'),
    path('favorite/<int:pk>/', views.favorite_view, name='favorite'),
    path('delete/<int:pk>/', views.delete_view, name='delete'),
    path('favorited/<int:pk>/',
         views.LikedAccountsListView.as_view(), name='favorited'),
    path('', views.PostListView.as_view(), name='post_list'),
]
