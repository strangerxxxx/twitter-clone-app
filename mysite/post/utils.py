from django.db.models import Count
from django.shortcuts import redirect
from django.utils.http import url_has_allowed_host_and_scheme

from .models import Post


def get_post_queryset(base_queryset=None):
    """投稿一覧用の共通クエリセット（関連データの prefetch と集計）。"""
    queryset = base_queryset if base_queryset is not None else Post.objects.all()
    return queryset.select_related(
        'author',
        'repost_parent',
        'repost_parent__author',
        'parent',
        'parent__author',
    ).prefetch_related(
        'liked_users',
        'replies',
        'reposted',
    ).annotate(
        liked_count=Count('liked_users', distinct=True),
        reply_count=Count('replies', distinct=True),
        repost_count=Count('reposted', distinct=True),
    ).order_by('-created_at')


def zip_posts_with_liked_status(user, posts):
    """投稿リストと、ユーザーがいいね済みかどうかの zip を返す。"""
    post_list = list(posts)
    if not user.is_authenticated or not post_list:
        return zip(post_list, [False] * len(post_list))

    liked_ids = set(
        Post.objects.filter(
            pk__in=[post.pk for post in post_list],
            liked_users=user,
        ).values_list('pk', flat=True)
    )
    return zip(post_list, [post.pk in liked_ids for post in post_list])


def redirect_to_referer(request, default='post:post_list', *args, **kwargs):
    """安全なリファラーへのリダイレクト。無効な場合はデフォルト URL へ。"""
    referer = request.META.get('HTTP_REFERER')
    if referer and url_has_allowed_host_and_scheme(
        referer,
        allowed_hosts={request.get_host()},
    ):
        return redirect(referer)
    return redirect(default, *args, **kwargs)
