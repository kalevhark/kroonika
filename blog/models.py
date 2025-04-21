import re

from django.db import models
from django.urls import reverse
from django.utils.text import slugify

from markdownx.models import MarkdownxField
from markdownx.utils import markdownify

# from wiki.models import escape_numberdot, add_markdownx_pildid, add_markdown_objectid

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
    body = MarkdownxField(
        'Lugu',
        help_text='<br>'.join(
            [
                'Tekst (MarkDown on toetatud);',
                'Pildi lisamiseks: [pilt_nnnn];',
                'Viite lisamiseks isikule, asutisele või kohale: nt [Mingi Isik]([isik_nnnn])',
            ]
        )
    )
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
        self.slug = slugify(value, allow_unicode=True)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        kwargs = {
            'slug': self.slug,
        }
        return reverse('blog:blog_detail', kwargs=kwargs)

    # # Create a property that returns the markdown instead
    @property
    def formatted_markdown(self):
        tekst = self.body
        if len(tekst) == 0:  # markdownx korrektseks tööks vaja, et sisu ei oleks null
            tekst = '<br>'
        # tekst = add_markdown_objectid(self, tekst)
        # tekst = add_markdownx_pildid(tekst)
        # viite_string = add_markdownx_viited(self)
        # return markdownify(escape_numberdot(tekst) + viite_string)
        # markdownified_text = markdownify(escape_numberdot(tekst) + viite_string)
        # if viite_string:  # viidete puhul ilmneb markdownx viga
        #     return fix_markdownified_text(markdownified_text)
        # else:
        #     return markdownified_text
        # return markdownify(escape_numberdot(tekst))
        return markdownify(tekst)

    # Create a property that returns the summary markdown instead
    @property
    def formatted_markdown_summary(self):
        summary = self.body
        if summary.find('\n') > 0:
            summary = summary[:summary.find('\n')]
        return markdownify(summary[:300] + "...")


    class Meta:
        verbose_name_plural = "Postitused"
        ordering = ['-created_on']


class Comment(models.Model):
    author = models.CharField(max_length=60)
    body = models.TextField()
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
