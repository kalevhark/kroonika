from django.conf import settings
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.shortcuts import render

import requests

from blog.forms import CommentForm
from blog.models import Post, Category, Comment

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

def blog_index(request, pk=''):
    # params = dict(request.GET)
    # pk = request.GET.get('pk', '')
    category = request.GET.get('category', '')
    posts = Post.objects.all()

    try: # kas on valitud kategooria
        category = int(category)
        posts = posts.filter(categories__id=category)
    except:
        pass

    try: # kas on valitud mingi jutt
        pk = int(pk)
        post = Post.objects.get(pk=pk)
        posts = posts.filter(created_on__lte=post.created_on)
    except:
        pass

    page = request.GET.get('page', 1)
    paginator = Paginator(posts, 1)
    try:
        jutud = paginator.page(page)
    except PageNotAnInteger:
        jutud = paginator.page(1)
    except EmptyPage:
        jutud = paginator.page(paginator.num_pages)
    jutt = jutud[0]

    # print(jutud, len(jutud), jutud.has_next())
    return render(
        request,
        'blog/blog_index_infinite.html',
        {
            'jutud': jutud,
            'jutt': jutt,
            'pk': pk,
            'category': category,
        }
    )

# def blog_detail(request, pk):
#     post = Post.objects.get(pk=pk)
#     post_url = post.get_absolute_url()
#     comments = Comment.objects.filter(post=post)
#     posts_next = Post.objects.filter(created_on__lt=post.created_on)
#     post_next_url = posts_next[0].get_absolute_url() if posts_next else None
#
#     form = CommentForm()
#     if request.method == "POST" and check_recaptcha(request):
#         form = CommentForm(request.POST)
#         if form.is_valid():
#             remote_addr = request.META['REMOTE_ADDR']  # kasutaja IP aadress
#             http_user_agent = request.META['HTTP_USER_AGENT']  # kasutaja veebilehitseja
#             comment = Comment(
#                 author=form.cleaned_data["author"],
#                 body=form.cleaned_data["body"],
#                 post=post,
#                 remote_addr=remote_addr,
#                 http_user_agent=http_user_agent
#             )
#             comment.save()
#
#     context = {
#         "post": post,
#         'post_url': post_url,
#         'post_next_url': post_next_url,
#         "comments": comments,
#         "form": form
#     }
#     return render(request, "blog/blog_detail.html", context)
