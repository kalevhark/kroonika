from django.conf import settings
from django.shortcuts import render

import requests

from blog.forms import CommentForm
from blog.models import Post, Comment

#
# reCAPTCHA kontrollifunktsioon
#
def check_recaptcha(request):
    if settings.DEBUG:
        return True

    data = request.POST
    # get the token submitted in the form
    recaptcha_response = data.get('g-recaptcha-response')
    # captcha verification
    url = f'https://www.google.com/recaptcha/api/siteverify'
    headers = {"Content-Type": "application/x-www-form-urlencoded; charset=utf-8"}
    payload = {
        'secret': settings.GOOGLE_RECAPTCHA_SECRET_KEY,
        'response': recaptcha_response
    }
    resp = requests.post(
        url,
        headers=headers,
        data=payload
    )
    result_json = resp.json()
    if result_json.get('success'):
        return True
    else:
        # Päringu teostamise IP aadress
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        print('recaptcha:', ip, result_json)
        return False

def blog_index(request):
    posts = Post.objects.all().order_by("-created_on")
    context = {"posts": posts}
    return render(request, "blog/blog_index.html", context)


def blog_category(request, category):
    posts = Post.objects.filter(categories__name__contains=category).order_by(
        "-created_on"
    )
    context = {"category": category, "posts": posts}
    return render(request, "blog/blog_category.html", context)


def blog_detail(request, pk):
    post = Post.objects.get(pk=pk)
    comments = Comment.objects.filter(post=post)

    form = CommentForm()
    if request.method == "POST" and check_recaptcha(request):
        form = CommentForm(request.POST)
        if form.is_valid():
            remote_addr = request.META['REMOTE_ADDR']  # kasutaja IP aadress
            http_user_agent = request.META['HTTP_USER_AGENT']  # kasutaja veebilehitseja
            comment = Comment(
                author=form.cleaned_data["author"],
                body=form.cleaned_data["body"],
                post=post,
                remote_addr=remote_addr,
                http_user_agent=http_user_agent
            )
            comment.save()

    context = {"post": post, "comments": comments, "form": form}
    return render(request, "blog/blog_detail.html", context)