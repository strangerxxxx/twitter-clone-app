from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.conf import settings
from django.core.paginator import Paginator
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy
from django.views.decorators.http import require_POST
from django.views.generic import DetailView
from django.views.generic.edit import CreateView

from .models import Post
from . import forms
from .mixins import PostPaginatedListView
from .utils import get_post_queryset, zip_posts_with_liked_status, redirect_to_referer


class PostListView(LoginRequiredMixin, PostPaginatedListView):
    template_name = 'post/post_list.html'
    model = Post

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        context['User'] = user
        context['description'] = 'タイムライン'
        context['zip'] = zip_posts_with_liked_status(user, context['post_list'])
        return context

    def get_queryset(self):
        user = self.request.user
        authors = list(user.following.all()) + [user]
        return get_post_queryset(Post.objects.filter(author__in=authors))


class PostCreateView(LoginRequiredMixin, CreateView):
    model = Post
    form_class = forms.PostCreationForm
    template_name = "post/post_create.html"
    success_url = reverse_lazy("post:post_list")
    description = "ツイートの作成"

    def form_valid(self, form):
        form.instance.author = self.request.user
        result = super().form_valid(form)
        messages.success(self.request, 'ツイートしました。')
        return result


@login_required
@require_POST
def favorite_view(request, pk):
    post = get_object_or_404(Post, pk=pk)
    user = request.user
    if post.liked_users.filter(pk=user.pk).exists():
        post.liked_users.remove(user)
        messages.warning(request, 'いいねを取り消しました。')
    else:
        post.liked_users.add(user)
        messages.success(request, 'いいねしました。')
    return redirect_to_referer(request)


@login_required
@require_POST
def delete_view(request, pk):
    post = get_object_or_404(Post, pk=pk)
    if post.author == request.user:
        post.delete()
        messages.warning(request, 'ツイートを削除しました。')
    else:
        messages.error(request, '自分のツイートのみ削除できます。')
    return redirect_to_referer(request)


class SearchPostListView(LoginRequiredMixin, PostPaginatedListView):
    template_name = 'post/search_list.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        context['User'] = user
        context['zip'] = zip_posts_with_liked_status(user, context['post_list'])
        return context

    def get_queryset(self):
        q_word = self.request.GET.get('query')
        queryset = get_post_queryset()
        if q_word:
            queryset = queryset.filter(content__icontains=q_word)
        return queryset


class PostStatusView(LoginRequiredMixin, DetailView):
    template_name = 'post/post_status.html'
    model = Post

    def get_queryset(self):
        return get_post_queryset()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        post = context['post']
        context['User'] = user
        context['pk'] = self.kwargs.get('pk')

        parent = None
        if post.parent_id:
            parent = get_post_queryset(
                Post.objects.filter(pk=post.parent_id)
            ).first()
        if parent:
            context['parent_post'] = parent
            context['parent_liked'] = parent.liked_users.filter(pk=user.pk).exists()
            context['parent_likes'] = parent.liked_count
            context['parent_reply_count'] = parent.reply_count
            context['parent_repost_count'] = parent.repost_count
        else:
            context['parent_post'] = None

        context['likes'] = post.liked_count
        context['reply_count'] = post.reply_count
        context['repost_count'] = post.repost_count
        context['liked'] = post.liked_users.filter(pk=user.pk).exists()

        reply_queryset = get_post_queryset(
            post.replies.all() | post.reposted.all()
        )
        reply_paginator = Paginator(reply_queryset, settings.POSTS_PER_PAGE)
        reply_page_obj = reply_paginator.get_page(self.request.GET.get('page'))
        context['reply_page_obj'] = reply_page_obj
        context['preserve_query'] = self.request.GET.copy()
        context['preserve_query'].pop('page', None)
        context['zip'] = zip_posts_with_liked_status(user, reply_page_obj)
        return context


@login_required
def reply_create_view(request, pk):
    post = get_object_or_404(Post, pk=pk)
    form = forms.PostCreationForm(request.POST or None)
    description = "返信の作成"
    if request.method == 'POST':
        if form.is_valid():
            reply = form.save(commit=False)
            reply.author = request.user
            reply.parent = post
            reply.content = "@" + post.author.username + " " + reply.content
            reply.save()
            messages.success(request, '返信しました。')
            return redirect('post:status', pk=post.pk)
        messages.error(request, '返信内容を入力してください。')

    context = {
        'form': form,
        'post': post,
        'description': description,
    }
    return render(request, 'post/post_create.html', context)


class ReplyPostListView(LoginRequiredMixin, PostPaginatedListView):
    """自分のツイートへの返信一覧（parent 参照で判定）。"""
    template_name = 'post/reply_list.html'
    model = Post

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        context['User'] = user
        context['zip'] = zip_posts_with_liked_status(user, context['post_list'])
        return context

    def get_queryset(self):
        return get_post_queryset(
            Post.objects.filter(parent__author=self.request.user)
        )


class LikedAccountsListView(LoginRequiredMixin, PostPaginatedListView):
    template_name = 'accounts/account_list.html'
    context_object_name = 'user_list'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['followings'] = self.request.user.following.all()
        context['description'] = "いいねしたユーザー一覧"
        return context

    def get_queryset(self):
        q_word = self.request.GET.get('query')
        post = get_object_or_404(Post, pk=self.kwargs['pk'])
        queryset = post.liked_users.all().prefetch_related('following')
        if q_word:
            queryset = queryset.filter(username__icontains=q_word)
        return queryset

    def get_paginate_by(self, queryset):
        return settings.USERS_PER_PAGE


@login_required
def repost_create_view(request, pk):
    post = get_object_or_404(Post, pk=pk)
    form = forms.PostCreationForm(request.POST or None)
    description = "リツイートの作成"
    if request.method == 'POST':
        if form.is_valid():
            repost = form.save(commit=False)
            repost.author = request.user
            repost.repost_parent = post
            repost.save()
            messages.success(request, 'リツイートしました。')
            return redirect('post:post_list')
        messages.error(request, 'リツイート内容を入力してください。')

    context = {
        'form': form,
        'post': post,
        'description': description,
    }
    return render(request, 'post/post_create.html', context)
