from django import forms
from .models import Task


class TaskModelForm(forms.ModelForm):
    class Meta:
        model = Task
        fields = ['title', 'description', 'complete']
        widgets = {
            'title': forms.TextInput(
                attrs={'class':'rounded bg-white mx-auto my-2 p-1 w-full text-slate-700 '}
            ),
            'description':forms.Textarea(
                attrs={'class': 'rounded bg-white mx-auto my-2 p-1 w-full text-slate-700 outline outline-offset-2 outline-1'}
            )
        }
       
    def clean(self):
        cleaned_data = super().clean()
        title = cleaned_data.get("title")
        qs = Task.objects.filter(title=title)
        if self.instance:
            qs = qs.exclude(id=self.instance.id)  # these last two lines allow you to update the title/slug field without rasing the error.
        if qs.exists():
            raise forms.ValidationError(
                "This title is taken, please choose another"
            )