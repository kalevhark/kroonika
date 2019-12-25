from django.db import models
from markdownx.models import MarkdownxField
from markdownx.utils import markdownify

class Category(models.Model):
    name = models.CharField(max_length=20)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = "Teemad"


class Post(models.Model):
    title = models.CharField(max_length=255)
    # body = models.TextField()
    body = MarkdownxField()
    created_on = models.DateTimeField(auto_now_add=True)
    last_modified = models.DateTimeField(auto_now=True)
    categories = models.ManyToManyField('Category', related_name='posts')

    def __str__(self):
        return self.title

    # Create a property that returns the markdown instead
    @property
    def formatted_markdown(self):
        return markdownify(self.body)

    def body_summary(self):
        summary = self.body
        if summary.find('\n') > 0:
            summary = summary[:summary.find('\n')]
        return markdownify(summary[:300] + "...")

    class Meta:
        verbose_name_plural = "Postitused"


class Comment(models.Model):
    author = models.CharField(max_length=60)
    body = models.TextField()
    created_on = models.DateTimeField(auto_now_add=True)
    post = models.ForeignKey('Post', on_delete=models.CASCADE)

    def __str__(self):
        return self.body[:100]

    class Meta:
        verbose_name_plural = "Kommentaarid"