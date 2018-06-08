
from on.activities.sleeping.models import Coefficient, Sleep_Finish_Save

import time

from django.http import JsonResponse, HttpResponseNotFound
from django.shortcuts import render
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt

from on.models import SleepingGoal, SleepingPunchRecord,Activity
from logging import getLogger
from on.settings.local import DEBUG
from on.task import send_img
from on.temp.push_template import do_push
from on.user import UserTicket, UserRecord, UserInfo, UserOrder


logger = getLogger("app")

@csrf_exempt
def create_sleep_goal(request):
    if request.POST:
        user = request.session.get("user")
        guaranty = request.POST.get("guaranty")
        coefficient = request.POST.get("coefficient")
        goal_type = request.POST.get("goal_type")
        goal_day = request.POST.get("goal_day")
        sleep_type = request.POST.get("sleep_type")
        reality_price = request.POST["reality_price"]
        deserve_price = request.POST["deserve_price"]
        multiple = request.POST.get("multiple", 1)
        punch_attention = request.POST.get("punch_attention", 1)
        is_no_use_point = request.POST.get("is_no_use_point", 0)
        if not all([guaranty, coefficient, goal_day, sleep_type, reality_price, deserve_price]):
            return JsonResponse({"status": 403, "errmsg": "参数不完整"})

        if DEBUG:
            try:
                goal = SleepingGoal.objects.create_goal(user_id=user.user_id,
                                                        guaranty=guaranty,
                                                        coefficient=coefficient,
                                                        goal_day=goal_day,
                                                        goal_type=goal_type,
                                                        sleep_type=sleep_type,
                                                        punch_attention=punch_attention,
                                                        is_no_use_point=is_no_use_point,
                                                        reality_price=reality_price,
                                                        deserve_price=deserve_price
                                                        )
                if not Coefficient.objects.filter(user_id=user.user_id):
                    Coefficient.objects.create(user_id=user.user_id, default_coeff=coefficient, sleep_type=sleep_type)
                # 顺便创建一条打卡记录
                # SleepingPunchRecord.objects.create(goal=goal, punch_time=timezone.now().strftime("%Y-%m-%d"),user_id=100274)
                response_data = {'status': 200, 'goal': goal.goal_id}
                return JsonResponse(response_data)
            except Exception as e:
                print("创建作息活动失败", e)
                return JsonResponse({"status": 403})
        else:
            try:
                goal = SleepingGoal.objects.create_goal(user_id=user.user_id,
                                                        guaranty=guaranty,
                                                        coefficient=coefficient,
                                                        goal_day=goal_day,
                                                        goal_type=goal_type,
                                                        multiple=multiple,
                                                        punch_attention=punch_attention,
                                                        is_no_use_point=is_no_use_point,
                                                        sleep_type=sleep_type,
                                                        reality_price=reality_price,
                                                        deserve_price=deserve_price
                                                        )
                coeff = Coefficient.objects.filter(user_id=user.user_id)
                if coeff:
                    coeff.delete()
                    Coefficient.objects.create(user_id=user.user_id, sleep_type=sleep_type, default_coeff=coefficient)
                else:
                    Coefficient.objects.create(user_id=user.user_id, sleep_type=sleep_type, default_coeff=coefficient)
                print(goal.goal_id)
                # 顺便创建一条打卡记录
                response_data = {'status': 200, 'goal': goal.goal_id}
                return JsonResponse(response_data)
            except Exception as e:
                print("创建作息活动失败", e)
                return JsonResponse({"status": 403})


@csrf_exempt
def sleeping_sleep_handler(request):
    if request.POST:

        user = request.session.get("user")
        goal_id = request.POST['goal']
        random = int(request.POST.get("random"))
        sleep_type = int(request.POST.get("sleep_type"))
        # if not all([goal_id,sleep_type]):
        #     return JsonResponse({"status":403,"errmsg":"数据不完整"})
        goal = SleepingGoal.objects.get(goal_id=goal_id)
        record = ""
        try:
            if DEBUG:
                if sleep_type == 0:
                    # 如果record无误，则打卡成功；否则打卡失败
                    record = SleepingPunchRecord.objects.create_sleep_record(goal=goal, sleep_type=sleep_type,
                                                                             user_id=user.user_id)
                    resp = send_img.delay(user.user_id, random, user.wechat_id, "0")
                    print("第{}张图片的发送结果{}".format(random, resp))
                elif sleep_type == 1:
                    record = SleepingPunchRecord.objects.update_getup_record(goal=goal, sleep_type=sleep_type,
                                                                             user_id=user.user_id)
                    resp = send_img.delay(user.user_id, random, user.wechat_id, "0")
                    print("第{}张图片的发送结果{}".format(random, resp))
                if record:
                    return JsonResponse({'status': 200})
                else:
                    return JsonResponse({'status': 201})
            else:

                if sleep_type == 0:
                    # 如果record无误，则打卡成功；否则打卡失败
                    record = SleepingPunchRecord.objects.create_sleep_record(goal=goal, sleep_type=sleep_type,
                                                                             user_id=user.user_id)
                    resp = send_img.delay(user.user_id, random, user.wechat_id, "0")
                    print("第{}张图片的发送结果{}".format(random, resp))
                elif sleep_type == 1:
                    record = SleepingPunchRecord.objects.update_getup_record(goal=goal, sleep_type=sleep_type,
                                                                             user_id=user.user_id)
                    resp = send_img.delay(user.user_id, random, user.wechat_id, "0")
                    print("第{}张图片的发送结果{}".format(random, resp))

                if record:
                    return JsonResponse({'status': 200})
                else:
                    return JsonResponse({'status': 201})
        except Exception as e:
            print(e)
            logger.error(e)
            return JsonResponse({"status": 403})

    else:
        return JsonResponse({"status": 403})


# 作息确认打卡
def sleeping_confirm_handler(request):
    if request.POST:
        user = request.session['user']
        # 查询当前打卡用户的openid
        # 查询用户的nickname
        goal_id = request.POST['goal']
        goal = SleepingGoal.objects.get(goal_id=goal_id)
        punch_time = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))
        # 如果record无误，则返回确认时间；否则打卡失败
        record = goal.punch.update_confirm_time()
        if record:
            """增加用户的完成天数"""
            UserRecord.objects.update_finish_day(user=request.session['user'])
            return JsonResponse({'status': 200,
                                 'time': record.confirm_time.time().strftime("%H:%M")})
        else:
            return JsonResponse({'status': 201})


@csrf_exempt
def delete_sleep_goal(request):
    user = request.session['user']
    try:
        if request.POST:
            activity_type = request.POST['goal_type']
            goal_id = request.POST['goal']
            if not all([activity_type, goal_id]):
                return JsonResponse({"status": 403})
            print("参数完整")
            sleep = SleepingGoal.objects.get(goal_id=goal_id)
            UserRecord.objects.finish_goal(user=user)
            print("开始更新押金")
            UserInfo.objects.update_deposit(user_id=user.user_id,
                                            pay_delta=-sleep.guaranty)
            print("更新成功", sleep.bonus)
            UserInfo.objects.sleep_handle(user_id=user.user_id, bonus=sleep.bonus, guaranty=sleep.guaranty,
                                          extra_earn=sleep.extra_earn)
            print("更新用户的余额成功")
            try:
                print("开始保存用户的数据")
                Sleep_Finish_Save.objects.save_finish(goal_id=goal_id)
                import time
                time.sleep(1)
            except Exception as e:
                print("记录用户的结束保存信息失败", e)
            try:
                SleepingPunchRecord.objects.filter(goal_id=goal_id).delete()
                SleepingGoal.objects.filter(goal_id=goal_id).delete()
                Coefficient.objects.filter(user_id=user.user_id).delete()
            except Exception as e:
                print("删除读书活动失败", e)
            # 用户的目标结束之后，更新参加人数跟奖金池，系数
            try:
                sleep.update_activity_person()
                act = Activity.objects.get(activity_id="a5a0206fb2aa4e8995263c7ab0afa1b5")
                act.bonus_all -= (sleep.guaranty + sleep.down_payment)
                act.save()
            except Exception as e:
                print("更新失败", e)
            return JsonResponse({"status": 200})
        else:
            return JsonResponse({"status": 403})
    except Exception as e:
        print(e)
        return JsonResponse({"status": 401})


@csrf_exempt
def save_sleep_comments(request):
    from on.activities.sleeping.models import CommentSleep
    user = request.session.get("user")
    time_now = timezone.now().strftime("%Y-%m-%d %H:%M")
    if request.POST:
        try:
            content = request.POST.get("content")
            voucher_ref = request.POST.get("voucher_ref")
            voucher_store = request.POST.get("voucher_store")
            # 若用户表不存在，则先给用户创建一个jilu
            CommentSleep.objects.create(user=user, content=content, voucher_ref=voucher_ref,
                                        voucher_store=voucher_store,
                                        c_time=time_now)
            return JsonResponse({"status": 200})
        except Exception as e:
            print("评论失败", e)
            return JsonResponse({"status": 401})
    else:
        return JsonResponse({"status": 401})


# sleeping 回复
@csrf_exempt
def sleep_reply(request):
    user = request.session.get("user")
    from on.activities.sleeping.models import ReplySleep
    if request.POST:
        r_content = request.POST.get("r_content")
        other_id = request.POST.get("other_id")
        try:
            ReplySleep.objects.create(user_id=user.user_id, other_id=other_id.replace("-", ""), r_content=r_content)
            return JsonResponse({"status": 200})
        except Exception as e:
            print("用户评论失败", e)
            return JsonResponse({"status": 403})
    return JsonResponse({"status": 403})


# sleeping 点赞
@csrf_exempt
def sleep_prise(request):
    from on.activities.sleeping.models import CommentSleep

    user = request.session.get("user")
    if request.POST:
        id = request.POST.get("id")
        try:
            CommentSleep.objects.praise_comment(user_id=user.user_id, punch_id=id)
            return JsonResponse({"status": 200})
        except Exception as e:
            print("点赞失败", e)
            return JsonResponse({"status": 401})
    else:
        return JsonResponse({"status": 401})


# sleeping删除评论
@csrf_exempt
def delete_sleep_comments(request):
    from on.activities.sleeping.models import CommentSleep
    if request.POST:
        user = request.session.get("user")
        id = request.POST.get("id")
        try:
            CommentSleep.objects.filter(id=id).update(is_delete=1)
            return JsonResponse({"status": 200})
        except Exception as e:
            print("删除失败", e)
            return JsonResponse({"status": 403})
    else:
        return JsonResponse({"status": 403})
