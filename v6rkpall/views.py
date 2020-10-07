from django.shortcuts import render

def blog_index(request):
    context = {}
    return render(request, "v6rkpall/index.html", context)