from django.conf.urls import url

from . import views

urlpatterns = [
    # 购物车路由
    url(r'^carts/$', views.CartView.as_view()),

    # 购物车路由
    url(r'^carts/selection/$', views.CartSelectedView.as_view()),

]