from userauths.serializer import ProfileSerializer, UserSerializer
from rest_framework import serializers

from store.models import Category, Product, Gallery, Specification, Size,Color, Cart, CartOrder , CartOrderItem, ProductFaq, Review, Wishlist, Notification, Coupon
from vendor.models import Vendor
from userauths.models import User, Profile

class CategorySerializer(serializers.ModelSerializer):

    class Meta:
        model = Category
        fields = "__all__"

class GallerySerializer(serializers.ModelSerializer):
    class Meta:
        model = Gallery
        fields = "__all__"

class SpecificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Specification
        fields = "__all__"

class SizeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Size
        fields = "__all__"

class ColorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Color
        fields = "__all__"

class ProductSerializer(serializers.ModelSerializer):
    gallery = GallerySerializer(many=True, read_only=True, source='gallery_set')
    color = ColorSerializer(many=True, read_only=True, source='color_set')
    specification = SpecificationSerializer(many=True, read_only=True, source='specification_set')
    size = SizeSerializer(many=True, read_only=True, source='size_set')

    class Meta:
        model = Product
        fields = [
            'id', 
            'title',
            'image',
            'description',
            'category',
            'price',
            'old_price',
            'shipping_amount',
            'stock_qty',
            'in_stock',
            'status',
            'featured',
            'views',
            'vendor',
            'gallery',
            'color',
            'specification',
            'product_rating',
            'rating_count',
            'orders',
            'size',
            'pid',
            'slug',
            'date',
        ]
        depth = 1

    def validate_price(self, value):
        if value is None or value == '':
            raise serializers.ValidationError("This field may not be blank.")
        return value

    def validate_old_price(self, value):
        if value is None or value == '':
            raise serializers.ValidationError("This field may not be blank.")
        return value

    def validate_shipping_amount(self, value):
        if value is None or value == '':
            raise serializers.ValidationError("This field may not be blank.")
        return value

    def validate_stock_qty(self, value):
        if value is None or value == '':
            raise serializers.ValidationError("This field may not be blank.")
        return value
    
    def __init__(self, *args, **kwargs):
        super(ProductSerializer, self).__init__(*args, **kwargs)
        request = self.context.get("request")
        if request and request.method == "POST":
            self.Meta.depth = 0
        else:
            self.Meta.depth = 3


class SimpleProductSerializer(serializers.ModelSerializer):
    category = serializers.StringRelatedField()

    class Meta:
        model = Product
        fields = [
            'id', 
            'title',
            'image',
            'category',
            'price',
            'old_price',
            'shipping_amount',  # Include shipping_amount
            'slug',
        ]


class ShopProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = [
            'id',
            'title',
            'image',
            'price',
            'old_price',
            'shipping_amount',
            'stock_qty',
            'category',
            'slug',
        ]

class VendorProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = [
            'id', 
            'title',
            'image',
            'price',
            'stock_qty',
            'status',
            'pid',
            'slug',
            'date',
        ]
        depth = 1

    def __init__(self, *args, **kwargs):
        super(VendorProductSerializer, self).__init__(*args, **kwargs) 
        request = self.context.get("request")
        if request and request.method == "POST":
            self.Meta.depth = 0
        else:
            self.Meta.depth = 1

class FilterProductByCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = [
            'id', 
            'title', 
            'image', 
            'price', 
            'old_price', 
            'category', 
            'slug'
        ]

class CartSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = Cart
        fields = "__all__"

    def __init__(self, *args, **kwargs): # extend  model
        super(CartSerializer, self).__init__(*args, **kwargs)

        request = self.context.get("request")
        if request and request.method == "POST":
            self.Meta.depth = 0

        else:
            self.Meta.depth = 3



class CartOrderItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = CartOrderItem
        fields = "__all__"

class CartOrderSerializer(serializers.ModelSerializer):
    orderitem = CartOrderItemSerializer(many=True, read_only=True)
    
    class Meta:
        model = CartOrder
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)  # No need to specify the class name in super()
        request = self.context.get("request")
        if request and request.method == "POST":
            self.Meta.depth = 0
        else:
            self.Meta.depth = 3

class CheckoutItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = CartOrderItem
        fields = ['product', 'qty', 'price', 'color', 'size', 'total']  # Include only necessary fields

class CheckoutOrderSerializer(serializers.ModelSerializer):
    items = CheckoutItemSerializer(source='orderitem_set', many=True, read_only=True)  
    class Meta:
        model = CartOrder
        fields = ['id', 'oid', 'buyer', 'sub_total', 'shipping_amount', 'tax_fee', 'service_fee', 'total', 'full_name', 'email', 'mobile', 'address', 'city', 'state', 'country', 'items']
        depth = 1  

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get("request")
        if request and request.method == "POST":
            self.Meta.depth = 0
        else:
            self.Meta.depth = 1

class SimpleCartOrderDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = CartOrder
        fields = ['id', 'oid', 'total', 'payment_status', 'order_status', 'shipping_amount', 'tax_fee', 'service_fee', 'saved']

class SimpleCartOrderSerializer(serializers.ModelSerializer):
    class Meta:
        model = CartOrder
        fields = ['id', 'oid', 'date', 'payment_status', 'order_status', 'total']



class SimpleProductDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = ['title', 'price', 'image', 'slug']

class SimpleCartOrderItemSerializer(serializers.ModelSerializer):
    product = SimpleProductDetailSerializer()

    class Meta:
        model = CartOrderItem
        fields = ['id', 'product', 'qty', 'price', 'sub_total', 'saved', 'tracking_id']

class SimpleVendorCartOrderDetailSerializer(serializers.ModelSerializer):
    orderitem = SimpleCartOrderItemSerializer(many=True, read_only=True)
    
    class Meta:
        model = CartOrder
        fields = ['oid', 'total', 'orderitem']

class FilterOrderSerializer(serializers.ModelSerializer):
    class Meta:
        model = CartOrder
        fields = ['id', 'oid', 'total', 'payment_status', 'order_status', 'date']

class CartOrderListSerializer(serializers.ModelSerializer):
    class Meta:
        model = CartOrder
        fields = ['oid', 'total', 'payment_status', 'order_status', 'date']

class OrderItemTrackingSerializer(serializers.ModelSerializer):
    class Meta:
        model = CartOrderItem
        fields = ['tracking_id']

    def create(self, validated_data):
        order_item = self.context['order_item']
        order_item.tracking_id = validated_data.get('tracking_id', order_item.tracking_id)
        order_item.save()
        return order_item
    
class InvoiceProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = [ 'title']
    
class CartOrderItemSerializer(serializers.ModelSerializer):
    product = ProductSerializer(read_only=True)

    class Meta:
        model = CartOrderItem
        fields = ['product', 'price', 'qty', 'sub_total', 'saved']

class InvoiceViewSerializer(serializers.ModelSerializer):
    order_items = CartOrderItemSerializer(many=True, source='orderitem', read_only=True)

    class Meta:
        model = CartOrder
        fields = ['oid', 'full_name', 'email', 'mobile', 'sub_total', 'shipping_amount', 'tax_fee', 'service_fee', 'total', 'order_items']
    
class VendorSerializer(serializers.ModelSerializer):
    # Serialize related CartOrderItem models
    user = UserSerializer(read_only=True)

    class Meta:
        model = Vendor
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super(VendorSerializer, self).__init__(*args, **kwargs)
        # Customize serialization depth based on the request method.
        request = self.context.get('request')
        if request and request.method == 'POST':
            # When creating a new cart order, set serialization depth to 0.
            self.Meta.depth = 0
        else:
            # For other methods, set serialization depth to 3.
            self.Meta.depth = 3

class ProductFaqSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = ProductFaq
        fields = "__all__"

    def __init__(self, *args, **kwargs): # extend  model
        super(ProductFaqSerializer, self).__init__(*args, **kwargs)

        request = self.context.get("request")
        if request and request.method == "POST":
            self.Meta.depth = 0

        else:
            self.Meta.depth = 3

class ReviewSerializer(serializers.ModelSerializer):
    profile = ProfileSerializer()
    
    class Meta:
        model = Review
        fields = ["id", "review", "rating", "user", "profile", "date", "product", "reply"]

    def __init__(self, *args, **kwargs): # extend  model
        super(ReviewSerializer, self).__init__(*args, **kwargs)

        request = self.context.get("request")
        if request and request.method == "POST":
            self.Meta.depth = 0

        else:
            self.Meta.depth = 3

class ReviewProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = Profile
        fields = ['full_name', 'image']

class ReviewProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = ['title']

class ReviewReplySerializer(serializers.ModelSerializer):
    class Meta:
        model = Review
        fields = ['reply']

class VendorReviewListSerializer(serializers.ModelSerializer):
    profile = ReviewProfileSerializer()
    product = ReviewProductSerializer()

    class Meta:
        model = Review
        fields = ['id', 'review', 'rating', 'profile', 'product', 'reply', 'date']

class WishlistSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = Wishlist
        fields = "__all__"

    def __init__(self, *args, **kwargs): # extend  model
        super(WishlistSerializer, self).__init__(*args, **kwargs)

        request = self.context.get("request")
        if request and request.method == "POST":
            self.Meta.depth = 0

        else:
            self.Meta.depth = 3

class CustomerWishlistSerializer(serializers.ModelSerializer):
    product_title = serializers.CharField(source='product.title')
    product_image = serializers.ImageField(source='product.image')
    product_price = serializers.DecimalField(source='product.price', max_digits=10, decimal_places=2)
    product_category = serializers.CharField(source='product.category.title')

    class Meta:
        model = Wishlist
        fields = ['id', 'product_title', 'product_image', 'product_price', 'product_category', 'date']

class CouponSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = Coupon
        fields = "__all__"

    def __init__(self, *args, **kwargs): # extend  model
        super(CouponSerializer, self).__init__(*args, **kwargs)

        request = self.context.get("request")
        if request and request.method == "POST":
            self.Meta.depth = 0

        else:
            self.Meta.depth = 3

class CouponListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Coupon
        fields = ['id', 'code', 'discount', 'active', 'date']
        depth = 1  

    def __init__(self, *args, **kwargs):  # Extend model
        super(CouponListSerializer, self).__init__(*args, **kwargs)  
        request = self.context.get("request")
        if request and request.method == "POST":
            self.Meta.depth = 0
        else:
            self.Meta.depth = 1
            

class NotificationSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = Notification
        fields = "__all__"

    def __init__(self, *args, **kwargs): # extend  model
        super(NotificationSerializer, self).__init__(*args, **kwargs)

        request = self.context.get("request")
        if request and request.method == "POST":
            self.Meta.depth = 0

        else:
            self.Meta.depth = 3

class CustomerNotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ['id', 'seen', 'date']

class MarkReviewSimpleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ['id', 'seen']

class NotificationListSerializer(serializers.ModelSerializer):
    product_title = serializers.SerializerMethodField()
    order_item_id = serializers.SerializerMethodField()

    class Meta:
        model = Notification
        fields = ['id', 'seen', 'date', 'product_title', 'order_item_id']

    def get_product_title(self, obj):
        return obj.order_item.product.title if obj.order_item and obj.order_item.product else None

    def get_order_item_id(self, obj):
        return obj.order_item.id if obj.order_item else None

    def __init__(self, *args, **kwargs):  # extend  model
        super(NotificationListSerializer, self).__init__(*args, **kwargs)

        request = self.context.get("request")
        if request and request.method == "POST":
            self.Meta.depth = 0
        else:
            self.Meta.depth = 1  # Reduced depth for performance

class SummarySerializer(serializers.Serializer):
    products = serializers.IntegerField()
    orders = serializers.IntegerField()
    revenue = serializers.DecimalField(max_digits=12, decimal_places=2)
    customers = serializers.IntegerField()  
    
class EarningSummarySerializer(serializers.Serializer):
    monthly_revenue = serializers.DecimalField(max_digits=10, decimal_places=2)
    total_revenue = serializers.DecimalField(max_digits=10, decimal_places=2)
    
class CouponSummarySerializer(serializers.Serializer):
    total_coupons = serializers.IntegerField()
    active_coupons = serializers.IntegerField()


class NotificationSummarySerializer(serializers.Serializer):
    read_noti = serializers.IntegerField()
    unread_noti = serializers.IntegerField()   
    all_noti = serializers.IntegerField()

class VendorSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)

    class Meta:
        model = Vendor
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super(VendorSerializer, self).__init__(*args, **kwargs)
        request = self.context.get('request')
        if request and request.method == 'POST':
            self.Meta.depth = 0
        else:
            self.Meta.depth = 3