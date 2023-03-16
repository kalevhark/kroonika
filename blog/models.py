import re

from django.db import models
from django.urls import reverse
from django.utils.text import slugify

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
    slug = models.SlugField(
        default='',
        editable=False,
        max_length=200,
    )
    title = models.CharField(
        max_length=255
    )
    body = MarkdownxField()
    created_on = models.DateTimeField(auto_now_add=True)
    last_modified = models.DateTimeField(auto_now=True)
    categories = models.ManyToManyField('Category', related_name='posts')
    total_accessed = models.PositiveIntegerField(
        verbose_name='Vaatamisi',
        default=0
    )

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        # Loome slugi teksti esimesest 10 sõnast max 200 tähemärki
        value = ' '.join(self.title.split(' ')[:10])[:200]
        # self.slug = slugify(value, allow_unicode=True)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        kwargs = {
            'pk': self.id,
        }
        return reverse('blog:blog_detail', kwargs=kwargs)

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
        ordering = ['-created_on']


class Comment(models.Model):
    author = models.CharField(max_length=60)
    body = models.TextField()
    # created_on = models.DateTimeField(auto_now_add=True)
    post = models.ForeignKey('Post', on_delete=models.CASCADE)
    remote_addr = models.CharField(
        'IP aadress',
        max_length=40,
        blank=True
    )
    http_user_agent = models.CharField(
        'Veebilehitseja',
        max_length=200,
        blank=True
    )
    # Tehnilised väljad
    inp_date = models.DateTimeField(
        'Lisatud',
        auto_now_add=True
    )

    def __str__(self):
        return self.body[:100]

    class Meta:
        verbose_name_plural = "Kommentaarid"