from django import forms


class LoginForm(forms.Form):
    user_id = forms.CharField(max_length=150)
    password = forms.CharField(widget=forms.PasswordInput)


class SignupForm(forms.Form):
    user_id = forms.CharField(max_length=150)
    email = forms.EmailField()
    password = forms.CharField(widget=forms.PasswordInput)
    password_confirm = forms.CharField(widget=forms.PasswordInput)

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        password_confirm = cleaned_data.get('password_confirm')

        if password and password_confirm and password != password_confirm:
            raise forms.ValidationError('비밀번호가 일치하지 않습니다.')

        return cleaned_data
