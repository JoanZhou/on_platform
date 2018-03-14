from django.contrib import admin
from django.conf.urls import url, include
from django.views.generic.base import RedirectView
from django.conf.urls import handler404, handler500
from on.timingtasks.calcbonus import test_calculate

from rest_framework.urlpatterns import format_suffix_patterns

from on import views as allview
from on import wechatviews, apiviews
from on.activities import views as activeview

urlpatterns = [
    url(r'^admin/', admin.site.urls),

    url(r'^favicon\.ico$', RedirectView.as_view(url='/static/images/favicon.ico')),
    url(r'^user/index', allview.show_user),
    url(r'^user/history', allview.show_history),
    url(r'^user/cash', allview.show_cash),
    url(r'^user/circle', allview.show_circle),
    url(r'^user/order', allview.show_order),

    url(r'^$', RedirectView.as_view(url='/activity/index')),
    url(r'^activity/index$', allview.show_activities, name='index'),
    url(r'^activity/(?P<pk>[0-9a-f-]+)$', allview.show_specific_activity, name='activity_detail'),

    url(r'^goal/index', activeview.show_goals),
    url(r'^goal/(?P<pk>[0-9a-f-]+)$', activeview.show_specific_goal),
    url(r'^goal/share/(?P<pk>[0-9a-f-]+)$', activeview.show_goal_share),

    url(r'^transfer$', wechatviews.transfer_to_person),
    url(r'^payback$', wechatviews.wechat_pay_back),
    url(r'^wechatpay$', wechatviews.wechat_pay),
    url(r'^wechat$', wechatviews.wechat_check),
    url(r'MP_verify_kJNErHZuAor4kA9O.txt', wechatviews.wechat_js_config),

    url(r'^api/update_address', allview.update_address),
    url(r'^api/running_sign_in', apiviews.running_sign_in_api),
    url(r'^api/running_no_sign_in', apiviews.running_no_sign_in_handler),
    url(r'^api/running_report', apiviews.running_report_handler),
    url(r'^api/running_praise', apiviews.running_praise_handler),

    url(r'^api/sleeping_sleep', apiviews.sleeping_sleep_handler),
    url(r'^api/sleeping_getup', apiviews.sleeping_getup_handler),
    url(r'^api/sleeping_confirm', apiviews.sleeping_confirm_handler),
    url(r'^api/sleeping_no_sign_in', apiviews.sleeping_no_sign_in_handler),
    url(r'^api/sleeping_delay', apiviews.sleeping_delay_handler),
    url(r'^api/create_goal', activeview.create_goal),
    url(r'^api/finish_goal', activeview.delete_goal),
    url(r'^api/start_reading', apiviews.reading_start_handler),
    url(r'^api/reading_sign_in', apiviews.reading_record_handler),
    url(r'api/search_deposit', apiviews.search_deposit),
    url(r'^test/profit', test_calculate)
]

urlpatterns = format_suffix_patterns(urlpatterns)

handler404 = "on.errorviews.page_not_found"

from on.timingtasks.calcbonus import calc_bonus_job
