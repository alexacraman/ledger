from django import forms
from .models import CommitteeNotification

BASE_INPUT_CLASS = ("text-slate-700 bg-blue-50 rounded border-2 border-slate-400 p-2 text-sm w-full block")

class CommitteeNotificationForm(forms.ModelForm):
    class Meta:
        model = CommitteeNotification
        fields = ["title", "message", "url"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['title'].widget.attrs.update({'class': BASE_INPUT_CLASS})
        self.fields['message'].widget.attrs.update({'class': BASE_INPUT_CLASS})
        self.fields['url'].widget.attrs.update({'class': BASE_INPUT_CLASS})
            