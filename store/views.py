from asyncio import TimeoutError

from django.http import Http404
import requests
from django.shortcuts import get_object_or_404, render, redirect
from django.conf import settings
from store.models import Category, ConfigSettings, Tax, Product, Gallery, Specification, Size, Color, Cart, CartOrder, CartOrderItem, ProductFaq, Review, Wishlist, Notification, Coupon
from store.serializers import CheckoutOrderSerializer, CouponSerializer, FilterProductByCategorySerializer, ProductSerializer, CategorySerializer, ReviewSerializer, CartSerializer, CartOrderSerializer, CartOrderItemSerializer, NotificationSerializer, SimpleProductSerializer
from userauths.models import User
from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from decimal import Decimal, InvalidOperation
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
import stripe
from requests.auth import HTTPBasicAuth
from rest_framework.parsers import JSONParser
from django.http import JsonResponse
from django.views import View
import json
import logging
import paypalrestsdk
from paypalrestsdk.notifications import WebhookEvent
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
import hashlib
import base64
from OpenSSL import crypto
import hmac
import binascii
from zlib import crc32
from rest_framework.views import APIView

stripe.api_key = settings.STRIPE_SECRET_KEY
PAYPAL_CLIENT_ID = settings.PAYPAL_CLIENT_ID
NEW_PAYPAL_SECRET_ID = settings.NEW_PAYPAL_SECRET_ID

logger = logging.getLogger(__name__)

def send_notification(user=None, vendor=None, order=None, order_item=None):
    Notification.objects.create(
        user=user,
        vendor=vendor,
        order=order,
        order_item=order_item
    )

class CategoryListAPIView(generics.ListAPIView):
    serializer_class = CategorySerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        return Category.objects.all().order_by('title')

class ProductPagination(PageNumberPagination):
    page_size = 10  # Number of products per page
    page_size_query_param = 'page_size'
    max_page_size = 100

class ProductListAPIView(generics.ListAPIView):
    serializer_class = SimpleProductSerializer
    pagination_class = ProductPagination
    permission_classes = [AllowAny]

    def get_queryset(self):
        return Product.objects.filter(status='published').select_related('category', 'vendor').order_by('-id')
    

class ProductDetailAPIView(generics.RetrieveAPIView):
    serializer_class = ProductSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        return Product.objects.prefetch_related(
            'gallery_set', 'color_set', 'specification_set', 'size_set'
        ).select_related('category', 'vendor')

    def get_object(self):
        queryset = self.get_queryset()
        slug = self.kwargs['slug']
        return get_object_or_404(queryset, slug=slug)
    
class ProductByCategoryAPIView(generics.ListAPIView):
    serializer_class = FilterProductByCategorySerializer

    def get_queryset(self):
        slug = self.kwargs['slug']
        category = get_object_or_404(Category, slug=slug)
        return Product.objects.filter(category=category).order_by('-id') 

class CartAPIView(generics.ListCreateAPIView):
    queryset = Cart.objects.all()
    serializer_class = CartSerializer
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        payload = request.data
        product_id = payload['product_id']
        user_id = payload.get('user_id')  # Use get to avoid KeyError
        qty = payload['qty']
        price = payload['price']
        shipping_amount = payload['shipping_amount']
        country = payload['country']
        size = payload['size']
        color = payload['color']
        cart_id = payload['cart_id']
        product = Product.objects.get(id=product_id)

        user = None
        if user_id and user_id != "undefined" and user_id != "0":
            user = User.objects.get(id=user_id)

        tax = Tax.objects.filter(country=country).first()
        tax_rate = tax.rate / 100 if tax else 0

        config_settings = ConfigSettings.objects.first()
        service_fee_percentage = Decimal(config_settings.service_fee_percentage) / 100

        try:
            cart = Cart.objects.filter(cart_id=cart_id, product=product).first()

            if cart:
                cart.product = product
                cart.user = user
                cart.qty = qty
                cart.price = price
                cart.sub_total = Decimal(price) * int(qty)
                cart.shipping_amount = Decimal(shipping_amount) * int(qty)
                cart.tax_fee = cart.sub_total * Decimal(tax_rate)
                cart.color = color
                cart.size = size
                cart.country = country
                cart.cart_id = cart_id
                cart.service_fee = service_fee_percentage * cart.sub_total
                cart.total = cart.sub_total + cart.shipping_amount + cart.service_fee + cart.tax_fee
                cart.save()

                return Response({'message': "Cart Update Successfully"}, status=status.HTTP_200_OK)
            else:
                cart = Cart(
                    product=product,
                    user=user,
                    qty=qty,
                    price=price,
                    sub_total=Decimal(price) * int(qty),
                    shipping_amount=Decimal(shipping_amount) * int(qty),
                    tax_fee=Decimal(price) * int(qty) * Decimal(tax_rate),
                    color=color,
                    size=size,
                    country=country,
                    cart_id=cart_id,
                )

                cart.service_fee = service_fee_percentage * cart.sub_total
                cart.total = cart.sub_total + cart.shipping_amount + cart.service_fee + cart.tax_fee
                cart.save()

                return Response({'message': "Cart Create Successfully"}, status=status.HTTP_201_CREATED)
        except InvalidOperation:
            return Response({'error': "Invalid data for decimal conversion"}, status=status.HTTP_400_BAD_REQUEST)


class CartListView(generics.ListAPIView):
    serializer_class = CartSerializer
    permission_classes = [AllowAny]
    queryset = Cart.objects.all()

    def get_queryset(self):
        cart_id = self.kwargs['cart_id']
        user_id = self.kwargs.get('user_id')

        if user_id:
            user = User.objects.filter(id=user_id).first()  # Ensure only one user is returned
            queryset = Cart.objects.filter(user=user, cart_id=cart_id).order_by('-id')
        else:
            queryset = Cart.objects.filter(cart_id=cart_id).order_by('-id')

        return queryset  # Return all matching items
    
class CartDetailView(generics.RetrieveAPIView):
    serializer_class = CartSerializer
    permission_classes = [AllowAny]
    lookup_field = "cart_id"

    def get_queryset(self):
        cart_id = self.kwargs['cart_id']
        user_id = self.kwargs.get('user_id')

        if user_id:
            user = User.objects.filter(id=user_id).first()  # Ensure only one user is returned
            queryset = Cart.objects.filter(user=user, cart_id=cart_id)
        else:
            queryset = Cart.objects.filter(cart_id=cart_id)

        return queryset  # Return all matching items

    def get(self, request, *args, **kwargs):
        queryset = self.get_queryset()

        total_shipping = 0.0
        total_tax = 0.0
        total_service_fee = 0.0
        total_sub_total = 0.0
        total_total = 0.0

        for cart_item in queryset:
            total_shipping += float(self.calculate_shipping(cart_item))
            total_tax += float(self.calculate_tax(cart_item))
            total_service_fee += float(self.calculate_service_fee(cart_item))
            total_sub_total += float(self.calculate_sub_total(cart_item))
            total_total += float(self.calculate_total(cart_item))

        data = {
            'shipping': total_shipping,
            'tax': total_tax,
            'service_fee': total_service_fee,
            'sub_total': total_sub_total,
            'total': total_total,
        }

        return Response(data)

    def calculate_shipping(self, cart_item):
        return cart_item.shipping_amount
        
    def calculate_tax(self, cart_item):
        return cart_item.tax_fee
        
    def calculate_service_fee(self, cart_item):
        return cart_item.service_fee
        
    def calculate_sub_total(self, cart_item):
        return cart_item.sub_total
        
    def calculate_total(self, cart_item):
        return cart_item.total
    

class CartItemDeleteAPIView(generics.DestroyAPIView): 
    serializer_class = CartSerializer
    lookup_field = 'cart_id'

    def get_object(self):
        cart_id = self.kwargs['cart_id']
        item_id = self.kwargs['item_id']
        user_id = self.kwargs.get('user_id')

        try:
            if user_id:
                user = User.objects.get(id=user_id)
                cart = Cart.objects.get(id=item_id, cart_id=cart_id, user=user)
            else:
                cart = Cart.objects.get(id=item_id, cart_id=cart_id)
        except Cart.DoesNotExist:
            raise Http404("Cart matching query does not exist.")

        return cart
        
class CreateOrderAPIView(generics.CreateAPIView):
    serializer_class = CartOrderSerializer
    queryset = CartOrder.objects.all()
    permission_classes = [AllowAny]

    def create(self, request):
        payload = request.data  # get data from frontend

        full_name = payload['full_name']
        email = payload['email']
        mobile = payload['mobile']
        address = payload['address']
        city = payload['city']
        state = payload['state']
        country = payload['country']
        cart_id = payload['cart_id']
        user_id = payload.get('user_id')

        user = User.objects.filter(id=user_id).first() if user_id != 0 else None

        cart_items = Cart.objects.filter(cart_id=cart_id)

        total_shipping = Decimal(0.00)
        total_tax = Decimal(0.00)
        total_service_fee = Decimal(0.00)
        total_sub_total = Decimal(0.00)
        total_initial_total = Decimal(0.00)
        total_total = Decimal(0.00)

        order = CartOrder.objects.create(
            full_name=full_name,
            payment_status="processing",
            email=email,
            mobile=mobile,
            address=address,
            city=city,
            state=state,
            country=country,
            buyer=user,  # Assign buyer here
            
        )

        for c in cart_items:
            CartOrderItem.objects.create(
                order=order,
                product=c.product,
                vendor=c.product.vendor,
                qty=c.qty,
                color=c.color,
                size=c.size,
                price=c.price,
                sub_total=c.sub_total,
                shipping_amount=c.shipping_amount,
                service_fee=c.service_fee,
                tax_fee=c.tax_fee,
                total=c.total,
                initial_total=c.total,
            )

            total_shipping += Decimal(c.shipping_amount)
            total_tax += Decimal(c.tax_fee)
            total_service_fee += Decimal(c.service_fee)
            total_sub_total += Decimal(c.sub_total)
            total_initial_total += Decimal(c.total)
            total_total += Decimal(c.total)

            order.vendor.add(c.product.vendor)

        order.sub_total = total_sub_total
        order.shipping_amount = total_shipping
        order.tax_fee = total_tax
        order.service_fee = total_service_fee
        order.initial_total = total_initial_total
        order.total = total_total

        order.save()

        # Clear the cart
        cart_items.delete()

        return Response({"message": "Order Created Successfully", "order_oid": order.oid}, status=status.HTTP_201_CREATED)


    
class CheckoutView(generics.RetrieveAPIView):
    serializer_class = CheckoutOrderSerializer
    lookup_field = 'order_oid'  

    def get_object(self):
        order_oid = self.kwargs['order_oid']
        cart = get_object_or_404(CartOrder, oid=order_oid)
        return cart
    
    def get_serializer_context(self):
        context = super().get_serializer_context()
        context.update({"request": self.request})
        return context

class CouponAPIView(generics.CreateAPIView):
    serializer_class = CouponSerializer
    queryset = Coupon.objects.all()
    permission_classes = [AllowAny]

    def create(self, request):
        payload = request.data

        order_oid = payload['order_oid']
        coupon_code = payload['coupon_code']

        try:
            order = CartOrder.objects.get(oid=order_oid)
            coupon = Coupon.objects.filter(code=coupon_code).first()

            if coupon:
                order_items = CartOrderItem.objects.filter(order=order, vendor=coupon.vendor)
                if order_items.exists():
                    for i in order_items:
                        if not coupon in i.coupon.all(): # Check if the coupon is already applied
                            discount = i.total * coupon.discount / 100

                            i.total -= discount
                            i.sub_total -= discount
                            i.coupon.add(coupon)
                            i.saved += discount

                            order.total -= discount
                            order.sub_total -= discount
                            order.saved += discount

                            i.save()
                            order.save()

                            return Response({"message": "Coupon Activated", "icon":"success"}, status=status.HTTP_200_OK)
                        else:
                            return Response({"message": "Coupon Already Activated", "icon":"warning"}, status=status.HTTP_200_OK)
                else:
                    return Response({"message": "Order Item Does Not Exist", "icon":"error"}, status=status.HTTP_200_OK)
            else:
                return Response({"message": "Coupon Does Not Exist", "icon":"error"}, status=status.HTTP_200_OK)
        except CartOrder.DoesNotExist:
            return Response({"message": "Order Does Not Exist", "icon":"error"}, status=status.HTTP_404_NOT_FOUND)
        except Coupon.DoesNotExist:
            return Response({"message": "Coupon Does Not Exist", "icon":"error"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"message": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
class StripeCheckoutView(generics.CreateAPIView):
    serializer_class = CartOrderSerializer
    permission_classes = [AllowAny]
    queryset = CartOrder.objects.all()

    def post(self, request, *args, **kwargs):
        order_oid = self.kwargs['order_oid']
        try:
            order = CartOrder.objects.get(oid=order_oid)
        except CartOrder.DoesNotExist:
            return Response({"message": "Order Not Found"}, status=status.HTTP_404_NOT_FOUND)

        try:
            checkout_session = stripe.checkout.Session.create(
                customer_email=order.email,
                payment_method_types=['card'],
                line_items=[
                    {
                        'price_data': {
                            'currency': 'HKD',
                            'product_data': {
                                'name': f"Order {order.oid}"
                            },
                            'unit_amount': int(order.total * 100),  # Convert to cents
                        },
                        'quantity': 1,
                    }
                ],
                mode='payment',
                success_url=f'{settings.SITE_URL}/payment-success/{order.oid}/?session_id={{CHECKOUT_SESSION_ID}}',
                cancel_url=f'{settings.SITE_URL}/payment-failed/?session_id={{CHECKOUT_SESSION_ID}}'
            )

            order.stripe_session_id = checkout_session.id
            order.save()

            return redirect(checkout_session.url)
        except stripe.error.StripeError as e:
            return Response({"error": f"Something went wrong while creating the checkout session: {str(e)}"})
    
def get_access_token(client_id, secret_key):
    token_url = 'https://api.sandbox.paypal.com/v1/oauth2/token'
    headers = {'Content-Type': 'application/x-www-form-urlencoded'}
    data = {'grant_type': 'client_credentials'}
    response = requests.post(token_url, headers=headers, data=data, auth=HTTPBasicAuth(client_id, secret_key))
    if response.status_code == 200:
        return response.json()['access_token']
    else:
        raise Exception(f"Failed to get access token: {response.text}")
    
def verify_webhook_signature(headers, body):
    url = 'https://api.sandbox.paypal.com/v1/notifications/verify-webhook-signature'
    access_token = get_access_token(PAYPAL_CLIENT_ID, NEW_PAYPAL_SECRET_ID)
    request_headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {access_token}',
    }
    data = {
        'transmission_id': headers.get('Paypal-Transmission-Id'),
        'transmission_time': headers.get('Paypal-Transmission-Time'),
        'cert_url': headers.get('Paypal-Cert-Url'),
        'auth_algo': headers.get('Paypal-Auth-Algo'),
        'transmission_sig': headers.get('Paypal-Transmission-Sig'),
        'webhook_id': '2SM60839WC788605R', 
        # 'webhook_id': '86444230E7577040K',  # sand box paypal webhook_id
        'webhook_event': json.loads(body)
    }
    response = requests.post(url, headers=request_headers, json=data)
    if response.status_code == 200:
        verification_status = response.json().get('verification_status')
        return verification_status == 'SUCCESS'
    else:
        return False

def process_payment(order, order_items, payment_method):
    if order.payment_status == "processing":
        order.payment_status = "paid"
        order.save()
        # Send notifications and emails
        if order.buyer is not None:
            send_notification(user=order.buyer, order=order)
        for o in order_items:
            send_notification(vendor=o.vendor, order=order, order_item=o)
            try:
                context = {
                    'order': order,
                    'order_items': order_items,
                }
                subject = "Order Placed Successfully"
                text_body = render_to_string("email/customer_order_confirmation.txt", context)
                html_body = render_to_string("email/customer_order_confirmation.html", context)
                msg = EmailMultiAlternatives(
                    subject=subject,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    to=[order.email],
                    body=text_body
                )
                msg.attach_alternative(html_body, "text/html")
                msg.send()
            except Exception as e:
                logger.error(f"Failed to send email to buyer: {e}")
        
        return Response({"message": f"{payment_method} Payment Successful"}, status=status.HTTP_200_OK)
    else:
        return Response({"message": "Already Paid"}, status=status.HTTP_200_OK)

class PaymentSuccessView(APIView):
    serializer_class = CartOrderSerializer

    def get(self, request, *args, **kwargs):
        order_oid = kwargs.get('order_oid')
        session_id = request.GET.get('session_id')

        if not order_oid:
            return Response({"error": "Missing order_oid"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            order = CartOrder.objects.get(oid=order_oid)
            order_items = CartOrderItem.objects.filter(order=order)
        except CartOrder.DoesNotExist:
            return Response({"error": "Order not found"}, status=status.HTTP_404_NOT_FOUND)

        if session_id and session_id != "null":
            try:
                session = stripe.checkout.Session.retrieve(session_id)
                if session.payment_status == "paid":
                    # Process payment and update order status
                    order.payment_status = "paid"
                    order.save()
                    return Response({"message": "Payment successful"}, status=status.HTTP_200_OK)
                else:
                    return Response({"message": "Payment status not paid"}, status=status.HTTP_402_PAYMENT_REQUIRED)
            except stripe.error.StripeError as e:
                return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response({"error": "No valid payment information provided"}, status=status.HTTP_400_BAD_REQUEST)

    def post(self, request, *args, **kwargs):
        payload = request.data
        logger.info(f"Payload received: {payload}")

        order_oid = payload.get('order_oid')
        session_id = payload.get('session_id')
        paypal_order_id = payload.get('paypal_order_id')

        if not order_oid:
            return Response({"error": "Missing order_oid"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            order = CartOrder.objects.get(oid=order_oid)
            order_items = CartOrderItem.objects.filter(order=order)
        except CartOrder.DoesNotExist:
            return Response({"error": "Order not found"}, status=status.HTTP_404_NOT_FOUND)

        if paypal_order_id and paypal_order_id != "null":
            paypal_api_url = f'https://api.sandbox.paypal.com/v2/checkout/orders/{paypal_order_id}'
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {get_access_token(settings.PAYPAL_CLIENT_ID, settings.NEW_PAYPAL_SECRET_ID)}',
            }
            response = requests.get(paypal_api_url, headers=headers)

            if response.status_code == 200:
                paypal_order_data = response.json()
                if paypal_order_data.get('status') == 'COMPLETED':
                    order.paypal_order_id = paypal_order_id
                    order.save()
                    return process_payment(order, order_items, "PayPal")
            else:
                return Response({"error": "Failed to verify PayPal order"}, status=status.HTTP_400_BAD_REQUEST)

        if session_id and session_id != "null":
            session = stripe.checkout.Session.retrieve(session_id)
            if session.payment_status == "paid":
                return process_payment(order, order_items, "Stripe")
            else:
                return Response({"message": "Payment status not paid"}, status=status.HTTP_402_PAYMENT_REQUIRED)

        return Response({"error": "No valid payment information provided"}, status=status.HTTP_400_BAD_REQUEST)


@method_decorator(csrf_exempt, name='dispatch')
class PayPalWebhookView(View):
    def post(self, request, *args, **kwargs):
        payload = request.body.decode('utf-8')
        headers = request.headers
        
        try:
            signature_verification = verify_webhook_signature(headers, payload)
        except Exception as e:
            logger.error(f"Signature verification error: {e}")
            return JsonResponse({'error': 'Signature verification failed'}, status=400)

        if not signature_verification:
            logger.error('Signature verification failed')
            return JsonResponse({'error': 'Invalid signature'}, status=400)

        payload = json.loads(payload)
        event_type = payload.get('event_type')

        logger.info(f"Webhook received: {json.dumps(payload, indent=4)}")

        resource = payload.get('resource')
        paypal_order_id = None

        if event_type == 'CHECKOUT.ORDER.APPROVED':
            paypal_order_id = resource.get('id')  # Ensure this correctly extracts the order ID
        elif event_type == 'PAYMENT.CAPTURE.COMPLETED':
            supplementary_data = resource.get('supplementary_data', {})
            related_ids = supplementary_data.get('related_ids', {})
            paypal_order_id = related_ids.get('order_id')

        if not paypal_order_id:
            logger.error("PayPal Order ID not found in webhook payload")
            return JsonResponse({'error': 'PayPal Order ID not found'}, status=400)
        
        try:
            order = CartOrder.objects.get(paypal_order_id=paypal_order_id)
            order_items = CartOrderItem.objects.filter(order=order)
            if event_type == 'PAYMENT.CAPTURE.COMPLETED':
                response = process_payment(order, order_items, "PayPal")
                return JsonResponse({'status': 'success'}, status=200)
            elif event_type == 'CHECKOUT.ORDER.APPROVED':
                
                order.order_status = 'approved'
                order.save()
                return JsonResponse({'status': 'success'}, status=200)
        except CartOrder.DoesNotExist:
            logger.error(f"Order not found: {paypal_order_id}")
            return JsonResponse({'error': 'Order not found'}, status=404)

        logger.warning(f"Unhandled event type: {event_type}")
        return JsonResponse({'error': 'Unhandled event type'}, status=400)




class ReviewListAPIView(generics.ListCreateAPIView):
    serializer_class = ReviewSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        product_id = self.kwargs['product_id']
        product = get_object_or_404(Product, id=product_id)
        return Review.objects.filter(product=product).order_by('-date')  # Ensure ordering

    def create(self, request, *args, **kwargs):
        payload = request.data
        user_id = payload['user_id']
        product_id = payload['product_id']
        rating = payload['rating']
        review = payload['review']

        user = get_object_or_404(User, id=user_id)
        product = get_object_or_404(Product, id=product_id)

        Review.objects.create(
            user=user,
            product=product,
            rating=rating,
            review=review
        )

        return Response({"message": "Review Created Successfully"}, status=status.HTTP_201_CREATED)
    
class SearchProductAPIView(generics.ListCreateAPIView):
    serializer_class = ProductSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        query = self.request.GET.get("query")
        return Product.objects.filter(status="published", title__icontains=query).order_by('-date')
        return products