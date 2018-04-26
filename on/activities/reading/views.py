from django.shortcuts import render
from django.shortcuts import render
from django.http import HttpResponse
from on.user import UserInfo, UserTicket, UserAddress, UserOrder
from on.models import Activity, ReadingGoal
from on.activities.reading.models import BookInfo, ReadingGoal, ReadTime, ReadingPunchRecord, Saying, \
    ReadingPunchPraise, ReadingPunchReport
from on.errorviews import page_not_found
from datetime import timedelta
import django.utils.timezone as timezone
from on.wechatconfig import get_wechat_config
from on.views import fake_data
import random
import math


def get_days(goal, goal_id):
    days_set = ['一', '二', '三', '四', '五', '六', '日']
    dates = []
    # 头一天的日期
    first_day = goal.start_time.date()
    start = goal.start_time
    # 活动的时间长36
    day_index = (timezone.now().date() - first_day).days + 1
    # 开始星期的星期数
    start_week = first_day.weekday()
    # 现在的时间的星期数4
    day_now = timezone.now().date().weekday()

    for i in range(day_index):
        # 开始的日期
        last = (goal.start_time + timedelta(days=i)).strftime("%Y-%m-%d")
        saying = Saying.objects.filter(id=random.randint(1, 4))

        last_date = first_day + timedelta(days=i)
        # 从那天开始到那一天结束的时间
        # end = last_date + timedelta(days=1)
        punch_inform = None
        punchs = ReadingPunchRecord.objects.filter(record_time=last,
                                                   goal_id=goal_id.replace("-", ""))
        is_complete = True if punchs else False
        if is_complete:
            punch_inform = punchs[0]

            # is_no_sign_in = goal.use_no_sign_in_date(i)
        # 判断是否是当天，格式是月份
        if last_date == timezone.now().date():
            is_day_now = True
        else:
            is_day_now = False
        # 判断当天是否开始
        # dates.append({
        #         #     "weekday": days_set[last_date.weekday()],
        #         #     "is_day_now": is_day_now,
        #         #     "date": last_date.day,
        #         #     "isfinish": is_complete,
        #         #     "punch": punch_inform,
        #         #     # "start_page":punch_inform.start_page,
        #         #     # "bonus":punch_inform.bonus,
        #         #     # "reading_page": int(punch_inform.reading_page),
        #         #     # "reading_delta": punch_inform.reading_delta,
        #         #     "start_page": 1,
        #         #     "bonus": 2,
        #         #     "reading_page": 3,
        #         #     "reading_delta": 4,
        #         #     "dayindex": i + 1,
        #         # })
        if punchs:
            dates.append({
                "dayindex": i + 1,
                "is_day_now": is_day_now,
                "date": last_date.day,
                "isfinish": is_complete,
                "start_page": punch_inform.start_page,
                "bonus": punch_inform.bonus,
                "saying": saying[0].content,
                "reading_page": int(punch_inform.reading_page),
                "reading_delta": math.ceil(punch_inform.reading_delta / 60),
            })
        else:
            dates.append({
                "dayindex": i + 1,
                "is_day_now": is_day_now,
                "date": last_date.day,
                "isfinish": is_complete,
                "saying": saying[0].content,
                "start_page": 1,
                "bonus": 1,
                "reading_page": 1,
                "reading_delta": 1,
            })
    # 补全日期
    # 前面插入空白日期补全日历start_week=3
    for i in range(start_week):
        blank_date2 = {
            "date": (first_day - timedelta(days=i + 1)).day,
            "isfinish": False,
            "punch": "",
            "dayindex": "0"
        }
        dates.insert(0, blank_date2)
    # 后面插入空白日期补全日历day_now=5

    for i in range(6 - day_now):
        blank_date1 = {
            "date": (timezone.now().date() + timedelta(days=i + 1)).day,
            "isfinish": False,
            "punch": "",
            "dayindex": "0"
        }
        dates.append(blank_date1)
    i = 0
    new_date = []
    while i < int(len(dates)):
        date_list = dates[i:i + 7]
        i += 7
        new_date.append(date_list)
    return new_date


def show_reading_goal(request, pk):
    from on.activities.reading.models import Comments, Reply

    user = request.session["user"]
    goal_id = pk

    read = ReadingGoal.objects.filter(goal_id=goal_id).filter(activity_type=ReadingGoal.get_activity()).first()
    readinginfo = BookInfo.objects.get_book_info(book_id=1)
    # user = UserInfo.objects.filter(user_id=user.user_id)[0]
    # user = UserInfo.objects.get(user_id=user.user_id)
    if read:
        if read.status == "SUCCESS" or read.status == "FAILED":
            return render(request, 'goal/finish.html',
                          {
                              'goal': read,
                              'goal_type': ReadingGoal.get_activity(),
                              "headimg": user.headimgurl
                          })
        elif read.status == "ACTIVE":
            # 天数.
            dates_inform = get_days(read, goal_id)
            state = ReadTime.objects.get_reading_state(user_id=user.user_id)
            time_range = ReadTime.objects.filter(user_id=user.user_id)[0]
            # 查询 Activity 相关的活动信息, 找到第一个符合类型要求且在进行中的活动
            app = Activity.objects.get_active_activity(activity_type=ReadingGoal.get_activity())
            person_goals = ReadingGoal.objects.filter(status="ACTIVE")[:5]
            persons = set()
            # TODO:FAKE
            app = fake_data([app])[0]
            confirm = UserOrder.objects.filter(user_id=user.user_id, goal_id=goal_id)
            if confirm:
                is_no_confirm = confirm[0].is_no_confirm
            elif read.is_start == 1:
                is_no_confirm = 1
            else:
                is_no_confirm = None
            for person_goal in person_goals:
                persons.add(UserInfo.objects.get(user_id=person_goal.user_id))

            owen = Comments.objects.filter(user_id=user.user_id).order_by("-c_time")
            comment_obj = Comments.objects.filter(is_delete=0).order_by("-c_time")
            datas = []
            for comment in comment_obj:
                report = ReadingPunchReport.objects.filter(punch_id=comment.id,user_id=user.user_id)
                reply = Reply.objects.filter(other_id=comment.id)
                response = [{"content": i.r_content, "other_id": i.user_id, "nickname": i.get_user_message.nickname} for
                            i in reply] if len(reply) > 0 else ""
                is_no_report = 1 if len(report) > 0 else 0
                prise = ReadingPunchPraise.objects.filter(punch_id=comment.id,user_id=user.user_id)
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
                        "is_no_report": is_no_report,
                        "is_no_prise": is_no_prise,
                        "reply_data": response
                    })
                else:
                    datas = []
            return render(request, "goal/reading.html",
                          {
                              "WechatJSConfig": get_wechat_config(request),
                              "app": app,
                              "goal": read,
                              "datesinform": dates_inform,
                              "notice": UserAddress.objects.address_is_complete(user=user),
                              "persons": persons,
                              "book_id": read.book_id,
                              "is_start": read.is_start,
                              "readinginfo": readinginfo,
                              "state": state,
                              "time_range": timezone.now() - time_range.start_read,
                              "is_no_confirm": is_no_confirm,
                              "user_comments": owen,
                              "datas": datas,
                              "nickname": user.nickname
                          })
        else:
            app = Activity.objects.get_active_activity(activity_type=ReadingGoal.get_activity())
            # 用户头像
            person_goals = ReadingGoal.objects.filter(status="ACTIVE")[:5]
            persons = set()
            # TODO:FAKE
            app = fake_data([app])[0]
            for person_goal in person_goals:
                persons.add(UserInfo.objects.get(user_id=person_goal.user_id))
            context = {
                "WechatJSConfig": get_wechat_config(request),
                "readinginfo": readinginfo,
                "app": app,
                "balance": user.balance
            }
            return render(request, "activity/reading.html", context)
    else:
        app = Activity.objects.get_active_activity(activity_type=ReadingGoal.get_activity())
        # 用户余额
        # 用户头像
        person_goals = ReadingGoal.objects.filter(status="ACTIVE")[:5]
        persons = set()
        # TODO:FAKE
        app = fake_data([app])[0]
        for person_goal in person_goals:
            persons.add(UserInfo.objects.get(user_id=person_goal.user_id))

        context = {
            "WechatJSConfig": get_wechat_config(request),
            "readinginfo": readinginfo,
            "app": app,
            "balance": user.balance
        }
        return render(request, "activity/reading.html", context)
