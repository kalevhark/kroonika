import re

# https://django-allauth.readthedocs.io/en/latest/forms.html
from allauth.account.forms import LoginForm
from allauth.account.forms import SignupForm

from django import forms

class MyCustomLoginForm(LoginForm):
    error_messages = {
        "account_inactive": "See konto on hetkel mitteaktiivne.",
        "email_password_mismatch": "Vale e-maili aadress ja/või salasõna.",
        "username_password_mismatch": "Vale kasutajanimi ja/või salasõna.",
    }

    # def login(self, *args, **kwargs):
        # Add your own processing here.
        # You must return the original result.
        # return super(MyCustomLoginForm, self).login(*args, **kwargs)

class MyCustomSignupForm(SignupForm):

    def clean(self):
        super(MyCustomSignupForm, self).clean()
        email = self.cleaned_data.get("email")
        pattern = re.compile(r"\.")
        if email and len(pattern.findall(email.split('@')[0])) > 1:
            print('Imelik e-posti aadress:', email)
            raise forms.ValidationError('imelik e-posti aadress')
        return self.cleaned_data