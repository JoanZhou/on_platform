a = {
    "touser": "",
    "template_id": "WlJal_LqCkIPcwId9cITDXw97c_V9AjF4cPRtZUPWTM",
    "url": "http://weixin.qq.com/download",
    "topcolor": "#FF0000",
    "data": {
        "first": {
            "value": "",
            "color": "#173177"
        },
        "keyword1": {
            "value": "",
            "color": "#173177"
        },
        "keyword2": {
            "value": "",
            "color": "#173177"
        },
        "remark": {
            "value": "",
            "color": "#173177"
        },
    }
}
b = {
    "touser": "",
    "template_id": "_rMUPRoWnRMxtYmFi3YQuOzpvv2gTBuFnkz7wZYYvyk",
    "url": "http://weixin.qq.com/download",
    "topcolor": "#FF0000",
    "data": {
        "first": {
            "value": "",
            "color": "#173177"
        },
        "keyword1": {
            "value": "",
            "color": "#173177"
        },
        "keyword2": {
            "value": "",
            "color": "#173177"
        },
        "keyword3": {
            "value": "",
            "color": "#173177"
        },
        "remark": {
            "value": "",
            "color": "#173177"
        },
    }
}
c = {
    "touser": "",
    "template_id": "2JVE73GD57B9vU3xYuVJ7fLucSMyaDrLWErO_Z7-pGQ-pGQ",
    "url": "http://weixin.qq.com/download",
    "topcolor": "#FF0000",
    "data": {
        "first": {
            "value": "",
            "color": "#173177"
        },
        "reason": {
            "value": "",
            "color": "#173177"
        },
        "keyword2": {
            "value": "",
            "color": "#173177"
        },
        "remark": {
            "value": "",
            "color": "#173177"
        },
    }
}
d = {
    "touser": "",
    "template_id": "ePs2EDcYNeyXxY0qLMjxP81m0bUA0KTiXL8byZ_hTk8",
    "url": "www.baidu.com",
    "topcolor": "#FF0000",
    "data": {
        "first": {
            "value": "",
            "color": "#173177"
        },
        "keyword1": {
            "value": "",
            "color": "#173177"
        },
        "keyword2": {
            "value": "",
            "color": "#173177"
        },
        "remark": {
            "value": "",
            "color": "#173177"
        },
    }
}
e = {
    "touser": "",
    "template_id": "rjH5YUcwwG-6k0RC7rRY-EzxRVUghHqm33BR_mH2GEk",
    "url": "http://weixin.qq.com/download",
    "topcolor": "#FF0000",
    "data": {
        "first": {
            "value": "",
            "color": "#173177"
        },
        "keyword1": {
            "value": "",
            "color": "#173177"
        },
        "keyword2": {
            "value": "",
            "color": "#173177"
        },
        "keyword3": {
            "value": "",
            "color": "#173177"
        },
        "keyword4": {
            "value": "",
            "color": "#173177"
        },
        "remark": {
            "value": "",
            "color": "#173177"
        },
    }
}
f = {
    "touser": "",
    "template_id": "wdUh6xWWGPbheCTd6mX1S-kGY38iK3DuQsSDhgt6dH8",
    "url": "http://weixin.qq.com/download",
    "topcolor": "#FF0000",
    "data": {
        "first": {
            "value": "",
            "color": "#173177"
        },
        "keyword1": {
            "value": "",
            "color": "#173177"
        },
        "keyword2": {
            "value": "",
            "color": "#173177"
        },
        "keyword3": {
            "value": "",
            "color": "#173177"
        },
        "remark": {
            "value": "",
            "color": "#173177"
        },
    }
}
def template():
    map = {
        # 生成目标的模板
        "create_goal": a,
        # #提现申请通知模板
        "withdraw": b,
        # 退款通知模板
        "Refund": c,
        # 打卡成功提醒模板
        "punch_success": d,
        # 订单完成提醒模板
        "complete_order": e,
        # 审核失败模板
        "audit_failure": f

    }
    return map

