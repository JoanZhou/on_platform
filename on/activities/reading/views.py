from django.shortcuts import render
from django.shortcuts import render, redirect
from django.http import HttpResponse
from on.user import UserInfo, UserTicket, UserAddress
from on.models import Activity, ReadingGoal
from on.errorviews import page_not_found
from datetime import timedelta
import django.utils.timezone as timezone
from on.wechatconfig import get_wechat_config
from on.views import fake_data

def get_days(goal):
    days_set = ['一', '二', '三', '四', '五', '六', '日']
    dates = []
    # 第几天
    first_day = goal.start_time.date()
    day_index = (timezone.now().date() - first_day).days + 1
    for i in range(-3, 4):
        last_date = timezone.now() + timedelta(days=i)
        # Y 表示 yes, N 表示 no, S 表示未开始
        is_complete = True
        punch_inform = None
        if i <= 0:
            punchs = goal.punch.get_day_record(i)
            is_complete = True if punchs else False
            if is_complete:
                punch_inform = punchs[0]
        dates.append({
            "weekday": days_set[last_date.weekday()],
            "date": last_date.day,
            "isfinish": is_complete,
            "punch": punch_inform,
            "dayindex": i + day_index
        })
    return dates


def show_reading_goal(request, pk):
    user = request.session['user']
    goal_id = pk
    goal = ReadingGoal.objects.filter(goal_id=goal_id).filter(activity_type=ReadingGoal.get_activity()).first()
    if goal:
        if goal.status != "ACTIVE":
            return render(request, 'goal/finish.html',
                          {
                              'goal': goal,
                              'goal_type': ReadingGoal.get_activity()
                           })
        else:
            # 天数
            dates_inform = get_days(goal)
            # 查询 Activity 相关的活动信息, 找到第一个符合类型要求且在进行中的活动
            app = Activity.objects.get_active_activity(activity_type=ReadingGoal.get_activity())
            person_goals = ReadingGoal.objects.filter(status="ACTIVE")[:5]
            persons = set()
            # TODO:FAKE
            app = fake_data([app])[0]
            for person_goal in person_goals:
                persons.add(UserInfo.objects.get(user_id=person_goal.user_id))

            return render(request, "goal/reading.html",
                          {
                              "WechatJSConfig": get_wechat_config(request),
                              "app": app,
                              "goal": goal,
                              "datesinform": dates_inform,
                              "notice": UserAddress.objects.address_is_complete(user=user),
                              "persons": persons,
                          })
    else:
        return page_not_found(request)
