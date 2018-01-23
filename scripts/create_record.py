import django
import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "on.settings.local")
django.setup()

from on.user import UserInfo, UserRecord

record = {
        'finish_times': 0,
        'finish_days': 0,
        'join_times': 0,
        'all_coefficient': 0
    }


if __name__ == '__main__':
    user = UserInfo.objects.get(wechat_id="Lq372899855")
    userrecord = UserRecord(
        user=user,
        **record)
    userrecord.save()

