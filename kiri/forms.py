from django import forms
from django.conf import settings
from django.core.mail import send_mail

class KiriForm(forms.Form):

    name = forms.CharField(max_length=120, initial='valgalinn.ee')
    email_from = forms.EmailField(initial=settings.DEFAULT_FROM_EMAIL)
    email_to = forms.EmailField()
    subject = forms.CharField(max_length=70)
    message = forms.CharField(widget=forms.Textarea)

    def get_info(self):
        """
        Method that returns formatted information
        :return: name, email_from, email_to, subject, message
        """
        # Cleaned data
        cl_data = super().clean()

        name = cl_data.get('name').strip()
        email_from = cl_data.get('email_from')
        email_to = cl_data.get('email_to')
        subject = cl_data.get('subject')
        message = cl_data.get('message')

        return name, email_from, email_to, subject, message

    def send(self):

        name, email_from, email_to, subject, message = self.get_info()
        # send_mail(
        #     subject=subject,
        #     message=msg,
        #     from_email=email_from, # f'{name} <{email_from}>'
        #     recipient_list=[email_to]
        # )
        return email_to, subject