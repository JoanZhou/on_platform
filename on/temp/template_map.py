a = {
    "touser": "",
    "template_id": "U4UwUUHXqj2EsM3L2x4cOBsLDbQNxZi8OXJdBtd_q2w",
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
    "template_id": "Pd6cbEhAgyaDH3yAJOtiyIpjSLnaw7g04Q14dhsbw7w",
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
    "template_id": "CB9aLimSfCXD_ErWqN6mqjKkoL37WGOJ9y9WEo8Ykp8",
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

