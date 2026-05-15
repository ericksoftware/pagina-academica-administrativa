from django.urls import path

from . import views

urlpatterns = [
    path('', views.administration_home, name='administration_home'),
]