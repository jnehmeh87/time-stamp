from django import forms
from workspaces.models import Project

class ReportForm(forms.Form):
    start_date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}))
    end_date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}))
    project = forms.ModelChoiceField(queryset=Project.objects.none(), required=False, widget=forms.Select(attrs={'class': 'form-select', 'id': 'id_project'}))

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        if user:
            self.fields['project'].queryset = Project.objects.filter(organization__members=user)
