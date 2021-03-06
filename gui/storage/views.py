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
import os
import re
import signal
import subprocess

from django.core.urlresolvers import reverse
from django.db import models as dmodels
from django.http import HttpResponse
from django.shortcuts import render
from django.utils import simplejson
from django.utils.translation import ugettext as _

from dojango.util import to_dojo_data
from metanasUI.common import humanize_size
from metanasUI.common.system import is_mounted
from metanasUI.freeadmin.views import JsonResponse, JsonResp
from metanasUI.middleware import zfs
from metanasUI.middleware.notifier import notifier
from metanasUI.services.exceptions import ServiceFailed
from metanasUI.services.models import iSCSITargetExtent
from metanasUI.storage import forms, models

log = logging.getLogger('storage.views')


def home(request):
    return render(request, 'storage/index.html', {
        'focused_tab': request.GET.get("tab", None),
    })


def tasks(request):
    task_list = models.Task.objects.order_by("task_filesystem").all()
    return render(request, 'storage/tasks.html', {
        'task_list': task_list,
        })


def volumes(request):
    mp_list = models.MountPoint.objects.exclude(
        mp_volume__vol_fstype__exact='iscsi').select_related().all()
    has_multipath = models.Disk.objects.exclude(
        disk_multipath_name='').exists()
    return render(request, 'storage/volumes.html', {
        'mp_list': mp_list,
        'has_multipath': has_multipath,
        })


def replications(request):
    zfsrepl_list = models.Replication.objects.select_related().all()
    return render(request, 'storage/replications.html', {
        'zfsrepl_list': zfsrepl_list,
        })


def replications_public_key(request):
    if os.path.exists('/data/ssh/replication.pub') and \
    os.path.isfile('/data/ssh/replication.pub'):
        with open('/data/ssh/replication.pub', 'r') as f:
            key = f.read()
    else:
        key = None
    return render(request, 'storage/replications_key.html', {
        'key': key,
        })


def snapshots(request):
    zfsnap_list = notifier().zfs_snapshot_list()
    return render(request, 'storage/snapshots.html', {
        'zfsnap_list': zfsnap_list,
        })


def snapshots_data(request):
    zfsnap = notifier().zfs_snapshot_list().items()
    zfsnap_list = []
    for vol, snaps in zfsnap:
        for snap in snaps:
            snap.update({
                'filesystem': vol,
            })
            zfsnap_list.append(snap)

    r = request.META.get("HTTP_RANGE", None)
    if r:
        r = r.split('=')[1].split('-')
        r1 = int(r[0])
        if r[1]:
            r2 = int(r[1]) + 1
        else:
            r = None

    for key in request.GET.keys():
        reg = re.search(r'sort\((?P<sign>.)(?P<field>.+?)\)', key)
        if reg:
            sign, field = reg.groups()
            if sign == '-':
                rev = True
            else:
                rev = False
            if field in zfsnap_list[0]:
                zfsnap_list.sort(key=lambda item: item[field], reverse=rev)

    data = []
    count = 0
    total = len(zfsnap_list)
    if r:
        zfsnap_list = zfsnap_list[r1:r2]
    for snap in zfsnap_list:
        clone_url = reverse('storage_clonesnap', kwargs={
            'snapshot': snap['fullname'],
            })
        if snap['parent'] == 'volume':
            clone_url += "?volume=true"
        snap['extra'] = simplejson.dumps({
            'clone_url': clone_url,
            'rollback_url': reverse('storage_snapshot_rollback', kwargs={
                'dataset': snap['filesystem'],
                'snapname': snap['name'],
                }) if snap['mostrecent'] else None,
            'delete_url': reverse('storage_snapshot_delete', kwargs={
                'dataset': snap['filesystem'],
                'snapname': snap['name'],
                }),
        })
        data.append(snap)
        count += 1

    if r:
        resp = HttpResponse(simplejson.dumps(data),
            content_type='application/json')
        resp['Content-Range'] = 'items %d-%d/%d' % (r1, r1 + count, total)
    else:
        resp = HttpResponse(simplejson.dumps(data),
            content_type='application/json')
    return resp


def wizard(request):

    if request.method == "POST":

        form = forms.VolumeWizardForm(request.POST)
        if form.is_valid():
            form.done(request)
            return JsonResponse(message=_("Volume successfully added."))
        else:
            if 'volume_disks' in request.POST:
                disks = request.POST.getlist('volume_disks')
            else:
                disks = None
            zpoolfields = re.compile(r'zpool_(.+)')
            zfsextra = [(zpoolfields.search(i).group(1), i, request.POST.get(i)) \
                        for i in request.POST.keys() if zpoolfields.match(i)]

    else:
        form = forms.VolumeWizardForm()
        disks = []
        zfsextra = None
    return render(request, 'storage/wizard.html', {
        'form': form,
        'disks': disks,
        'zfsextra': zfsextra,
        'zfsversion': notifier().zfs_get_version(),
    })


def volimport(request):

    if request.method == "POST":

        form = forms.VolumeImportForm(request.POST)
        if form.is_valid():
            form.done(request)
            return JsonResponse(message=_("Volume successfully added."))
        else:

            if 'volume_disks' in request.POST:
                disks = request.POST.getlist('volume_disks')
            else:
                disks = None
    else:
        form = forms.VolumeImportForm()
        disks = []
    return render(request, 'storage/import.html', {
        'form': form,
        'disks': disks
    })


def volautoimport(request):

    if request.method == "POST":

        form = forms.VolumeAutoImportForm(request.POST)
        if form.is_valid():
            form.done(request)
            return JsonResponse(message=_("Volume successfully added."))
        else:

            if 'volume_disks' in request.POST:
                disks = request.POST.getlist('volume_disks')
            else:
                disks = None
    else:
        form = forms.VolumeAutoImportForm()
        disks = []
    return render(request, 'storage/autoimport.html', {
        'form': form,
        'disks': disks
    })


def disks_datagrid(request):

    names = [
        _('Name'),
        _('Serial'),
        _('Description'),
        _("Transfer Mode"),
        _("HDD Standby"),
        _("Advanced Power Management"),
        _("Acoustic Level"),
        _("Enable S.M.A.R.T."),
        _("S.M.A.R.T. Extra Options")]
    _n = [
        'devname',
        'disk_serial',
        'disk_description',
        'disk_transfermode',
        'disk_hddstandby',
        'disk_advpowermgmt',
        'disk_acousticlevel',
        'disk_togglesmart',
        'disk_smartoptions',
        ]

    """
    Nasty hack to calculate the width of the datagrid column
    dojo DataGrid width="auto" doesnt work correctly and dont allow
         column resize with mouse
    """
    width = []
    for x in names:
        val = 8
        for letter in x:
            if letter.isupper():
                val += 10
            elif letter.isdigit():
                val += 9
            else:
                val += 7
        width.append(val)
    fields = zip(names, _n, width)

    return render(request, 'storage/datagrid_disks.html', {
        'app': 'storage',
        'model': 'Disk',
        'fields': fields,
    })


def disks_datagrid_json(request):

    disks = models.Disk.objects.filter(
        disk_enabled=True,
        disk_multipath_name=''
        )

    complete = []
    for data in disks:
        ret = {}
        ret['edit'] = {
            'edit_url': reverse('freeadmin_model_edit', kwargs={
                'app': 'storage',
                'model': 'Disk',
                'oid': data.id,
                }) + '?deletable=false',
            'wipe_url': reverse('storage_disk_wipe', kwargs={
                'devname': data.disk_name,
                }),
            }
        ret['edit'] = simplejson.dumps(ret['edit'])

        for f in data._meta.fields:
            # filefields can't be json serialized
            if isinstance(f, dmodels.ImageField) or \
            isinstance(f, dmodels.FileField):
                ret[f.attname] = unicode(getattr(data, f.attname))
            else:
                #json_encode() this?
                ret[f.attname] = getattr(data, f.attname)
        ret['devname'] = data.devname

        complete.append(ret)

    return HttpResponse(simplejson.dumps(
        to_dojo_data(complete,
            identifier=models.Disk._meta.pk.name,
            num_rows=len(disks))
    ))


def volume_disks(request, volume_id):
    volume = models.Volume.objects.get(id=volume_id)
    disk_list = models.Disk.objects.filter(disk_group__group_volume=volume_id)
    return render(request, 'storage/volume_detail.html', {
        'focused_tab': 'storage',
        'volume': volume,
        'disk_list': disk_list,
    })


def dataset_create(request, fs):
    defaults = {'dataset_compression': 'inherit', 'dataset_atime': 'inherit'}
    if request.method == 'POST':
        dataset_form = forms.ZFSDataset_CreateForm(request.POST, fs=fs)
        if dataset_form.is_valid():
            props = {}
            cleaned_data = dataset_form.cleaned_data
            dataset_name = "%s/%s" % (fs, cleaned_data.get('dataset_name'))
            dataset_compression = cleaned_data.get('dataset_compression')
            props['compression'] = dataset_compression.__str__()
            dataset_atime = cleaned_data.get('dataset_atime')
            props['atime'] = dataset_atime.__str__()
            refquota = cleaned_data.get('dataset_refquota')
            if refquota != '0':
                props['refquota'] = refquota.__str__()
            quota = cleaned_data.get('dataset_quota')
            if quota != '0':
                props['quota'] = quota.__str__()
            refreservation = cleaned_data.get('dataset_refreserv')
            if refreservation != '0':
                props['refreservation'] = refreservation.__str__()
            refreservation = cleaned_data.get('dataset_reserv')
            if refreservation != '0':
                props['refreservation'] = refreservation.__str__()
            errno, errmsg = notifier().create_zfs_dataset(
                path=str(dataset_name),
                props=props)
            if errno == 0:
                return JsonResponse(message=_("Dataset successfully added."))
            else:
                dataset_form.set_error(errmsg)
    else:
        dataset_form = forms.ZFSDataset_CreateForm(initial=defaults, fs=fs)
    return render(request, 'storage/datasets.html', {
        'form': dataset_form,
        'fs': fs,
    })


def dataset_edit(request, dataset_name):
    if request.method == 'POST':
        dataset_form = forms.ZFSDataset_EditForm(request.POST, fs=dataset_name)
        if dataset_form.is_valid():
            if dataset_form.cleaned_data["dataset_quota"] == "0":
                dataset_form.cleaned_data["dataset_quota"] = "none"
            if dataset_form.cleaned_data["dataset_refquota"] == "0":
                dataset_form.cleaned_data["dataset_refquota"] = "none"

            error = False
            errors = {}

            for attr in ('compression',
                    'atime',
                    'reservation',
                    'refreservation',
                    'quota',
                    'refquota',
                    ):
                formfield = 'dataset_%s' % attr
                if dataset_form.cleaned_data[formfield] == "inherit":
                    success, err = notifier().zfs_inherit_option(
                        dataset_name,
                        attr,
                        )
                else:
                    success, err = notifier().zfs_set_option(
                        dataset_name,
                        attr,
                        dataset_form.cleaned_data[formfield],
                        )
                error |= not success
                if not success:
                    errors[formfield] = err

            if not error:
                return JsonResponse(message=_("Dataset successfully edited."))
            else:
                for field, err in errors.items():
                    dataset_form._errors[field] = dataset_form.error_class([
                        err,
                        ])
    else:
        dataset_form = forms.ZFSDataset_EditForm(fs=dataset_name)
    return render(request, 'storage/dataset_edit.html', {
        'dataset_name': dataset_name,
        'form': dataset_form
    })


def zvol_create(request, volume_name):
    defaults = {'zvol_compression': 'inherit', }
    if request.method == 'POST':
        zvol_form = forms.ZVol_CreateForm(request.POST, vol_name=volume_name)
        if zvol_form.is_valid():
            props = {}
            cleaned_data = zvol_form.cleaned_data
            zvol_size = cleaned_data.get('zvol_size')
            zvol_name = "%s/%s" % (volume_name, cleaned_data.get('zvol_name'))
            zvol_compression = cleaned_data.get('zvol_compression')
            props['compression'] = str(zvol_compression)
            errno, errmsg = notifier().create_zfs_vol(name=str(zvol_name),
                size=str(zvol_size),
                props=props)
            if errno == 0:
                return JsonResponse(
                    message=_("ZFS Volume successfully added.")
                    )
            else:
                zvol_form.set_error(errmsg)
    else:
        zvol_form = forms.ZVol_CreateForm(initial=defaults,
            vol_name=volume_name)
    return render(request, 'storage/zvols.html', {
        'form': zvol_form,
        'volume_name': volume_name,
    })


def zvol_delete(request, name):

    if request.method == 'POST':
        extents = iSCSITargetExtent.objects.filter(
            iscsi_target_extent_type='ZVOL',
            iscsi_target_extent_path='zvol/' + name)
        if extents.count() > 0:
            return JsonResponse(
                error=True,
                message=_("This is in use by the iscsi target, please remove "
                    "it there first."))
        retval = notifier().destroy_zfs_vol(name)
        if retval == '':
            return JsonResponse(
                message=_("ZFS Volume successfully destroyed.")
                )
        else:
            return JsonResponse(error=True, message=retval)
    else:
        return render(request, 'storage/zvol_confirm_delete.html', {
            'name': name,
        })


def zfsvolume_edit(request, object_id):

    mp = models.MountPoint.objects.get(pk=object_id)
    volume_form = forms.ZFSVolume_EditForm(mp=mp)

    if request.method == 'POST':
        volume_form = forms.ZFSVolume_EditForm(request.POST, mp=mp)
        if volume_form.is_valid():
            volume = mp.mp_volume
            volume_name = volume.vol_name
            volume_name = mp.mp_path.replace("/mnt/", "")

            if volume_form.cleaned_data["volume_refquota"] == "0":
                volume_form.cleaned_data["volume_refquota"] = "none"

            error, errors = False, {}
            for attr in ('compression',
                    'atime',
                    'refquota',
                    'refreservation',
                    ):
                formfield = 'volume_%s' % attr
                if volume_form.cleaned_data[formfield] == "inherit":
                    success, err = notifier().zfs_inherit_option(
                        volume_name,
                        attr,
                        )
                else:
                    success, err = notifier().zfs_set_option(
                        volume_name,
                        attr,
                        volume_form.cleaned_data[formfield],
                        )
                if not success:
                    error = True
                    errors[formfield] = err

            if not error:
                return JsonResponse(
                    message=_("Native dataset successfully edited.")
                    )
            else:
                for field, err in errors.items():
                    volume_form._errors[field] = volume_form.error_class([
                        err,
                        ])
    return render(request, 'storage/volume_edit.html', {
        'mp': mp,
        'form': volume_form
    })


def mp_permission(request, path):
    path = '/' + path
    if request.method == 'POST':
        form = forms.MountPointAccessForm(request.POST)
        if form.is_valid():
            form.commit(path=path)
            return JsonResponse(
                message=_("Mount Point permissions successfully updated.")
                )
    else:
        form = forms.MountPointAccessForm(initial={'path': path})
    return render(request, 'storage/permission.html', {
        'path': path,
        'form': form,
    })


def dataset_delete(request, name):

    datasets = zfs.list_datasets(path=name, recursive=True)
    if request.method == 'POST':
        form = forms.Dataset_Destroy(request.POST, fs=name, datasets=datasets)
        if form.is_valid():
            retval = notifier().destroy_zfs_dataset(path=name, recursive=True)
            if retval == '':
                notifier().restart("collectd")
                return JsonResponse(
                    message=_("Dataset successfully destroyed.")
                    )
            else:
                return JsonResponse(error=True, message=retval)
    else:
        form = forms.Dataset_Destroy(fs=name, datasets=datasets)
    return render(request, 'storage/dataset_confirm_delete.html', {
        'name': name,
        'form': form,
        'datasets': datasets,
    })


def snapshot_delete(request, dataset, snapname):
    snapshot = '%s@%s' % (dataset, snapname)
    if request.method == 'POST':
        retval = notifier().destroy_zfs_dataset(path=str(snapshot))
        if retval == '':
            notifier().restart("collectd")
            return JsonResponse(message=_("Snapshot successfully deleted."))
        else:
            return JsonResponse(error=True, message=retval)
    else:
        return render(request, 'storage/snapshot_confirm_delete.html', {
            'snapname': snapname,
            'dataset': dataset,
        })


def snapshot_delete_bulk(request):

    snaps = request.POST.get("snaps", None)
    delete = request.POST.get("delete", None)
    if snaps and delete == "true":
        snap_list = snaps.split('|')
        for snapshot in snap_list:
            retval = notifier().destroy_zfs_dataset(path=str(snapshot))
            if retval != '':
                return JsonResponse(error=True, message=retval)
        notifier().restart("collectd")
        return JsonResponse(message=_("Snapshots successfully deleted."))

    return render(request, 'storage/snapshot_confirm_delete_bulk.html', {
        'snaps': snaps,
    })


def snapshot_rollback(request, dataset, snapname):
    snapshot = '%s@%s' % (dataset, snapname)
    if request.method == "POST":
        ret = notifier().rollback_zfs_snapshot(snapshot=snapshot.__str__())
        if ret == '':
            return JsonResponse(message=_("Rollback successful."))
        else:
            return JsonResponse(error=True, message=ret)
    else:
        return render(request, 'storage/snapshot_confirm_rollback.html', {
            'snapname': snapname,
            'dataset': dataset,
        })


def periodicsnap(request):

    if request.method == "POST":

        form = forms.PeriodicSnapForm(request.POST)
        if form.is_valid():
            form.save()

            return JsonResponse(message=_("Snapshot successfully added."))
    else:
        form = forms.PeriodicSnapForm()
    return render(request, 'storage/periodicsnap.html', {
        'form': form,
        'extra_js': models.Task._admin.extra_js,
    })


def manualsnap(request, fs):
    if request.method == "POST":
        form = forms.ManualSnapshotForm(request.POST)
        if form.is_valid():
            form.commit(fs)
            return JsonResponse(message=_("Snapshot successfully taken."))
    else:
        form = forms.ManualSnapshotForm()
    return render(request, 'storage/manualsnap.html', {
        'form': form,
        'fs': fs,
    })


def clonesnap(request, snapshot):
    initial = {'cs_snapshot': snapshot}
    if request.method == "POST":
        form = forms.CloneSnapshotForm(request.POST, initial=initial)
        if form.is_valid():
            retval = form.commit()
            if retval == '':
                return JsonResponse(message=_("Snapshot successfully cloned."))
            else:
                return JsonResponse(error=True, message=retval)
    else:
        is_volume = 'volume' in request.GET
        form = forms.CloneSnapshotForm(initial=initial, is_volume=is_volume)
    return render(request, 'storage/clonesnap.html', {
        'form': form,
        'snapshot': snapshot,
    })


def geom_disk_replace(request, vname):

    volume = models.Volume.objects.get(vol_name=vname)
    if request.method == "POST":
        form = forms.UFSDiskReplacementForm(request.POST)
        if form.is_valid():
            if form.done(volume):
                return JsonResponse(
                    message=_("Disk replacement has been initiated.")
                    )
            else:
                return JsonResponse(
                    error=True,
                    message=_("An error occurred."))

    else:
        form = forms.UFSDiskReplacementForm()
    return render(request, 'storage/geom_disk_replace.html', {
        'form': form,
        'vname': vname,
    })


def disk_detach(request, vname, label):

    volume = models.Volume.objects.get(vol_name=vname)

    if request.method == "POST":
        notifier().zfs_detach_disk(volume, label)
        return JsonResponse(
            message=_("Disk detach has been successfully done.")
            )

    return render(request, 'storage/disk_detach.html', {
        'vname': vname,
        'label': label,
    })


def disk_offline(request, vname, label):

    volume = models.Volume.objects.get(vol_name=vname)
    disk = notifier().label_to_disk(label)

    if request.method == "POST":
        notifier().zfs_offline_disk(volume, label)
        return JsonResponse(
            message=_("Disk offline operation has been issued.")
            )

    return render(request, 'storage/disk_offline.html', {
        'vname': vname,
        'label': label,
        'disk': disk,
    })


def zpool_disk_remove(request, vname, label):

    volume = models.Volume.objects.get(vol_name=vname)
    disk = notifier().label_to_disk(label)

    if request.method == "POST":
        notifier().zfs_remove_disk(volume, label)
        return JsonResponse(message=_("Disk has been removed."))

    return render(request, 'storage/disk_remove.html', {
        'vname': vname,
        'label': label,
        'disk': disk,
    })


def volume_detach(request, vid):

    volume = models.Volume.objects.get(pk=vid)
    usedbytes = sum(
        [mp._get_used_bytes() for mp in volume.mountpoint_set.all()]
        )
    usedsize = humanize_size(usedbytes)
    services = volume.has_attachments()
    if request.method == "POST":
        form = forms.VolumeExport(request.POST,
            instance=volume,
            services=services)
        if form.is_valid():
            try:
                volume.delete(destroy=form.cleaned_data['mark_new'],
                    cascade=form.cleaned_data.get('cascade', True))
                return JsonResponse(
                    message=_("The volume has been successfully detached")
                    )
            except ServiceFailed, e:
                return JsonResponse(error=True, message=unicode(e))
    else:
        form = forms.VolumeExport(instance=volume, services=services)
    return render(request, 'storage/volume_detach.html', {
        'volume': volume,
        'form': form,
        'used': usedsize,
        'services': services,
    })


def zpool_scrub(request, vid):
    volume = models.Volume.objects.get(pk=vid)
    pool = notifier().zpool_parse(volume.vol_name)
    if request.method == "POST":
        if request.POST.get("scrub") == 'IN_PROGRESS':
            notifier().zfs_scrub(str(volume.vol_name), stop=True)
        else:
            notifier().zfs_scrub(str(volume.vol_name))
        return JsonResponse(message=_("The scrub process has begun"))

    return render(request, 'storage/scrub_confirm.html', {
        'volume': volume,
        'scrub': pool.scrub,
    })


def volume_status(request, vid):
    volume = models.Volume.objects.get(id=vid)
    return render(request, 'storage/volume_status.html', {
        'name': volume.vol_name,
        'volume': volume,
    })


def volume_status_json(request, vid):
    volume = models.Volume.objects.get(id=vid)
    if volume.vol_fstype == 'ZFS':
        pool = notifier().zpool_parse(volume.vol_name)
        items = pool.treedump()
    else:
        items = notifier().geom_disks_dump(volume)
        children = [{'_reference': item['id']} for item in items]
        items.append({
            'name': volume.vol_name,
            'id': len(items) + 1,
            'status': '',
            'type': 'root',
            'children': children,
        })
    return HttpResponse(simplejson.dumps({
        'identifier': 'id',
        'label': 'name',
        'items': items,
    }, indent=2), content_type='application/json')


def zpool_disk_replace(request, vname, label):

    disk = notifier().label_to_disk(label)
    volume = models.Volume.objects.get(vol_name=vname)
    if request.method == "POST":
        form = forms.ZFSDiskReplacementForm(request.POST, disk=disk)
        if form.is_valid():
            if form.done(volume, disk, label):
                return JsonResponse(
                    message=_("Disk replacement has been initiated.")
                    )
            else:
                return JsonResponse(
                    error=True,
                    message=_("An error occurred."))

    else:
        form = forms.ZFSDiskReplacementForm(disk=disk)
    return render(request, 'storage/zpool_disk_replace.html', {
        'form': form,
        'vname': vname,
        'label': label,
        'disk': disk,
    })


def multipath_status(request):
    return render(request, 'storage/multipath_status.html')


def multipath_status_json(request):

    multipaths = notifier().multipath_all()
    _id = 1
    items = []
    for mp in multipaths:
        children = []
        for cn in mp.consumers:
            items.append({
                'id': str(_id),
                'name': cn.devname,
                'status': cn.status,
                'type': 'consumer',
            })
            children.append({'_reference': str(_id)})
            _id += 1
        data = {
            'id': str(_id),
            'name': mp.devname,
            'status': mp.status,
            'type': 'root',
            'children': children,
        }
        items.append(data)
        _id += 1
    return HttpResponse(simplejson.dumps({
        'identifier': 'id',
        'label': 'name',
        'items': items,
    }, indent=2), content_type='application/json')


def scrubs(request):
    scrubs = models.Scrub.objects.all().order_by('id')
    return render(request, 'storage/scrub.html', {
        'scrubs': scrubs,
        })


def disk_wipe(request, devname):

    form = forms.DiskWipeForm()
    if request.method == "POST":
        form = forms.DiskWipeForm(request.POST)
        if form.is_valid():
            mounted = []
            for geom in notifier().disk_get_consumers(devname):
                gname = geom.xpathEval("./name")[0].content
                dev = "/dev/%s" % (gname, )
                if dev not in mounted and is_mounted(device=dev):
                    mounted.append(dev)
            for vol in models.Volume.objects.filter(
                vol_fstype='ZFS'
                ):
                if devname in vol.get_disks():
                    mounted.append(vol.vol_name)
            if mounted:
                form._errors['__all__'] = form.error_class([
                    "Umount the following mount points before proceeding:"
                    "<br /> %s" % (
                    '<br /> '.join(mounted),
                    )
                    ])
            else:
                notifier().disk_wipe(devname, form.cleaned_data['method'])
                return JsonResp(request,
                    message=_("Disk successfully wiped")
                    )

        return JsonResp(request, form=form)

    return render(request, "storage/disk_wipe.html", {
        'devname': devname,
        'form': form,
        })


def disk_wipe_progress(request, devname):

    pidfile = '/var/tmp/disk_wipe_%s.pid' % (devname, )
    if not os.path.exists(pidfile):
        return HttpResponse('new Object({state: "starting"});')

    with open(pidfile, 'r') as f:
        pid = f.read()

    try:
        os.kill(int(pid), signal.SIGINFO)
        with open('/var/tmp/disk_wipe_%s.progress' % (devname, ), 'r') as f:
            data = f.read()
            transf = re.findall(r'^(?P<bytes>\d+) bytes transferred.*',
                data, re.M)
            if transf:
                pipe = subprocess.Popen([
                    "/usr/sbin/diskinfo",
                    devname,
                    ],
                    stdout=subprocess.PIPE)
                output = pipe.communicate()[0]
                size = output.split()[2]
                received = transf[-1]
        return HttpResponse('new Object({state: "uploading", received: %s, size: %s});' % (received, size))

    except Exception, e:
        pass
    return HttpResponse('new Object({state: "starting"});')
