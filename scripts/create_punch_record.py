import dateutil.parser

import django
import os
import datetime

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "on.settings.local")
django.setup()

from on.models import Activity, RunningGoal, RunningPunchRecord
from on.user import UserInfo

if __name__ == '__main__':
    for i in range(1,10):
        user = UserInfo.objects.get(wechat_id="o0jd6wk8OK77nbVqPNLKG-2urQxQ")
        goal = RunningGoal.objects.get(goal_id="a07639a497e8427b940ceac6bfe1fa51")
        running_goal_free = {
            'goal': goal,
            'voucher_ref': '/static/order/demo.png',
            'voucher_store': 'hhhh',
            'distance': 10+i,
            'praise': 1,
            'report': 2
        }
        record = RunningPunchRecord(**running_goal_free)
        record.save()

