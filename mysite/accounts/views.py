from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView, LogoutView, PasswordChangeView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.decorators.http import require_POST
from django.views.generic.edit import FormView
from django.views.generic import TemplateView, CreateView
from django.urls import reverse_lazy
from django.contrib.auth import get_user_model, login, authenticate
from django.conf import settings
from django.core.paginator import Paginator
from django.shortcuts import render, redirect, get_object_or_404

from post.models import Post
from post.mixins import UserPaginatedListView
from post.utils import get_post_queryset, zip_posts_with_liked_status, redirect_to_referer
from . import forms
from .forms import UpLoadProfileImgForm


class MyLoginView(LoginView):
    form_class = forms.LoginForm
    template_name = "accounts/login.html"

    def form_valid(self, form):
        result = super().form_valid(form)
        messages.success(self.request, 'ログインしました。')
        return result


class MyLogoutView(LoginRequiredMixin, LogoutView):
    template_name = "accounts/logout.html"
    http_method_names = ['get', 'post', 'options']

    def get(self, request, *args, **kwargs):
        return self.render_to_response(self.get_context_data())

    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        messages.warning(request, 'ログアウトしました。')
        return response


class IndexView(TemplateView):
    template_name = "accounts/index.html"


class UserCreateView(CreateView):
    form_class = forms.CustomUserCreationForm
    template_name = "accounts/create.html"
    success_url = reverse_lazy("post:post_list")

    def form_valid(self, form):
        result = super().form_valid(form)
        messages.success(self.request, 'アカウントを作成しました。')
        username = form.cleaned_data.get("username")
        raw_pw = form.cleaned_data.get("password1")
        user = authenticate(username=username, password=raw_pw)
        login(self.request, user)
        return result


class UserChangeView(LoginRequiredMixin, FormView):
    template_name = 'accounts/edit.html'
    form_class = forms.UserChangeForm

    def form_valid(self, form):
        form.update(user=self.request.user)
        result = super().form_valid(form)
        messages.success(self.request, 'ユーザー情報を変更しました。')
        return result

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update({
            'username': self.request.user.username,
            'email': self.request.user.email,
            'introduction': self.request.user.introduction,
        })
        return kwargs

    def get_success_url(self):
        return reverse_lazy('accounts:profile', args=[self.request.user.username])


class UserPasswordChangeView(LoginRequiredMixin, PasswordChangeView):
    form_class = forms.UserPasswordChangeForm
    template_name = 'accounts/password_change.html'

    def get_success_url(self):
        return reverse_lazy('accounts:profile', args=[self.request.user.username])

    def form_valid(self, form):
        result = super().form_valid(form)
        messages.success(self.request, 'パスワードを変更しました。')
        return result


def user_profile_view(request, username):
    user = get_object_or_404(get_user_model(), username=username)
    me = request.user
    followers = user.followers.all()
    is_following = me.is_authenticated and user.followers.filter(pk=me.pk).exists()
    follower_count = followers.count()
    following_count = user.following.count()

    post_queryset = get_post_queryset(Post.objects.filter(author=user))
    paginator = Paginator(post_queryset, settings.POSTS_PER_PAGE)
    page_obj = paginator.get_page(request.GET.get('page'))
    preserve_query = request.GET.copy()
    preserve_query.pop('page', None)

    context = {
        'User': user,
        'zip': zip_posts_with_liked_status(me, page_obj),
        'page_obj': page_obj,
        'preserve_query': preserve_query,
        'is_following': is_following,
        'followers': followers,
        'follower_count': follower_count,
        'following_count': following_count,
    }
    return render(request, 'accounts/user_profile.html', context)


@login_required
@require_POST
def remove_view(request, username):
    user = get_object_or_404(get_user_model(), username=username)
    if user == request.user:
        messages.error(request, '自分自身のフォローは解除できません。')
    else:
        user.followers.remove(request.user)
        messages.warning(request, 'フォローを解除しました。')
    return redirect_to_referer(request, 'accounts:profile', username)


@login_required
@require_POST
def follow_view(request, username):
    user = get_object_or_404(get_user_model(), username=username)
    if user == request.user:
        messages.error(request, '自分自身はフォローできません。')
    else:
        user.followers.add(request.user)
        messages.success(request, 'フォローしました。')
    return redirect_to_referer(request, 'accounts:profile', username)


@login_required
def edit_profile_icon(request):
    if request.method != 'POST':
        form = UpLoadProfileImgForm()
    else:
        form = UpLoadProfileImgForm(request.POST, request.FILES)
        if form.is_valid():
            request.user.icon = form.cleaned_data['icon']
            request.user.save(update_fields=['icon'])
            messages.success(request, 'アイコンを変更しました。')
            return redirect('accounts:profile', request.user.username)
    context = {
        'form': form
    }
    return render(request, 'accounts/icon.html', context)


class AccountsListView(LoginRequiredMixin, UserPaginatedListView):
    template_name = 'accounts/account_list.html'
    context_object_name = 'user_list'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['followings'] = self.request.user.following.all()
        context['description'] = "ユーザー一覧"
        return context

    def get_queryset(self):
        q_word = self.request.GET.get('query')
        queryset = get_user_model().objects.all()
        if q_word:
            queryset = queryset.filter(username__icontains=q_word)
        return queryset


class FollowingListView(LoginRequiredMixin, UserPaginatedListView):
    template_name = 'accounts/account_list.html'
    context_object_name = 'user_list'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['followings'] = self.request.user.following.all()
        context['description'] = "@" + self.kwargs.get('username', "") + "さんのフォロー一覧"
        return context

    def get_queryset(self):
        q_word = self.request.GET.get('query')
        username = self.kwargs.get('username')
        queryset = get_object_or_404(
            get_user_model(), username=username).following.all()
        if q_word:
            queryset = queryset.filter(username__icontains=q_word)
        return queryset


class FollowerListView(LoginRequiredMixin, UserPaginatedListView):
    template_name = 'accounts/account_list.html'
    context_object_name = 'user_list'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['followings'] = self.request.user.following.all()
        context['description'] = "@" + self.kwargs.get('username', "") + "さんのフォロワー一覧"
        return context

    def get_queryset(self):
        q_word = self.request.GET.get('query')
        username = self.kwargs.get('username', "")
        queryset = get_object_or_404(
            get_user_model(), username=username).followers.all()
        if q_word:
            queryset = queryset.filter(username__icontains=q_word)
        return queryset
