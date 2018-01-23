from django.http import HttpResponse, HttpResponseNotFound, JsonResponse
from django.shortcuts import render_to_response, render
from django.views.decorators.csrf import csrf_exempt
from wechatpy import parse_message, create_reply
from wechatpy.exceptions import InvalidAppIdException
from wechatpy.exceptions import InvalidSignatureException
from wechatpy.utils import check_signature
from on.wechatconfig import TOKEN, DOMAIN, payClient, NotifyUrl
from on.user import UserInfo, UserTrade, UserWithdraw, UserRefund, UserOrder
from on.activities.reading.models import ReadingGoal
from wechatpy.events import BaseEvent
from wechatpy.messages import BaseMessage
from wechatpy import parse_message
import xmltodict
from wechatpy.utils import to_text
from on.views import oauth
from logging import getLogger
import json
from on.views import get_son_models
import math
from django.conf import settings
from wechatpy.replies import ArticlesReply, ImageReply
from wechatpy.utils import ObjectDict
import uuid

article_2018  = [{
    # On!说明
    'title': '2018 Let\'s On! 一起来立个Flag吧！',
    'description': 'test',
    'image': 'https://mmbiz.qpic.cn/mmbiz_png/GsETib8eibZY23xPrlzOKUE8mM4Iic5JibRibkYicH7n35jt5HaktibkkjicgB6eO8mNgOCciaAvlopFZTicUIsJNop8GCeA/0?wx_fmt=png',
    'url': 'https://mp.weixin.qq.com/s?__biz=MzI2Mjc4OTU4Ng==&mid=2247483757&idx=1&sn=bad525c9dfd25e2afc74608058c2210d&chksm=ea4481d0dd3308c670620a8c9ada954888e37a618710ff0dbe41942fc2555f495a980ece56e3#rd'
},{
    # 参与方式
    'title': '【预定参与】活动',
    'description': 'test',
    'image': 'https://mmbiz.qpic.cn/mmbiz_png/GsETib8eibZY20xQwceTCibyib7YIKibjS0CyXLlbgNSXxoZKkFr7W5v4tUrYL71zN8zeAdxYulibYhg0icJHWqPBYsYQ/0?wx_fmt=png',
    'url': 'https://mp.weixin.qq.com/s?__biz=MzI2Mjc4OTU4Ng==&mid=2247483757&idx=2&sn=52f0b8841ca6bfe2c63098e709fbf4cc&chksm=ea4481d0dd3308c66bfb380995fb5075ebfd6f011247d0708ad4c510a381a9f9f91f699b8d91#rd'
},{
    'title': '【支持On!】活动',
    'description': 'test',
    'image': 'https://mmbiz.qpic.cn/mmbiz_png/GsETib8eibZY1cAwwwd2EOau3pghFMk6ILba8a7AyiczpibtpJe7xhy0RK6PZ3vo0DazIIMO95AJphdqeKg93bLJMw/0?wx_fmt=png',
    'url': 'https://mp.weixin.qq.com/s?__biz=MzI2Mjc4OTU4Ng==&mid=2247483757&idx=3&sn=e1cb922e553a52fdd49425aea14d7421&chksm=ea4481d0dd3308c6eee06268b1279a9f0d0ed21ffb7bd50c2822efe608a557e9c6bcdfdbf673#rd'
},{
    'title': 'On! 有什么不同？',
    'description': 'test',
    'image': 'https://mmbiz.qpic.cn/mmbiz_jpg/GsETib8eibZY1pTvH0dFibfVtFqyAxLYEyFDicu6xiaRxxwcY9Xs3icYS82kFVpSVhiaho2KBWBD1K3oHbnJkI2rCuNqg/0?wx_fmt=jpeg',
    'url': 'https://mp.weixin.qq.com/s?__biz=MzI2Mjc4OTU4Ng==&mid=2247483757&idx=4&sn=798372dca5b507a75446cc394175263e&chksm=ea4481d0dd3308c69910c6516985b779c640b3047c92197aa86846fc6bf0a9aed49681608b44#rd'
},{
    'title': 'On! 有什么好玩？',
    'description': 'test',
    'image': 'http://mmbiz.qpic.cn/mmbiz_png/GsETib8eibZY1pTvH0dFibfVtFqyAxLYEyFgrte7ljzlVIxpG2KElcFfpphiaOicr0pn7ZxKeXTM1sqWnD8BgHSibbaA/640?wx_fmt=png&tp=webp&wxfrom=5&wx_lazy=1',
    'url': 'https://mp.weixin.qq.com/s?__biz=MzI2Mjc4OTU4Ng==&mid=2247483757&idx=5&sn=85f6c907247ffb29c7f96da2da856d1b&chksm=ea4481d0dd3308c6d5739d3c0266f97c4c0806f0244603dabeb659064909a01ab5f7a212b3ca#rd'
},{
    'title': 'On! 有什么福利？',
    'description': 'test',
    'image': 'http://mmbiz.qpic.cn/mmbiz_jpg/GsETib8eibZY1cAwwwd2EOau3pghFMk6IL91J3RK7mFFv5INfUhG9KEOlaiaVniaW14BJQs0JXOlyIm4vlE8GyKEww/640?wx_fmt=jpeg&tp=webp&wxfrom=5&wx_lazy=1',
    'url': 'https://mp.weixin.qq.com/s?__biz=MzI2Mjc4OTU4Ng==&mid=2247483757&idx=6&sn=bbab1d1e2830f681063e99c460295cde&chksm=ea4481d0dd3308c6475baa028183aa8a15d9bc26d7fa2d08206e157d18bcc59cb9a4f56850b5#rd'
}]


inform_articles= [{
    # On!说明
    'title': '平台介绍&概况说明',
    'description': 'test',
    'image': 'https://mmbiz.qpic.cn/mmbiz_png/GsETib8eibZY1zZxe0pSyoic9PBHgC8lCODB9BQyBGRmic3KFzgeUBsciaXvPplt7lkUB8JKGuPLE9hiaRCuyPJhaVSg/0?wx_fmt=png',
    'url': 'https://mp.weixin.qq.com/s?__biz=MzI2Mjc4OTU4Ng==&mid=2247483694&idx=1&sn=2a270285b50932ed5a39995d5a4b6040&chksm=ea448193dd3308859d193fb3b50442ee0e77b9327bf05e68825d2b737c7c35dc64125d629df4#rd'
},{
    # 参与方式
    'title': '活动参与方式',
    'description': 'test',
    'image': 'https://mmbiz.qpic.cn/mmbiz_png/GsETib8eibZY2j1kI7mrJs96V1icMaNyHyF0GkcDLK4TbWc5E5MGrzGZLciciaVDAULMia5iaJBFpooU31PWuyG4tglfQ/0?wx_fmt=png',
    'url': 'https://mp.weixin.qq.com/s?__biz=MzI2Mjc4OTU4Ng==&mid=2247483694&idx=2&sn=34eaf70ff67f6f1eaaa500c6f0303425&chksm=ea448193dd330885b348af47bb4aac628125d98995029397fc6743d1998e7b4b73d765bb4b44#rd'
},{
    'title': '提现相关问题',
    'description': 'test',
    'image': 'https://mmbiz.qpic.cn/mmbiz_png/GsETib8eibZY2j1kI7mrJs96V1icMaNyHyFAv9rRohPt6Qu96X80lPATxFVWEaEdwtVEyMrkpH1CmVXECdjqrZvbg/0?wx_fmt=png',
    'url': 'https://mp.weixin.qq.com/s?__biz=MzI2Mjc4OTU4Ng==&mid=2247483694&idx=3&sn=c5b23717c2589d1a77e80dec302d6151&chksm=ea448193dd330885741904acf5658562fd89d650b891e2a517f36867a49e3135886bff749d43#rd'
},{
    'title': '订单及商品相关问题',
    'description': 'test',
    'image': 'https://mmbiz.qpic.cn/mmbiz_png/GsETib8eibZY2j1kI7mrJs96V1icMaNyHyFKN1yiaYWJoKBmLY2Mu081TpYwDItwSIicNgaewbpR5OB2SlfhHszOKbg/0?wx_fmt=png',
    'url': 'https://mp.weixin.qq.com/s?__biz=MzI2Mjc4OTU4Ng==&mid=2247483694&idx=4&sn=39b263666f84fd62627a19be9bc1be53&chksm=ea448193dd33088582f7b93f738767925e50cdd4b5926b643bfc1d383686f6cc9a2a1f4b5fa3#rd'
},{
    'title': 'On!平台元素说明',
    'description': 'test',
    'image': 'https://mmbiz.qpic.cn/mmbiz_png/GsETib8eibZY2j1kI7mrJs96V1icMaNyHyFHZstBe4mYR4T9Lg3icLiaa8GfcgJHybNaQR0VnYg3hy2ub7KwGusxDzA/0?wx_fmt=png',
    'url': 'https://mp.weixin.qq.com/s?__biz=MzI2Mjc4OTU4Ng==&mid=2247483694&idx=5&sn=b160a992d091be653a46978f8a195435&chksm=ea448193dd330885e93abb6a55c69efcec5af92ab46283b734fc7ec26fa1f70d2670f64c9fde#rd'
}]


logger = getLogger("money")

# 用于安全域名的验证
def wechat_js_config(request):
    return HttpResponse("kJNErHZuAor4kA9O")

# 关注事件时发送的欢迎语
welcome_str = '欢迎来到On蜕变！\n为了明天的自己Let\'s On![Yeah!]'
# 点击app时发送的消息
app_information = 'App将在4月份上线，敬请期待！'
# 固定回复模板
inform_str = '请稍等，On!君还在路上！'

# 验证URL函数
@csrf_exempt
def wechat_check(request):
    if request.method == 'GET':
        # 校验
        signature = request.GET.get('signature', '')
        timestamp = request.GET.get('timestamp', '')
        nonce = request.GET.get('nonce', '')
        echo_str = request.GET.get('echostr', '')
        try:
            check_signature(TOKEN, signature, timestamp, nonce)
        except InvalidSignatureException:
            return HttpResponse(status=403)
        return HttpResponse(echo_str)
    else:
        # 自动回复文本
        try:
            msg = parse_message(request.body)
            if isinstance(msg, BaseEvent):
                if msg.event == 'subscribe':
                    reply = create_reply(article_2018, message=msg)
                elif msg.event == 'click':
                    if msg.key == 'app_information':
                        reply = create_reply(app_information, msg)
                else:
                    reply = create_reply('Sorry, can not handle this for now', msg)
            elif isinstance(msg, BaseMessage):
                if msg.type == 'text':
                    content = msg.content
                    if "说明" in content:
                        reply = create_reply(inform_articles, message=msg)
                    elif "客服" in content:
                        reply = ImageReply(message=msg, media_id='nvnR6egwWE1WzzIcMXo403dxqfcx5fV_GRhQnRH8Wsw')
                    elif "2018" in content:
                        reply = create_reply(article_2018, message=msg)
                    else:
                        reply = create_reply('', message=msg)
                        #reply = ArticlesReply(message=msg)
                else:
                    reply = create_reply('', message=msg)
            else:
                reply = create_reply('Sorry, can not handle this for now', msg)
            return HttpResponse(reply.render(), content_type="application/xml")
        except (InvalidSignatureException, InvalidAppIdException):
            return HttpResponse(status=403)


@oauth
def wechat_pay(request):
    # attach 里带了新建目标的 id
    if request.POST:
        openid = request.session['user'].wechat_id
        if settings.DEBUG:
            fee = 1
        else:
            fee = int(float(request.POST['price']) * 100)
        goal_id = request.POST['goal']
        order_res = payClient.order.create(trade_type="JSAPI",
                                           body="目标活动押金",
                                           total_fee=fee,
                                           notify_url=NotifyUrl,
                                           user_id=openid,
                                           detail="支付活动目标的押金",
                                           device_info="WEB",
                                           attach=goal_id)
        prepay_id = order_res['prepay_id']
        pay_code = payClient.jsapi.get_jsapi_params(prepay_id=prepay_id)
        return JsonResponse(pay_code)
    else:
        return HttpResponseNotFound


# 已开通企业付款，实现微信转账接口
def transfer_to_person(request):
    try:
        user = request.session['user']
        if settings.DEBUG:
            price = 100
        else:
            price = int(100 * float(request.POST['price']))
            balance = UserInfo.objects.get(user_id=user.user_id).balance
            assert price == int(100 * balance)
        if price < 100:
            # 201 错误码代表最小提取1.00元
            return JsonResponse({'status': 201})
        else:
            if settings.DEBUG:
                data = payClient.transfer.transfer(user_id='o0jd6wk8OK77nbVqPNLKG-2urQxQ',
                                                   amount=100,
                                                   desc="用户{0}发起提现".format(user.user_id),
                                                   check_name="NO_CHECK")
            else:
                data = payClient.transfer.transfer(user_id=user.wechat_id,
                                                   amount=price,
                                                   desc="用户{0}发起提现".format(user.user_id),
                                                   check_name="NO_CHECK")
            if data['result_code'] == 'SUCCESS':
                UserWithdraw.objects.create_withdraw(openid=user.wechat_id,
                                                     amount=price,
                                                     trade_data=data)
                # 更新用户的余额
                UserInfo.objects.clear_balance(user_id=user.user_id)
                return JsonResponse({'status': 200})
            else:
                logger.error("用户{0}发起提现".format(user.user_id))
                logger.error(data)
                # 说明付款失败，联系客服处理
                return JsonResponse({'status': 401})
    except AssertionError as a:
        return JsonResponse({'status': 403})
    except Exception as e:
        logger.error(str(e))
        return JsonResponse({'status': 401})


@csrf_exempt
def wechat_pay_back(request):
    if settings.DEBUG:
        goal_id = request.POST['goal']
        user = request.session['user']
        transaction_id = str(uuid.uuid4())
        trade_data = {
            "device_info":"DEBUG",
            "openid": "o0jd6wk8OK77nbVqPNLKG-2urQxQ",
            "trade_type":"JSAPI",
            "trade_state":"SUCCESS",
            "bank_type":"DEBUG",
            "total_fee":1,
            "cash_fee":1,
            "fee_type":"CNY",
            "transaction_id":transaction_id,
            "out_trade_no":uuid.uuid4(),
            "time_end":23456,
            "result_code":"SUCCESS"
        }
        UserTrade.objects.create_trade(goal_id=goal_id, trade_data=trade_data)
        # 更新用户的押金信息
        UserInfo.objects.update_deposit(user_id=user.user_id, pay_delta=float(trade_data['total_fee']) / 100)
        # 当支付成功后,将attach中的goal取出来, 设其为活跃状态
        from on.activities.base import Goal
        sub_models = get_son_models(Goal)
        for sub_model_key in sub_models:
            sub_model = sub_models[sub_model_key]
            goal = sub_model.objects.filter(user_id=user.user_id).filter(goal_id=goal_id).filter(status='PENDING')
            if goal:
                # 如果找到了用户该类型的goal，将其设置为活跃状态
                goal = goal.first()
                goal.status = 'ACTIVE'
                goal.save()
                # 更新对应活动的奖金池与参与人数
                goal.update_activity(user_id=user.user_id)
                # 如果是阅读活动，则需要在支付完成后新建一个发货订单
                if sub_model_key == ReadingGoal.__name__:
                    UserOrder.objects.create_reading_goal_order(user_id=user.user_id,
                                                                order_name=goal.book_name,
                                                                order_money=goal.price,
                                                                order_image=goal.imageurl)
        return JsonResponse({'status':200})
    # 微信支付回调接口，此时支付成功，可以将流水记录写入数据库
    else:
        try:
            res = payClient.parse_payment_result(request.body)
            xml_str = "<xml><return_code><![CDATA[{0}]]></return_code></xml>".format(res['result_code'])
        except Exception as e:
            logger.error(e)
            return HttpResponseNotFound
        else:
            try:
                user = UserInfo.objects.get_user_by_openid(res['openid'])
                goal_id = res['attach']
                # 把支付的结果写入交易表中
                if not UserTrade.objects.exist_trade(res['transaction_id']):
                    UserTrade.objects.create_trade(goal_id=goal_id, trade_data=res)
                    # 更新用户的押金信息
                    UserInfo.objects.update_deposit(user_id=user.user_id, pay_delta=float(res['total_fee'])/100)
                    # 当支付成功后,将attach中的goal取出来, 设其为活跃状态
                    from on.activities.base import Goal
                    sub_models = get_son_models(Goal)
                    for sub_model_key in sub_models:
                        sub_model = sub_models[sub_model_key]
                        goal = sub_model.objects.filter(user_id=user.user_id).filter(goal_id=goal_id).filter(status='PENDING')
                        if goal:
                            # 如果找到了用户该类型的goal，将其设置为活跃状态
                            goal = goal.first()
                            goal.status = 'ACTIVE'
                            goal.save()
                            # 更新对应活动的奖金池与参与人数
                            goal.update_activity(user_id=user.user_id)
                            # 如果是阅读活动，则需要在支付完成后新建一个发货订单
                            if sub_model_key == ReadingGoal.__name__:
                                UserOrder.objects.create_reading_goal_order(user_id=user.user_id,
                                                                            order_name=goal.book_name,
                                                                            order_money=goal.price,
                                                                            order_image=goal.imageurl)
                            break
            except Exception as e:
                logger.error(e)
            return HttpResponse(xml_str)
