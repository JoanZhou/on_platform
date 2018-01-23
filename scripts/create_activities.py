#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Script to create On! activities
#

import dateutil.parser
import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "on.settings.local")
django.setup()
from on.activities.base import Activity

activities = [
{
        'activity_type': u'2',
        'coefficient': 0,
        'active_participants': 0,
        'max_participants': 10000000,
        'description': u'读书',
    },
    {
        'activity_type': u'1',
        'coefficient': 0,
        'active_participants': 0,
        'max_participants': 10000000,
        'description': u'跑步',
    },
    {
        'activity_type': u'0',
        'coefficient': 0,
        'active_participants': 0,
        'max_participants': 10000000,
        'description': u'作息',
    }]

"""
{
    'activity_type': u'3',
    'start_time': '2017-10-01 00:00:00',
    'end_time': None,
    'status': 'pending',
    'coefficient': 20,
    'active_participants': 0,
    'max_participants': 500,
    'logoimgurl': 'https://i2.kknews.cc/large/11140000ded9b4d94975',
    'description': u'',
}
"""

if __name__ == '__main__':
    for activity_data in activities:
        print('Creating activity - %s' % (activity_data['activity_type']))

        # Parse datetime string to Django DateTimeField
        try:
            a = Activity(**activity_data)
            a.save()
        except Exception as e:
            print(e)
