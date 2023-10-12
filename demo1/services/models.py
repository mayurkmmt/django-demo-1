from ckeditor_uploader.fields import RichTextUploadingField
from django.db import models
from django.utils.translation import get_language


class Service(models.Model):
    ISSUE = 'issue'
    ADDON = 'addon'

    category = models.CharField(max_length=20, choices=(
        (ISSUE, 'Issue'),
        (ADDON, 'Add-on'),
    ), default=ISSUE)
    name = models.CharField(max_length=30)
    slug = models.SlugField(help_text="Unique URL-friendly version of name.")
    description = models.TextField(blank=True,
                                   help_text="Supplemental text (add-ons)")
    icon = models.FileField(blank=True, upload_to='services')
    url = models.URLField(null=True, blank=True,
                          help_text=(f"Supplemental URL (defaults to service "
                                     f"detail page)"))

    priority = models.DecimalField(max_digits=5, decimal_places=2, default=0.0,
                                   help_text="Prioritize display ordering.")
    content = RichTextUploadingField(null=True, blank=True,
                                     help_text="Service information page \
                                                content")

    def get_name(self):
        lang = get_language()
        try:
            translation = self.servicetranslation_set.get(language=lang)
            return translation.name
        except self.servicetranslation_set.model.DoesNotExist:
            return self.name

    def get_description(self):
        lang = get_language()
        try:
            translation = self.servicetranslation_set.get(language=lang)
            return translation.description
        except self.servicetranslation_set.model.DoesNotExist:
            return self.description

    def get_url(self):
        lang = get_language()
        try:
            translation = self.servicetranslation_set.get(language=lang)
            return translation.url
        except self.servicetranslation_set.model.DoesNotExist:
            return self.url

    def get_content(self):
        lang = get_language()
        try:
            translation = self.servicetranslation_set.get(language=lang)
            return translation.content
        except self.servicetranslation_set.model.DoesNotExist:
            return self.content

    def __str__(self):
        return self.name


class ServiceTranslation(models.Model):
    service = models.ForeignKey(Service, on_delete=models.CASCADE)

    language = models.CharField(max_length=2, choices=(
        ('es', "Spanish"),
    ))

    name = models.CharField(max_length=30)
    description = models.TextField(blank=True)
    url = models.URLField(null=True, blank=True,
                          help_text=(f"Supplemental URL (defaults to service "
                                     f"detail page)"))
    content = RichTextUploadingField(null=True, blank=True,
                                     help_text="Service information page \
                                                content")

    class Meta:
        unique_together = ('service', 'language')
