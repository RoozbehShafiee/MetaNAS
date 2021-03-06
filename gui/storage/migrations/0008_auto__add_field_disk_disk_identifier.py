# encoding: utf-8
from subprocess import Popen, PIPE
import datetime
import re

from django.db import models

from libxml2 import parseDoc
from south.db import db
from south.v2 import SchemaMigration

def geom_confxml():
    sysctl_proc = Popen(['sysctl', '-b', 'kern.geom.confxml'], stdout=PIPE)
    return parseDoc(sysctl_proc.communicate()[0][:-1])

def serial_from_device(devname):
    p1 = Popen(["/usr/local/sbin/smartctl", "-i", "/dev/%s" % devname], stdout=PIPE)
    output = p1.communicate()[0]
    search = re.search(r'^Serial Number:[ \t\s]+(?P<serial>.+)', output, re.I|re.M)
    if search:
        return search.group("serial")
    return None

def device_to_identifier(name):
    name = str(name)
    doc = geom_confxml()

    search = doc.xpathEval("//class[name = 'PART']/..//*[name = '%s']//config[type = 'freebsd-zfs']/rawuuid" % name)
    if len(search) > 0:
        return "{uuid}%s" % search[0].content
    search = doc.xpathEval("//class[name = 'PART']/geom/..//*[name = '%s']//config[type = 'freebsd-ufs']/rawuuid" % name)
    if len(search) > 0:
        return "{uuid}%s" % search[0].content

    search = doc.xpathEval("//class[name = 'LABEL']/geom[name = '%s']/provider/name" % name)
    if len(search) > 0:
        return "{label}%s" % search[0].content

    serial = serial_from_device(name)
    if serial:
        return "{serial}%s" % serial

    return "{devicename}%s" % name

def identifier_to_device(ident):
    doc = geom_confxml()

    search = re.search(r'\{(?P<type>.+?)\}(?P<value>.+)', ident)
    if not search:
        return None

    tp = search.group("type")
    value = search.group("value")

    if tp == 'uuid':
        search = doc.xpathEval("//class[name = 'PART']/geom//config[rawuuid = '%s']/../../name" % value)
        if len(search) > 0:
            for entry in search:
                if not entry.content.startswith("label"):
                    return entry.content
        return None

    elif tp == 'label':
        search = doc.xpathEval("//class[name = 'LABEL']/geom//provider[name = '%s']/../name" % value)
        if len(search) > 0:
            return search[0].content
        return None

    elif tp == 'serial':
        p1 = Popen(["sysctl", "-n", "kern.disks"], stdout=PIPE)
        output = p1.communicate()[0]
        RE_NOCD = re.compile('^a?cd[0-9]+$')
        devs = filter(lambda y: not RE_NOCD.match(y), output.split(' '))
        for devname in devs:
            serial = serial_from_device(devname)
            if serial == value:
                return devname
        return None

    elif tp == 'devicename':
        return value
    else:
        raise NotImplementedError


class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding field 'Disk.disk_identifier'
        db.add_column('storage_disk', 'disk_identifier', self.gf('django.db.models.fields.CharField')(default='', max_length=42), keep_default=False)

        for disk in orm.Disk.objects.all():
            ident = device_to_identifier(disk.disk_disks)
            if ident:
                disk.disk_identifier = ident
                disk.save()

        # Deleting field 'Disk.disk_disks'
        db.delete_column('storage_disk', 'disk_disks')

    def backwards(self, orm):
        
        # Adding field 'Disk.disk_disks'
        db.add_column('storage_disk', 'disk_disks', self.gf('django.db.models.fields.CharField')(default='', max_length=120), keep_default=False)

        for disk in orm.Disk.objects.all():
            dname = identifier_to_device(disk.disk_identifier)
            if dname:
                disk.disk_disks = dname
                disk.save()
        
        # Deleting field 'Disk.disk_identifier'
        db.delete_column('storage_disk', 'disk_identifier')


    models = {
        'storage.disk': {
            'Meta': {'object_name': 'Disk'},
            'disk_acousticlevel': ('django.db.models.fields.CharField', [], {'default': "'Disabled'", 'max_length': '120'}),
            'disk_advpowermgmt': ('django.db.models.fields.CharField', [], {'default': "'Disabled'", 'max_length': '120'}),
            'disk_description': ('django.db.models.fields.CharField', [], {'max_length': '120', 'blank': 'True'}),
            'disk_disks': ('django.db.models.fields.CharField', [], {'max_length': '120'}),
            'disk_group': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['storage.DiskGroup']"}),
            'disk_hddstandby': ('django.db.models.fields.CharField', [], {'default': "'Always On'", 'max_length': '120'}),
            'disk_identifier': ('django.db.models.fields.CharField', [], {'max_length': '42'}),
            'disk_name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '120'}),
            'disk_smartoptions': ('django.db.models.fields.CharField', [], {'max_length': '120', 'blank': 'True'}),
            'disk_togglesmart': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'disk_transfermode': ('django.db.models.fields.CharField', [], {'default': "'Auto'", 'max_length': '120'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        'storage.diskgroup': {
            'Meta': {'object_name': 'DiskGroup'},
            'group_name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '120'}),
            'group_type': ('django.db.models.fields.CharField', [], {'max_length': '120'}),
            'group_volume': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['storage.Volume']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        'storage.mountpoint': {
            'Meta': {'object_name': 'MountPoint'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'mp_ischild': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'mp_options': ('django.db.models.fields.CharField', [], {'max_length': '120', 'null': 'True'}),
            'mp_path': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '120'}),
            'mp_volume': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['storage.Volume']"})
        },
        'storage.replication': {
            'Meta': {'object_name': 'Replication'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'repl_lastsnapshot': ('django.db.models.fields.CharField', [], {'max_length': '120', 'blank': 'True'}),
            'repl_mountpoint': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['storage.MountPoint']"}),
            'repl_remote': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['storage.ReplRemote']"}),
            'repl_zfs': ('django.db.models.fields.CharField', [], {'max_length': '120'})
        },
        'storage.replremote': {
            'Meta': {'object_name': 'ReplRemote'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'ssh_remote_hostkey': ('django.db.models.fields.CharField', [], {'max_length': '2048'}),
            'ssh_remote_hostname': ('django.db.models.fields.CharField', [], {'max_length': '120'})
        },
        'storage.task': {
            'Meta': {'object_name': 'Task'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'task_begin': ('django.db.models.fields.TimeField', [], {'default': 'datetime.time(9, 0)'}),
            'task_byweekday': ('django.db.models.fields.CharField', [], {'default': "'1,2,3,4,5'", 'max_length': '120', 'blank': 'True'}),
            'task_end': ('django.db.models.fields.TimeField', [], {'default': 'datetime.time(18, 0)'}),
            'task_interval': ('django.db.models.fields.PositiveIntegerField', [], {'default': '60', 'max_length': '120'}),
            'task_mountpoint': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['storage.MountPoint']"}),
            'task_recursive': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'task_repeat_unit': ('django.db.models.fields.CharField', [], {'default': "'weekly'", 'max_length': '120'}),
            'task_ret_count': ('django.db.models.fields.PositiveIntegerField', [], {'default': '2'}),
            'task_ret_unit': ('django.db.models.fields.CharField', [], {'default': "'week'", 'max_length': '120'})
        },
        'storage.volume': {
            'Meta': {'object_name': 'Volume'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'vol_fstype': ('django.db.models.fields.CharField', [], {'max_length': '120'}),
            'vol_name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '120'})
        }
    }

    complete_apps = ['storage']
