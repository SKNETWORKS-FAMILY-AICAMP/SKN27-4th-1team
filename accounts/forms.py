from django import forms
from django.contrib.auth.models import User


def _field_attrs(placeholder, autocomplete=None):
    attrs = {"placeholder": placeholder}
    if autocomplete:
        attrs["autocomplete"] = autocomplete
    return attrs


class LoginForm(forms.Form):
    username = forms.CharField(
        max_length=150,
        error_messages={"required": "아이디를 입력해 주십시오."},
        widget=forms.TextInput(attrs=_field_attrs("기록자 ID", "username")),
    )
    password = forms.CharField(
        error_messages={"required": "비밀번호를 입력해 주십시오."},
        widget=forms.PasswordInput(attrs=_field_attrs("비밀번호", "current-password")),
    )
    next = forms.CharField(required=False, widget=forms.HiddenInput)


class SignupForm(forms.Form):
    username = forms.CharField(
        max_length=150,
        error_messages={"required": "아이디를 입력해 주십시오."},
        widget=forms.TextInput(attrs=_field_attrs("기록자 ID", "username")),
    )
    email = forms.EmailField(
        required=False,
        widget=forms.EmailInput(attrs=_field_attrs("선택 입력", "email")),
    )
    password = forms.CharField(
        min_length=8,
        error_messages={
            "required": "비밀번호를 입력해 주십시오.",
            "min_length": "비밀번호는 8자 이상이어야 합니다.",
        },
        widget=forms.PasswordInput(attrs=_field_attrs("8자 이상", "new-password")),
    )
    password_confirm = forms.CharField(
        error_messages={"required": "비밀번호 확인을 입력해 주십시오."},
        widget=forms.PasswordInput(attrs=_field_attrs("비밀번호 확인", "new-password")),
    )
    next = forms.CharField(required=False, widget=forms.HiddenInput)

    def clean_username(self):
        username = self.cleaned_data["username"].strip()
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError("이미 가입된 아이디입니다.")
        return username

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        password_confirm = cleaned_data.get('password_confirm')

        if password and password_confirm and password != password_confirm:
            raise forms.ValidationError('비밀번호가 일치하지 않습니다.')

        return cleaned_data
