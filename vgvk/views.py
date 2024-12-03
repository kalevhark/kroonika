from django.shortcuts import render

# Create your views here.
def vgvk_index(request):
    return render(request, 'vgvk/vgvk_index.html', {})