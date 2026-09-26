from django.urls import path

from . import views

app_name = 'orders'

urlpatterns = [
    path('cart/', views.CartView.as_view(), name='cart'),
    path('cart/add/<int:pk>/', views.CartAddView.as_view(), name='cart_add'),
    path('cart/update/<int:pk>/', views.CartUpdateView.as_view(), name='cart_update'),
    path('cart/remove/<int:pk>/', views.CartRemoveView.as_view(), name='cart_remove'),
    path('coupon/apply/', views.CouponApplyView.as_view(), name='coupon_apply'),
    path('coupon/remove/', views.CouponRemoveView.as_view(), name='coupon_remove'),
    path('checkout/', views.CheckoutView.as_view(), name='checkout'),
    path('order/<int:pk>/', views.OrderDetailView.as_view(), name='order_detail'),
    path('order/<int:pk>/pay/', views.PaymentStartView.as_view(), name='payment_start'),
    path('order/<int:pk>/verify/', views.PaymentVerifyView.as_view(), name='payment_verify'),
]
