from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm, PasswordChangeForm
from django.forms import ModelForm
from django import forms
from django.shortcuts import get_object_or_404


class LoginForm(AuthenticationForm):
    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)
        for field in self.fields.values():
            field.widget.attrs['placeholder'] = field.label
            field.widget.attrs['class'] = 'form-control'


class CustomUserCreationForm(UserCreationForm):
    class Meta:
        model = get_user_model()
        fields = UserCreationForm.Meta.fields + ('email',)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs['placeholder'] = field.label
            field.widget.attrs['class'] = 'form-control'


class UserChangeForm(ModelForm):
    class Meta:
        model = get_user_model()
        fields = (
            'username',
            'email',
            'introduction',
        )

    def __init__(self, username=None, email=None, introduction=None, *args, **kwargs):
        kwargs.setdefault('label_suffix', '')
        if username:
            user = get_object_or_404(get_user_model(), username=username)
            super().__init__(instance=user, *args, **kwargs)
        else:
            super().__init__(*args, **kwargs)
        # ユーザーの更新前情報をフォームに挿入
        if username:
            self.fields['username'].widget.attrs['value'] = username
        if email:
            self.fields['email'].widget.attrs['value'] = email
        if introduction:
            self.fields['introduction'].widget.attrs['value'] = introduction
        for field in self.fields.values():
            field.widget.attrs['placeholder'] = field.label
            field.widget.attrs['class'] = 'form-control'

    def update(self, user):
        fields = []
        if user.username != self.cleaned_data['username']:
            user.username = self.cleaned_data['username']
            fields.append('username')
        if user.email != self.cleaned_data['email']:
            user.email = self.cleaned_data['email']
            fields.append('email')
        if user.introduction != self.cleaned_data['introduction']:
            user.introduction = self.cleaned_data['introduction']
            fields.append('introduction')
        user.save(update_fields=fields)


class UserPasswordChangeForm(PasswordChangeForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs['placeholder'] = field.label
            field.widget.attrs['class'] = 'form-control'


class UpLoadProfileImgForm(forms.Form):
    icon = forms.ImageField()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs['placeholder'] = field.label
            field.widget.attrs['class'] = 'form-control'
