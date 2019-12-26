import re

from django.db import models
from markdownx.models import MarkdownxField
from markdownx.utils import markdownify

# Lisab numbri ja punkti vahele backslashi
def add_escape(matchobj):
    leiti = matchobj.group(0)
    return "\\".join([leiti[:-1], "."])

# Muudab teksti, et markdown ei märgistaks automaatselt nummerdatud liste
def escape_numberdot(string):
    # Otsime kas teksti alguses on arv ja punkt
    string_modified = re.sub(r"(\A)(\d+)*\.", add_escape, string)
    # Otsime kas lõigu alguses on arv ja punkt
    string_modified = re.sub(r"(\n)(\d+)*\.", add_escape, string_modified)
    return string_modified

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
        return markdownify(escape_numberdot(self.body))

    # Create a property that returns the summary markdown instead
    @property
    def formatted_markdown_summary(self):
        summary = self.body
        if summary.find('\n') > 0:
            summary = summary[:summary.find('\n')]
        return markdownify(escape_numberdot(summary[:300]) + "...")

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