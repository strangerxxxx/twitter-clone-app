from django import forms
from .models import Post


class PostCreationForm(forms.ModelForm):
    class Meta:
        model = Post
        fields = ('content',)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs['placeholder'] = "いまどうしてる？"
            field.widget.attrs['class'] = 'form-control'
            field.widget.attrs[
                'onkeydown'] = "if(event.ctrlKey&&event.keyCode==13){document.getElementById('submit').click();return false};"

    def clean_content(self):
        content = self.cleaned_data['content'].strip()
        if not content:
            raise forms.ValidationError('ツイート内容を入力してください。')
        if len(content) > 280:
            raise forms.ValidationError('ツイートは280文字以内で入力してください。')
        return content
