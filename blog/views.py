from django.shortcuts import render

from blog.forms import CommentForm
from blog.models import Post, Comment


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
    if request.method == "POST":
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