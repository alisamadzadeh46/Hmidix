"""URL configuration for the Hamidix project."""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

admin.site.site_header = 'مدیریت فروشگاه Hamidix'
admin.site.site_title = 'پنل مدیریت Hamidix'
admin.site.index_title = 'پنل مدیریت'

urlpatterns = [
    path('hx-secure-9f3k/admin/', admin.site.urls),
    path('auth/', include('accounts.urls')),
    path('', include('orders.urls')),
    path('', include('shop.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
