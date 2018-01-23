from django.shortcuts import render
from on.user import UserInfo, UserTicket
from on.models import Activity, SleepingGoal, SleepingPunchRecord
from on.errorviews import page_not_found
from datetime import date, datetime, timedelta
import django.utils.timezone as timezone
from on.views import fake_data
from django.conf import settings

# 这里注意一点，只有在结算时才判定用户当天是否完成任务
def get_days(goal):
    days_set = ['一', '二', '三', '四', '五', '六', '日']
    dates = []
    mode = 'forbidden'
    time_now = timezone.now()
    # 获取显示第几天的数值, 作息中开始时间的当晚就已经是第1天
    first_day = goal.start_time.date()
    day_index = (timezone.now().date() - first_day).days + 1
    # 获取应该起床的时间
    should_get_up_time = datetime.combine(date.today(), goal.getup_time)
    # 如果用户使用了延时卡，则延长打卡时间
    morning_limit = should_get_up_time + timedelta(hours=1) if goal.use_delay_date(0) else should_get_up_time

    # 如果是夜间，则算作后一天 21:00-23:59
    if time_now.hour >= 21 and time_now.hour < 24:
        mode = 'night'
        day_index += 1
    # 如果是早上，则检查是否有延时券
    elif time_now.hour >= 5 and time_now <= morning_limit:
        mode = 'morning'
    # 如果是早上，则按照当天计算
    elif time_now > morning_limit and time_now.hour < 13:
        # 在这段时间段内,检查时间应该已经产生了,查询今日的检查时间
        check_time = goal.punch.get_today_check_time()
        # 如果检查时间存在且当前时间与check_time之间的时间符合关系
        if check_time and time_now >= check_time and time_now <= check_time + timedelta(minutes=15):
            mode = 'check'
    # 否则是凌晨时间
    elif time_now.hour < 5:
        mode = 'forbidden'
    # 否则的话应该是前一天的下午时间段，day_index + 1
    else:
        day_index += 1
        mode = 'forbidden'

    # 确定查询日期界限
    for i in range(-3, 4):
        # 将目前的时间推到8小时以后，这样可以保证不论白天还是夜晚所获取的数据均正常
        last_date = timezone.now() + timedelta(days=i)
        # 是否完成了今日的打卡
        is_complete = False
        # 今天是否使用了免签卡
        is_no_sign_in = False
        # 今天是否使用了延时卡
        is_delay = False
        # 对于历史记录，判断它们是否完成了打卡
        if i <= 0:
            # 使用confirm的时间来判断是否成功打卡
            punchs = goal.punch.get_day_record(i)
            # 如果有confirm那肯定是没有问题的
            is_complete = True if punchs else False
            if not is_complete:
                # 如果未完成的话，则查看当天是否使用了免签券
                is_no_sign_in = goal.use_no_sign_in_date(i)
        if i == 0:
            # 判断是否使用了延时卡
            is_delay = goal.use_delay_date(i)
            # 如果当天没有使用，且时间超过了限制，则自动使用延时卡
            if not is_delay and should_get_up_time < time_now < should_get_up_time + timedelta(hours=1):
                has_ticket = UserTicket.objects.use_ticket(goal_id=goal.goal_id,
                                                           ticket_type="D")
                if has_ticket:
                    mode = 'morning'
        # 不论是否使用了免签券，都需要获得所有名义上今天的打卡时间
        sleep_time, getup_time, confirm_time, check_time, checktime_end = goal.get_time_for_display(i)


        if settings.DEBUG:
            if not sleep_time:
                mode = "night"
            elif not getup_time:
                mode = "morning"
            elif not confirm_time:
                mode = "check"
            else:
                mode = "forbidden"

        dates.append({
            # mode字段是留给今天准备的
            "mode": mode,
            "weekday": days_set[last_date.weekday()],
            "date": last_date.day,
            "isfinish": is_complete,
            "isnosignin": is_no_sign_in,
            "isdelay": is_delay,
            "dayindex": i + day_index,
            "getuptime": getup_time,
            "sleeptime": sleep_time,
            "confirmtime": confirm_time,
            "checktime": check_time,
            "checktimeend": checktime_end
        })
    return dates


def show_sleeping_goal(request, pk):
    goal_id = pk
    goal = SleepingGoal.objects.filter(goal_id=goal_id).filter(activity_type=SleepingGoal.get_activity()).first()
    if goal:
        if goal.status != "ACTIVE":
            return render(request, 'goal/finish.html',
                          {
                              'goal': goal,
                              'goal_type': SleepingGoal.get_activity()
                           })
        else:
            # 延迟券
            delay_ticket = UserTicket.objects.get_delay_tickets(goal_id=goal_id)
            # 免签券
            nosign_ticket = UserTicket.objects.get_nosigned_tickets(goal_id=goal_id)
            # 天数
            dates_inform = get_days(goal)
            # 查询 Activity 相关的活动信息, 找到第一个符合类型要求且在进行中的活动
            app = Activity.objects.get_active_activity(activity_type=SleepingGoal.get_activity())
            # TODO:FAKE
            app = fake_data([app])[0]
            # 查询头像
            person_goals = SleepingGoal.objects.filter(status="ACTIVE")[:5]
            persons = set()
            for person_goal in person_goals:
                persons.add(UserInfo.objects.get(user_id=person_goal.user_id))

            return render(request, "goal/sleeping.html",
                          {
                              "app": app,
                              "goal": goal,
                              'delay': delay_ticket,
                              'nosign': nosign_ticket,
                              "datesinform": dates_inform,
                              "getuptime": goal.getup_time.strftime("%H:%M"),
                              "persons": persons
                          })
    else:
        return page_not_found(request)
