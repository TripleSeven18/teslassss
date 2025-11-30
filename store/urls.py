from django.urls import path
from django.contrib.auth import views as auth_views

from store.forms import (
    LoginForm,
    PasswordChangeForm,
    PasswordResetForm,
    SetPasswordForm
)
from . import views


app_name = 'store'


urlpatterns = [

    # -----------------------------------
    # HOME
    # -----------------------------------
    path('', views.home, name="home"),


    # -----------------------------------
    # CART + CHECKOUT + ORDERS
    # -----------------------------------
    path('add-to-cart/', views.add_to_cart, name="add-to-cart"),
    path('remove-cart/<int:cart_id>/', views.remove_cart, name="remove-cart"),
    path('plus-cart/<int:cart_id>/', views.plus_cart, name="plus-cart"),
    path('minus-cart/<int:cart_id>/', views.minus_cart, name="minus-cart"),

    path('cart/', views.cart, name="cart"),
    path('checkout/', views.checkout, name="checkout"),
    path('orders/', views.orders, name="orders"),
    path('mpesa/', views.mpesa_payment, name="mpesa_payment"),


    # -----------------------------------
    # PRODUCT + CATEGORY VIEWS
    # -----------------------------------
    path('product/<slug:slug>/', views.detail, name="product-detail"),
    path('categories/', views.all_categories, name="all-categories"),
    path('<slug:slug>/', views.category_products, name="category-products"),

    path('shop/', views.shop, name="shop"),


    # -----------------------------------
    # NEWSLETTER
    # -----------------------------------
    path('subscribe-newsletter/', views.subscribe_newsletter, name='subscribe-newsletter'),


    # -----------------------------------
    # AUTHENTICATION + USER PROFILE
    # -----------------------------------
    path(
        'accounts/register/',
        views.RegistrationView.as_view(),
        name="register"
    ),

    path(
        'accounts/login/',
        auth_views.LoginView.as_view(
            template_name='account/login.html',
            authentication_form=LoginForm
        ),
        name="login"
    ),

    path('accounts/profile/', views.profile, name="profile"),

    path(
        'accounts/add-address/',
        views.AddressView.as_view(),
        name="add-address"
    ),

    path(
        'accounts/remove-address/<int:id>/',
        views.remove_address,
        name="remove-address"
    ),

    path(
        'accounts/logout/',
        auth_views.LogoutView.as_view(next_page='store:login'),
        name="logout"
    ),


    # -----------------------------------
    # PASSWORD MANAGEMENT
    # -----------------------------------
    path(
        'accounts/password-change/',
        auth_views.PasswordChangeView.as_view(
            template_name='account/password_change.html',
            form_class=PasswordChangeForm,
            success_url='/accounts/password-change-done/'
        ),
        name="password-change"
    ),

    path(
        'accounts/password-change-done/',
        auth_views.PasswordChangeDoneView.as_view(
            template_name='account/password_change_done.html'
        ),
        name="password-change-done"
    ),

    path(
        'accounts/password-reset/',
        auth_views.PasswordResetView.as_view(
            template_name='account/password_reset.html',
            form_class=PasswordResetForm,
            success_url='/accounts/password-reset/done/'
        ),
        name="password-reset"
    ),

    path(
        'accounts/password-reset/done/',
        auth_views.PasswordResetDoneView.as_view(
            template_name='account/password_reset_done.html'
        ),
        name="password_reset_done"
    ),

    path(
        'accounts/password-reset-confirm/<uidb64>/<token>/',
        auth_views.PasswordResetConfirmView.as_view(
            template_name='account/password_reset_confirm.html',
            form_class=SetPasswordForm,
            success_url='/accounts/password-reset-complete/'
        ),
        name="password_reset_confirm"
    ),

    path(
        'accounts/password-reset-complete/',
        auth_views.PasswordResetCompleteView.as_view(
            template_name='account/password_reset_complete.html'
        ),
        name="password_reset_complete"
    ),


    # -----------------------------------
    # EXTRA / TEST PAGE
    # -----------------------------------
    path('product/test/', views.test, name="test"),

]
