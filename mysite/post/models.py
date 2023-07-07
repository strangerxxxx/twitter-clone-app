from django.db import models

# Create your models here.

from django.contrib.auth import get_user_model


class Post(models.Model):
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    author = models.ForeignKey(get_user_model(), verbose_name='author',
                               on_delete=models.CASCADE)
    parent = models.ForeignKey('self', blank=True, null=True, related_name='replies',
                               on_delete=models.SET_NULL)
    liked_users = models.ManyToManyField(
        get_user_model(), related_name='favorite_posts', blank=True, symmetrical=False)
    repost_parent = models.ForeignKey('self', blank=True, null=True, related_name='reposted',
                                      on_delete=models.SET_NULL)

    def __str__(self):
        return self.content
