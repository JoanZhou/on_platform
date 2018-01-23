#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Script to create On! test users
#

import django
import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "on.settings.local")
django.setup()

from on.user import UserInfo

profiles = [
    {
        'wechat_id': 'Lq372899855',
        'nickname': 'test',
        'sex': 2,
        'headimgurl': 'http://wx.qlogo.cn/mmopen/g3MonUZtNHkdmzicIlibx6iaFqAc56vxLSUfpb6n5WKSYVY0ChQKkiaJSgQ1dZuTOgvLLrhJbERQQ4eMsv84eavHiaiceqxibJxCfHe/0',
        'deposit': 0,
        'points': 0,
        'balance': 0,
        'virtual_balance': 0
    }]


if __name__ == '__main__':
    for profile_data in profiles:
        print('Cresting user - %s' % profile_data['wechat_id'])
        # Check if user already exists

        userinfo = UserInfo(**profile_data)
        userinfo.save()

