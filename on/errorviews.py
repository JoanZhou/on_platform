from django.shortcuts import render


# 找不到页面
def page_not_found(request):
    return render(request, '404.html')