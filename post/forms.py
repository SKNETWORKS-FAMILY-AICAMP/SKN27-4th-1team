from django import forms


class WitnessPostForm(forms.Form):
    title = forms.CharField(max_length=100)
    region = forms.CharField(max_length=100, required=False)
    content = forms.CharField(widget=forms.Textarea)
