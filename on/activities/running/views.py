from django.shortcuts import render
from django.shortcuts import render, redirect
from django.http import HttpResponse
from on.user import UserInfo, UserTicket
from on.models import Activity, Goal, RunningGoal, SleepingGoal, RunningPunchRecord
from on.errorviews import page_not_found
from datetime import timedelta, date, datetime
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
        is_no_sign_in = False
        punch_inform = None
        if i <= 0:
            punchs = goal.punch.get_day_record(i)
            is_complete = True if punchs else False
            if is_complete:
                punch_inform = punchs[0]
            else:
                is_no_sign_in = goal.use_no_sign_in_date(i)
        dates.append({
            "weekday": days_set[last_date.weekday()],
            "date": last_date.day,
            "isfinish": is_complete,
            "isnosignin": is_no_sign_in,
            "punch": punch_inform,
            "dayindex": i + day_index
        })
    return dates


def show_running_goal(request, pk):
    goal_id = pk
    goal = RunningGoal.objects.filter(goal_id=goal_id).filter(activity_type=RunningGoal.get_activity()).first()
    if goal:
        if goal.status != "ACTIVE":
            return render(request, 'goal/finish.html',
                          {
                              'goal': goal,
                              'goal_type': RunningGoal.get_activity()
                           })
        else:
            # 免签券
            nosign_ticket = UserTicket.objects.get_nosigned_tickets(goal_id=goal_id)
            # 天数
            dates_inform = get_days(goal)
            # 查询 Activity 相关的活动信息, 找到第一个符合类型要求且在进行中的活动
            app = Activity.objects.get_active_activity(activity_type=RunningGoal.get_activity())
            # TODO:FAKE
            app = fake_data([app])[0]
            # 查询 Activity 相关的头像信息
            person_goals = RunningGoal.objects.filter(status="ACTIVE")[:5]
            persons = set()
            for person_goal in person_goals:
                persons.add(UserInfo.objects.get(user_id=person_goal.user_id))
            # 随机查询24小时内存在的打卡记录，展示在本页面中
            lastday, today = timezone.now() - timedelta(days=1), timezone.now()
            random_records = RunningPunchRecord.objects.filter(record_time__range=(lastday, today)).order_by('?')[:5]
            news = []
            for record in random_records:
                userinfo = UserInfo.objects.get(user_id=record.goal.user_id)
                record_time = record.record_time
                dis_day = "今日" if record_time.day == today.day else "昨日"
                dis_date = "{0} {1}:{2}".format(dis_day,
                                               record_time.hour,
                                               record_time.minute)
                news.append({
                    "headimage": userinfo.headimgurl,
                    "date": dis_date,
                    "distance": record.distance,
                    "praise": record.praise,
                    "report": record.report,
                    "name": userinfo.nickname,
                    "voucher_ref": record.voucher_ref,
                    "punch_id": record.punch_id
                })
            if app:
                return render(request, "goal/running.html",
                              {
                                  "WechatJSConfig": get_wechat_config(request),
                                  "app": app,
                                  "goal": goal,
                                  'nosign': nosign_ticket,
                                  "datesinform": dates_inform,
                                  "persons": persons,
                                  "news": news
                              })
            else:
                return page_not_found(request)
    else:
        return page_not_found(request)

