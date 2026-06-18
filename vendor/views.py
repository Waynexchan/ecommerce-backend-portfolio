from django.http import Http404

from asyncio.exceptions import TimeoutError
from django.shortcuts import render, redirect
from django.conf import settings
from userauths.serializer import ProfileSerializer
from vendor.models import Vendor
from django.db import models, transaction
from store.models import Category, Tax, Product, Gallery, Specification, Size, Color, Cart, CartOrder, CartOrderItem, ProductFaq, Review, Wishlist, Notification, Coupon
from store.serializers import CartOrderListSerializer, CouponListSerializer, CouponSerializer, EarningSummarySerializer, FilterOrderSerializer, NotificationListSerializer, OrderItemTrackingSerializer, ProductSerializer, CouponSummarySerializer, NotificationSummarySerializer, CategorySerializer, ReviewReplySerializer, ReviewSerializer, CartSerializer, CartOrderSerializer, CartOrderItemSerializer, NotificationSerializer, ShopProductSerializer, SimpleVendorCartOrderDetailSerializer, VendorProductSerializer, VendorReviewListSerializer, VendorSerializer, WishlistSerializer, SummarySerializer, SpecificationSerializer, ColorSerializer, SizeSerializer, GallerySerializer
from userauths.models import Profile, User

from rest_framework.decorators import api_view
from django.db.models.functions import ExtractMonth
from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from decimal import Decimal
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings
from django.shortcuts import get_object_or_404
from django.core.cache import cache
from django.utils.timezone import now, make_aware
from datetime import datetime, timedelta
from rest_framework.pagination import PageNumberPagination
import logging

logger = logging.getLogger(__name__)

class VendorRegister(generics.CreateAPIView):
    serializer_class = VendorSerializer
    queryset = Vendor.objects.all()
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        payload = request.data

        image = payload['image']
        name = payload['name']
        email = payload['email']
        description = payload['description']
        mobile = payload['mobile']
        user_id = payload['user_id']

        vendor = Vendor.objects.create(
            image=image,
            name=name,
            email=email,
            description=description,
            mobile=mobile,
            user_id=user_id,
        )

        return Response({"message": "Created vendor account"})

class DashboardStatsAPIView(generics.ListAPIView):
    serializer_class = SummarySerializer

    def get_queryset(self):

        vendor_id = self.kwargs['vendor_id']
        vendor = Vendor.objects.get(id=vendor_id)

        # Calculate summary values
        product_count = Product.objects.filter(vendor=vendor).count()

        order_count = CartOrder.objects.filter(vendor=vendor, payment_status="paid").count()
        
        revenue = CartOrderItem.objects.filter(vendor=vendor, order__payment_status="paid").aggregate(
            total_revenue=models.Sum(models.F('sub_total') + models.F('shipping_amount')))['total_revenue'] or 0
        
        # Calculate the number of unique customers
        unique_customers = CartOrder.objects.filter(
            vendor=vendor, payment_status="paid").values('buyer').distinct().count()

        # Return a dummy list as we only need one summary object
        return [{
            'products': product_count,
            'orders': order_count,
            'revenue': revenue,
            'customers': unique_customers,
        }]

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

@api_view(['GET'])
def MonthlyOrderChartAPIView(request, vendor_id):
    vendor = Vendor.objects.get(id=vendor_id)
    orders = CartOrder.objects.filter(vendor=vendor, payment_status="paid")
    orders_by_month = orders.annotate(month=ExtractMonth("date")).values("month").annotate(orders=models.Count("id")).order_by("month")
    return Response(orders_by_month)

@api_view(['GET'])
def MonthlyProductChartAPIView(request, vendor_id):
    vendor = Vendor.objects.get(id=vendor_id)
    products = Product.objects.filter(vendor=vendor)
    orders_by_month = products.annotate(month=ExtractMonth("date")).values("month").annotate(orders=models.Count("id")).order_by("month")
    return Response(orders_by_month)

class ProductAPIView(generics.ListAPIView):
    serializer_class = VendorProductSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        vendor_id = self.kwargs['vendor_id']
        vendor = Vendor.objects.get(id=vendor_id)
        return Product.objects.filter(vendor=vendor).only(
            'id', 'title', 'image', 'price', 'stock_qty', 'status', 'pid', 'slug', 'date'
        ).order_by('-id')


class OrderAPIView(generics.ListAPIView):
    serializer_class = CartOrderListSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        try:
            vendor_id = self.kwargs['vendor_id']
            logger.debug(f"Fetching orders for vendor_id: {vendor_id}")
            vendor = get_object_or_404(Vendor, id=vendor_id)
            queryset = CartOrder.objects.filter(vendor=vendor, payment_status="paid").select_related('buyer').prefetch_related('cartorderitem_set').order_by('-id')
            logger.debug(f"Found {queryset.count()} orders for vendor_id: {vendor_id}")
            return queryset
        except Http404:
            logger.error(f"Vendor with id {vendor_id} does not exist")
            raise serializers.ValidationError("Vendor not found")
        except Exception as e:
            logger.error(f"Error fetching orders: {e}")
            raise serializers.ValidationError("An error occurred while fetching orders")
    
class OrderDetailAPIView(generics.RetrieveAPIView):
    serializer_class = SimpleVendorCartOrderDetailSerializer
    permission_classes = [AllowAny]

    def get_object(self):
        vendor_id = self.kwargs['vendor_id']
        order_oid = self.kwargs['order_oid']
        vendor = Vendor.objects.get(id=vendor_id)
        return CartOrder.objects.get(vendor=vendor, oid=order_oid)

class OrderItemTrackingView(generics.ListCreateAPIView):
    serializer_class = OrderItemTrackingSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        order_oid = self.kwargs['order_oid']
        order_item_id = self.kwargs['order_item_id']
        return CartOrderItem.objects.filter(order__oid=order_oid, id=order_item_id).order_by('id')

    def perform_create(self, serializer):
        order_oid = self.kwargs['order_oid']
        order_item_id = self.kwargs['order_item_id']
        order_item = CartOrderItem.objects.get(order__oid=order_oid, id=order_item_id)
        serializer = self.get_serializer(data=self.request.data, context={'order_item': order_item})
        serializer.is_valid(raise_exception=True)
        serializer.save()

    
class RevenueAPIView(generics.ListAPIView):
    serializer_class = CartOrderItemSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        vendor_id = self.kwargs['vendor_id']
        vendor = Vendor.objects.get(id=vendor_id)

        return CartOrderItem.objects.filter(vendor=vendor, order__payment_status="paid").aggregate(
            total_revenue=models.Sum(models.F('sub_total') + models.F('shipping_amount')))['total_revenue'] or 0

class FilterOrderAPIView(generics.ListAPIView):
    serializer_class = FilterOrderSerializer
    permission_classes =[AllowAny]

    def get_queryset(self, *args, **kwargs):
        vendor_id = self.kwargs['vendor_id']
        vendor = Vendor.objects.get(id=vendor_id)

        filter = self.request.GET.get("filter")

        if filter == 'paid':
            orders = CartOrder.objects.filter(vendor=vendor, payment_status='paid').order_by('-id')
        elif filter == 'pending':
            orders = CartOrder.objects.filter(vendor=vendor, payment_status='pending').order_by('-id')
        elif filter == 'processing':
            orders = CartOrder.objects.filter(vendor=vendor, payment_status='processing').order_by('-id')
        elif filter == 'cancelled':
            orders = CartOrder.objects.filter(vendor=vendor, payment_status='cancelled').order_by('-id')
        elif filter == 'latest':
            orders = CartOrder.objects.filter(vendor=vendor, payment_status='paid').order_by('-id')
        elif filter == 'oldest':
            orders = CartOrder.objects.filter(vendor=vendor, payment_status='paid').order_by('id')
        elif filter == 'Pending':
            orders = CartOrder.objects.filter(vendor=vendor, order_status="pending", payment_status='paid').order_by('-id')
        elif filter == 'Fulfilled':
            orders = CartOrder.objects.filter(vendor=vendor, order_status="fulfilled", payment_status='paid').order_by('-id')            
        elif filter == 'Cancelled':
            orders = CartOrder.objects.filter(vendor=vendor, order_status="cancelled", payment_status='paid').order_by('-id') 
        else:
            orders = CartOrder.objects.filter(vendor=vendor, payment_status='paid').order_by('-id') 

        return orders

class FilterProductAPIView(generics.ListAPIView):
    serializer_class = ProductSerializer
    permission_classes = (AllowAny,)

    def get_queryset(self):
        vendor_id = self.kwargs['vendor_id']
        filter = self.request.GET.get('filter')

        vendor = Vendor.objects.get(id=vendor_id)
        if filter == "published":
            products = Product.objects.filter(vendor=vendor, status="published").order_by('id')
        elif filter == "draft":
            products = Product.objects.filter(vendor=vendor, status="draft").order_by('id')
        elif filter == "disabled":
            products = Product.objects.filter(vendor=vendor, status="disabled").order_by('id')
        elif filter == "in-review":
            products = Product.objects.filter(vendor=vendor, status="in-review").order_by('id')
        elif filter == "latest":
            products = Product.objects.filter(vendor=vendor).order_by('-id')
        elif filter == "oldest":
            products = Product.objects.filter(vendor=vendor).order_by('id')
        else:
            products = Product.objects.filter(vendor=vendor).order_by('id')
        return products
    
class EarningAPIView(generics.ListAPIView):
    serializer_class = EarningSummarySerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        vendor_id = self.kwargs['vendor_id']
        vendor = Vendor.objects.get(id=vendor_id)

        one_month_ago = now() - timedelta(days=28)
        monthly_revenue = CartOrderItem.objects.filter(vendor=vendor, order__payment_status="paid", date__gte=one_month_ago).aggregate(
            total_revenue=models.Sum(models.F('sub_total') + models.F('shipping_amount')))['total_revenue'] or 0
        total_revenue = CartOrderItem.objects.filter(vendor=vendor, order__payment_status="paid").aggregate(
            total_revenue=models.Sum(models.F('sub_total') + models.F('shipping_amount')))['total_revenue'] or 0

        return [{
            'monthly_revenue': monthly_revenue,
            'total_revenue': total_revenue,
        }]

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

@api_view(('GET',))    
def MonthlyEarningTracker(request, vendor_id):
    vendor = Vendor.objects.get(id=vendor_id)
    monthly_earning_tracker = (
        CartOrderItem.objects
        .filter(vendor=vendor, order__payment_status="paid")
        .annotate(month=ExtractMonth("date"))
        .values("month")
        .annotate(
            sales_count=models.Sum("qty"),
            total_earning=models.Sum(models.F('sub_total') + models.F('shipping_amount'))
        ).order_by('-month')
    )

    return Response(monthly_earning_tracker)

class ReviewListAPIView(generics.ListAPIView):
    serializer_class = VendorReviewListSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        vendor_id = self.kwargs['vendor_id']
        vendor = Vendor.objects.get(id=vendor_id)
        return Review.objects.filter(product__vendor=vendor).order_by('id')
    
class ReviewDetailAPIView(generics.RetrieveUpdateAPIView):
    serializer_class = ReviewSerializer  # Default serializer for GET requests
    permission_classes = [AllowAny]

    def get_serializer_class(self):
        if self.request.method == 'PATCH':
            return ReviewReplySerializer  # for PATCH requests
        return ReviewSerializer

    def get_object(self):
        vendor_id = self.kwargs['vendor_id']
        review_id = self.kwargs['review_id']

        vendor = Vendor.objects.get(id=vendor_id)
        review = Review.objects.get(id=review_id, product__vendor=vendor)

        return review
    
class CouponListAPIView(generics.ListAPIView):
    serializer_class = CouponListSerializer
    permission_classes = (AllowAny, )

    def get_queryset(self):
        vendor_id = self.kwargs['vendor_id']
        queryset = Coupon.objects.filter(vendor__id=vendor_id).only('id', 'code', 'discount', 'active').order_by('-id')
        
        return queryset
    
class CouponCreateAPIView(generics.CreateAPIView):
    serializer_class = CouponSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        vendor_id = self.kwargs['vendor_id']
        vendor = Vendor.objects.get(id=vendor_id)

        return Coupon.objects.filter(vendor=vendor)
    
    def create(self, request, *args, **kwargs):
        payload = request.data

        vendor_id = payload['vendor_id']
        code = payload['code']
        discount = payload['discount']
        active = payload['active']

        vendor = Vendor.objects.get(id=vendor_id)
        Coupon.objects.create(
            vendor=vendor,
            code=code,
            discount=discount,
            active=(active.lower() == 'true')
        )

        return Response({"message": "Coupon created successfully"}, status=status.HTTP_201_CREATED)
    
class CouponDetailAPIView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = CouponSerializer
    permission_classes = (AllowAny, )

    def get_object(self):
        vendor_id = self.kwargs['vendor_id']
        coupon_id = self.kwargs['coupon_id']

        vendor = Vendor.objects.get(id=vendor_id)

        coupon = Coupon.objects.get(vendor=vendor, id=coupon_id)
        return coupon

class CouponStatsAPIView(generics.ListAPIView):
    serializer_class = CouponSummarySerializer
    permission_classes=[AllowAny]

    def get_queryset(self):

        vendor_id = self.kwargs['vendor_id']
        vendor = Vendor.objects.get(id=vendor_id)

        total_coupons = Coupon.objects.filter(vendor=vendor).count()
        active_coupons = Coupon.objects.filter(
            vendor=vendor, active=True).count()

        return [{
            'total_coupons': total_coupons,
            'active_coupons': active_coupons,
        }]

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
class NotificationAPIView(generics.ListAPIView):
    serializer_class = NotificationListSerializer
    permission_classes = [AllowAny]
    pagination_class = PageNumberPagination

    def get_queryset(self):
        vendor_id = self.kwargs['vendor_id']
        return Notification.objects.filter(vendor__id=vendor_id, seen=False).select_related('order_item__product').prefetch_related('order_item__product').order_by('-date')

    
class NotificationSummaryAPIView(generics.ListAPIView):
    serializer_class = NotificationSummarySerializer
    permission_classes=[AllowAny]

    def get_queryset(self):

        vendor_id = self.kwargs['vendor_id']
        vendor = Vendor.objects.get(id=vendor_id)

        un_read_noti = Notification.objects.filter(vendor=vendor, seen=False).count()
        read_noti = Notification.objects.filter(vendor=vendor, seen=True).count()
        all_noti = Notification.objects.filter(vendor=vendor).count()

        return [{
            'unread_noti': un_read_noti,
            'read_noti': read_noti,
            'all_noti': all_noti,
        }]
    
    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
class NotificationVendorMarkAsSeen(generics.RetrieveAPIView):
    serializer_class = NotificationSerializer
    permission_classes=[AllowAny]

    def get_object(self):
        vendor_id = self.kwargs['vendor_id']
        noti_id = self.kwargs['noti_id']

        vendor = Vendor.objects.get(id=vendor_id)
        noti = Notification.objects.get(vendor=vendor, id=noti_id)

        noti.seen = True
        noti.save()

        return noti

class VendorProfileUpdate(generics.RetrieveUpdateAPIView):
    queryset = Profile.objects.all()
    serializer_class = ProfileSerializer
    permission_classes = [AllowAny]

class ShopUpdateView(generics.RetrieveUpdateAPIView):
    queryset = Vendor.objects.all()
    serializer_class = VendorSerializer
    permission_classes = [AllowAny]

class ShopAPIView(generics.RetrieveAPIView):
    serializer_class = VendorSerializer
    permission_classes = [AllowAny]

    def get_object(self):
        vendor_slug = self.kwargs['vendor_slug']
        return Vendor.objects.get(slug=vendor_slug)
    
class ShopProductAPIView(generics.ListAPIView):
    serializer_class = ShopProductSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        vendor_slug = self.kwargs['vendor_slug']
        vendor = Vendor.objects.get(slug=vendor_slug)
        products = Product.objects.filter(vendor=vendor).order_by('id')
        return products
    
class ProductCreateView(generics.CreateAPIView):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer

    @transaction.atomic
    def perform_create(self, serializer):
        serializer.is_valid(raise_exception=True)
        serializer.save()
        product_instance = serializer.instance

        specifications_data = []
        colors_data = []
        sizes_data = []
        gallery_data = []
        # Loop through the keys of self.request.data
        for key, value in self.request.data.items():
            # Example key: specifications[0][title]
            if key.startswith('specifications') and '[title]' in key:
                # Extract index from key
                index = key.split('[')[1].split(']')[0]
                title = value
                content_key = f'specifications[{index}][content]'
                content = self.request.data.get(content_key)
                specifications_data.append({'title': title, 'content': content})

            # Example key: colors[0][name]
            elif key.startswith('colors') and '[name]' in key:
                # Extract index from key
                index = key.split('[')[1].split(']')[0]
                name = value
                color_code_key = f'colors[{index}][color_code]'
                color_code = self.request.data.get(color_code_key)
                image_key = f'colors[{index}][image]'
                image = self.request.data.get(image_key)
                colors_data.append({'name': name, 'color_code': color_code, 'image': image})

            # Example key: sizes[0][name]
            elif key.startswith('sizes') and '[name]' in key:
                # Extract index from key
                index = key.split('[')[1].split(']')[0]
                name = value
                price_key = f'sizes[{index}][price]'
                price = self.request.data.get(price_key)
                sizes_data.append({'name': name, 'price': price})

            # Example key: gallery[0][image]
            elif key.startswith('gallery') and '[image]' in key:
                # Extract index from key
                index = key.split('[')[1].split(']')[0]
                image = value
                gallery_data.append({'image': image})


        # Save nested serializers with the product instance
        self.save_nested_data(product_instance, SpecificationSerializer, specifications_data)
        self.save_nested_data(product_instance, ColorSerializer, colors_data)
        self.save_nested_data(product_instance, SizeSerializer, sizes_data)
        self.save_nested_data(product_instance, GallerySerializer, gallery_data)

    def save_nested_data(self, product_instance, serializer_class, data):
        serializer = serializer_class(data=data, many=True, context={'product_instance': product_instance})
        serializer.is_valid(raise_exception=True)
        serializer.save(product=product_instance)
       
class ProductUpdateView(generics.RetrieveUpdateAPIView):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    permission_classes = (AllowAny, )

    def get_object(self):
        vendor_id = self.kwargs['vendor_id']
        product_pid = self.kwargs['product_pid']
        vendor = Vendor.objects.get(id=vendor_id)
        product = Product.objects.get(pid=product_pid, vendor=vendor)
        return product

    @transaction.atomic
    def update(self, request, *args, **kwargs):
        product_instance = self.get_object()
        print("Received data:", request.data)
        print("Received files:", request.FILES)
        
        serializer = self.get_serializer(product_instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        product_instance.specification_set.all().delete()
        product_instance.color_set.all().delete()
        product_instance.size_set.all().delete()
        product_instance.gallery_set.all().delete()

        specifications_data = []
        colors_data = []
        sizes_data = []
        gallery_data = []

        for key, value in request.data.items():
            if key.startswith('specifications') and '[title]' in key:
                index = key.split('[')[1].split(']')[0]
                title = value
                content_key = f'specifications[{index}][content]'
                content = request.data.get(content_key)
                specifications_data.append({'title': title, 'content': content})

            elif key.startswith('colors') and '[name]' in key:
                index = key.split('[')[1].split(']')[0]
                name = value
                color_code_key = f'colors[{index}][color_code]'
                color_code = request.data.get(color_code_key)
                image_key = f'colors[{index}][image]'
                image = request.FILES.get(image_key)
                if image:
                    colors_data.append({'name': name, 'color_code': color_code, 'image': image})
                else:
                    colors_data.append({'name': name, 'color_code': color_code})

            elif key.startswith('sizes') and '[name]' in key:
                index = key.split('[')[1].split(']')[0]
                name = value
                price_key = f'sizes[{index}][price]'
                price = request.data.get(price_key)
                if price and price != 'NaN':  # Ensure price is not NaN
                    sizes_data.append({'name': name, 'price': price})

            elif key.startswith('gallery') and '[image]' in key:
                index = key.split('[')[1].split(']')[0]
                image = request.FILES.get(f'gallery[{index}][image]')
                if image:
                    gallery_data.append({'image': image})

        self.save_nested_data(product_instance, SpecificationSerializer, specifications_data)
        self.save_nested_data(product_instance, ColorSerializer, colors_data)
        self.save_nested_data(product_instance, SizeSerializer, sizes_data)
        self.save_nested_data(product_instance, GallerySerializer, gallery_data)

        return Response({'message': 'Product updated successfully'}, status=status.HTTP_200_OK)

    def save_nested_data(self, product_instance, serializer_class, data):
        serializer = serializer_class(data=data, many=True, context={'product_instance': product_instance})
        serializer.is_valid(raise_exception=True)
        serializer.save(product=product_instance)


class ProductDeleteAPIView(generics.DestroyAPIView):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer

    def get_object(self):
        vendor_id = self.kwargs['vendor_id']
        product_id = self.kwargs['product_pid']

        vendor = Vendor.objects.get(id=vendor_id)
        product = Product.objects.get(pid=product_id, vendor=vendor)

        return product