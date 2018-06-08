
from on.activities.riding.model import RidingCoefficient, Riding_Finish_Save

from logging import getLogger

import requests
from django.conf import settings
from django.http import JsonResponse, HttpResponseNotFound
from django.shortcuts import render
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from wechatpy.utils import random_string
from on.models import  RidingGoal, RidingPunchRecord
from on.settings.local import DEBUG

logger = getLogger("app")


@csrf_exempt
def create_riding_goal(request):
    print('开始创建骑行活动')
    if request.POST:
        print(11111111111)
        user = request.session.get("user")
        # if DEBUG:
        # 	user_id = 101077
        # else:
        user_id = user.user_id
        print(222222222222)
        data_json = request.POST
        print(3333333333333)
        goal_type = data_json.get("goal_type")
        print(444444444444444)
        guaranty = data_json.get("guaranty")
        print(444444444444)
        coefficient = data_json.get("coefficient")
        print(55555555555555555)
        multiple = data_json.get("multiple")
        print(6666666666666666666)
        kilos_day = data_json.get("kilos_day", "")
        print(77777777777777777777777)
        goal_distance = data_json.get('goal_distance', '')
        print(9999999999)
        print('goal_distance', goal_distance)
        print(100000000000000000)
        mode = data_json.get("mode")
        print(122222222222222)
        goal_day = data_json.get("goal_day")
        print(13333333333333333333333)
        reality_price = data_json.get("reality_price")
        print(14444444444444444444444444)
        deserve_price = data_json.get('deserve_price')
        print(15555555555555555555)
        down_num = data_json.get("down_num")
        print(16666666666666666)
        down_payment = data_json.get("down_payment")
        print(17777777777777777777777)
        activate_deposit = data_json.get("activate_deposit")
        print(1888888888888888888888)

        punch_attention = data_json.get("punch_attention", 1)
        # print('punch_attention', punch_attention)
        print(199999999999999999)
        is_no_use_point = data_json.get("is_no_use_point", 0)
        # distance = data_json.get("distance", "")
        print(2000000000000000000000)
        deduction_point = data_json.get("deduction_point", 0)
        print(211111111111111111111111)
        deduction_guaranty = data_json.get("deduction_guaranty", 0)
        print(233333333333333333333333333333)
        start_time = timezone.now()
        print(244444444444444444444)
        # 参数教检

        # 自由模式与日常模式的个别参数不一样,自由模式没有每日距离,goal_distance表示的是目标距离
        if goal_type == 0:
            print('自由模式')
            if not all([reality_price, deserve_price, down_num, guaranty, down_payment, coefficient
                           , mode, goal_day, punch_attention, is_no_use_point, goal_distance, deduction_point,
                        deduction_guaranty, multiple]):
                print('333333333')
                return JsonResponse({"status": 403, "errmsg": "参数不完整"})
        # 日常模式，有每日距离，kilos_day表示的是剩余距离
        elif goal_type == 1:
            print('日常模式')
            if not all([reality_price, deserve_price, down_num, guaranty, down_payment, coefficient
                           , mode, goal_day, punch_attention, is_no_use_point, kilos_day, deduction_point,
                        deduction_guaranty, multiple]):
                return JsonResponse({"status": 403, "errmsg": "参数不完整"})

        # 若参数完整，处理业务
        try:
            goal = RidingGoal.objects.create_ridinggoal(user_id=user_id,
                                                        goal_type=goal_type,
                                                        guaranty=guaranty,
                                                        down_payment=down_payment,
                                                        activate_deposit=activate_deposit,
                                                        coefficient=coefficient,
                                                        mode=mode,
                                                        goal_day=goal_day,
                                                        goal_distance=goal_distance,
                                                        reality_price=reality_price,
                                                        deserve_price=deserve_price,
                                                        down_num=down_num,
                                                        start_time=start_time,
                                                        kilos_day=kilos_day,
                                                        multiple=multiple,
                                                        deduction_point=deduction_point,
                                                        deduction_guaranty=deduction_guaranty,
                                                        )
            coeff = RidingCoefficient.objects.filter(user_id=user_id)
            if coeff is not None:
                coeff.delete()
                RidingCoefficient.objects.create(user_id=user_id, default_coeff=coefficient, goal_type=goal_type)
            else:
                RidingCoefficient.objects.create(user_id=user_id, default_coeff=coefficient, goal_type=goal_type)
            print('骑行活动创建成功')
            return JsonResponse({"status": 200, "goal": goal.goal_id})
        except Exception as e:
            print(e)
            return JsonResponse({"status": 502})


@csrf_exempt
def riding_punch(request):
    print("进入骑行打卡")
    """获取随机数"""
    user = request.session.get("user")
    random = request.POST.get("random")
    if DEBUG:
        user_id = 101077
    else:
        user_id = user.user_id
    # try:
    #     resp = send_img.delay(user.user_id, random, user.wechat_id, "1")
    #     print("第{}张图片的发送结果{}".format(random, resp))
    # except Exception as e:
    #     print(e)
    #     logger.error(e)
    """获取对应的目标的goal id"""
    goal_id = request.POST.get('goal', ' ')
    distance = float(request.POST.get('distance', 0))
    goal = RidingGoal.objects.get(goal_id=goal_id)
    """获取前端传递的两个路径"""
    file_filepath = request.POST.get("file_filepath")

    file_refpath = request.POST.get("file_refpath")
    document = request.POST.get("document", " ")
    """获取当前的时间"""
    punch_time = timezone.now()
    print("获取参数完成")
    try:
        punch = RidingPunchRecord.objects.create_riding_redord(goal=goal,
                                                               user_id=user_id,
                                                               voucher_ref=file_refpath,
                                                               voucher_store=file_filepath,
                                                               distance=distance,
                                                               record_time=punch_time,
                                                               document=document)
        # goal.punch_day += 1
        print('打卡成功')
        return JsonResponse({"status": 200})
    except Exception as e:
        logger.error(e)
        return JsonResponse({"status": 405})


@csrf_exempt
def save_riding_comments(request):
    from on.activities.riding.model import CommentRiding
    user = request.session.get("user")
    time_now = timezone.now().strftime("%Y-%m-%d %H:%M")
    if request.POST:
        try:
            content = request.POST.get("content")
            voucher_ref = request.POST.get("voucher_ref")
            voucher_store = request.POST.get("voucher_store")
            # 若用户表不存在，则先给用户创建一个jilu
            CommentRiding.objects.create(user=user, content=content, voucher_ref=voucher_ref,
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
def riding_reply(request):
    user = request.session.get("user")
    from on.activities.riding.model import RidingReply
    if request.POST:
        r_content = request.POST.get("r_content")
        other_id = request.POST.get("other_id")
        try:
            RidingReply.objects.create(user_id=user.user_id, other_id=other_id.replace("-", ""), r_content=r_content)
            return JsonResponse({"status": 200})
        except Exception as e:
            print("用户评论失败", e)
            return JsonResponse({"status": 403})
    return JsonResponse({"status": 403})


# sleeping 点赞
@csrf_exempt
def riding_prise(request):
    from on.activities.riding.model import CommentRiding

    user = request.session.get("user")
    if request.POST:
        id = request.POST.get("id")
        try:
            CommentRiding.objects.praise_comment(user_id=user.user_id, punch_id=id)
            return JsonResponse({"status": 200})
        except Exception as e:
            print("点赞失败", e)
            return JsonResponse({"status": 401})
    else:
        return JsonResponse({"status": 401})


# sleeping删除评论
@csrf_exempt
def delete_riding_comments(request):
    from on.activities.riding.model import CommentRiding
    if request.POST:
        user = request.session.get("user")
        id = request.POST.get("id")
        try:
            CommentRiding.objects.filter(id=id).update(is_delete=1)
            return JsonResponse({"status": 200})
        except Exception as e:
            print("删除失败", e)
            return JsonResponse({"status": 403})
    else:
        return JsonResponse({"status": 403})