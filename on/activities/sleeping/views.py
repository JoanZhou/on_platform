from django.shortcuts import render
from on.user import UserInfo, UserTicket
from on.models import Activity, SleepingGoal, SleepingPunchRecord
from on.errorviews import page_not_found
from datetime import date, datetime, timedelta
import django.utils.timezone as timezone
# from on.views import fake_data
from on.wechatconfig import get_wechat_config
import random
from on.upload_test import print_test
import decimal


# 这里注意一点，只有在结算时才判定用户当天是否完成任务
def get_days(goal,sleep_type):
    from on.activities.reading.models import Saying
    days_set = ['一', '二', '三', '四', '五', '六', '日']
    dates = []
    time_now = timezone.now()

    # 获取显示第几天的数值, 作息中开始时间的当晚就已经是第1天
    first_day = goal.start_time.date()
    day_index = (timezone.now().date() - first_day).days + 1
    # 确定查询日期界限1
    for i in range(day_index):
        # 将目前的时间推到8小时以后，这样可以保证不论白天还是夜晚所获取的数据均正常
        last_date = first_day + timedelta(days=i)
        that_day = (goal.start_time + timedelta(days=i)).strftime("%Y-%m-%d")
        records = SleepingPunchRecord.objects.filter(goal=goal, punch_time=that_day)
        saying = Saying.objects.filter(activity_type=int(goal.activity_type), id=random.randint(31, 64))
        # 是否完成了今日的打卡
        punchs = goal.punch.get_day_record(i)
        is_complete = True if punchs else False
        is_day_now = True if last_date == timezone.now().date() else False
        dayindex = i
        is_night = False
        is_morning = False
        punch_record = SleepingPunchRecord.objects.filter(punch_time=that_day,goal=goal)
        # sleep_type = SleepingGoal.objects.filter(goal=goal)
        # sleepType = 1
        # if sleep_type:
        #     sleep_type = sleep_type[0]
        #     sleepType = sleep_type
        record_morning = None
        record_night = None
        button = 0
        if punch_record:
            record_morning = punch_record[0].get_up_time
            record_night = punch_record[0].sleep_time
        if time_now.hour >= 5 and time_now.hour < 8:
            dayindex = i
            button = 1 if record_morning else 0
            is_morning = True
        elif time_now.hour < 21 and time_now.hour >= 8:
            dayindex = i
        elif time_now.hour >= 21 and time_now.hour < 24 and sleep_type == 0:
            button = 1 if record_night else 0
            dayindex = i + 1
            is_night = True

        if records:
            records = records[0]
            is_sleep_punch = True if records.sleep_time else False
            dates.append({
                "weekday": days_set[last_date.weekday()],
                "date": last_date.day,
                "isfinish": is_complete,
                "dayindex": dayindex,
                "is_day_now": is_day_now,
                "saying": saying[0].content,
                'records': records,
                'is_night': is_night,
                'is_morning': is_morning,
                "is_sleep_punch": is_sleep_punch,
                "button": button
            })
        else:
            dates.append({
                "weekday": days_set[last_date.weekday()],
                "date": last_date.day,
                "isfinish": is_complete,
                "dayindex": dayindex,
                "is_day_now": is_day_now,
                "saying": saying[0].content,
                "is_night": is_night,
                "is_morning": is_morning,
                "button": button

            })
    for i in range(first_day.weekday()):
        blank_date2 = {
            "date": (first_day - timedelta(days=i + 1)).day,
            "isfinish": False,
            "isnosignin": False,
            "punch": "",
            "dayindex": "-1"
        }
        dates.insert(0, blank_date2)
    # 后面插入空白日期补全日历day_now=5
    day_now = timezone.now().date().weekday()
    back_day = 6 - day_now
    # b_day = None
    # day_num = 1
    # '''如果实在九点之前，那么就直接是跟原本补全的一样'''
    # if time_now.hour < 21:
    #     day_num = 1
    #     b_day = back_day
    # # 如果是九点之后，并且不是第一天，那么不做处理
    # elif time_now.hour >= 21 and time_now.hour < 24 and not is_first_day:
    #     day_num = 1
    #     b_day = back_day
    # # 若是酒店之后且是第一天，那么就补全日期一天
    # elif time_now.hour >= 21 and time_now.hour < 24 and is_first_day:
    #     day_num = 2
    #     b_day = back_day - 1
    for i in range(back_day):
        blank_date1 = {
            "date": (timezone.now().date() + timedelta(days=i + 1)).day,
            "isfinish": False,
            "isnosignin": False,
            "punch": "",
            "dayindex": "-1"
        }
        dates.append(blank_date1)
    i = 0
    new_date = []
    while i < int(len(dates)):
        date_list = dates[i:i + 7]
        i += 7
        new_date.append(date_list)
    return new_date

#
def comment_all(user):
    from on.activities.sleeping.models import CommentSleep, ReplySleep, SleepingPunchPraise
    comment_obj = CommentSleep.objects.filter(is_delete=0,is_top=1).order_by("-c_time")
    datas = []
    for comment in comment_obj:
        reply = ReplySleep.objects.filter(other_id=comment.id).order_by('id')
        response = [{"content": i.r_content, "other_id": i.user_id, "nickname": i.get_user_message.nickname} for
                    i in reply] if len(reply) > 0 else ""
        prise = SleepingPunchPraise.objects.filter(punch_id=comment.id, user_id=user.user_id)
        is_no_prise = 1 if len(prise) > 0 else 0
        ref = comment.voucher_ref.split(",") if len(comment.voucher_ref) > 0 else ""
        top = comment.is_top
        if top == 0:
            datas.append({
                "id": comment.id,
                'user_id': comment.user_id,
                "content": comment.content,
                "c_time": comment.c_time,
                "prise": comment.prise,
                "report": comment.report,
                "voucher_ref": ref,
                "is_delete": comment.is_delete,
                "is_top": comment.is_top,
                "headimgurl": comment.get_some_message.headimgurl,
                "nickname": comment.get_some_message.nickname,
                "is_no_prise": is_no_prise,
                "reply_data": response
            })
    return datas


def show_sleeping_goal(request, pk):
    from on.activities.sleeping.models import Coefficient
    # goal_id = pk
    goal = SleepingGoal.objects.filter(goal_id=pk).filter(activity_type=SleepingGoal.get_activity()).first()
    user = request.session['user']
    user_id = user.user_id
    print_test()
    if goal:
        if goal.status != "ACTIVE":
            return render(request, 'goal/finish.html',
                          {
                              'goal': goal,
                              'goal_type': SleepingGoal.get_activity(),
                              "headimg":user.headimgurl
                          })
        else:
            # 天数
            sleep_type = goal.sleep_type
            dates_inform = get_days(goal,sleep_type)
            # 查询 Activity 相关的活动信息, 找到第一个符合类型要求且在进行中的活动
            app = Activity.objects.get_active_activity(activity_type=SleepingGoal.get_activity())
            new_coeff = 0
            default = 0
            extra_coeff=0
            try:
                coeff = Coefficient.objects.get(user_id=user_id)
                default = coeff.default_coeff
                new_coeff = coeff.new_coeff
                if new_coeff:
                    extra_coeff = (new_coeff-default)/default*decimal.Decimal(100)
                    if extra_coeff >0:
                        extra_coeff  = "+%2d"%extra_coeff+"%"
                    elif extra_coeff <0:
                        extra_coeff = "%2d"%extra_coeff+"%"
                    else:
                        pass
                else:
                    extra_coeff =""
            except Coefficient.DoesNotExist as e:
                print(e)
            # 查询头像
            person_goals = SleepingGoal.objects.filter(status="ACTIVE")[:5]
            persons = set()
            for person_goal in person_goals:
                persons.add(UserInfo.objects.get(user_id=person_goal.user_id))
            # datas = comment_all(user=user)
            return render(request, "goal/sleeping.html",
                          {
                              "app": app,
                              "WechatJSConfig": get_wechat_config(request),
                              "goal": goal,
                              "nickname": user.nickname,
                              "datesinform": dates_inform,
                              "new_coeff":new_coeff,
                              # "getuptime": goal.getup_time.strftime("%H:%M"),
                              "persons": persons,
                              "datas": comment_all(user=user),
                              "default":default,
                              "extra_coeff":extra_coeff
                          })
    else:
        return page_not_found(request)
