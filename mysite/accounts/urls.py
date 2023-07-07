from django.urls import path
from . import views

app_name = 'accounts'
urlpatterns = [
    path('login/', views.MyLoginView.as_view(), name="login"),
    path('logout/', views.MyLogoutView.as_view(), name="logout"),
    path('create/', views.UserCreateView.as_view(), name="create"),
    path('edit/', views.UserChangeView.as_view(), name="edit"),
    path('icon/', views.edit_profile_icon, name="icon"),
    path('password/', views.UserPasswordChangeView.as_view(), name="password"),
    path('accounts/', views.AccountsListView.as_view(), name="search_accounts"),
    path('@<str:username>/followings/',
         views.FollowingListView.as_view(), name="followings"),
    path('@<str:username>/followers/',
         views.FollowerListView.as_view(), name="followers"),
    path('@<str:username>/remove/', views.remove_view, name="remove"),
    path('@<str:username>/follow/', views.follow_view, name="follow"),
    path('@<str:username>/', views.user_profile_view, name='profile'),
]
