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

import glob
import os
import pwd
import re
import shutil
import subprocess

from django.forms import FileField
from django.conf import settings
from django.contrib.formtools.wizard import FormWizard
from django.shortcuts import render_to_response
from django.utils.decorators import method_decorator
from django.utils.translation import ugettext_lazy as _
from django.views.decorators.csrf import csrf_protect
from django.http import Http404

from dojango import forms
from metanasUI import choices
from metanasUI.common.forms import ModelForm, Form
from metanasUI.freeadmin.forms import CronMultiple
from metanasUI.middleware.notifier import notifier
from metanasUI.storage.models import MountPoint
from metanasUI.system import models


class FileWizard(FormWizard):

    def __init__(self, *args, **kwargs):
        self.templates = kwargs.pop('templates', [])
        self.saved_prefix = kwargs.pop("prefix", '')
        super(FileWizard, self).__init__(*args, **kwargs)

    @method_decorator(csrf_protect)
    def __call__(self, request, *args, **kwargs):
        """
        IMPORTANT
        This method was stolen from FormWizard.__call__

        This was necessary because the original code doesn't accept File Upload
        The reason of this is because there is no clean way to hold the information
        of an uploaded file across steps

        Also, an extra context is used to set the ajax post path/url
        """
        if 'extra_context' in kwargs:
            self.extra_context.update(kwargs['extra_context'])
        self.extra_context.update({'postpath': request.path})
        current_step = self.determine_step(request, *args, **kwargs)
        self.parse_params(request, *args, **kwargs)
        self.previous_form_list = []
        for i in range(current_step):
            f = self.get_form(i, request.POST, request.FILES)
            if not self._check_security_hash(request.POST.get("hash_%d" % i, ''),
                                             request, f):
                return self.render_hash_failure(request, i)

            if not f.is_valid():
                return self.render_revalidation_failure(request, i, f)
            else:
                self.process_step(request, f, i)
                self.previous_form_list.append(f)
        if request.method == 'POST':
            form = self.get_form(current_step, request.POST, request.FILES)
        else:
            form = self.get_form(current_step)
        if form.is_valid():
            self.process_step(request, form, current_step)
            next_step = current_step + 1

            if next_step == self.num_steps():
                return self.done(request, self.previous_form_list + [form])
            else:
                form = self.get_form(next_step)
                self.step = current_step = next_step

        return self.render(form, request, current_step)

    def get_form(self, step, data=None, files=None):
        """
        This is also required to pass request.FILES to the form
        """
        if files is not None:
            if step >= self.num_steps():
                raise Http404('Step %s does not exist' % step)
            return self.form_list[step](data, files, prefix=self.prefix_for_step(step), initial=self.initial.get(step, None))
        else:
            return super(FileWizard, self).get_form(step, data)

    def done(self, request, form_list):
        response = render_to_response('system/done.html', {
            #'form_list': form_list,
            'retval': getattr(self, 'retval', None),
        })
        if not request.is_ajax():
            response.content = ("<html><body><textarea>"
            + response.content +
            "</textarea></boby></html>")
        return response

    def get_template(self, step):
        if self.templates:
            for i, tpl in enumerate(self.templates):
                if '%s' in tpl:
                    self.templates[i] = tpl % step
            return self.templates
        return ['system/wizard_%s.html' % step, 'system/wizard.html']

    def process_step(self, request, form, step):
        super(FileWizard, self).process_step(request, form, step)
        """
        We execute the form done method if there is one, for each step
        """
        if hasattr(form, 'done'):
            retval = form.done(request=request,
                previous_form_list=self.previous_form_list)
            if step == self.num_steps() - 1:
                self.retval = retval

    def render(self, form, request, step, context=None):
        """
        IMPORTANT
        Stole from django to replace Dojango fields

        Renders the given Form object, returning an HttpResponse.
        """
        old_data = request.POST
        prev_fields = []
        if old_data:
            hidden = forms.HiddenInput()
            # Collect all data from previous steps and render it as HTML hidden fields.
            for i in range(step):
                old_form = self.get_form(i, old_data)
                hash_name = 'hash_%s' % i
                for bf in old_form:
                    html = bf.as_hidden()
                    prev_fields.append(
                        html.replace('type="hidden"',
                            'type="hidden" data-dojo-type="dijit.form.TextBox"')
                        )
                prev_fields.append(hidden.render(hash_name, old_data.get(hash_name, self.security_hash(request, old_form))))
        return self.render_template(request, form, ''.join(prev_fields), step, context)

    def render_template(self, request, *args, **kwargs):
        response = super(FileWizard, self).render_template(request, *args, **kwargs)
        # This is required for the workaround dojo.io.frame for file upload
        if not request.is_ajax():
            response.content = ("<html><body><textarea>"
            + response.content +
            "</textarea></boby></html>")
        return response

    def prefix_for_step(self, step):
        "Given the step, returns a Form prefix to use."
        return '%s%s' % (self.saved_prefix, str(step))


class SettingsForm(ModelForm):

    class Meta:
        model = models.Settings
        widgets = {
            'stg_timezone': forms.widgets.FilteringSelect(),
            'stg_language': forms.widgets.FilteringSelect(),
        }

    def __init__(self, *args, **kwargs):
        super(SettingsForm, self).__init__(*args, **kwargs)
        self.instance._original_stg_guiprotocol = self.instance.stg_guiprotocol
        self.instance._original_stg_guiaddress = self.instance.stg_guiaddress
        self.instance._original_stg_guiport = self.instance.stg_guiport
        self.instance._original_stg_syslogserver = self.instance.stg_syslogserver
        self.fields['stg_language'].choices = settings.LANGUAGES
        self.fields['stg_language'].label = _("Language (Require UI reload)")
        self.fields['stg_guiaddress'] = forms.ChoiceField(
            label=self.fields['stg_guiaddress'].label
            )
        self.fields['stg_guiaddress'].choices = [['0.0.0.0', '0.0.0.0']] + list(choices.IPChoices())

    def clean_stg_guiport(self):
        val = self.cleaned_data.get("stg_guiport")
        if val == '':
            return val
        try:
            val = int(val)
            if val < 1 or val > 65535:
                raise forms.ValidationError(_("You must specify a number between 1 and 65535, inclusive."))
        except ValueError:
            raise forms.ValidationError(_("Number is required."))
        return val

    def save(self):
        super(SettingsForm, self).save()
        if self.instance._original_stg_syslogserver != self.instance.stg_syslogserver:
            notifier().restart("syslogd")
        notifier().reload("timeservices")

    def done(self, request, events):
        if self.instance._original_stg_guiprotocol != self.instance.stg_guiprotocol or \
            self.instance._original_stg_guiaddress != self.instance.stg_guiaddress or \
            self.instance._original_stg_guiport != self.instance.stg_guiport:
            if self.instance.stg_guiaddress == "0.0.0.0":
                address = request.META['HTTP_HOST'].split(':')[0]
            else:
                address = self.instance.stg_guiaddress
            newurl = "%s://%s" % (self.instance.stg_guiprotocol,
                                    address
                                    )
            if self.instance.stg_guiport != '':
                newurl += ":" + self.instance.stg_guiport
            if self.instance._original_stg_guiprotocol == 'http':
                notifier().start_ssl("nginx")
            events.append("restartHttpd('%s')" % newurl)


class NTPForm(ModelForm):

    force = forms.BooleanField(label=_("Force"), required=False)

    class Meta:
        model = models.NTPServer

    def __init__(self, *args, **kwargs):
        super(NTPForm, self).__init__(*args, **kwargs)
        self.usable = True

    def clean_ntp_address(self):
        addr = self.cleaned_data.get("ntp_address")
        p1 = subprocess.Popen(["ntpq", "-c", "rv", addr],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        data = p1.communicate()[0]
        #TODO: ntpq does not return error code in case of errors
        if not re.search(r'version=', data):
            self.usable = False
        return addr

    def clean_ntp_maxpoll(self):
        maxp = self.cleaned_data.get("ntp_maxpoll")
        minp = self.cleaned_data.get("ntp_minpoll")
        if not maxp > minp:
            raise forms.ValidationError(_("Max Poll should be higher than Min Poll"))
        return maxp

    def clean(self):
        cdata = self.cleaned_data
        if not cdata.get("force", False) and not self.usable:
            self._errors['ntp_address'] = self.error_class([_("Server could not be reached. Check \"Force\" to continue regardless.")])
            del cdata['ntp_address']
        return cdata

    def save(self):
        super(NTPForm, self).save()
        notifier().start("mx-ntpd")
        notifier().restart("ntpd")


class AdvancedForm(ModelForm):

    class Meta:
        exclude = ('adv_zeroconfbonjour', 'adv_tuning', 'adv_firmwarevc', 'adv_systembeep')
        model = models.Advanced

    def __init__(self, *args, **kwargs):
        super(AdvancedForm, self).__init__(*args, **kwargs)
        self.instance._original_adv_motd = self.instance.adv_motd
        self.instance._original_adv_consolemenu = self.instance.adv_consolemenu
        self.instance._original_adv_powerdaemon = self.instance.adv_powerdaemon
        self.instance._original_adv_serialconsole = self.instance.adv_serialconsole
        self.instance._original_adv_consolescreensaver = self.instance.adv_consolescreensaver
        self.instance._original_adv_consolemsg = self.instance.adv_consolemsg
        self.instance._original_adv_advancedmode = self.instance.adv_advancedmode

    def save(self):
        super(AdvancedForm, self).save()
        if self.instance._original_adv_motd != self.instance.adv_motd:
            notifier().start("motd")
        if self.instance._original_adv_consolemenu != self.instance.adv_consolemenu:
            notifier().start("ttys")
        if self.instance._original_adv_powerdaemon != self.instance.adv_powerdaemon:
            notifier().restart("powerd")
        if self.instance._original_adv_serialconsole != self.instance.adv_serialconsole:
            notifier().start("ttys")
            notifier().start("loader")
        if self.instance._original_adv_consolescreensaver != self.instance.adv_consolescreensaver:
            if self.instance.adv_consolescreensaver == 0:
                notifier().stop("saver")
            else:
                notifier().start("saver")
            notifier().start("loader")

    def done(self, request, events):
        if self.instance._original_adv_consolemsg != self.instance.adv_consolemsg:
            if self.instance.adv_consolemsg:
                events.append("_msg_start()")
            else:
                events.append("_msg_stop()")
        if self.instance._original_adv_advancedmode != self.instance.adv_advancedmode:
            #Invalidate cache
            request.session.pop("adv_mode", None)


class EmailForm(ModelForm):
    em_pass1 = forms.CharField(
        label=_("Password"),
        widget=forms.PasswordInput,
        required=False)
    em_pass2 = forms.CharField(
        label=_("Password confirmation"),
        widget=forms.PasswordInput,
        help_text=_("Enter the same password as above, for verification."),
        required=False)

    class Meta:
        model = models.Email
        exclude = ('em_pass',)

    def __init__(self, *args, **kwargs):
        super(EmailForm, self).__init__(*args, **kwargs)
        try:
            self.fields['em_pass1'].initial = self.instance.em_pass
            self.fields['em_pass2'].initial = self.instance.em_pass
        except:
            pass
        self.fields['em_smtp'].widget.attrs['onChange'] = ('javascript:'
            'toggleGeneric("id_em_smtp", ["id_em_pass1", "id_em_pass2", '
            '"id_em_user"], true);')
        ro = True

        if len(self.data) > 0:
            if self.data.get("em_smtp", None) == "on":
                ro = False
        else:
            if self.instance.em_smtp == True:
                ro = False
        if ro:
            self.fields['em_user'].widget.attrs['disabled'] = 'disabled'
            self.fields['em_pass1'].widget.attrs['disabled'] = 'disabled'
            self.fields['em_pass2'].widget.attrs['disabled'] = 'disabled'

    def clean_em_user(self):
        if self.cleaned_data['em_smtp'] == True and \
                self.cleaned_data['em_user'] == "":
            raise forms.ValidationError(_("This field is required"))
        return self.cleaned_data['em_user']

    def clean_em_pass1(self):
        if self.cleaned_data['em_smtp'] == True and \
                self.cleaned_data['em_pass1'] == "":
            raise forms.ValidationError(_("This field is required"))
        return self.cleaned_data['em_pass1']

    def clean_em_pass2(self):
        if self.cleaned_data['em_smtp'] == True and \
                self.cleaned_data.get('em_pass2', "") == "":
            raise forms.ValidationError(_("This field is required"))
        pass1 = self.cleaned_data.get("em_pass1", "")
        pass2 = self.cleaned_data.get("em_pass2", "")
        if pass1 != pass2:
            raise forms.ValidationError(_("The two password fields didn't match."))
        return pass2

    def save(self, commit=True):
        email = super(EmailForm, self).save(commit=False)
        if commit:
            email.em_pass = self.cleaned_data['em_pass2']
            email.save()
        return email


class SSLForm(ModelForm):

    class Meta:
        model = models.SSL

    def save(self):
        super(SSLForm, self).save()
        notifier().start_ssl("nginx")


class SMARTTestForm(ModelForm):

    class Meta:
        model = models.SMARTTest
        widgets = {
            'smarttest_hour': CronMultiple(
                attrs={'numChoices': 24, 'label': _("hour")}
                ),
            'smarttest_daymonth': CronMultiple(
                attrs={'numChoices': 31, 'start': 1, 'label': _("day of month")}
                ),
            'smarttest_dayweek': forms.CheckboxSelectMultiple(
                choices=choices.WEEKDAYS_CHOICES
                ),
            'smarttest_month': forms.CheckboxSelectMultiple(
                choices=choices.MONTHS_CHOICES
                ),
        }

    def __init__(self, *args, **kwargs):
        if 'instance' in kwargs:
            ins = kwargs.get('instance')
            ins.smarttest_month = ins.smarttest_month.replace("10", "a").replace("11", "b").replace("12", "c")
            if ins.smarttest_daymonth == "..":
                ins.smarttest_daymonth = '*/1'
            elif ',' in ins.smarttest_daymonth:
                days = [int(day) for day in ins.smarttest_daymonth.split(',')]
                gap = days[1] - days[0]
                everyx = range(0, 32, gap)[1:]
                if everyx == days:
                    ins.smarttest_daymonth = '*/%d' % gap
            if ins.smarttest_hour == "..":
                ins.smarttest_hour = '*/1'
            elif ',' in ins.smarttest_hour:
                hours = [int(hour) for hour in ins.smarttest_hour.split(',')]
                gap = hours[1] - hours[0]
                everyx = range(0, 24, gap)
                if everyx == hours:
                    ins.smarttest_hour = '*/%d' % gap
        super(SMARTTestForm, self).__init__(*args, **kwargs)
        self.fields.keyOrder.remove('smarttest_disks')
        self.fields.keyOrder.insert(0, 'smarttest_disks')

    def save(self):
        super(SMARTTestForm, self).save()
        notifier().restart("smartd")

    def clean_smarttest_disks(self):
        disks = self.cleaned_data.get("smarttest_disks")
        used_disks = []
        for disk in disks:
            qs = models.SMARTTest.objects.filter(
                smarttest_disks__in=[disk]
                )
            if self.instance.id:
                qs = qs.exclude(id=self.instance.id)
            if qs.count() > 0:
                used_disks.append(disk.disk_name)
        if used_disks:
            raise forms.ValidationError(
                _("The following disks already have tests for this type: "
                    "%s" % (
                        ', '.join(used_disks),
                    ),
                    )
                )
        return disks

    def clean_smarttest_hour(self):
        h = self.cleaned_data.get("smarttest_hour")
        if h.startswith('*/'):
            each = int(h.split('*/')[1])
            if each == 1:
                return ".."
        return h

    def clean_smarttest_daymonth(self):
        h = self.cleaned_data.get("smarttest_daymonth")
        if h.startswith('*/'):
            each = int(h.split('*/')[1])
            if each == 1:
                return ".."
        return h

    def clean_smarttest_month(self):
        m = eval(self.cleaned_data.get("smarttest_month"))
        m = ",".join(m)
        m = m.replace("a", "10").replace("b", "11").replace("c", "12")
        return m

    def clean_smarttest_dayweek(self):
        w = eval(self.cleaned_data.get("smarttest_dayweek"))
        w = ",".join(w)
        return w


class FirmwareTemporaryLocationForm(Form):
    mountpoint = forms.ChoiceField(
        label=_("Place to temporarily place firmware file"),
        help_text=_("The system will use this place to temporarily store the "
            "firmware file before it's being applied."),
        choices=(),
        widget=forms.Select(attrs={'class': 'required'}),
        )

    def __init__(self, *args, **kwargs):
        super(FirmwareTemporaryLocationForm, self).__init__(*args, **kwargs)
        self.fields['mountpoint'].choices = [(x.mp_path, x.mp_path) for x in MountPoint.objects.exclude(mp_volume__vol_fstype='iscsi')]

    def done(self, *args, **kwargs):
        notifier().change_upload_location(self.cleaned_data["mountpoint"].__str__())


class FirmwareUploadForm(Form):
    firmware = FileField(label=_("New image to be installed"), required=True)
    sha256 = forms.CharField(label=_("SHA256 sum for the image"), required=True)

    def clean(self):
        cleaned_data = self.cleaned_data
        filename = '/var/tmp/firmware/firmware.txz'
        if cleaned_data.get('firmware'):
            if hasattr(cleaned_data['firmware'], 'temporary_file_path'):
                shutil.move(cleaned_data['firmware'].temporary_file_path(), filename)
            else:
                with open(filename, 'wb+') as fw:
                    for c in cleaned_data['firmware'].chunks():
                        fw.write(c)
            retval = notifier().validate_update(filename)
            if not retval:
                msg = _(u"Invalid firmware")
                self._errors["firmware"] = self.error_class([msg])
                del cleaned_data["firmware"]
            elif 'sha256' in cleaned_data:
                checksum = notifier().checksum(filename)
                if checksum != str(cleaned_data['sha256']).strip():
                    msg = _(u"Invalid checksum")
                    self._errors["firmware"] = self.error_class([msg])
                    del cleaned_data["firmware"]
        else:
            self._errors["firmware"] = self.error_class([_("This field is required.")])
        return cleaned_data

    def done(self, request, *args, **kwargs):
        notifier().apply_update('/var/tmp/firmware/firmware.txz')
        request.session['allow_reboot'] = True


class ConfigUploadForm(Form):
    config = FileField(label=_("New config to be installed"))


class CronJobForm(ModelForm):

    class Meta:
        model = models.CronJob
        widgets = {
            'cron_command': forms.widgets.TextInput(),
            'cron_minute': CronMultiple(
                attrs={'numChoices': 60, 'label': _("minute")}
                ),
            'cron_hour': CronMultiple(
                attrs={'numChoices': 24, 'label': _("hour")}
                ),
            'cron_daymonth': CronMultiple(
                attrs={'numChoices': 31, 'start': 1, 'label': _("day of month")}
                ),
            'cron_dayweek': forms.CheckboxSelectMultiple(
                choices=choices.WEEKDAYS_CHOICES
                ),
            'cron_month': forms.CheckboxSelectMultiple(
                choices=choices.MONTHS_CHOICES
                ),
        }

    def __init__(self, *args, **kwargs):
        if 'instance' in kwargs:
            ins = kwargs.get('instance')
            if ins.cron_month == '*':
                ins.cron_month = "1,2,3,4,5,6,7,8,9,a,b,c"
            else:
                ins.cron_month = ins.cron_month.replace("10", "a").replace("11", "b").replace("12", "c")
            if ins.cron_dayweek == '*':
                ins.cron_dayweek = "1,2,3,4,5,6,7"
        super(CronJobForm, self).__init__(*args, **kwargs)

    def clean_cron_user(self):
        user = self.cleaned_data.get("cron_user")
        # See #1061 or FreeBSD PR 162976
        if len(user) > 17:
            raise forms.ValidationError("Usernames cannot exceed 17 characters for cronjobs")
        # Windows users can have spaces in their usernames
        # http://www.freebsd.org/cgi/query-pr.cgi?pr=164808
        if ' ' in user:
            raise forms.ValidationError("Usernames cannot have spaces")
        return user

    def clean_cron_month(self):
        m = eval(self.cleaned_data.get("cron_month"))
        if len(m) == 12:
            return '*'
        m = ",".join(m)
        m = m.replace("a", "10").replace("b", "11").replace("c", "12")
        return m

    def clean_cron_dayweek(self):
        w = eval(self.cleaned_data.get("cron_dayweek"))
        if len(w) == 7:
            return '*'
        w = ",".join(w)
        return w

    def save(self):
        super(CronJobForm, self).save()
        notifier().restart("cron")


class RsyncForm(ModelForm):

    class Meta:
        model = models.Rsync
        widgets = {
            'rsync_minute': CronMultiple(
                attrs={'numChoices': 60, 'label': _("minute")}
                ),
            'rsync_hour': CronMultiple(
                attrs={'numChoices': 24, 'label': _("hour")}
                ),
            'rsync_daymonth': CronMultiple(
                attrs={'numChoices': 31, 'start': 1, 'label': _("day of month")}
                ),
            'rsync_dayweek': forms.CheckboxSelectMultiple(
                choices=choices.WEEKDAYS_CHOICES
                ),
            'rsync_month': forms.CheckboxSelectMultiple(
                choices=choices.MONTHS_CHOICES
                ),
        }

    def __init__(self, *args, **kwargs):
        if 'instance' in kwargs:
            ins = kwargs.get('instance')
            if ins.rsync_month == '*':
                ins.rsync_month = "1,2,3,4,5,6,7,8,9,a,b,c"
            else:
                ins.rsync_month = ins.rsync_month.replace("10", "a").replace("11", "b").replace("12", "c")
            if ins.rsync_dayweek == '*':
                ins.rsync_dayweek = "1,2,3,4,5,6,7"
        super(RsyncForm, self).__init__(*args, **kwargs)
        self.fields['rsync_mode'].widget.attrs['onChange'] = "rsyncModeToggle();"

    def clean_rsync_user(self):
        user = self.cleaned_data.get("rsync_user")
        # See #1061 or FreeBSD PR 162976
        if len(user) > 17:
            raise forms.ValidationError("Usernames cannot exceed 17 "
                "characters for rsync tasks")
        # Windows users can have spaces in their usernames
        # http://www.freebsd.org/cgi/query-pr.cgi?pr=164808
        if ' ' in user:
            raise forms.ValidationError("Usernames cannot have spaces")
        return user

    def clean_rsync_remotemodule(self):
        mode = self.cleaned_data.get("rsync_mode")
        val = self.cleaned_data.get("rsync_remotemodule")
        if mode == 'module' and not val:
            raise forms.ValidationError(_("This field is required"))
        return val

    def clean_rsync_remotepath(self):
        mode = self.cleaned_data.get("rsync_mode")
        val = self.cleaned_data.get("rsync_remotepath")
        if mode == 'ssh' and not val:
            raise forms.ValidationError(_("This field is required"))
        return val

    def clean_rsync_month(self):
        m = eval(self.cleaned_data.get("rsync_month"))
        if len(m) == 12:
            return '*'
        m = ",".join(m)
        m = m.replace("a", "10").replace("b", "11").replace("c", "12")
        return m

    def clean_rsync_dayweek(self):
        w = eval(self.cleaned_data.get("rsync_dayweek"))
        if len(w) == 7:
            return '*'
        w = ",".join(w)
        return w

    def clean_rsync_extra(self):
        extra = self.cleaned_data.get("rsync_extra")
        if extra:
            extra = extra.replace('\n', ' ')
        return extra

    def clean(self):
        cdata = self.cleaned_data
        mode = cdata.get("rsync_mode")
        user = cdata.get("rsync_user")
        if mode == 'ssh':
            try:
                home = pwd.getpwnam(user).pw_dir
                search = os.path.join(home, ".ssh", "id_[edr]*.*")
                if not glob.glob(search):
                    raise ValueError
            except (KeyError, ValueError, AttributeError, TypeError):
                self._errors['rsync_user'] = self.error_class([
                    _("In order to use rsync over SSH you need a user<br />"
                      "with a public key (DSA/ECDSA/RSA) set up in home dir."),
                    ])
                cdata.pop('rsync_user', None)
        return cdata

    def save(self):
        super(RsyncForm, self).save()
        notifier().restart("cron")

"""
TODO: Move to a unittest .py file.

invalid_sysctls = [
    'a.0',
    'a.b',
    'a..b',
    'a._.b',
    'a.b._.c',
    '0',
    '0.a',
    'a-b',
    'a',
]

valid_sysctls = [
    'ab.0',
    'ab.b',
    'smbios.system.version',
    'dev.emu10kx.0.multichannel_recording',
    'hw.bce.tso0',
    'kern.sched.preempt_thresh',
    'net.inet.tcp.tso',
]

assert len(filter(SYSCTL_VARNAME_FORMAT_RE.match, invalid_sysctls)) == 0
assert len(filter(SYSCTL_VARNAME_FORMAT_RE.match, valid_sysctls)) == len(valid_sysctls)
"""

# NOTE:
# - setenv in the kernel is more permissive than this, but we want to reduce
#   user footshooting.
# - this doesn't reject all benign input; it just rejects input that would
#   break system boots.
# XXX: note that I'm explicitly rejecting input for root sysctl nodes.
SYSCTL_TUNABLE_VARNAME_FORMAT = """Variable names must:
1. Start with a letter.
2. End with a letter or number.
3. Can contain a combination of alphanumeric characters, numbers, underscores,
   and/or periods.
"""
SYSCTL_VARNAME_FORMAT_RE = \
    re.compile('[a-z][a-z0-9_]+\.([a-z0-9_]+\.)*[a-z0-9_]+', re.I)

TUNABLE_VARNAME_FORMAT_RE = \
    re.compile('[a-z][a-z0-9_]+\.*([a-z0-9_]+\.)*[a-z0-9_]+', re.I)


class SysctlForm(ModelForm):
    class Meta:
        model = models.Sysctl

    def clean_sysctl_comment(self):
        return self.cleaned_data.get('sysctl_comment').strip()

    def clean_sysctl_mib(self):
        value = self.cleaned_data.get('sysctl_mib').strip()
        if SYSCTL_VARNAME_FORMAT_RE.match(value):
            return value
        raise forms.ValidationError(_(SYSCTL_TUNABLE_VARNAME_FORMAT))

    def clean_sysctl_value(self):
        value = self.cleaned_data.get('sysctl_value')
        if '"' in value or "'" in value:
            raise forms.ValidationError(_('Quotes are not allowed'))
        return value

    def save(self):
        super(SysctlForm, self).save()
        notifier().reload("sysctl")


class TunableForm(ModelForm):
    class Meta:
        model = models.Tunable

    def clean_ldr_comment(self):
        return self.cleaned_data.get('ldr_comment').strip()

    def clean_ldr_value(self):
        value = self.cleaned_data.get('ldr_value')
        if '"' in value or "'" in value:
            raise forms.ValidationError(_('Quotes are not allowed'))
        return value

    def clean_ldr_var(self):
        value = self.cleaned_data.get('ldr_var').strip()
        if TUNABLE_VARNAME_FORMAT_RE.match(value):
            return value
        raise forms.ValidationError(_(SYSCTL_TUNABLE_VARNAME_FORMAT))

    def save(self):
        super(TunableForm, self).save()
        notifier().reload("loader")
