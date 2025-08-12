from django import forms
from .models import TimeEntry, Project, TimeEntryImage

class ReportForm(forms.Form):
    start_date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}))
    end_date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}))
    project = forms.ModelChoiceField(queryset=Project.objects.none(), required=False, empty_label="All Projects", widget=forms.Select(attrs={'class': 'form-select'}))

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if user:
            self.fields['project'].queryset = Project.objects.filter(user=user)


class MultiImageInput(forms.ClearableFileInput):
    allow_multiple_selected = True

class TimeEntryUpdateForm(forms.ModelForm):
    images = forms.ImageField(
        required=False,
        widget=MultiImageInput(attrs={'class': 'form-control', 'multiple': True}),
        help_text="You can select multiple images."
    )

    class Meta:
        model = TimeEntry
        fields = ['title', 'project', 'description', 'notes', 'category', 'images']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'project': forms.Select(attrs={'class': 'form-select'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'category': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if user:
            # Populate project choices with projects owned by the current user
            self.fields['project'].queryset = Project.objects.filter(user=user)
            self.fields['project'].empty_label = "No Project"

    def save(self, commit=True):
        instance = super().save(commit=commit)
        # Only attach images once the instance has a primary key
        image_files = self.files.getlist('images')
        if commit and image_files:
            TimeEntryImage.objects.bulk_create([
                TimeEntryImage(time_entry=instance, image=img) for img in image_files
            ])
        elif not commit:
            # Defer to caller if they save with commit=False
            self._pending_images = image_files
        return instance

    def save_m2m(self):
        super().save_m2m()
        # If commit=False path used and later manually saved:
        if hasattr(self, '_pending_images') and self._pending_images:
            TimeEntryImage.objects.bulk_create([
                TimeEntryImage(time_entry=self.instance, image=img) for img in self._pending_images
            ])
            del self._pending_images
