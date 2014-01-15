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
import logging

from django import template
from django.forms.forms import BoundField
from django.utils.html import conditional_escape
from django.utils.encoding import force_unicode

from dojango import forms
from metanasUI.system.models import Advanced

register = template.Library()

log = logging.getLogger('freeadmin.templatetags')


class FormRender(template.Node):

    def __init__(self, arg):
        self.arg = arg

    def render(self, context):
        form = context[self.arg]

        #TODO: cache
        #if adv_mode is None:
        adv_mode = Advanced.objects.order_by('-id')[0].adv_advancedmode
        #request.session['adv_mode'] = adv_mode
        form.advDefault = adv_mode

        if hasattr(form, "_meta") and hasattr(form._meta.model, '_admin'):
            model = form._meta.model
        else:
            model = None

        new_fields = form.fields.keys()
        output, hidden_fields, composed = [], [], {}

        top_errors = form.non_field_errors()
        if top_errors:
            output.append("<tr><td colspan=\"2\">%s</td></tr>" % (
                force_unicode(top_errors),
                ))
        else:
            if form.prefix:
                prefix = form.prefix + "-__all__"
            else:
                prefix = "__all__"
            output.append("""<tr>
<td colspan="2">
<input type="hidden" data-dojo-type="dijit.form.TextBox" name="%s" />
</td></tr>""" % (prefix,))

        if model:
            for label, fields in model._admin.composed_fields:
                for field in fields[1:]:
                    new_fields.remove(field)
                composed[fields[0]] = (label, fields)

        advanced_fields = getattr(form, 'advanced_fields', [])
        for field in new_fields:
            is_adv = field in advanced_fields
            _hide = ' style="display:none;"' if not adv_mode and is_adv else ''
            is_adv = ' class="advancedField"' if is_adv else ''
            if field in composed:
                label, fields = composed.get(field)
                html = u"""<tr><th><label%s>%s</label></th><td>""" % (
                    _hide,
                    label)
                for field in fields:
                    bf = BoundField(form, form.fields.get(field), field)
                    bf_errors = form.error_class(
                        [conditional_escape(error) for error in bf.errors]
                        )
                    html += unicode(bf_errors) + unicode(bf)
                html += u"</td></tr>"
                output.append(html)
            else:
                bf = BoundField(form, form.fields.get(field), field)
                bf_errors = form.error_class(
                    [conditional_escape(error) for error in bf.errors]
                    )
                if bf.is_hidden:
                    hidden_fields.append(unicode(bf))
                else:
                    if bf.help_text:
                        help_text = """<div data-dojo-type="dijit.Tooltip" data-dojo-props="connectId: '%shelp', showDelay: 200">%s</div><img id="%shelp" src="/static/images/ui/MoreInformation_16x16px.png" style="width:16px; height: 16px; cursor: help;" />""" % (bf.auto_id, bf.help_text, bf.auto_id)
                    else:
                        help_text = ""
                    html = u"""<tr%s%s><th>%s</th><td>%s%s %s</td></tr>""" % (
                        is_adv,
                        _hide,
                        bf.label_tag(),
                        bf_errors,
                        bf,
                        help_text,
                        )
                    output.append(html)

        if hidden_fields:
            str_hidden = u''.join(hidden_fields)
            output.append(str_hidden)

        return ''.join(output)


@register.tag(name="admin_form")
def do_admin_form(parser, token):
    try:
        tag_name, arg = token.contents.split(None, 1)
    except ValueError:
        raise template.TemplateSyntaxError("%r tag requires arguments" % (
            token.contents.split()[0],
            ))

    return FormRender(arg)