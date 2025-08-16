from django import forms
from ibabi.models import ibabiSession

class ibabiSessionForm(forms.ModelForm):
    class Meta:
        model = ibabiSession
        fields = ['date', 'sector']
