from django.urls import path

from . import views

app_name = 'shop'

urlpatterns = [
    path('', views.HomeView.as_view(), name='home'),
    path('products/', views.ProductListView.as_view(), name='product_list'),
    path('about/', views.AboutView.as_view(), name='about'),
    path('contact/', views.ContactView.as_view(), name='contact'),
    path('how-to-order/', views.HowToOrderView.as_view(), name='how_to_order'),
    path('shipping/', views.ShippingPolicyView.as_view(), name='shipping'),
    path('payment-methods/', views.PaymentMethodsView.as_view(), name='payment_methods'),
    path('category/<str:slug>/', views.CategoryView.as_view(), name='category'),
    path('product/<str:slug>/', views.ProductDetailView.as_view(), name='product_detail'),
    path('product/<str:slug>/review/', views.ReviewCreateView.as_view(), name='add_review'),
]
