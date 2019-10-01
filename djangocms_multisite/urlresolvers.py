# -*- coding: utf-8 -*-
from __future__ import absolute_import, print_function, unicode_literals
import sys

from django.conf import settings
from django.conf.urls import url, include
from django.contrib.sites.models import Site
from django.urls import URLResolver as RegexURLResolver
from django.dispatch import receiver

from cms.apphook_pool import apphook_pool
from cms.appresolver import get_app_patterns
from cms.constants import SLUG_REGEXP
from cms.signals import urls_need_reloading
from cms.views import details

MULTISITE_PATTERNS = {}
if settings.APPEND_SLASH:
    regexp = r'^(?P<slug>%s)/$' % SLUG_REGEXP
else:
    regexp = r'^(?P<slug>%s)$' % SLUG_REGEXP


@receiver(urls_need_reloading, dispatch_uid='cms_clear_multisite_patterns')
def clear_multisite_patterns(*args, **kwargs):
    global MULTISITE_PATTERNS
    MULTISITE_PATTERNS = {}


class CMSMultisiteRegexURLResolver(RegexURLResolver):
    @property
    def url_patterns(self):
        # Don't tweak anything if it's migration-related operation
        if ('makemigrations' in sys.argv or 'migrate' in sys.argv):
            return []

        site = Site.objects.get_current()
        try:
            return MULTISITE_PATTERNS[site.pk]
        except KeyError:

            if apphook_pool.get_apphooks():
                # If there are some application urls, use special resolver,
                # so we will have standard reverse support.
                urlpatterns = get_app_patterns()
            else:
                urlpatterns = []

            urlpatterns.extend([
                url(r'^cms_wizard/', include('cms.wizards.urls')),
                url(regexp, details, name='pages-details-by-slug'),
                url(r'^$', details, {'slug': ''}, name='pages-root'),
            ])
            MULTISITE_PATTERNS[site.pk] = urlpatterns
        return MULTISITE_PATTERNS[site.pk]


def cms_multisite_url(regex, view, kwargs=None, name=None, prefix=''):
    if isinstance(view, (list, tuple)):
        # For include(...) processing.
        urlconf_module, app_name, namespace = view
        return CMSMultisiteRegexURLResolver(regex, urlconf_module, kwargs, app_name=app_name, namespace=namespace)
    else:
        return url(regex, view, kwargs, name, prefix)
