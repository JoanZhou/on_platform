#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Script to create On! running tasks
#

import dateutil.parser

import django
import os
import datetime

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "on.settings.local")
django.setup()

from on.models import Activity, RunningGoal, RunningPunchRecord, ReadingGoal, ReadingPunchRecord, SleepingGoal, SleepingPunchRecord
from on.user import UserInfo

if __name__ == '__main__':

    user = UserInfo.objects.get(wechat_id="o0jd6wk8OK77nbVqPNLKG-2urQxQ")

    running_goal_free = {
        'start_time': '2017-12-17 00:00:00',
        'end_time': '2017-12-25 00:00:00',
        'guaranty': 150,
        'goal_type': 0,
        'down_payment': 50,
        'coefficient': 30,
        'goal_distance':50,
        'left_distance': 50,
        'bonus':0,
        'user_id':user.user_id,
        'status':'ACTIVE'
    }

    running_goal_no_free = {
        'start_time': '2017-12-18 00:00:00',
        'end_time': '2017-12-25 00:00:00',
        'guaranty': 150,
        'goal_type': 1,
        'down_payment': 50,
        'coefficient': 30,
        'goal_distance': 50,
        'kilos_day':5,
        'bonus':0,
        'user_id':user.user_id,
        'status': 'ACTIVE'
    }


    reading_goal = {
        'start_time': '2017-11-30 00:00:00',
        'end_time': '2017-12-03 00:00:00',
        'guaranty': 150,
        'down_payment': 50,
        'coefficient': 30,
        'goal_page': 200,
        'finish_page': 5,
        'book_name': '沉默的大多数',
        'bonus': 0,
        'user_id': user.user_id,
        'status': 'ACTIVE'
    }

    sleeping_goal = {
        'start_time': '2017-12-17 00:00:00',
        'end_time': '2017-12-31 00:00:00',
        'guaranty': 150,
        'down_payment': 50,
        'coefficient': 30,
        'getup_time': datetime.time(7,0,0),
        'bonus': 0,
        'user_id': user.user_id,
        'status': 'ACTIVE'
    }

    for time_field in ['start_time', 'end_time']:
        if running_goal_no_free[time_field]:
            running_goal_no_free[time_field] = dateutil.parser.parse(running_goal_no_free[time_field])
        if reading_goal[time_field]:
            reading_goal[time_field] = dateutil.parser.parse(reading_goal[time_field])
        if sleeping_goal[time_field]:
            sleeping_goal[time_field] = dateutil.parser.parse(sleeping_goal[time_field])

    try:
        task = RunningGoal(
            activity_type = '1',
            **running_goal_no_free
        )
        task.save()
        print("Create Running Goal...")
    except Exception as e:
        print(e)

    task = ReadingGoal(
        activity_type = '2',
        **reading_goal
    )
    try:
        task.save()
        print("Create Reading Goal...")
    except Exception as e:
        print(e)

    task = SleepingGoal(
        activity_type= '0',
        **sleeping_goal
    )
    try:
        task.save()
        print("Create Sleeping Goal...")
    except Exception as e:
        print(e)
    """
    for record_data in task_records:
        print('Creating task record - %s %s' % (task, record_data['record_time']))
        # Parse datetime string to Django DateTimeField
        record_data['record_time'] = dateutil.parser.parse(record_data['record_time'])
        if task.punch.filter(record_time=record_data['record_time']).exists():
            print('\tRecord existing, skipped...')
            continue
        record = RunningPunchRecord(
            goal=task,
            **record_data
        )
        record.save()
    """