from wiki.forms import VihjeForm

def add_vihjevorm(request):
    return {
        'feedbackform': VihjeForm()
    }


