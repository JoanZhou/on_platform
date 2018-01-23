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

    user = UserInfo.objects.get(wechat_id="Lq372899855")

    running_goal_free = {
        'start_time': '2017-12-17 00:00:00',
        'end_time': '2017-12-25 00:00:00',
        'guaranty': 150,
        'goal_type': 0,
        'down_payment': 50,
        'coefficient': 30,
        'goal_distance':50,
        'left_distance': 50,
        'goal_day': 15,
        'left_day': 13,
        'fin_all':0,
        'bonus':0,
        'user_id':user.user_id
    }

    running_goal_no_free = {
        'start_time': '2017-12-18 00:00:00',
        'end_time': '2017-12-25 00:00:00',
        'guaranty': 180,
        'goal_type': 1,
        'down_payment': 30,
        'coefficient': 30,
        'goal_day': 15,
        'left_day': 14,
        'kilos_day':5,
        'fin_all':0,
        'bonus':0,
        'user_id':user.user_id
    }


    for time_field in ['start_time', 'end_time']:
        if running_goal_free[time_field]:
            running_goal_free[time_field] = dateutil.parser.parse(running_goal_free[time_field])
        if running_goal_no_free[time_field]:
            running_goal_no_free[time_field] = dateutil.parser.parse(running_goal_no_free[time_field])

    try:
        task = RunningGoal(
            activity_type = '1',
            **running_goal_free
        )
        task.save()
        print("Create Running Goal...")
    except Exception as e:
        print(e)

    try:
        task = RunningGoal(
            activity_type = '1',
            **running_goal_no_free
        )
        task.save()
        print("Create Running Goal...")
    except Exception as e:
        print(e)