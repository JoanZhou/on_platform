import django
import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "on.settings.local")
django.setup()

from on.user import UserInfo, UserTicket
from on.activities.running.models import RunningGoal

tickets = [{
        'ticket_type': 'NS',
        'number':3
    },
    {
        'ticket_type': 'D',
        'number':3
    }]

if __name__ == '__main__':
    user = UserInfo.objects.get(wechat_id="Lq372899855")
    goal_id = RunningGoal.objects.all().first()
    for ticket in tickets:
        UserTicket.objects.create_ticket(goal_id,ticket['ticket_type'],ticket['number'])

