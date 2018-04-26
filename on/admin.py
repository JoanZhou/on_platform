from django.contrib import admin
from on.activities.reading.models import ReadingGoal,ReadingPunchRecord
from on.activities.running.models import RunningGoal,RunningPunchRecord,RunningPunchPraise,RunningPunchReport
from on.activities.sleeping.models import SleepingGoal,SleepingPunchRecord
from on.activities.base import Activity
from on.user import UserInfo,UserTrade,UserWithdraw,UserRefund,UserSettlement,UserRelation,UserRecord,UserTicket,UserTicketUseage,UserAddress,UserOrder

class ReadingGoalAdmin(admin.ModelAdmin):
    list_display = ('book_name','goal_page','finish_page','max_return','is_start','price','imageurl')

class RunningGoalAdmin(admin.ModelAdmin):
    list_display = ['goal_distance','kilos_day','left_distance','goal_id','user_id','activity_type','goal_type','start_time','goal_day','status','mode','guaranty','down_payment','coefficient','bonus','none_punch_days']
    list_per_page = 50
    ordering = ["-user_id"]

class UserInfoAdmin(admin.ModelAdmin):
    list_per_page = 20
    filter_vertical = ['user_id','sex','wechat_id']
    list_display = ['user_id','sex','wechat_id','nickname','deposit','points','balance',
                    'virtual_balance','all_profit','today_profit']


admin.site.register(ReadingGoal)
admin.site.register(ReadingPunchRecord)
admin.site.register(RunningGoal)
admin.site.register(RunningPunchRecord)
admin.site.register(RunningPunchPraise)
admin.site.register(RunningPunchReport)
admin.site.register(SleepingGoal)
admin.site.register(SleepingPunchRecord)
admin.site.register(Activity)
admin.site.register(UserInfo)
admin.site.register(UserTrade)
admin.site.register(UserWithdraw)
admin.site.register(UserRefund)
admin.site.register(UserSettlement)
admin.site.register(UserRelation)
admin.site.register(UserRecord)
admin.site.register(UserTicket)
admin.site.register(UserTicketUseage)
admin.site.register(UserAddress)
admin.site.register(UserOrder)
