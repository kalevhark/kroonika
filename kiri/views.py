from email.mime.image import MIMEImage
import os

from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.mail import EmailMultiAlternatives
from django.shortcuts import render
from django.template.loader import render_to_string
from django.urls import reverse_lazy
from django.views.generic import FormView, TemplateView

from .forms import KiriForm

class KiriView(LoginRequiredMixin, FormView):
    redirect_field_name = 'next'
    template_name = 'kiri/contact.html'
    form_class = KiriForm
    success_url = reverse_lazy('kiri:success', kwargs={'email_to': '', 'subject': ''})

    # def form_valid(self, form):
    #     # Calls the custom send method
    #     email_to, subject = form.send()
    #     self.success_url = reverse_lazy('kiri:success', kwargs={'email_to': email_to, 'subject': subject})
    #     return super().form_valid(form)

    def get(self, request, *args, **kwargs):
        form = self.form_class()
        return render(request, self.template_name, {'form': form})

    def post(self, request, *args, **kwargs):
        form = self.form_class(request.POST, request.FILES)
        if form.is_valid():
            files = request.FILES.getlist('file_field')
            email_to, subject = form.send(files)
            self.success_url = reverse_lazy('kiri:success', kwargs={'email_to': email_to, 'subject': subject})
            return super().form_valid(form)
        else:
            return render(request, self.template_name, {'form': form})

class KiriSuccessView(TemplateView):
    template_name = 'kiri/success.html'

    def get(self, request, email_to=None, subject=None, *args, **kwargs):
        context = {
            'email_to': email_to,
            'subject': subject
        }
        return render(request, self.template_name, context)


# e-postiga j6ukukaarti saatmiseks
def send_j6ulukaart():

    saajad = ['valga@valga.ee', 'muuseum@valgamuuseum.ee', 'valgamaa@redcross.ee', 'valga@isamaalinemuuseum.ee']

    name = 'valgalinn.ee',
    email_from = 'valgalinn.ee <info@valgalinn.ee>'
    email_to = ['info@valgalinn.ee']
    bcc = ['kalev.hark@mail.ee', 'kalevhark@gmail.com', 'kalev.hark@sotsiaalkindlustusamet.ee']
    subject = 'valgalinn.ee jõulutervitus'
    message  = ''

    merge_data = {
        'name': name,
        'subject': subject,
        'message': message,
        'email_from': email_from,
        'valgalinn_ee_logo': 'valgalinn_ee_logo.png',
        'valgalinn_ee_j6ulukaart': 'valgalinn_ee_j6ulukaart2023.jpg',
        'valgalinn_ee_j6ulukaart_imagefile': 'VaMFp4053F2891-334_1_j6ul2023_kaart.jpg',
    }

    html_content = render_to_string('kiri/email_j6ulukaart2023.html', merge_data)
    msg = EmailMultiAlternatives(
        subject,
        message,
        email_from,
        email_to,
        bcc,
    )
    msg.attach_alternative(html_content, "text/html")
    msg.content_subtype = 'html'
    msg.mixed_subtype = 'related'

    print(settings.BASE_DIR)

    # lisame logo:
    img_path = os.path.join(settings.BASE_DIR, 'wiki/static/wiki/favicon-32x32.png')
    with open(img_path, 'rb') as f:
        banner_image = MIMEImage(f.read())
        banner_image.add_header('Content-ID', f'<{merge_data["valgalinn_ee_logo"]}>')
        msg.attach(banner_image)

    # lisame j6ulukaardi:
    img_path = os.path.join(settings.BASE_DIR, f'wiki/static/wiki/img/special/{merge_data["valgalinn_ee_j6ulukaart_imagefile"]}')
    with open(img_path, 'rb') as f:
        banner_image = MIMEImage(f.read())
        banner_image.add_header('Content-ID', f'<{merge_data["valgalinn_ee_j6ulukaart"]}>')
        msg.attach(banner_image)

    # import mimetypes
    # if files: # kui failid lisatud
    #     for f in files:
    #         print(dir(f))
    #         print(f.name, f.file, f.content_type)
    #         msg.attach(f.name, f.read(), f.content_type)
    #         # filename, content and mimetype

    msg.send(fail_silently=False)