from wechatpy import WeChatClient
from wechatpy.client.api.jsapi import WeChatJSAPI
from wechatpy.pay.api import WeChatJSAPI as PayJSAPI
from wechatpy.pay import WeChatPay
from wechatpy.pay.api import WeChatOrder
from wechatpy.oauth import WeChatOAuth
from wechatpy.client.api.media import WeChatMedia
from django.template import Template, Context
from wechatpy.utils import random_string, to_text
import time
import os
import requests
import json
from django.conf import settings

AppSecret = "23f0462bee8c56e09a2ac99321ed9952"
TOKEN = "TOKEN123456"
EncodingAESKey = "ZzmDNEMPfwJgGETNSKfIHfQiBmZHVLQa0DkOyledf35"
AppId = "wx4495e2082f63f8ac"
DOMAIN = "http://wechat.onmytarget.cn"
WechatJSConfig= '''
wx.config({
    debug: false,
    appId: \'wx4495e2082f63f8ac\',
    timestamp: {{timestamp}},
    nonceStr: \'{{nonceStr}}\',
    signature: \'{{signature}}\',
    jsApiList:[
    \'chooseImage\',
    \'previewImage\',
    \'uploadImage\',
    \'downloadImage\',
    \'onMenuShareTimeline\',
    \'chooseWXPay\',
    \'onMenuShareAppMessage\',
    \'checkJsApi\',
    \'translateVoice\',
    \'startRecord\',
    \'stopRecord\',
    \'onVoiceRecordEnd\',
    \'playVoice\',
    \'onVoicePlayEnd\',
    \'pauseVoice\',
    \'stopVoice\',
    \'uploadVoice\',
    \'downloadVoice\',
    \'getNetworkType\',
    \'openLocation\',
    \'getLocation\',
    \'hideOptionMenu\',
    \'showOptionMenu\',
    \'closeWindow\',
    \'hideMenuItems\',
    \'showMenuItems\',
    \'hideAllNonBaseMenuItem\',
    \'showAllNonBaseMenuItem\',
    ]
});
'''
ApiKey = "Kp1b4lH5z3n0DqGxu2IcQsV6F7PUWvmZ"
MchID = "1491203572"
NotifyUrl = "http://wechat.onmytarget.cn/payback"

client = WeChatClient(AppId, AppSecret)
jsApiClient = WeChatJSAPI(client=client)
mediaApiClient = WeChatMedia(client=client)
payClient = WeChatPay(appid=AppId,
                      api_key=ApiKey,
                      mch_id=MchID,
                      mch_cert=os.path.join(settings.BASE_DIR, 'carcert','apiclient_cert.pem'),
                      mch_key=os.path.join(settings.BASE_DIR,'carcert','apiclient_key.pem'))
oauthClient = WeChatOAuth(app_id=AppId,
                          secret=AppSecret,
                          redirect_uri=DOMAIN)


def get_wechat_config(request):
    """
    获取微信config字符串
    :param request:
    :return:
    """
    timestamp = to_text(int(time.time()))
    nonce_str = random_string(32)
    jsapi_ticket = jsApiClient.get_jsapi_ticket()
    url = DOMAIN + request.get_full_path()
    signature = jsApiClient.get_jsapi_signature(nonce_str,
                                                jsapi_ticket,
                                                timestamp,
                                                url)
    config_dict = Context({
        'timestamp':timestamp,
        'nonceStr':nonce_str,
        'signature':signature
    })

    template = Template(WechatJSConfig)
    wechat_config = template.render(config_dict)
    return wechat_config
