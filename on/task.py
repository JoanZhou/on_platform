#coding=utf-8
from __future__ import absolute_import
from celery import shared_task
import time
import json
import requests
import os
from selenium import webdriver
import random
from django.conf import settings
import datetime





chrome_options = webdriver.ChromeOptions()
chrome_options.add_argument('--headless')

WECHAT_APPID = "wx4495e2082f63f8ac"
WECHAT_APPSECRET = "23f0462bee8c56e09a2ac99321ed9952"

def getToken():
    print('开始获取新的access_token')
    # 获取用户的accesstoken
    url = 'https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid=' + WECHAT_APPID + "&secret=" + WECHAT_APPSECRET
    token_str = requests.post(url).content.decode()
    token_json = json.loads(token_str)
    token = token_json['access_token']
    return token



@shared_task
def send_img(user_id,random,openid,activity_type):
    try:
        token = getToken()

        time_now = datetime.datetime.now().strftime("%Y-%m-%d")
        print("开始截图")
        browser = webdriver.Chrome(chrome_options=chrome_options)
        browser.set_window_size(385*2, 680*2)
        browser.get(
            "http://wechat.onmytarget.cn/user/user_screenshot?user_id={}&img_random={}&activity_type={}".format(user_id,random,activity_type))

        img_name = "{}_{}.png".format(user_id,  random)
        screen_path = os.path.join("./screenshot/", str(user_id) + "/", "{}".format(time_now) + "/")
        print(screen_path, "保存的路径")
        if not os.path.exists(screen_path):
            os.makedirs(screen_path)
        # 将截取的图片保存到截图文件夹中
        browser.save_screenshot(screen_path + img_name)
        full_path = screen_path + img_name
        print("保存成功")
        url = "https://api.weixin.qq.com/cgi-bin/media/upload?access_token={}&type={}".format(token, "image")
        file = {"file": open(full_path, "rb")}
        date = requests.post(url, files=file)
        resp_json = json.loads(date.content.decode())
        print(resp_json, "发送图片的返回值")
        media_id = resp_json["media_id"]
        print(media_id)
        kefu = "https://api.weixin.qq.com/cgi-bin/message/custom/send?access_token={}".format(token)
        data_str = {
            "touser": "{}".format(openid),
            "msgtype": "image",
            "image":
                {
                    "media_id": "{}".format(media_id)
                }
        }
        data = json.dumps(data_str)
        response = requests.post(kefu, data)
        print("发送成功")
        print(response.content.decode())
    except Exception as e:
        print(e)


@shared_task
def send_img_test():
    print("进入测试")
    try:
        token = getToken()
        print("开始截图")
        browser = webdriver.Chrome(chrome_options=chrome_options)
        browser.set_window_size(385*2, 700*2)
        # browser.viewportSize = {'width': 1920, 'height': 1080}
        browser.get(
            "http://wechat.onmytarget.cn/user/user_screenshot?user_id={}&img_random={}".format(100274, 6))

        img_name = "{}_{}_{}.png".format(100274, "555", 6)
        screen_path = os.path.join("./screenshot/", str(100274) + "/", "555" + "/")
        print(screen_path, "保存的路径")
        if not os.path.exists(screen_path):
            os.makedirs(screen_path)
        # 将截取的图片保存到截图文件夹中
        browser.save_screenshot(screen_path + img_name)
        full_path = screen_path + img_name
        print("保存成功")
        url = "https://api.weixin.qq.com/cgi-bin/media/upload?access_token={}&type={}".format(token, "image")
        file = {"file": open(full_path, "rb")}
        date = requests.post(url, files=file)
        resp_json = json.loads(date.content.decode())
        print(resp_json, "发送图片的返回值")
        media_id = resp_json["media_id"]
        print(media_id)
        kefu = "https://api.weixin.qq.com/cgi-bin/message/custom/send?access_token={}".format(token)
        data_str = {
            "touser": "o0jd6wgPxXAFK9aifqR858FOWDV0",
            "msgtype": "image",
            "image":
                {
                    "media_id": "{}".format(media_id)
                }
        }
        data = json.dumps(data_str)
        response = requests.post(kefu, data)
        print("发送成功")
        print(response.content.decode())
    except Exception as e:
        print(e)