from django.urls import path

from . import views

urlpatterns = [
    path("", views.index, name="index"),
    path("price-calculator/", views.calculator, name="calculator"),
    path("privacy/", views.privacy, name="privacy"),
    path("api/options/", views.api_options, name="api_options"),
    path("api/estimate/", views.api_estimate, name="api_estimate"),
    path("api/order/", views.api_order, name="api_order"),
    path("api/consultation/", views.api_consultation, name="api_consultation"),
]
