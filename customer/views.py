from asyncio.exceptions import TimeoutError
from django.shortcuts import render, redirect
from django.conf import settings
from store.models import Category, Tax, Product, Gallery, Specification, Size, Color, Cart, CartOrder, CartOrderItem, ProductFaq, Review, Wishlist, Notification, Coupon
from store.serializers import CouponSerializer, CustomerNotificationSerializer, CustomerWishlistSerializer, InvoiceViewSerializer, MarkReviewSimpleSerializer, ProductSerializer, CategorySerializer, ReviewSerializer, CartSerializer, CartOrderSerializer, CartOrderItemSerializer, NotificationSerializer, SimpleCartOrderDetailSerializer, SimpleCartOrderSerializer, WishlistSerializer
from userauths.models import User
import requests
from django.shortcuts import get_object_or_404

from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from decimal import Decimal
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings

import stripe

class OrderAPIView(generics.ListAPIView):
    serializer_class = SimpleCartOrderSerializer
    permission_classes = [AllowAny]  # allowany only for testing now

    def get_queryset(self):
        user_id = self.kwargs['user_id']
        user = User.objects.get(id=user_id)
        orders = CartOrder.objects.filter(buyer=user, payment_status="paid").order_by('-date')  # Order by date
        return orders
    
class OrderDetailAPIView(generics.RetrieveAPIView):
    serializer_class = SimpleCartOrderDetailSerializer
    permission_classes = [AllowAny]

    def get_object(self):
        user_id = self.kwargs['user_id']
        order_oid = self.kwargs['order_oid']

        user = User.objects.get(id=user_id)

        order = CartOrder.objects.get(buyer=user, oid=order_oid, payment_status="paid")
        return order
    
class InvoiceAPIView(generics.RetrieveAPIView):
    serializer_class = InvoiceViewSerializer
    permission_classes = [AllowAny]

    def get_object(self):
        user_id = self.kwargs['user_id']
        order_oid = self.kwargs['order_oid']

        user = User.objects.get(id=user_id)
        order = CartOrder.objects.get(buyer=user, oid=order_oid, payment_status="paid")
        return order
    
class WishlistAPIView(generics.ListCreateAPIView):
    serializer_class = CustomerWishlistSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        user_id = self.kwargs['user_id']
        user = get_object_or_404(User, id=user_id)
        return Wishlist.objects.filter(user=user).order_by('-date')

    def create(self, request, *args, **kwargs):
        payload = request.data
        product_id = payload['product_id']
        user_id = payload['user_id']

        product = get_object_or_404(Product, id=product_id)
        user = get_object_or_404(User, id=user_id)

        wishlist, created = Wishlist.objects.get_or_create(product=product, user=user)

        if not created:
            wishlist.delete()
            return Response({"message": "Wishlist deleted successfully."}, status=status.HTTP_200_OK)
        else:
            return Response({"message": "Wishlist added successfully."}, status=status.HTTP_201_CREATED)

class WishlistDetailAPIView(generics.DestroyAPIView):
    serializer_class = CustomerWishlistSerializer
    permission_classes = [AllowAny]

    def get_object(self):
        user_id = self.kwargs['user_id']
        wishlist_id = self.kwargs['wishlist_id']
        return get_object_or_404(Wishlist, id=wishlist_id, user_id=user_id)

    def delete(self, request, *args, **kwargs):
        wishlist_item = self.get_object()
        wishlist_item.delete()
        return Response({"message": "Wishlist deleted successfully."}, status=status.HTTP_200_OK)

class CustomerNotification(generics.ListAPIView):
    serializer_class = CustomerNotificationSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        user_id = self.kwargs['user_id']
        user = User.objects.get(id=user_id)
        return Notification.objects.filter(user=user, seen=False).order_by('-date')  # Order by date 
    
class MarkCustomerNotificationAsSeen(generics.RetrieveAPIView):
    serializer_class = MarkReviewSimpleSerializer
    permission_classes = [AllowAny]

    def get_object(self):
        user_id = self.kwargs['user_id']
        noti_id = self.kwargs['noti_id']

        user = User.objects.get(id=user_id)
        noti = Notification.objects.get(id=noti_id, user=user)

        if noti.seen != True:
            noti.seen = True
            noti.save()
        
        return noti