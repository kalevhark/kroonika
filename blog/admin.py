from django.contrib import admin
# from markdownx.admin import MarkdownxModelAdmin

from blog.models import Post, Category, Comment

# class PostAdmin(MarkdownxModelAdmin):
class PostAdmin(admin.ModelAdmin):
    pass

class CategoryAdmin(admin.ModelAdmin):
    pass

class CommentAdmin(admin.ModelAdmin):
    pass

admin.site.register(Post, PostAdmin)
admin.site.register(Category, CategoryAdmin)
admin.site.register(Comment, CommentAdmin)
