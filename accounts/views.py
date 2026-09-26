from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import (
    CreateView,
    DeleteView,
    FormView,
    ListView,
    TemplateView,
    UpdateView,
)

from core.http import safe_redirect_url

from .forms import AddressForm, LoginForm, ProfileForm, RegisterForm


class AuthView(FormView):
    """Combined login / register page (two tabs in one template)."""

    template_name = 'accounts/auth.html'
    form_class = LoginForm
    success_url = reverse_lazy('shop:home')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.setdefault('login_form', kwargs.get('form', LoginForm()))
        ctx.setdefault('register_form', RegisterForm())
        ctx.setdefault('active_tab', 'login')
        return ctx

    def post(self, request, *args, **kwargs):
        if request.POST.get('action') == 'register':
            return self._handle_register(request)
        return self._handle_login(request)

    def _handle_login(self, request):
        form = LoginForm(request.POST)
        if form.is_valid():
            user = authenticate(
                request,
                phone=form.cleaned_data['phone'],
                password=form.cleaned_data['password'],
            )
            if user is not None:
                login(request, user)
                messages.success(request, f'خوش آمدید {user.get_short_name()}')
                return self._redirect_after_login(request)
            form.add_error(None, 'شماره تلفن یا رمز عبور اشتباه است.')
        return self.render_to_response(
            self.get_context_data(login_form=form, active_tab='login')
        )

    def _handle_register(self, request):
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user, backend='accounts.backends.PhoneBackend')
            messages.success(request, 'ثبت‌نام با موفقیت انجام شد.')
            return self._redirect_after_login(request)
        return self.render_to_response(
            self.get_context_data(register_form=form, active_tab='register')
        )

    def _redirect_after_login(self, request):
        nxt = request.POST.get('next') or request.GET.get('next')
        return redirect(safe_redirect_url(request, nxt, self.success_url))


class LogoutView(View):
    """Log the user out and send them to the home page.

    Accepts POST only, so a third-party page cannot log users out with a
    simple link or image (logout CSRF). Templates render it as a small form.
    """

    http_method_names = ['post']

    def post(self, request, *args, **kwargs):
        logout(request)
        messages.info(request, 'از حساب خود خارج شدید.')
        return redirect('shop:home')


class ProfileView(LoginRequiredMixin, TemplateView):
    """Dashboard: summary of recent orders, address & review counts."""

    template_name = 'accounts/profile/dashboard.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        user = self.request.user
        orders = user.orders.all()
        ctx['recent_orders'] = orders[:5]
        ctx['order_count'] = orders.count()
        ctx['address_count'] = user.addresses.count()
        ctx['review_count'] = user.reviews.count()
        return ctx


class OrdersView(LoginRequiredMixin, ListView):
    """Paginated order history of the current user."""

    template_name = 'accounts/profile/orders.html'
    context_object_name = 'orders'
    paginate_by = 10

    def get_queryset(self):
        return self.request.user.orders.all()


class UserAddressMixin(LoginRequiredMixin):
    """Scope address views to the addresses of the logged-in user."""

    success_url = reverse_lazy('accounts:addresses')

    def get_queryset(self):
        return self.request.user.addresses.all()


class AddressListView(UserAddressMixin, ListView):
    """Saved addresses of the current user."""

    template_name = 'accounts/profile/addresses.html'
    context_object_name = 'addresses'


class AddressCreateView(UserAddressMixin, CreateView):
    form_class = AddressForm
    template_name = 'accounts/profile/address_form.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['next'] = self.request.GET.get('next', '')
        return ctx

    def form_valid(self, form):
        form.instance.user = self.request.user
        messages.success(self.request, 'آدرس جدید ثبت شد.')
        return super().form_valid(form)

    def get_success_url(self):
        # Checkout links here with ?next= so the user returns after adding one.
        nxt = self.request.POST.get('next', '').strip()
        return safe_redirect_url(self.request, nxt, self.success_url)


class AddressUpdateView(UserAddressMixin, UpdateView):
    form_class = AddressForm
    template_name = 'accounts/profile/address_form.html'

    def form_valid(self, form):
        messages.success(self.request, 'آدرس ویرایش شد.')
        return super().form_valid(form)


class AddressDeleteView(UserAddressMixin, DeleteView):
    template_name = 'accounts/profile/address_confirm_delete.html'

    def form_valid(self, form):
        messages.info(self.request, 'آدرس حذف شد.')
        return super().form_valid(form)


class ReviewsView(LoginRequiredMixin, ListView):
    """Reviews written by the current user."""

    template_name = 'accounts/profile/reviews.html'
    context_object_name = 'reviews'
    paginate_by = 10

    def get_queryset(self):
        return self.request.user.reviews.select_related('product').all()


class AccountEditView(LoginRequiredMixin, UpdateView):
    """Edit the current user's own profile details."""

    form_class = ProfileForm
    template_name = 'accounts/profile/account.html'
    success_url = reverse_lazy('accounts:account')

    def get_object(self, queryset=None):
        return self.request.user

    def form_valid(self, form):
        messages.success(self.request, 'اطلاعات حساب به‌روزرسانی شد.')
        return super().form_valid(form)
