from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from userauths import views as userauths_views
from store import views as store_views
from customer import views as customer_views
from vendor import views as vendor_views


urlpatterns = [
    path('user/token/', userauths_views.MyTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('user/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('user/register/', userauths_views.RegisterView.as_view(), name='auth_register'),
    path('user/password-reset/<email>', userauths_views.PasswordResetEmailVerify.as_view(), name='user_profile'),
    path('user/password-change/', userauths_views.PasswordChangeView.as_view(), name='password_change'),
    path('user/profile/<user_id>/', userauths_views.ProfileView.as_view(), name='profile-view'),

    # Store Endpoints
    path('category/', store_views.CategoryListAPIView.as_view()),
    path('products/', store_views.ProductListAPIView.as_view()),
    path('products/<slug>/', store_views.ProductDetailAPIView.as_view()),
    
    path('cart-view/', store_views.CartAPIView.as_view()), #to add items into the cart
    #Separate to two different urls
    path('cart-list/<str:cart_id>/<int:user_id>/', store_views.CartListView.as_view()),
    path('cart-list/<str:cart_id>/', store_views.CartListView.as_view()),
    #cart detail
    path('cart-detail/<str:cart_id>/', store_views.CartDetailView.as_view()),
    path('cart-detail/<str:cart_id>/<int:user_id>/', store_views.CartDetailView.as_view()),
    #Delete cart
    path('cart-delete/<str:cart_id>/<int:item_id>/<int:user_id>/', store_views.CartItemDeleteAPIView.as_view()),
    path('cart-delete/<str:cart_id>/<int:item_id>/', store_views.CartItemDeleteAPIView.as_view()),
    path('create-order/', store_views.CreateOrderAPIView.as_view()),
    path('checkout/<str:order_oid>/', store_views.CheckoutView.as_view()),
    path('coupon/', store_views.CouponAPIView.as_view()),
    path('reviews/<int:product_id>/', store_views.ReviewListAPIView.as_view()),
    path('search/', store_views.SearchProductAPIView.as_view()),



    # Payment Endpoints
    path('stripe-checkout/<str:order_oid>/', store_views.StripeCheckoutView.as_view(), name='stripe-checkout'),
    path('payment-success/', store_views.PaymentSuccessView.as_view(), name='payment-success'),
    path('payment-success/<str:order_oid>/', store_views.PaymentSuccessView.as_view(), name='payment-success-order'),
    path('webhooks/paypal/', store_views.PayPalWebhookView.as_view(), name='paypal-webhook'),

    # Customer EndPoints
    path('customer/orders/<int:user_id>/', customer_views.OrderAPIView.as_view(), name='customer-orders'),
    path('customer/order/<int:user_id>/<str:order_oid>/', customer_views.OrderDetailAPIView.as_view(), name='customer-order-detail'),
    path('customer/wishlist/<int:user_id>/', customer_views.WishlistAPIView.as_view(), name='customer-wishlist'),
    path('customer/wishlist/<int:user_id>/<int:wishlist_id>/', customer_views.WishlistDetailAPIView.as_view(), name='customer-wishlist-detail'),
    path('customer/notification/<int:user_id>/', customer_views.CustomerNotification.as_view(), name='customer-notification'),
    path('customer/notification/<int:user_id>/<int:noti_id>/', customer_views.MarkCustomerNotificationAsSeen.as_view(), name='customer-mark-notification'),
    path('products/category/<slug:slug>/', store_views.ProductByCategoryAPIView.as_view(), name='products-by-category'),
    path('customer/invoice/<int:user_id>/<str:order_oid>/', customer_views.InvoiceAPIView.as_view(), name='customer-invoice-detail'),
    # Vendor Dashboard
    path('vendor-register/', vendor_views.VendorRegister.as_view(), name='vendor-register'),
    path('vendor/stats/<vendor_id>/', vendor_views.DashboardStatsAPIView.as_view()),
    path('vendor-orders-chart/<vendor_id>/', vendor_views.MonthlyOrderChartAPIView),
    path('vendor-product-chart/<vendor_id>/', vendor_views.MonthlyProductChartAPIView),
    path('vendor/products/<vendor_id>/', vendor_views.ProductAPIView.as_view()),
    path('vendor/orders/<int:vendor_id>/', vendor_views.OrderAPIView.as_view()),
    path('vendor/orders/<vendor_id>/<order_oid>/', vendor_views.OrderDetailAPIView.as_view()),
    path('vendor/orders/<str:order_oid>/item/<int:order_item_id>/tracking/', vendor_views.OrderItemTrackingView.as_view(), name='order_item_tracking'),
    path('vendor/orders/filter/<vendor_id>', vendor_views.FilterOrderAPIView.as_view()),
    path('vendor/revenue/<vendor_id>/', vendor_views.RevenueAPIView.as_view()),
    path('vendor-product-filter/<vendor_id>/', vendor_views.FilterProductAPIView.as_view()),
    path('vendor-earning/<vendor_id>/', vendor_views.EarningAPIView.as_view()),
    path('vendor-monthly-earning/<vendor_id>/', vendor_views.MonthlyEarningTracker),
    path('vendor-reviews/<vendor_id>/', vendor_views.ReviewListAPIView.as_view()),
    path('vendor-reviews/<vendor_id>/<review_id>/', vendor_views.ReviewDetailAPIView.as_view()),
    path('vendor-coupon-list/<vendor_id>/', vendor_views.CouponListAPIView.as_view()),
    path('vendor-coupon-detail/<vendor_id>/<coupon_id>/', vendor_views.CouponDetailAPIView.as_view()),
    path('vendor-coupon-stats/<vendor_id>/', vendor_views.CouponStatsAPIView.as_view()),
    path('vendor-coupon-create/<vendor_id>/', vendor_views.CouponCreateAPIView.as_view()),
    path('vendor-noti-list/<vendor_id>/', vendor_views.NotificationAPIView.as_view()),

    path('vendor-noti-summary/<vendor_id>/', vendor_views.NotificationSummaryAPIView.as_view()),
    path('vendor-noti-mark-as-seen/<vendor_id>/<noti_id>/', vendor_views.NotificationVendorMarkAsSeen.as_view()),
    path('vendor-settings/<int:pk>/', vendor_views.VendorProfileUpdate.as_view()),
    path('vendor-shop-settings/<int:pk>/', vendor_views.ShopUpdateView.as_view()),
    path('shop/<vendor_slug>/', vendor_views.ShopAPIView.as_view()),
    path('vendor-products/<vendor_slug>/', vendor_views.ShopProductAPIView.as_view()),
    path('vendor-product-create/<vendor_id>/', vendor_views.ProductCreateView.as_view(), name='vendor-product-create'),
    path('vendor-product-update/<vendor_id>/<product_pid>/', vendor_views.ProductUpdateView.as_view(), name='vendor-product-update'),
    path('vendor-delete-product/<vendor_id>/<product_pid>/', vendor_views.ProductDeleteAPIView.as_view(), name='vendor-product-delete'),








]