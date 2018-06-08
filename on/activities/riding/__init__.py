from django.db import models
import uuid
from django.http import JsonResponse
from on.activities.base import Goal, Activity
from on.user import UserInfo, UserTicket, UserRecord, UserSettlement
import django.utils.timezone as timezone
from django.conf import settings
import os
import pytz
import math
from datetime import timedelta, datetime