from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render
from django.urls import reverse_lazy
from django.views.generic import FormView, TemplateView

from .forms import KiriForm

class KiriView(LoginRequiredMixin, FormView):
    redirect_field_name = 'next'
    template_name = 'kiri/contact.html'
    form_class = KiriForm
    success_url = reverse_lazy('kiri:success', kwargs={'email_to': '', 'subject': ''})

    def form_valid(self, form):
        # Calls the custom send method
        email_to, subject = form.send()
        self.success_url = reverse_lazy('kiri:success', kwargs={'email_to': email_to, 'subject': subject})
        return super().form_valid(form)

class KiriSuccessView(TemplateView):
    template_name = 'kiri/success.html'

    def get(self, request, email_to=None, subject=None, *args, **kwargs):
        context = {
            'email_to': email_to,
            'subject': subject
        }
        return render(request, self.template_name, context)


