#+
# Copyright 2012 MetaComplex, Corp.
# All rights reserved
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted providing that the following conditions
# are met:
# 1. Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright
#    notice, this list of conditions and the following disclaimer in the
#    documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE AUTHOR ``AS IS'' AND ANY EXPRESS OR
# IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR ANY
# DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS
# OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION)
# HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT,
# STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING
# IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
#
#####################################################################
import os

from django.conf.urls.defaults import include, patterns
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.views.static import serve
from django.conf import settings
from django.template.loader import add_to_builtins
from django.views.generic import TemplateView

from metanasUI.freeadmin.middleware import public
from metanasUI.freeadmin.views import adminInterface
from metanasUI.freeadmin.navtree import navtree

handler500 = 'freeadmin.views.server_error'
handler404 = 'django.views.defaults.page_not_found'

navtree.prepare_modelforms()

add_to_builtins('django.templatetags.i18n')

urlpatterns = patterns('',
    ('^$', adminInterface),
    (r'^reporting/graphs/(?P<path>.*)',
        public(serve),
        {'document_root': '/var/db/graphs/'}),
    (r'^media/(?P<path>.*)',
        public(serve),
        {'document_root': settings.MEDIA_ROOT}),
    (r'^static/(?P<path>.*)',
        public(serve),
        {'document_root': os.path.join(settings.HERE, "freeadmin/static") }),
    (r'^dojango/(?P<path>.*)$',
        public(serve),
        {'document_root': os.path.abspath(os.path.dirname(__file__)+'/dojango/')}),
    (r'^jsi18n/', 'django.views.i18n.javascript_catalog'),
    (r'^dojangogrid/', include('dojango.urls')),
    (r'^admin/', include('freeadmin.urls')),
    (r'^account/', include('account.urls')),
    (r'^system/', include('system.urls')),
    (r'^network/', include('network.urls')),
    (r'^storage/', include('storage.urls')),
    (r'^sharing/', include('sharing.urls')),
    (r'^services/', include('services.urls')),
    (r'^plugins/', include('plugins.urls')),
    )

urlpatterns += staticfiles_urlpatterns()
