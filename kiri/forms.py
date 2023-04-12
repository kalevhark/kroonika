from django import forms
from django.conf import settings
from django.core.mail import send_mail
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string

class KiriForm(forms.Form):

    name = forms.CharField(
        max_length=120,
        initial='valgalinn.ee',
        required=False,
        label='Saatja nimi'
    )
    email_from = forms.EmailField(
        initial=settings.DEFAULT_FROM_EMAIL,
        label='Saatja aadress'
    )
    email_to = forms.EmailField(
        label='Saaja aadress'
    )

    subject = forms.CharField(
        max_length=70,
        label='Pealkiri'
    )
    message = forms.CharField(
        widget=forms.Textarea,
        label='Kirja sisu'
    )
    file_field = forms.FileField(
        widget=forms.ClearableFileInput(attrs={'class': 'custom-file-input my-3', 'multiple': True}),
        required=False,
        label=''
    )

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

    def send(self, files):
        name, email_from, email_to, subject, message = self.get_info()
        if name:
            email_from = f'{name} <{email_from}>'

        # send_mail(
        #     subject=subject,
        #     message=msg,
        #     from_email=email_from, # f'{name} <{email_from}>'
        #     recipient_list=[email_to]
        # )

        merge_data = {
            'name': name,
            'subject': subject,
            'message': message,
            'email_from': email_from
        }
        html_content = render_to_string('kiri/email_base.html', merge_data)
        msg = EmailMultiAlternatives(
            subject,
            message,
            email_from,
            [email_to]
        )
        msg.attach_alternative(html_content, "text/html")

        import mimetypes
        if files: # kui failid lisatud
            for f in files:
                print(dir(f))
                print(f.name, f.file, f.content_type)
                msg.attach(f.name, f.read(), f.content_type)
                # filename, content and mimetype

        msg.send(fail_silently=False)

        return email_to, subject