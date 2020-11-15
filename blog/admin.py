from django.contrib import admin
from markdownx.admin import MarkdownxModelAdmin

from blog.models import Post, Category, Comment

class PostAdmin(MarkdownxModelAdmin):
    pass

class CategoryAdmin(admin.ModelAdmin):
    pass

class CommentAdmin(admin.ModelAdmin):
    readonly_fields = ['inp_date']
    list_display = [
        'id',
        'inp_date',
        'remote_addr',
        'lyhi_kirjeldus',
    ]

    def lyhi_kirjeldus(self, obj):
        if len(obj.body) < 33:
            tekst = obj.body
        else:
            tekst = obj.body[:30] + '...'
        return tekst

    lyhi_kirjeldus.short_description = 'Vihje'

admin.site.register(Post, PostAdmin)
admin.site.register(Category, CategoryAdmin)
admin.site.register(Comment, CommentAdmin)
