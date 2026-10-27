from django import forms
from .models import Record

DEFAULT_INPUT_CLASSES = (
     "rounded w-full bg-white text-slate-700 my-4 p-2 outline outline-offset-1 focus:outline-none focus:ring focus:ring-blue-400"
)

class RecordForm(forms.ModelForm):
    class Meta:
        model = Record
        fields = ['date', 'project', 'task_description', 'duration_hours', 'status', 'notes']
        widgets = { 
            'date': forms.DateInput( format='%Y-%m-%d', attrs={'type': 'date'} ), # This forces the widget to output YYYY-MM-DD format so the browser can read it
            'task_description': forms.Textarea(attrs={'rows': 3}),
            'notes': forms.Textarea(attrs={'rows': 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            field.widget.attrs['class'] = DEFAULT_INPUT_CLASSES

