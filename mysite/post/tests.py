from io import BytesIO

from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, Client, RequestFactory
from django.urls import reverse
from PIL import Image

from post.models import Post
from post.utils import get_post_queryset, zip_posts_with_liked_status, redirect_to_referer


User = get_user_model()


def make_test_image(name='icon.png'):
    image_io = BytesIO()
    Image.new('RGB', (10, 10), color='red').save(image_io, format='PNG')
    image_io.seek(0)
    return SimpleUploadedFile(name, image_io.read(), content_type='image/png')


class PostViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='alice',
            email='alice@example.com',
            password='pass12345',
        )
        self.other = User.objects.create_user(
            username='bob',
            email='bob@example.com',
            password='pass12345',
        )
        self.client.login(username='alice', password='pass12345')

    def test_login_required_redirects_to_login(self):
        self.client.logout()
        response = self.client.get(reverse('post:post_list'))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('accounts:login'), response.url)

    def test_create_post(self):
        response = self.client.post(
            reverse('post:post_create'),
            {'content': 'hello world'},
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Post.objects.filter(content='hello world', author=self.user).exists())

    def test_create_post_rejects_empty_content(self):
        response = self.client.post(reverse('post:post_create'), {'content': '   '})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Post.objects.count(), 0)

    def test_favorite_and_delete_post(self):
        post = Post.objects.create(content='tweet', author=self.user)
        response = self.client.post(reverse('post:favorite', args=[post.pk]))
        self.assertEqual(response.status_code, 302)
        self.assertTrue(post.liked_users.filter(pk=self.user.pk).exists())

        response = self.client.post(reverse('post:delete', args=[post.pk]))
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Post.objects.filter(pk=post.pk).exists())

    def test_favorite_requires_post(self):
        post = Post.objects.create(content='tweet', author=self.user)
        response = self.client.get(reverse('post:favorite', args=[post.pk]))
        self.assertEqual(response.status_code, 405)

    def test_unfavorite_toggle(self):
        post = Post.objects.create(content='tweet', author=self.user)
        post.liked_users.add(self.user)

        response = self.client.post(reverse('post:favorite', args=[post.pk]))
        self.assertEqual(response.status_code, 302)
        self.assertFalse(post.liked_users.filter(pk=self.user.pk).exists())

    def test_delete_requires_post(self):
        post = Post.objects.create(content='tweet', author=self.user)
        response = self.client.get(reverse('post:delete', args=[post.pk]))
        self.assertEqual(response.status_code, 405)
        self.assertTrue(Post.objects.filter(pk=post.pk).exists())

    def test_cannot_delete_other_users_post(self):
        post = Post.objects.create(content='bob tweet', author=self.other)
        response = self.client.post(reverse('post:delete', args=[post.pk]))
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Post.objects.filter(pk=post.pk).exists())

    def test_reply_list_uses_parent_relationship(self):
        parent = Post.objects.create(content='parent tweet', author=self.user)
        reply = Post.objects.create(
            content='@alice thanks',
            author=self.other,
            parent=parent,
        )
        unrelated = Post.objects.create(
            content='@alice unrelated mention',
            author=self.other,
        )

        response = self.client.get(reverse('post:replies'))
        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertIn(reply.content, content)
        self.assertNotIn(unrelated.content, content)

    def test_reply_create_sets_parent(self):
        parent = Post.objects.create(content='parent', author=self.other)
        response = self.client.post(
            reverse('post:reply', args=[parent.pk]),
            {'content': 'my reply'},
        )
        self.assertEqual(response.status_code, 302)
        reply = Post.objects.get(parent=parent, author=self.user)
        self.assertIn('@bob', reply.content)

    def test_reply_create_rejects_empty_content(self):
        parent = Post.objects.create(content='parent', author=self.other)
        response = self.client.post(
            reverse('post:reply', args=[parent.pk]),
            {'content': ''},
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Post.objects.filter(parent=parent).exists())

    def test_repost_create(self):
        original = Post.objects.create(content='original tweet', author=self.other)
        response = self.client.post(
            reverse('post:repost', args=[original.pk]),
            {'content': 'repost comment'},
        )
        self.assertEqual(response.status_code, 302)
        repost = Post.objects.get(repost_parent=original, author=self.user)
        self.assertEqual(repost.content, 'repost comment')

    def test_repost_rejects_empty_content(self):
        original = Post.objects.create(content='original', author=self.other)
        response = self.client.post(
            reverse('post:repost', args=[original.pk]),
            {'content': '   '},
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Post.objects.filter(repost_parent=original).exists())

    def test_search_posts_by_query(self):
        Post.objects.create(content='django tutorial', author=self.user)
        Post.objects.create(content='python news', author=self.other)

        response = self.client.get(reverse('post:search'), {'query': 'django'})
        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertIn('django tutorial', content)
        self.assertNotIn('python news', content)

    def test_search_preserves_query_in_pagination(self):
        for i in range(25):
            Post.objects.create(content=f'django post {i}', author=self.user)

        response = self.client.get(reverse('post:search'), {'query': 'django', 'page': 2})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['preserve_query']['query'], 'django')

    def test_post_status_view(self):
        post = Post.objects.create(content='status tweet', author=self.user)
        response = self.client.get(reverse('post:status', args=[post.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'status tweet')

    def test_post_status_shows_replies(self):
        post = Post.objects.create(content='parent', author=self.user)
        reply = Post.objects.create(
            content='@alice reply text',
            author=self.other,
            parent=post,
        )
        response = self.client.get(reverse('post:status', args=[post.pk]))
        self.assertContains(response, reply.content)

    def test_liked_accounts_list(self):
        post = Post.objects.create(content='liked tweet', author=self.user)
        post.liked_users.add(self.other)

        response = self.client.get(reverse('post:favorited', args=[post.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'bob')

    def test_timeline_includes_following_users_posts(self):
        self.other.followers.add(self.user)
        Post.objects.create(content='bob timeline tweet', author=self.other)

        response = self.client.get(reverse('post:post_list'))
        self.assertContains(response, 'bob timeline tweet')

    def test_timeline_excludes_non_following_users(self):
        Post.objects.create(content='bob hidden tweet', author=self.other)

        response = self.client.get(reverse('post:post_list'))
        self.assertNotContains(response, 'bob hidden tweet')

    def test_timeline_pagination(self):
        for i in range(25):
            Post.objects.create(content=f'tweet {i}', author=self.user)

        response = self.client.get(reverse('post:post_list'))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['page_obj'].has_next())

        response = self.client.get(reverse('post:post_list') + '?page=2')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['post_list']), 5)


class PostFormTests(TestCase):
    def test_content_max_length(self):
        from post.forms import PostCreationForm

        form = PostCreationForm({'content': 'a' * 281})
        self.assertFalse(form.is_valid())
        self.assertIn('content', form.errors)

    def test_content_strips_whitespace(self):
        from post.forms import PostCreationForm

        form = PostCreationForm({'content': '  hello  '})
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data['content'], 'hello')


class PostUtilsTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='alice',
            email='alice@example.com',
            password='pass12345',
        )
        self.factory = RequestFactory()

    def test_get_post_queryset_annotates_counts(self):
        post = Post.objects.create(content='tweet', author=self.user)
        post.liked_users.add(self.user)
        Post.objects.create(content='reply', author=self.user, parent=post)

        annotated = get_post_queryset(Post.objects.filter(pk=post.pk)).first()
        self.assertEqual(annotated.liked_count, 1)
        self.assertEqual(annotated.reply_count, 1)

    def test_zip_posts_with_liked_status(self):
        post1 = Post.objects.create(content='a', author=self.user)
        post2 = Post.objects.create(content='b', author=self.user)
        post1.liked_users.add(self.user)

        zipped = list(zip_posts_with_liked_status(self.user, [post1, post2]))
        self.assertEqual(zipped, [(post1, True), (post2, False)])

    def test_zip_posts_with_anonymous_user(self):
        post = Post.objects.create(content='a', author=self.user)
        zipped = list(zip_posts_with_liked_status(AnonymousUser(), [post]))
        self.assertEqual(zipped, [(post, False)])

    def test_redirect_to_referer_uses_safe_referer(self):
        request = self.factory.post('/favorite/1/', HTTP_REFERER='http://testserver/search/')
        response = redirect_to_referer(request)
        self.assertEqual(response.status_code, 302)
        self.assertIn('/search/', response.url)

    def test_redirect_to_referer_falls_back_to_default(self):
        request = self.factory.post('/favorite/1/')
        response = redirect_to_referer(request)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('post:post_list'))

    def test_redirect_to_referer_rejects_external_host(self):
        request = self.factory.post(
            '/favorite/1/',
            HTTP_REFERER='http://evil.example.com/phishing',
        )
        response = redirect_to_referer(request)
        self.assertEqual(response.url, reverse('post:post_list'))
