from django.contrib.auth import views as auth_views
from django.urls import path, reverse_lazy

from . import views

app_name = 'accounts'

urlpatterns = [
    path('login/', views.AuthView.as_view(), name='login'),
    path('logout/', views.LogoutView.as_view(), name='logout'),

    # Password reset flow
    path('password-reset/', auth_views.PasswordResetView.as_view(
        template_name='accounts/password_reset.html',
        email_template_name='accounts/password_reset_email.html',
        html_email_template_name='accounts/password_reset_email.html',
        subject_template_name='accounts/password_reset_subject.txt',
        success_url=reverse_lazy('accounts:password_reset_done'),
    ), name='password_reset'),
    path('password-reset/done/', auth_views.PasswordResetDoneView.as_view(
        template_name='accounts/password_reset_done.html',
    ), name='password_reset_done'),
    path('password-reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(
        template_name='accounts/password_reset_confirm.html',
        success_url=reverse_lazy('accounts:password_reset_complete'),
    ), name='password_reset_confirm'),
    path('password-reset/complete/', auth_views.PasswordResetCompleteView.as_view(
        template_name='accounts/password_reset_complete.html',
    ), name='password_reset_complete'),

    # Profile dashboard + sections
    path('profile/', views.ProfileView.as_view(), name='profile'),
    path('profile/orders/', views.OrdersView.as_view(), name='orders'),
    path('profile/reviews/', views.ReviewsView.as_view(), name='reviews'),
    path('profile/account/', views.AccountEditView.as_view(), name='account'),

    # Addresses
    path('profile/addresses/', views.AddressListView.as_view(), name='addresses'),
    path('profile/addresses/add/', views.AddressCreateView.as_view(), name='address_add'),
    path('profile/addresses/<int:pk>/edit/', views.AddressUpdateView.as_view(), name='address_edit'),
    path('profile/addresses/<int:pk>/delete/', views.AddressDeleteView.as_view(), name='address_delete'),
]
