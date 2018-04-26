import decimal
import re
import uuid
from logging import getLogger
from django.shortcuts import render, redirect
import django.utils.timezone as timezone
import xmltodict
from django.conf import settings
from django.http import HttpResponse, HttpResponseNotFound, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from wechatpy import create_reply
from wechatpy import parse_message
from wechatpy.events import BaseEvent
from wechatpy.exceptions import InvalidAppIdException
from wechatpy.exceptions import InvalidSignatureException
from wechatpy.messages import BaseMessage
from wechatpy.replies import ImageReply
from wechatpy.utils import check_signature
from datetime import timedelta, date, datetime
from on.activities.reading.models import ReadingGoal
from on.user import UserInfo, UserTrade, UserWithdraw, UserOrder, UserInvite, Invitenum, newUserWithdraw, UserAddress
from on.activities.running.models import RunningGoal, Activity
from on.views import get_son_models
from on.views import oauth
from on.wechatconfig import oauthClient, client
from on.wechatconfig import TOKEN, payClient, NotifyUrl
from django.db import connection



article_2018 = [{
    # On!说明
    'title': '2018 Let\'s On! 一起来立个Flag吧！',
    'description': 'test',
    'image': 'https://mmbiz.qpic.cn/mmbiz_png/GsETib8eibZY23xPrlzOKUE8mM4Iic5JibRibkYicH7n35jt5HaktibkkjicgB6eO8mNgOCciaAvlopFZTicUIsJNop8GCeA/0?wx_fmt=png',
    'url': 'https://mp.weixin.qq.com/s?__biz=MzI2Mjc4OTU4Ng==&mid=2247483757&idx=1&sn=bad525c9dfd25e2afc74608058c2210d&chksm=ea4481d0dd3308c670620a8c9ada954888e37a618710ff0dbe41942fc2555f495a980ece56e3#rd'
}, {
    # 参与方式
    'title': '【预定参与】活动',
    'description': 'test',
    'image': 'https://mmbiz.qpic.cn/mmbiz_png/GsETib8eibZY20xQwceTCibyib7YIKibjS0CyXLlbgNSXxoZKkFr7W5v4tUrYL71zN8zeAdxYulibYhg0icJHWqPBYsYQ/0?wx_fmt=png',
    'url': 'https://mp.weixin.qq.com/s?__biz=MzI2Mjc4OTU4Ng==&mid=2247483757&idx=2&sn=52f0b8841ca6bfe2c63098e709fbf4cc&chksm=ea4481d0dd3308c66bfb380995fb5075ebfd6f011247d0708ad4c510a381a9f9f91f699b8d91#rd'
}, {
    'title': '【支持On!】活动',
    'description': 'test',
    'image': 'https://mmbiz.qpic.cn/mmbiz_png/GsETib8eibZY1cAwwwd2EOau3pghFMk6ILba8a7AyiczpibtpJe7xhy0RK6PZ3vo0DazIIMO95AJphdqeKg93bLJMw/0?wx_fmt=png',
    'url': 'https://mp.weixin.qq.com/s?__biz=MzI2Mjc4OTU4Ng==&mid=2247483757&idx=3&sn=e1cb922e553a52fdd49425aea14d7421&chksm=ea4481d0dd3308c6eee06268b1279a9f0d0ed21ffb7bd50c2822efe608a557e9c6bcdfdbf673#rd'
}, {
    'title': 'On! 有什么不同？',
    'description': 'test',
    'image': 'https://mmbiz.qpic.cn/mmbiz_jpg/GsETib8eibZY1pTvH0dFibfVtFqyAxLYEyFDicu6xiaRxxwcY9Xs3icYS82kFVpSVhiaho2KBWBD1K3oHbnJkI2rCuNqg/0?wx_fmt=jpeg',
    'url': 'https://mp.weixin.qq.com/s?__biz=MzI2Mjc4OTU4Ng==&mid=2247483757&idx=4&sn=798372dca5b507a75446cc394175263e&chksm=ea4481d0dd3308c69910c6516985b779c640b3047c92197aa86846fc6bf0a9aed49681608b44#rd'
}, {
    'title': 'On! 有什么好玩？',
    'description': 'test',
    'image': 'http://mmbiz.qpic.cn/mmbiz_png/GsETib8eibZY1pTvH0dFibfVtFqyAxLYEyFgrte7ljzlVIxpG2KElcFfpphiaOicr0pn7ZxKeXTM1sqWnD8BgHSibbaA/640?wx_fmt=png&tp=webp&wxfrom=5&wx_lazy=1',
    'url': 'https://mp.weixin.qq.com/s?__biz=MzI2Mjc4OTU4Ng==&mid=2247483757&idx=5&sn=85f6c907247ffb29c7f96da2da856d1b&chksm=ea4481d0dd3308c6d5739d3c0266f97c4c0806f0244603dabeb659064909a01ab5f7a212b3ca#rd'
}, {
    'title': 'On! 有什么福利？',
    'description': 'test',
    'image': 'http://mmbiz.qpic.cn/mmbiz_jpg/GsETib8eibZY1cAwwwd2EOau3pghFMk6IL91J3RK7mFFv5INfUhG9KEOlaiaVniaW14BJQs0JXOlyIm4vlE8GyKEww/640?wx_fmt=jpeg&tp=webp&wxfrom=5&wx_lazy=1',
    'url': 'https://mp.weixin.qq.com/s?__biz=MzI2Mjc4OTU4Ng==&mid=2247483757&idx=6&sn=bbab1d1e2830f681063e99c460295cde&chksm=ea4481d0dd3308c6475baa028183aa8a15d9bc26d7fa2d08206e157d18bcc59cb9a4f56850b5#rd'
}]

inform_articles = [{
    # On!说明
    'title': '平台介绍&概况说明',
    'description': 'test',
    'image': 'https://mmbiz.qpic.cn/mmbiz_png/GsETib8eibZY1zZxe0pSyoic9PBHgC8lCODB9BQyBGRmic3KFzgeUBsciaXvPplt7lkUB8JKGuPLE9hiaRCuyPJhaVSg/0?wx_fmt=png',
    'url': 'https://mp.weixin.qq.com/s?__biz=MzI2Mjc4OTU4Ng==&mid=2247483694&idx=1&sn=2a270285b50932ed5a39995d5a4b6040&chksm=ea448193dd3308859d193fb3b50442ee0e77b9327bf05e68825d2b737c7c35dc64125d629df4#rd'
}, {
    # 参与方式
    'title': '活动参与方式',
    'description': 'test',
    'image': 'https://mmbiz.qpic.cn/mmbiz_png/GsETib8eibZY2j1kI7mrJs96V1icMaNyHyF0GkcDLK4TbWc5E5MGrzGZLciciaVDAULMia5iaJBFpooU31PWuyG4tglfQ/0?wx_fmt=png',
    'url': 'https://mp.weixin.qq.com/s?__biz=MzI2Mjc4OTU4Ng==&mid=2247483694&idx=2&sn=34eaf70ff67f6f1eaaa500c6f0303425&chksm=ea448193dd330885b348af47bb4aac628125d98995029397fc6743d1998e7b4b73d765bb4b44#rd'
}, {
    'title': '提现相关问题',
    'description': 'test',
    'image': 'https://mmbiz.qpic.cn/mmbiz_png/GsETib8eibZY2j1kI7mrJs96V1icMaNyHyFAv9rRohPt6Qu96X80lPATxFVWEaEdwtVEyMrkpH1CmVXECdjqrZvbg/0?wx_fmt=png',
    'url': 'https://mp.weixin.qq.com/s?__biz=MzI2Mjc4OTU4Ng==&mid=2247483694&idx=3&sn=c5b23717c2589d1a77e80dec302d6151&chksm=ea448193dd330885741904acf5658562fd89d650b891e2a517f36867a49e3135886bff749d43#rd'
}, {
    'title': '订单及商品相关问题',
    'description': 'test',
    'image': 'https://mmbiz.qpic.cn/mmbiz_png/GsETib8eibZY2j1kI7mrJs96V1icMaNyHyFKN1yiaYWJoKBmLY2Mu081TpYwDItwSIicNgaewbpR5OB2SlfhHszOKbg/0?wx_fmt=png',
    'url': 'https://mp.weixin.qq.com/s?__biz=MzI2Mjc4OTU4Ng==&mid=2247483694&idx=4&sn=39b263666f84fd62627a19be9bc1be53&chksm=ea448193dd33088582f7b93f738767925e50cdd4b5926b643bfc1d383686f6cc9a2a1f4b5fa3#rd'
}, {
    'title': 'On!平台元素说明',
    'description': 'test',
    'image': 'https://mmbiz.qpic.cn/mmbiz_png/GsETib8eibZY2j1kI7mrJs96V1icMaNyHyFHZstBe4mYR4T9Lg3icLiaa8GfcgJHybNaQR0VnYg3hy2ub7KwGusxDzA/0?wx_fmt=png',
    'url': 'https://mp.weixin.qq.com/s?__biz=MzI2Mjc4OTU4Ng==&mid=2247483694&idx=5&sn=b160a992d091be653a46978f8a195435&chksm=ea448193dd330885e93abb6a55c69efcec5af92ab46283b734fc7ec26fa1f70d2670f64c9fde#rd'
}]

article_leizhu = [
    {
        # On!说明
        'title': '世界读书日，好书100本免费大放送！',
        'description': '今天您能够免费读到一本好书！',
        'image': 'http://mmbiz.qpic.cn/mmbiz_jpg/GsETib8eibZY03W7ia3TDIAGDX2b6rOFXtOWich6Ql8CMjaBQ0jS5kSGh5v1XIZhw987stIcTPmN7AatIR63TiaYATA/0',
        'url': 'https://mp.weixin.qq.com/s/EeqEBNizhRHBG2pI0oGnWw'
    },
    # {
    #     # On!说明
    #     'title': '擂主模式开始啦！打卡最高瓜分10万',
    #     'description': '1元瓜分10万，夭寿啦！！！',
    #     'image': 'http://mmbiz.qpic.cn/mmbiz_jpg/GsETib8eibZY3cPu5XAXukpkgHw23PmO0agVtXkHWa9VDrYZ3C8BtYBahFsawnMZiaBDoib4V9Dl9N5Pa4ZX7dx9Tg/0',
    #     'url': 'https://mp.weixin.qq.com/s?__biz=MzI2Mjc4OTU4Ng==&mid=2247483817&idx=1&sn=6855ad2314c6775f1d93aeed0814b9a7&chksm=ea448114dd33080228d4fd03d2d6756c708402146c09ed4be2b45d242d99cc53d87a3287f811#rd'
    # }
]
# from on.temp.template_map import template
from on.temp.push_template import do_push
import time

logger = getLogger("money")


def send_tem(openid, url, goal_content, activate, activate_time):
    data = {
        "touser": openid,
        "template_id": "WlJal_LqCkIPcwId9cITDXw97c_V9AjF4cPRtZUPWTM",
        "url": url,
        "topcolor": "#FF0000",
        "data": {
            "first": {
                "value": goal_content,
                "color": "#173177"
            },
            "keyword1": {
                "value": activate,
                "color": "#173177"
            },
            "keyword2": {
                "value": activate_time,
                "color": "#173177"
            },
            "remark": {
                "value": "小贴士: 系数越高瓜分越高",
                "color": "#173177"
            },
        }
    }
    return data


def Withdraw_temp(openid, url, price, balance, withdraw_time):
    withdraw = {
        "touser": openid,
        "template_id": "0ABTMFq46xaLRW_FQFlCsmlmH7nRE_Q8suCLkFBEZ4I",
        "url": url,
        "topcolor": "#FF0000",
        "data": {
            "first": {
                "value": "您的提现申请已经受理",
                "color": "#173177"
            },
            "keyword1": {
                "value": price,
                "color": "#173177"
            },
            "keyword2": {
                "value": balance,
                "color": "#173177"
            },
            "keyword3": {
                "value": withdraw_time,
                "color": "#173177"
            },
            "remark": {
                "value": "温馨提示：1~3个工作日内到账",
                "color": "#173177"
            },
        }
    }
    return withdraw


# 用于安全域名的验证
def wechat_js_config(request):
    return HttpResponse("kJNErHZuAor4kA9O")


# 关注事件时发送的欢迎语
welcome_str = '欢迎来到On蜕变！\n为了明天的自己Let\'s On![Yeah!]'
# 点击app时发送的消息
app_information = 'App将在4月份上线，敬请期待！'
# 固定回复模板
inform_str = '请稍等，On!君还在路上！'
withdraw = "我的房间->个人中心->我的钱包->提现"
scan = "欢迎关注On！"
introduce_informmation = ""


# 判断用户的openid是否已经存在
# def

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
                    reply = create_reply(article_leizhu, message=msg)
                elif msg.event == 'click':
                    if msg.key == 'inform_articles':
                        reply = create_reply(inform_articles, msg)
                    elif msg.key == "service":
                        reply = ImageReply(message=msg, media_id='nvnR6egwWE1WzzIcMXo403dxqfcx5fV_GRhQnRH8Wsw')
                # 添加扫描二维码关注事件
                elif msg.event == "scan":
                    reply = create_reply(article_leizhu, message=msg)
                    try:
                        xml_data = str(request.body.decode())
                        dict = xmltodict.parse(xml_data)
                        user = dict["xml"]["FromUserName"]
                        print("扫码用户的openid:{}".format(user))
                        # user_li = re.findall(r"qrscene_(\d+)", user)
                        # user_id = int("".join(user_li)) + 100000
                        # openid = dict["xml"]["FromUserName"]
                    except Exception as e:
                        print(e)
                elif msg.event == "subscribe_scan":
                    reply = create_reply(article_leizhu, message=msg)
                    xml_data = str(request.body.decode())
                    print(xml_data,"454545454")
                    dict = xmltodict.parse(xml_data)
                    user = dict["xml"]["EventKey"]
                    user_li = re.findall(r"qrscene_(\d+)", user)
                    user_id = int("".join(user_li)) + 100000
                    openid = dict["xml"]["FromUserName"]
                    print("扫码用户的openid:{},id:{}".format(openid, user_id))
                    userinfo = UserInfo.objects.check_user(openid)
                    create_time = timezone.now()
                    # if create_time.strftime("%Y-%m-%d") == "2018-04-1":
                    #     fools_day = 1
                    # else:
                    #     fools_day = 0
                    # 如果该用户关系已经存在，那么就不创建该用户关系表
                    if len(UserInvite.objects.filter(invite=openid)) > 0:
                        print("用户关系已经存在，则什么也不做")
                        pass
                    else:
                        print("用户关系不存在，则创建用户关系表")
                        # 创建用户关系
                        UserInvite.objects.create(user_id=user_id, invite=openid, create_time=create_time,
                                                  fools_day=0)
                        # 创建用户邀请数量表
                        Invitenum.objects.undate_num(user_id=user_id)
                        # 增加用户赚取收益比例
                        Invitenum.objects.earning(user_id=user_id)
                else:
                    reply = create_reply('请重试', msg)
            elif isinstance(msg, BaseMessage):
                if msg.type == 'text':
                    content = msg.content
                    if "说明" in content:
                        reply = create_reply(inform_articles, message=msg)
                    elif "客服" in content:
                        reply = ImageReply(message=msg, media_id='nvnR6egwWE1WzzIcMXo403dxqfcx5fV_GRhQnRH8Wsw')
                    elif "2018" in content:
                        reply = create_reply(article_2018, message=msg)
                    elif "提现" in content:
                        reply = create_reply(withdraw, message=msg)
                    else:
                        reply = create_reply('', message=msg)
                else:
                    reply = create_reply('', message=msg)
            else:
                reply = create_reply('Sorry, can not handle this for now', msg)
            return HttpResponse(reply.render(), content_type="application/xml")
        except (InvalidSignatureException, InvalidAppIdException):
            return HttpResponse(status=403)



@oauth
def wechat_pay(request):
    try:
        # attach 里带了新建目标的 id
        user = request.session['user']
        if request.POST:
            openid = user.wechat_id
            rem = request.POST["rem"]
            # 实际付出的钱,必须正数，防止恶意请求
            reality = float(request.POST['reality'])
            # 应该要付出的钱
            deserve = float(request.POST["deserve"])
            # 余额需要支付的钱
            # 如果使用余额
            if rem == '1':
                # 查询用户现在的余额是多少
                user_balance_now = UserInfo.objects.get(user_id=user.user_id).balance
                # 实际应该要付的金额可以直接传过去
                if reality > 0.01:
                    # 若实际支付出去的金额大于0的话，说明余额的钱不够全部支付金额的
                    fee = int(float(reality) * 100)
                    # 余额清零
                    UserInfo.objects.clear_balance(user_id=user.user_id)
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
                # 如果实际应该要付的金额<=0.01，那么就直接让用户支付0.01
                else:
                    print("0.1的情况")
                    if reality == 0.01:
                        # 现在是等于0.01的情况，要判断余额确实大于应付
                        # assert user_balance_now > int(float(deserve) * 100)
                        fee = int(float(reality) * 100)
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
                        # 使用完余额，应该将钱从余额里面扣除
                        # UserInfo.objects.use_balance(user_id=user.user_id,pay_delay = decimal.Decimal(-deserve))
                        return JsonResponse(pay_code)
                    else:
                        return HttpResponse(403)
                        # fee = int(float(request.POST['reality']) * 100)
            # 不使用余额
            else:
                print("不适用余额")
                # fee = int(float(request.POST['deserve']) * 100)
                fee = int(float(deserve) * 100)
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
    except AssertionError as e:
        return JsonResponse({"status": 403})


# 已开通企业付款，实现微信转账接口
def transfer_to_person(request):
    try:
        user = request.session['user']
        print("当前用户的user_id：{}".format(user.user_id))
        if settings.DEBUG:
            price = 100
        else:
            # 从前端传过来的提现金额
            price = int(100 * decimal.Decimal(request.POST['price']))
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
                print("用户{}开始发起提现".format(user.user_id))
                # 检查用户现在的余额是多少
                user_balance_now = UserInfo.objects.get(user_id=user.user_id)
                # 提现金额必须等于现在的金额，否则无法提现
                print("用户现在的余额是多少{}".format(user_balance_now.balance))
                data = payClient.transfer.transfer(user_id=user.wechat_id,
                                                   amount=price,
                                                   desc="用户{0}发起提现".format(user.user_id),
                                                   check_name="NO_CHECK")
                print("用户开始发起提现，提款成功的状态码{}".format(data['result_code']))
                user_balance_now.balance = 0
                user_balance_now.save()
                print("开始判断提款状态吗")
            if data['result_code'] == 'SUCCESS':
                print(data['result_code'], '提款成功的状态码')
                print(user.wechat_id, price, data, user.user_id, "每一项数据")
                try:
                    newUserWithdraw.objects.create(
                        user_id=user.user_id,
                        openid=user.wechat_id,
                        amount=price,
                        partner_trade_no=data["partner_trade_no"],
                        payment_no=data["payment_no"]
                    )
                except Exception as e:
                    print("创建体现记录失败",e)
                # 更新用户的余额
                user_info = UserInfo.objects.get(user_id=user.user_id)
                user_info.balance = 0
                user_info.save()
                print(user_info.balance, "测试现在用户的余额")
                price = "%.2f" % (price / 100)
                print(price, "用户现在的金额")
                # 查询当前余额
                withdraw_time = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))
                url = 'http://wechat.onmytarget.cn/'
                # 构造模板发送模板
                data = Withdraw_temp(user.wechat_id, url, price, 0, withdraw_time)
                do_push(data)
                return JsonResponse({'status': 200})
            else:
                print(data['result_code'], '若是提款失败的状态码')
                logger.error("用户{0}发起提现".format(user.user_id))
                logger.error(data)
                # 说明付款失败，联系客服处理
                return JsonResponse({'status': 401})
    except AssertionError as a:
        print("表示用户现在提现的金额与余额不匹配")
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
            "device_info": "DEBUG",
            "openid": "o0jd6wk8OK77nbVqPNLKG-2urQxQ",
            "trade_type": "JSAPI",
            "trade_state": "SUCCESS",
            "bank_type": "DEBUG",
            "total_fee": 1,
            "cash_fee": 1,
            "fee_type": "CNY",
            "transaction_id": transaction_id,
            "out_trade_no": uuid.uuid4(),
            "time_end": 23456,
            "result_code": "SUCCESS"
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
        return JsonResponse({'status': 200})
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
                print(goal_id,type(goal_id),"订单里面查出来的id")
                # 把支付的结果写入交易表中
                if not UserTrade.objects.exist_trade(res['transaction_id']):
                    UserTrade.objects.create_trade(goal_id=goal_id, trade_data=res)
                    # 当支付成功后,将attach中的goal取出来, 设其为活跃状态
                    from on.activities.base import Goal
                    sub_models = get_son_models(Goal)
                    for sub_model_key in sub_models:
                        sub_model = sub_models[sub_model_key]
                        goal = sub_model.objects.filter(user_id=user.user_id,goal_id=goal_id,status='PENDING')
                        # TODO
                        if goal:
                            goal = goal.first()
                            print("如果找到了用户该类型的goal，将其设置为活跃状态")
                            try:
                                print("将用户的状态设置为活跃")
                                sub_model.objects.filter(user_id=user.user_id, goal_id=goal_id, status='PENDING').update(status="ACTIVE")
                                print("设置成功")
                            except Exception as e:
                                print("状态修改失败",e)


                            # 更新用户的余额信息
                            print("更新用户的余额信息")
                            try:
                                user = UserInfo.objects.get(user_id=user.user_id)
                                user.balance -= decimal.Decimal((goal.deserve_price - goal.reality_price))
                                user.save()
                            except Exception as e:
                                print(e)


                            # # 更新用户的押金信息
                            deposit = goal.guaranty + goal.down_payment
                            UserInfo.objects.update_deposit(user_id=user.user_id,
                                                            pay_delta=decimal.Decimal(deposit))
                            print("更新跑步活动对应活动的奖金池与参与人数")
                            # 更新对应活动的奖金池与参与人数
                            if goal.activity_type == "1":
                                goal.update_activity(user_id=user.user_id)
                                activate = Activity.objects.get(activity_type=1)
                                activate.bonus_all += decimal.Decimal(10)
                                activate.save()

                                # 构造模板
                                openid = res["openid"]
                                goal_content = "恭喜你成功报名参加活动"
                                activate = "跑步活动"
                                # date_time = time.strftime('%Y年%m月%d日', time.localtime(time.time()))
                                start_time = timezone.now().strftime('%m月%d日')
                                end_time = (timezone.now() + timedelta(days=goal.goal_day)).strftime('%m月%d日')
                                date_time = "{}-{}(±1天)".format(start_time, end_time)
                                url = 'http://wechat.onmytarget.cn/'
                                data = send_tem(openid, url, goal_content, activate, date_time)
                                print("用户{}支付成功,当前用户id:{}".format(user.nickname, user.user_id))
                                print("开始发送模板")
                                do_push(data)
                            # 支付成功，删除用户未支付成的所有记录
                                try:
                                    failed = RunningGoal.objects.filter(user_id=user.user_id, status="PENDING")
                                    failed.delete()
                                except Exception as e:
                                    print(e,'删除记录未成功')


                                #发送模板

                            # 如果是阅读活动，则需要在支付完成后新建一个发货订单
                            print("开始创建订单")
                            if goal.activity_type == "2":
                                try:
                                    active = Activity.objects.get(activity_id='fac28454e818458f86639e7d40554597')
                                    active.active_participants +=1
                                    active.save()
                                    with connection.cursor() as cursor:
                                        resp = cursor.execute("""DELETE FROM on_readinggoal WHERE user_id=%s AND `status`='PENDING'""",[user.user_id])
                                except Exception as e:
                                    print("删除订单中的pending失败，{}".format(e))
                                print("支付成功，开始创建订单")
                                try:
                                    print(goal.goal_id,goal.goal_type,goal.price)
                                    read_goal = ReadingGoal.objects.get(goal_id=goal_id)
                                    UserOrder.objects.create_reading_goal_order(user_id=user.user_id,
                                                                                order_name=read_goal.book_name,
                                                                                order_money=read_goal.price,
                                                                                order_image=read_goal.imageurl,
                                                                                goal_id = read_goal.goal_id
                                                                                )
                                    print("订单创建成功")
                                except Exception as e:
                                    print(e,"订单未创建成功")



                            break
            except Exception as e:
                logger.error(e)
            return HttpResponse(xml_str)
