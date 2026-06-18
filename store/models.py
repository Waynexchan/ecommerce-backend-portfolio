from django.db import models
from django.utils.text import slugify
from django.dispatch import receiver
from django.db.models.signals import post_save
from vendor.models import Vendor
from userauths.models import User, Profile
from django.utils import timezone
from shortuuid.django_fields import ShortUUIDField
from django.utils.timezone import now

class Category(models.Model):
    title = models.CharField(max_length=100)
    image = models.FileField(upload_to="category", default="category.jpg", null=True, blank=True)
    active = models.BooleanField(default=True)
    slug = models.SlugField(unique=True)

    def __str__(self):
        return self.title


class Product(models.Model):
    Status = (
        ("draft", "Draft"),
        ("disabled", "Disabled"),
        ("rejected", "Rejected"),
        ("in_review", "In Review"),
        ("published", "Published"),
    )

    title = models.CharField(max_length=100)
    image = models.FileField(upload_to="products", default="product.jpg", null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True)
    
    price = models.DecimalField(decimal_places=2, max_digits=12, default=0.00)
    old_price = models.DecimalField(decimal_places=2, max_digits=12, default=0.00)
    shipping_amount = models.DecimalField(decimal_places=2, max_digits=12, default=0.00)
    stock_qty = models.PositiveIntegerField(default=1)
    in_stock = models.BooleanField(default=True)
    status = models.CharField(max_length=100, choices=Status, default="published")
    featured = models.BooleanField(default=False)
    views = models.PositiveIntegerField(default=0)
    rating = models.PositiveIntegerField(default=0, null=True, blank=True)
    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE)
    pid = ShortUUIDField(unique=True, length=10, alphabet="abcdefg12345")
    slug = models.SlugField(unique=True, null=True, blank=True)
    date = models.DateTimeField(default=now)  # Ensure timezone-aware datetime

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super(Product, self).save(*args, **kwargs)

    def __str__(self):
        return self.title
    
    def product_rating(self): 
        product_rating = Review.objects.filter(product=self).aggregate(avg_rating=models.Avg("rating"))
        return product_rating['avg_rating']
    
    def rating_count(self):
        return Review.objects.filter(product=self).count()

    def gallery(self):
        return Gallery.objects.filter(product=self)
    
    def specification(self):
        return Specification.objects.filter(product=self)
    
    def size(self):
        return Size.objects.filter(product=self)
    
    def color(self):
        return Color.objects.filter(product=self)
    
    def orders(self):
        return CartOrderItem.objects.filter(product=self).count()
    
    class Meta:
        indexes = [
            models.Index(fields=['slug']),
            models.Index(fields=['category']),
            models.Index(fields=['status']),
            models.Index(fields=['vendor']),
        ]
        ordering = ['-date']  # Ensure default ordering by date

class Gallery(models.Model):
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True)
    image = models.FileField(upload_to="products", default="product.jpg", null=True, blank=True)
    active = models.BooleanField(default=True)
    gid = ShortUUIDField(unique=True, length=10, alphabet="abcdefg12345")

    def __str__(self):
        return self.product.title

    class Meta:
        verbose_name_plural = "Product Images"


class Specification(models.Model):
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True)
    title = models.CharField(max_length=1000, null=True, blank=True)
    content = models.CharField(max_length=1000, null=True, blank=True)

    def __str__(self):
        return self.title


class Size(models.Model):
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True)
    name = models.CharField(max_length=1000, null=True, blank=True)
    price = models.DecimalField(decimal_places=2, max_digits=12, default=0.00, null=True, blank=True)  # different price for different size

    def __str__(self):
        return self.name


class Color(models.Model):
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True)
    name = models.CharField(max_length=1000, null=True, blank=True)
    color_code = models.CharField(max_length=1000, null=True, blank=True)

    
    def __str__(self):
        return self.name


class Cart(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    qty = models.PositiveIntegerField(default=0)
    price = models.DecimalField(default=0.00, max_digits=12, decimal_places=2)
    sub_total = models.DecimalField(default=0.00, max_digits=12, decimal_places=2)
    shipping_amount = models.DecimalField(default=0.00, max_digits=12, decimal_places=2)
    service_fee = models.DecimalField(default=0.00, max_digits=12, decimal_places=2)
    tax_fee = models.DecimalField(default=0.00, max_digits=12, decimal_places=2)
    total = models.DecimalField(default=0.00, max_digits=12, decimal_places=2)
    country = models.CharField(max_length=100, null=True, blank=True)
    size = models.CharField(max_length=100, null=True, blank=True)
    color = models.CharField(max_length=100, null=True, blank=True)
    cart_id = models.CharField(max_length=100, null=True, blank=True)
    date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.cart_id} - {self.product.title}"


class CartOrder(models.Model):
    PAYMENT_STATUS = (
        ("paid", "Paid"),
        ("pending", "Pending"),
        ("processing", "Processing"),
        ("cancelled", "Cancelled"),
    )

    ORDER_STATUS = (
        ("pending", "Pending"),
        ("fulfilled", "Fulfilled"),
        ("cancelled", "Cancelled"),
    )
    vendor = models.ManyToManyField(Vendor, blank=True)  # order from different vendors
    buyer = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    sub_total = models.DecimalField(default=0.00, max_digits=12, decimal_places=2)
    shipping_amount = models.DecimalField(default=0.00, max_digits=12, decimal_places=2)
    tax_fee = models.DecimalField(default=0.00, max_digits=12, decimal_places=2)
    service_fee = models.DecimalField(default=0.00, max_digits=12, decimal_places=2)
    total = models.DecimalField(default=0.00, max_digits=12, decimal_places=2)

    payment_status = models.CharField(choices=PAYMENT_STATUS, max_length=100, default="pending")
    order_status = models.CharField(choices=ORDER_STATUS, max_length=100, default="pending")

    # Coupons
    initial_total = models.DecimalField(default=0.00, max_digits=12, decimal_places=2)
    saved = models.DecimalField(default=0.00, max_digits=12, decimal_places=2)

    # Bio Data
    full_name = models.CharField(max_length=100, null=True, blank=True)
    email = models.CharField(max_length=100, null=True, blank=True)
    mobile = models.CharField(max_length=100, null=True, blank=True)

    # Shipping Address
    address = models.CharField(max_length=100, null=True, blank=True)
    city = models.CharField(max_length=100, null=True, blank=True)
    state = models.CharField(max_length=100, null=True, blank=True)
    country = models.CharField(max_length=100, null=True, blank=True)

    #Stripe
    stripe_session_id = models.CharField(max_length=1000, null=True, blank=True)
    paypal_order_id = models.CharField(max_length=255, null=True, blank=True)

    oid = ShortUUIDField(unique=True, length=10, alphabet="abcdefg12345")
    date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.oid
    
    def orderitem(self):
        return CartOrderItem.objects.filter(order=self)

    def save(self, *args, **kwargs):
        super(CartOrder, self).save(*args, **kwargs)

class CartOrderItem(models.Model):
    order = models.ForeignKey(CartOrder, on_delete=models.CASCADE)
    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)

    qty = models.PositiveIntegerField(default=0)
    price = models.DecimalField(default=0.00, max_digits=12, decimal_places=2)
    sub_total = models.DecimalField(default=0.00, max_digits=12, decimal_places=2)
    shipping_amount = models.DecimalField(default=0.00, max_digits=12, decimal_places=2)
    service_fee = models.DecimalField(default=0.00, max_digits=12, decimal_places=2)
    tax_fee = models.DecimalField(default=0.00, max_digits=12, decimal_places=2)
    total = models.DecimalField(default=0.00, max_digits=12, decimal_places=2)
    country = models.CharField(max_length=100, null=True, blank=True)
    tracking_id = models.CharField(max_length=255, null=True, blank=True)
    size = models.CharField(max_length=100, null=True, blank=True)
    color = models.CharField(max_length=100, null=True, blank=True)

    # Coupons
    coupon = models.ManyToManyField("store.Coupon", blank=True)
    initial_total = models.DecimalField(default=0.00, max_digits=12, decimal_places=2)
    saved = models.DecimalField(default=0.00, max_digits=12, decimal_places=2)

    oid = ShortUUIDField(unique=True, length=10, alphabet="abcdefg12345")
    date = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if self.date and timezone.is_naive(self.date):
            self.date = timezone.make_aware(self.date, timezone.get_current_timezone())
        super().save(*args, **kwargs)

    class Meta:
        ordering = ['id']

    def __str__(self):
        return self.oid

class ProductFaq(models.Model):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    product = models.ForeignKey(Product, on_delete= models.CASCADE)
    email = models.EmailField(null=True, blank=True)
    question = models.CharField(max_length=1000)
    answer = models.TextField(null=True, blank=True)
    active = models.BooleanField(default=False)
    date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.question
    
    class Meta:
        verbose_name_plural = "Product FAQS"

class Review(models.Model):
    RATING = (
        (1, "1 Star"),
        (2, "2 Star"),
        (3, "3 Star"),
        (4, "4 Star"),
        (5, "5 Star"),
    )
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, db_index=True)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, db_index=True)
    review = models.TextField()
    reply = models.TextField(null=True, blank=True)
    rating = models.IntegerField(choices=RATING)
    active = models.BooleanField(default=False)
    date = models.DateTimeField(default=now)  # Ensure timezone-aware datetime

    def __str__(self):
        return self.product.title
    
    class Meta:
        verbose_name_plural = "Reviews & Rating"
        ordering = ['-date']  # Ensure default ordering by date

    def profile(self):
        return Profile.objects.select_related('user').get(user=self.user)
    
@receiver(post_save, sender=Review) # rating after a new review saved
def update_product_rating(sender, instance, **kwargs):
    if instance.product:
        product = instance.product
        product.rating = product.product_rating()
        product.save()

class Wishlist(models.Model):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    product = models.ForeignKey(Product, on_delete= models.CASCADE)
    date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.product.title
    
class Notification(models.Model):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    order = models.ForeignKey(CartOrder, on_delete=models.SET_NULL, null=True, blank=True)
    vendor = models.ForeignKey(Vendor, on_delete=models.SET_NULL, null=True, blank=True)
    order_item = models.ForeignKey(CartOrderItem, on_delete=models.SET_NULL, null=True, blank=True)
    seen = models.BooleanField(default=False)
    date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        if self.order:
            return self.order.oid
        else:
            return "Notification -{self.pk}"
        
class Coupon(models.Model):
    coupon = models.ManyToManyField("self", blank=True, related_name="related_coupons")
    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE)
    user_by = models.ManyToManyField(User, blank=True)
    code = models.CharField(max_length=1000)
    discount = models.IntegerField(default=1)
    active = models.BooleanField(default=False)
    date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.code
    
class Tax(models.Model):
    country = models.CharField(max_length=100)
    rate = models.IntegerField(default = 5, help_text = "Numbers added here are n percentage e.g 5%")
    active = models.BooleanField(default=True)
    date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.country
    
    class Meta:
        verbose_name_plural = "Taxes"
        ordering = ['country']

class ConfigSettings(models.Model):
    SERVICE_FEE_CHARGE_TYPE = (
    ("percentage", "Percentage"),
    ("flat_rate", "Flat Rate"),
)
    currency_sign = models.CharField(default="$", max_length=10)
    currency_abbreviation = models.CharField(default="USD", max_length=10)
    service_fee_percentage = models.IntegerField(default=5, help_text="NOTE: Numbers added here are in percentage (%) e.g. 4%")
    service_fee_flat_rate = models.DecimalField(default=0.7, max_digits=12, decimal_places=2, help_text="NOTE: Add the amount you want to charge as service fee e.g $2.30")
    service_fee_charge_type = models.CharField(default="percentage", max_length=30, choices=SERVICE_FEE_CHARGE_TYPE)

    class Meta:
        verbose_name = ("Settings")
        verbose_name_plural = ("Settings")

    def __str__(self):
        return "Config Settings"