from io import BytesIO

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, Client
from django.urls import reverse
from PIL import Image

from accounts.forms import UserChangeForm


User = get_user_model()


def make_test_image(name='icon.png'):
    image_io = BytesIO()
    Image.new('RGB', (10, 10), color='blue').save(image_io, format='PNG')
    image_io.seek(0)
    return SimpleUploadedFile(name, image_io.read(), content_type='image/png')


class AccountViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='alice',
            email='alice@example.com',
            password='pass12345',
            introduction='hello',
        )
        self.other = User.objects.create_user(
            username='bob',
            email='bob@example.com',
            password='pass12345',
        )
        self.client.login(username='alice', password='pass12345')

    def test_follow_and_remove(self):
        response = self.client.post(reverse('accounts:follow', args=['bob']))
        self.assertEqual(response.status_code, 302)
        self.assertTrue(self.other.followers.filter(pk=self.user.pk).exists())

        response = self.client.post(reverse('accounts:remove', args=['bob']))
        self.assertEqual(response.status_code, 302)
        self.assertFalse(self.other.followers.filter(pk=self.user.pk).exists())

    def test_follow_requires_post(self):
        response = self.client.get(reverse('accounts:follow', args=['bob']))
        self.assertEqual(response.status_code, 405)
        self.assertFalse(self.other.followers.filter(pk=self.user.pk).exists())

    def test_cannot_follow_self(self):
        response = self.client.post(reverse('accounts:follow', args=['alice']))
        self.assertEqual(response.status_code, 302)
        self.assertFalse(self.user.followers.filter(pk=self.user.pk).exists())

    def test_cannot_remove_self_follow(self):
        response = self.client.post(reverse('accounts:remove', args=['alice']))
        self.assertEqual(response.status_code, 302)
        self.assertFalse(self.user.followers.filter(pk=self.user.pk).exists())

    def test_user_registration_and_login(self):
        self.client.logout()
        response = self.client.post(
            reverse('accounts:create'),
            {
                'username': 'charlie',
                'email': 'charlie@example.com',
                'password1': 'pass12345',
                'password2': 'pass12345',
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(User.objects.filter(username='charlie').exists())

    def test_login_and_logout(self):
        self.client.logout()
        response = self.client.post(
            reverse('accounts:login'),
            {'username': 'alice', 'password': 'pass12345'},
        )
        self.assertEqual(response.status_code, 302)

        response = self.client.post(reverse('accounts:logout'))
        self.assertEqual(response.status_code, 302)

    def test_logout_page_shows_form_on_get(self):
        response = self.client.get(reverse('accounts:logout'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'ログアウト')

    def test_login_required_redirect(self):
        self.client.logout()
        response = self.client.get(reverse('accounts:search_accounts'))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('accounts:login'), response.url)

    def test_profile_view(self):
        response = self.client.get(reverse('accounts:profile', args=['alice']))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '@alice')

    def test_profile_view_anonymous_can_view(self):
        self.client.logout()
        response = self.client.get(reverse('accounts:profile', args=['alice']))
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context['is_following'])

    def test_profile_shows_is_following(self):
        self.other.followers.add(self.user)
        response = self.client.get(reverse('accounts:profile', args=['bob']))
        self.assertTrue(response.context['is_following'])

    def test_profile_pagination(self):
        from post.models import Post

        for i in range(25):
            Post.objects.create(content=f'profile tweet {i}', author=self.user)

        response = self.client.get(reverse('accounts:profile', args=['alice']))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['page_obj'].has_next())

    def test_user_edit_updates_profile(self):
        response = self.client.post(
            reverse('accounts:edit'),
            {
                'username': 'alice',
                'email': 'alice_new@example.com',
                'introduction': 'updated bio',
            },
        )
        self.assertEqual(response.status_code, 302)
        self.user.refresh_from_db()
        self.assertEqual(self.user.email, 'alice_new@example.com')
        self.assertEqual(self.user.introduction, 'updated bio')

    def test_password_change(self):
        response = self.client.post(
            reverse('accounts:password'),
            {
                'old_password': 'pass12345',
                'new_password1': 'newpass12345',
                'new_password2': 'newpass12345',
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            self.client.login(username='alice', password='newpass12345')
        )

    def test_accounts_list_search(self):
        response = self.client.get(reverse('accounts:search_accounts'), {'query': 'bob'})
        self.assertEqual(response.status_code, 200)
        user_list = response.context['user_list']
        self.assertEqual(len(user_list), 1)
        self.assertEqual(user_list[0].username, 'bob')

    def test_following_list(self):
        self.user.followers.add(self.other)
        response = self.client.get(reverse('accounts:followings', args=['bob']))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'alice')

    def test_follower_list(self):
        self.other.followers.add(self.user)
        response = self.client.get(reverse('accounts:followers', args=['bob']))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'alice')

    def test_edit_profile_icon(self):
        response = self.client.post(
            reverse('accounts:icon'),
            {'icon': make_test_image()},
        )
        self.assertEqual(response.status_code, 302)
        self.user.refresh_from_db()
        self.assertTrue(self.user.icon)

    def test_edit_profile_icon_get_shows_form(self):
        response = self.client.get(reverse('accounts:icon'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'icon')


class AccountFormTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='alice',
            email='alice@example.com',
            password='pass12345',
            introduction='bio',
        )

    def test_user_change_form_update_with_no_changes(self):
        form = UserChangeForm(
            username='alice',
            email='alice@example.com',
            introduction='bio',
            data={
                'username': 'alice',
                'email': 'alice@example.com',
                'introduction': 'bio',
            },
        )
        self.assertTrue(form.is_valid())
        form.update(user=self.user)
        self.user.refresh_from_db()
        self.assertEqual(self.user.email, 'alice@example.com')

    def test_user_change_form_updates_username(self):
        form = UserChangeForm(
            username='alice',
            email='alice@example.com',
            introduction='bio',
            data={
                'username': 'alice2',
                'email': 'alice@example.com',
                'introduction': 'bio',
            },
        )
        self.assertTrue(form.is_valid())
        form.update(user=self.user)
        self.user.refresh_from_db()
        self.assertEqual(self.user.username, 'alice2')
