from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('products/', views.product_list, name='product_list'),
    path('product/<slug:slug>/', views.product_detail, name='product_detail'),

    # Live Search & Pincode JSON APIs
    path('api/search-suggest/', views.search_suggest, name='search_suggest'),
    path('api/check-pincode/', views.check_pincode, name='check_pincode'),

    # Cart & Coupons
    path('cart/', views.cart_view, name='cart'),
    path('cart/add/<int:product_id>/', views.cart_add, name='cart_add'),
    path('cart/update/<str:item_id>/', views.cart_update, name='cart_update'),
    path('cart/coupon/', views.cart_coupon, name='cart_coupon'),

    # Wishlist & Compare
    path('wishlist/', views.wishlist_view, name='wishlist'),
    path('wishlist/toggle/<int:product_id>/', views.wishlist_toggle, name='wishlist_toggle'),
    path('compare/', views.compare_view, name='compare'),
    path('compare/toggle/<int:product_id>/', views.compare_toggle, name='compare_toggle'),
    path('compare/clear/', views.compare_clear, name='compare_clear'),

    # Checkout & Orders
    path('checkout/', views.checkout_view, name='checkout'),
    path('orders/', views.orders_view, name='orders'),
    path('orders/<str:order_number>/', views.order_detail, name='order_detail'),
    path('orders/<str:order_number>/invoice/', views.order_invoice, name='order_invoice'),

    # Auth & Account
    path('login/', views.login_view, name='login'),
    path('signup/', views.signup_view, name='signup'),
    path('logout/', views.logout_view, name='logout'),
    path('account/', views.account_view, name='account'),

    # Flipkart Signature Zones
    path('supercoins/', views.supercoins_view, name='supercoins'),
    path('plus/', views.plus_view, name='plus'),
    path('seller/', views.seller_view, name='seller'),
    path('support/', views.support_view, name='support'),
    path('notifications/', views.notifications_view, name='notifications'),
]
