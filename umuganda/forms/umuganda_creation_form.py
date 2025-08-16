from django import forms
from ibabi.models import ibabiSession
from datetime import date as dt, timedelta

class ibabiSessionForm(forms.ModelForm):
    class Meta:
        model = ibabiSession
        fields = ['date']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        self.sector = kwargs.pop('sector', None)
        super().__init__(*args, **kwargs)

    def clean_date(self):
        date = self.cleaned_data.get('date')

        if not date:
            return date

        if date < dt.today():
            raise forms.ValidationError("ibabi date cannot be in the past.")

        if self.sector:
            recent_session = (
                ibabiSession.objects
                .filter(sector=self.sector)
                .order_by('-date')
                .first()
            )

            if recent_session:
                days_since_last = (date - recent_session.date).days
                if days_since_last < 29:
                    raise forms.ValidationError(
                        f"An ibabi was already scheduled on {recent_session.date}. "
                        f"You must wait at least 29 days before assigning a new one."
                    )

        return date
        