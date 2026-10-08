from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import RedirectView, TemplateView
urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('quiz.urls', namespace='quiz')), 
    path('impressum/', TemplateView.as_view(template_name='impressum.html'), name='impressum'),
    path('datenschutz/', TemplateView.as_view(template_name='datenschutz.html'), name='datenschutz'),
]
