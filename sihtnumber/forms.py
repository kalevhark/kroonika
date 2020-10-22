from django import forms
from django.core.exceptions import ValidationError

class OtsiSihtnumberForm(forms.Form):
    aadressid = forms.CharField(
        max_length=10000,
        widget=forms.Textarea(attrs={'rows':20, 'cols':80}),
        help_text="Täisaadressid eraldi ridadele"
    )

    def clean_renewal_date(self):
        data = self.cleaned_data['aadressid']

        # Check if a date is not in the past.
        if len(data) == 0:
            raise ValidationError('Aadresse ei ole sisestatud')

        # Remember to always return the cleaned data.
        return data