# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Removing unique constraint on 'SMARTTest', fields ['smarttest_type', 'smarttest_disk']
        db.delete_unique('system_smarttest', ['smarttest_type', 'smarttest_disk_id'])

        # Deleting field 'SMARTTest.smarttest_disk'
        db.delete_column('system_smarttest', 'smarttest_disk_id')


    def backwards(self, orm):
        
        # Adding field 'SMARTTest.smarttest_disk'
        db.add_column('system_smarttest', 'smarttest_disk', self.gf('django.db.models.fields.related.ForeignKey')(default=1, related_name='smarttestdisk', to=orm['storage.Disk']), keep_default=False)

        # Adding unique constraint on 'SMARTTest', fields ['smarttest_type', 'smarttest_disk']
        db.create_unique('system_smarttest', ['smarttest_type', 'smarttest_disk_id'])


    models = {
        'storage.disk': {
            'Meta': {'ordering': "['disk_name']", 'object_name': 'Disk'},
            'disk_acousticlevel': ('django.db.models.fields.CharField', [], {'default': "'Disabled'", 'max_length': '120'}),
            'disk_advpowermgmt': ('django.db.models.fields.CharField', [], {'default': "'Disabled'", 'max_length': '120'}),
            'disk_description': ('django.db.models.fields.CharField', [], {'max_length': '120', 'blank': 'True'}),
            'disk_enabled': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'disk_hddstandby': ('django.db.models.fields.CharField', [], {'default': "'Always On'", 'max_length': '120'}),
            'disk_identifier': ('django.db.models.fields.CharField', [], {'max_length': '42'}),
            'disk_multipath_member': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'disk_multipath_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'disk_name': ('django.db.models.fields.CharField', [], {'max_length': '120'}),
            'disk_serial': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'disk_smartoptions': ('django.db.models.fields.CharField', [], {'max_length': '120', 'blank': 'True'}),
            'disk_togglesmart': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'disk_transfermode': ('django.db.models.fields.CharField', [], {'default': "'Auto'", 'max_length': '120'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        'system.advanced': {
            'Meta': {'object_name': 'Advanced'},
            'adv_advancedmode': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'adv_autotune': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'adv_consolemenu': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'adv_consolemsg': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'adv_consolescreensaver': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'adv_firmwarevc': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'adv_motd': ('django.db.models.fields.TextField', [], {'max_length': '1024'}),
            'adv_powerdaemon': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'adv_serialconsole': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'adv_swapondrive': ('django.db.models.fields.IntegerField', [], {'default': '2'}),
            'adv_systembeep': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'adv_traceback': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'adv_tuning': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'adv_zeroconfbonjour': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        'system.cronjob': {
            'Meta': {'ordering': "['cron_description', 'cron_user']", 'object_name': 'CronJob'},
            'cron_command': ('django.db.models.fields.TextField', [], {}),
            'cron_daymonth': ('django.db.models.fields.CharField', [], {'default': "'*'", 'max_length': '100'}),
            'cron_dayweek': ('django.db.models.fields.CharField', [], {'default': "'1,2,3,4,5,6,7'", 'max_length': '100'}),
            'cron_description': ('django.db.models.fields.CharField', [], {'max_length': '200', 'blank': 'True'}),
            'cron_enabled': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'cron_hour': ('django.db.models.fields.CharField', [], {'default': "'*'", 'max_length': '100'}),
            'cron_minute': ('django.db.models.fields.CharField', [], {'default': "'00'", 'max_length': '100'}),
            'cron_month': ('django.db.models.fields.CharField', [], {'default': "'1,2,3,4,5,6,7,8,9,a,b,c'", 'max_length': '100'}),
            'cron_user': ('freeadmin.models.UserField', [], {'max_length': '60'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        'system.email': {
            'Meta': {'object_name': 'Email'},
            'em_fromemail': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '120'}),
            'em_outgoingserver': ('django.db.models.fields.CharField', [], {'max_length': '120', 'blank': 'True'}),
            'em_pass': ('django.db.models.fields.CharField', [], {'max_length': '120', 'null': 'True', 'blank': 'True'}),
            'em_port': ('django.db.models.fields.IntegerField', [], {'default': '25'}),
            'em_security': ('django.db.models.fields.CharField', [], {'default': "'plain'", 'max_length': '120'}),
            'em_smtp': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'em_user': ('django.db.models.fields.CharField', [], {'max_length': '120', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        'system.ntpserver': {
            'Meta': {'ordering': "['ntp_address']", 'object_name': 'NTPServer'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'ntp_address': ('django.db.models.fields.CharField', [], {'max_length': '120'}),
            'ntp_burst': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'ntp_iburst': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'ntp_maxpoll': ('django.db.models.fields.IntegerField', [], {'default': '10'}),
            'ntp_minpoll': ('django.db.models.fields.IntegerField', [], {'default': '6'}),
            'ntp_prefer': ('django.db.models.fields.BooleanField', [], {'default': 'False'})
        },
        'system.rsync': {
            'Meta': {'ordering': "['rsync_path', 'rsync_desc']", 'object_name': 'Rsync'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'rsync_archive': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'rsync_compress': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'rsync_daymonth': ('django.db.models.fields.CharField', [], {'default': "'*'", 'max_length': '100'}),
            'rsync_dayweek': ('django.db.models.fields.CharField', [], {'default': "'1,2,3,4,5,6,7'", 'max_length': '100'}),
            'rsync_delete': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'rsync_desc': ('django.db.models.fields.CharField', [], {'max_length': '120', 'blank': 'True'}),
            'rsync_direction': ('django.db.models.fields.CharField', [], {'default': "'push'", 'max_length': '10'}),
            'rsync_enabled': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'rsync_extra': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'rsync_hour': ('django.db.models.fields.CharField', [], {'default': "'*'", 'max_length': '100'}),
            'rsync_minute': ('django.db.models.fields.CharField', [], {'default': "'00'", 'max_length': '100'}),
            'rsync_mode': ('django.db.models.fields.CharField', [], {'default': "'module'", 'max_length': '20'}),
            'rsync_month': ('django.db.models.fields.CharField', [], {'default': "'1,2,3,4,5,6,7,8,9,a,b,c'", 'max_length': '100'}),
            'rsync_path': ('freeadmin.models.PathField', [], {'max_length': '255'}),
            'rsync_preserveattr': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'rsync_preserveperm': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'rsync_quiet': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'rsync_recursive': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'rsync_remotehost': ('django.db.models.fields.CharField', [], {'max_length': '120'}),
            'rsync_remotemodule': ('django.db.models.fields.CharField', [], {'max_length': '120', 'blank': 'True'}),
            'rsync_remotepath': ('django.db.models.fields.CharField', [], {'max_length': '120', 'blank': 'True'}),
            'rsync_times': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'rsync_user': ('freeadmin.models.UserField', [], {'max_length': '60'})
        },
        'system.settings': {
            'Meta': {'object_name': 'Settings'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'stg_guiaddress': ('django.db.models.fields.CharField', [], {'default': "'0.0.0.0'", 'max_length': '120', 'blank': 'True'}),
            'stg_guiport': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '120', 'blank': 'True'}),
            'stg_guiprotocol': ('django.db.models.fields.CharField', [], {'default': "'http'", 'max_length': '120'}),
            'stg_language': ('django.db.models.fields.CharField', [], {'default': "'en'", 'max_length': '120'}),
            'stg_syslogserver': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '120', 'blank': 'True'}),
            'stg_timezone': ('django.db.models.fields.CharField', [], {'default': "'Asia/Tehran'", 'max_length': '120'})
        },
        'system.smarttest': {
            'Meta': {'ordering': "['smarttest_type']", 'object_name': 'SMARTTest'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'smarttest_daymonth': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'smarttest_dayweek': ('django.db.models.fields.CharField', [], {'default': "'1,2,3,4,5,6,7'", 'max_length': '100'}),
            'smarttest_desc': ('django.db.models.fields.CharField', [], {'max_length': '120', 'blank': 'True'}),
            'smarttest_disks': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['storage.Disk']", 'symmetrical': 'False'}),
            'smarttest_hour': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'smarttest_month': ('django.db.models.fields.CharField', [], {'default': "'1,2,3,4,5,6,7,8,9,10,a,b,c'", 'max_length': '100'}),
            'smarttest_type': ('django.db.models.fields.CharField', [], {'max_length': '2'})
        },
        'system.ssl': {
            'Meta': {'object_name': 'SSL'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'ssl_certfile': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'ssl_city': ('django.db.models.fields.CharField', [], {'max_length': '120', 'null': 'True', 'blank': 'True'}),
            'ssl_common': ('django.db.models.fields.CharField', [], {'max_length': '120', 'null': 'True', 'blank': 'True'}),
            'ssl_country': ('django.db.models.fields.CharField', [], {'max_length': '120', 'null': 'True', 'blank': 'True'}),
            'ssl_email': ('django.db.models.fields.CharField', [], {'max_length': '120', 'null': 'True', 'blank': 'True'}),
            'ssl_org': ('django.db.models.fields.CharField', [], {'max_length': '120', 'null': 'True', 'blank': 'True'}),
            'ssl_state': ('django.db.models.fields.CharField', [], {'max_length': '120', 'null': 'True', 'blank': 'True'}),
            'ssl_unit': ('django.db.models.fields.CharField', [], {'max_length': '120', 'null': 'True', 'blank': 'True'})
        },
        'system.sysctl': {
            'Meta': {'ordering': "['sysctl_mib']", 'object_name': 'Sysctl'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'sysctl_comment': ('django.db.models.fields.CharField', [], {'max_length': '100', 'blank': 'True'}),
            'sysctl_enabled': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'sysctl_mib': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '50'}),
            'sysctl_value': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'system.tunable': {
            'Meta': {'ordering': "['tun_var']", 'object_name': 'Tunable'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'tun_comment': ('django.db.models.fields.CharField', [], {'max_length': '100', 'blank': 'True'}),
            'tun_enabled': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'tun_value': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'tun_var': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '50'})
        }
    }

    complete_apps = ['system']