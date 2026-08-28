from django.conf import settings
from django.views.generic import ListView


class PreserveQueryMixin:
    """ページネーション時に検索クエリなど GET パラメータを保持する。"""

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        query = self.request.GET.copy()
        query.pop('page', None)
        context['preserve_query'] = query
        return context


class PostPaginatedListView(PreserveQueryMixin, ListView):
    """投稿一覧用のページネーション付き ListView。"""

    def get_paginate_by(self, queryset):
        return settings.POSTS_PER_PAGE


class UserPaginatedListView(PreserveQueryMixin, ListView):
    """ユーザー一覧用のページネーション付き ListView。"""

    def get_paginate_by(self, queryset):
        return settings.USERS_PER_PAGE
