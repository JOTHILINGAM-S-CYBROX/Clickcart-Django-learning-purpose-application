from decimal import Decimal
import uuid
from django.contrib.auth.models import User
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Avg
from django.utils import timezone
from django.utils.text import slugify


class Category(models.Model):
    """Product category or subcategory for Clickcart navigation and filtering."""

    name = models.CharField(max_length=120)
    slug = models.SlugField(max_length=140, unique=True)
    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='subcategories',
    )
    icon_image = models.CharField(
        max_length=255,
        default='landingpage/images/cat-electronics.svg',
        help_text='Static path to category icon image',
    )
    tagline = models.CharField(max_length=160, blank=True)
    display_order = models.PositiveIntegerField(default=0)
    is_featured = models.BooleanField(default=True)

    class Meta:
        verbose_name_plural = 'Categories'
        ordering = ['display_order', 'name']

    def __str__(self):
        if self.parent:
            return f'{self.parent.name} > {self.name}'
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class Brand(models.Model):
    """Product brand metadata."""

    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=120, unique=True)
    tagline = models.CharField(max_length=160, blank=True)
    is_assured = models.BooleanField(default=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class SellerProfile(models.Model):
    """Marketplace seller account linked to a Django User."""

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='seller_profile')
    store_name = models.CharField(max_length=150, unique=True)
    slug = models.SlugField(max_length=170, unique=True)
    gstin = models.CharField(max_length=20, blank=True)
    pickup_pincode = models.CharField(max_length=6, default='560001')
    description = models.TextField(blank=True)
    rating = models.DecimalField(max_digits=3, decimal_places=1, default=Decimal('4.5'))
    total_ratings = models.PositiveIntegerField(default=120)
    is_verified = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.store_name

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.store_name) or f'seller-{self.user_id}'
            self.slug = base
        super().save(*args, **kwargs)


class CustomerProfile(models.Model):
    """Extended customer profile storing SuperCoins, Plus membership, and Wallet."""

    GENDER_CHOICES = [
        ('M', 'Male'),
        ('F', 'Female'),
        ('O', 'Other'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='customer_profile')
    phone = models.CharField(max_length=15, blank=True)
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES, blank=True)
    supercoins = models.PositiveIntegerField(default=50)
    is_plus_member = models.BooleanField(default=False)
    wallet_balance = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('2500.00'))
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.user.username} Profile'


class Address(models.Model):
    """Saved shipping addresses for a user."""

    ADDRESS_TYPES = [
        ('HOME', 'Home (All day delivery)'),
        ('WORK', 'Work (Delivery between 10 AM - 5 PM)'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='addresses')
    full_name = models.CharField(max_length=120)
    phone = models.CharField(max_length=15)
    pincode = models.CharField(max_length=6)
    locality = models.CharField(max_length=120)
    street_address = models.TextField()
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    landmark = models.CharField(max_length=150, blank=True)
    address_type = models.CharField(max_length=10, choices=ADDRESS_TYPES, default='HOME')
    is_default = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = 'Addresses'
        ordering = ['-is_default', '-created_at']

    def __str__(self):
        return f'{self.full_name} - {self.city} ({self.pincode})'

    def save(self, *args, **kwargs):
        if self.is_default:
            Address.objects.filter(user=self.user, is_default=True).exclude(pk=self.pk).update(is_default=False)
        super().save(*args, **kwargs)


class Product(models.Model):
    """Core catalog product matching Flipkart product detail capabilities."""

    seller = models.ForeignKey(SellerProfile, on_delete=models.CASCADE, related_name='products')
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='products')
    brand = models.ForeignKey(Brand, on_delete=models.SET_NULL, null=True, related_name='products')
    title = models.CharField(max_length=255)
    slug = models.SlugField(max_length=280, unique=True)
    sku = models.CharField(max_length=50, unique=True)
    short_description = models.CharField(max_length=300)
    description = models.TextField()
    highlights = models.TextField(
        blank=True,
        help_text='One highlight bullet per line',
    )
    specifications = models.JSONField(default=dict, blank=True)
    mrp = models.DecimalField(max_digits=10, decimal_places=2)
    selling_price = models.DecimalField(max_digits=10, decimal_places=2)
    stock = models.PositiveIntegerField(default=25)
    is_assured = models.BooleanField(default=True, verbose_name='Clickcart Assured')
    is_cod_available = models.BooleanField(default=True)
    is_exchange_available = models.BooleanField(default=False)
    max_exchange_discount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    warranty_summary = models.CharField(max_length=200, default='1 Year Manufacturer Warranty')
    return_policy_days = models.PositiveIntegerField(default=7)
    delivery_days = models.PositiveIntegerField(default=2)
    is_fast_delivery = models.BooleanField(default=True)
    is_deal_of_day = models.BooleanField(default=False)
    is_trending = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    primary_image = models.CharField(max_length=255, default='landingpage/images/prod-phone.svg')
    gallery_images = models.JSONField(default=list, blank=True)
    rating_avg = models.DecimalField(max_digits=3, decimal_places=1, default=Decimal('4.4'))
    rating_count = models.PositiveIntegerField(default=0)
    sold_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-is_trending', '-sold_count', '-created_at']

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.title)[:240] or 'product'
            slug = base
            counter = 1
            while Product.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f'{base}-{counter}'
                counter += 1
            self.slug = slug
        if not self.sku:
            self.sku = f'CC-{uuid.uuid4().hex[:8].upper()}'
        super().save(*args, **kwargs)

    @property
    def discount_percent(self):
        if self.mrp and self.mrp > self.selling_price:
            return int(round(((self.mrp - self.selling_price) / self.mrp) * 100))
        return 0

    @property
    def savings_amount(self):
        return max(Decimal('0.00'), self.mrp - self.selling_price)

    @property
    def supercoins_reward(self):
        coins = int(self.selling_price // Decimal('100')) * 2
        return min(100, max(2, coins))

    @property
    def emi_per_month(self):
        return int(round(self.selling_price / Decimal('12')))

    @property
    def highlights_list(self):
        return [line.strip() for line in self.highlights.splitlines() if line.strip()]

    @property
    def all_images(self):
        imgs = [self.primary_image] if self.primary_image else []
        for img in (self.gallery_images or []):
            if img and img not in imgs:
                imgs.append(img)
        return imgs

    def recalculate_ratings(self):
        agg = self.reviews.aggregate(avg=Avg('rating'))
        count = self.reviews.count()
        self.rating_count = count
        if agg['avg'] is not None:
            self.rating_avg = round(Decimal(str(agg['avg'])), 1)
        self.save(update_fields=['rating_avg', 'rating_count'])


class ProductVariant(models.Model):
    """Color, Size, or Storage variants for a product."""

    VARIANT_TYPES = [
        ('COLOR', 'Color'),
        ('STORAGE', 'Storage / RAM'),
        ('SIZE', 'Size'),
        ('PACK', 'Pack'),
    ]

    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='variants')
    variant_type = models.CharField(max_length=20, choices=VARIANT_TYPES, default='COLOR')
    name = models.CharField(max_length=80)
    color_hex = models.CharField(max_length=16, blank=True)
    price_delta = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    stock = models.PositiveIntegerField(default=15)
    sku_suffix = models.CharField(max_length=30, blank=True)

    class Meta:
        ordering = ['variant_type', 'price_delta', 'id']

    def __str__(self):
        return f'{self.product.title} ({self.name})'

    @property
    def effective_price(self):
        return max(Decimal('1.00'), self.product.selling_price + self.price_delta)


class Banner(models.Model):
    """Promotional banners for homepage hero carousel and grid strips."""

    PLACEMENTS = [
        ('HERO', 'Hero Carousel'),
        ('MID_GRID', 'Mid Page 3-Card Strip'),
        ('BANK_OFFER', 'Bank & Wallet Strip'),
    ]

    title = models.CharField(max_length=160)
    subtitle = models.CharField(max_length=220, blank=True)
    badge_text = models.CharField(max_length=60, blank=True)
    cta_text = models.CharField(max_length=50, default='Shop Now')
    target_url = models.CharField(max_length=255, default='/products/')
    image_path = models.CharField(max_length=255, default='landingpage/images/banner-bigbillion.svg')
    bg_gradient = models.CharField(
        max_length=160,
        default='linear-gradient(135deg, #2874F0 0%, #1746A2 100%)',
    )
    placement = models.CharField(max_length=20, choices=PLACEMENTS, default='HERO')
    display_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['placement', 'display_order', 'id']

    def __str__(self):
        return f'[{self.placement}] {self.title}'


class Coupon(models.Model):
    """Discount coupon codes usable in Cart and Checkout."""

    DISCOUNT_TYPES = [
        ('PERCENT', 'Percentage'),
        ('FLAT', 'Flat Amount'),
    ]

    code = models.CharField(max_length=30, unique=True)
    title = models.CharField(max_length=140)
    description = models.CharField(max_length=255)
    discount_type = models.CharField(max_length=10, choices=DISCOUNT_TYPES, default='PERCENT')
    discount_value = models.DecimalField(max_digits=8, decimal_places=2)
    max_discount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('1500.00'))
    min_order_value = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('499.00'))
    is_plus_only = models.BooleanField(default=False)
    valid_until = models.DateTimeField()
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['min_order_value', 'code']

    def __str__(self):
        return self.code

    def is_valid_now(self):
        return self.is_active and self.valid_until >= timezone.now()

    def calculate_discount(self, subtotal, user=None):
        if not self.is_valid_now():
            return Decimal('0.00'), 'This coupon has expired or is inactive.'
        if subtotal < self.min_order_value:
            return Decimal('0.00'), f'Minimum order of ₹{int(self.min_order_value)} required.'
        if self.is_plus_only:
            is_plus = bool(user and user.is_authenticated and getattr(getattr(user, 'customer_profile', None), 'is_plus_member', False))
            if not is_plus:
                return Decimal('0.00'), 'This coupon is exclusive to Clickcart Plus members.'

        if self.discount_type == 'PERCENT':
            disc = (subtotal * self.discount_value) / Decimal('100')
            disc = min(disc, self.max_discount)
        else:
            disc = min(self.discount_value, subtotal)
        return round(disc, 2), f'Coupon {self.code} applied! You save ₹{int(round(disc))}.'


class PincodeServiceability(models.Model):
    """Pincode delivery estimate and COD availability lookup."""

    pincode = models.CharField(max_length=6, unique=True)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    delivery_days = models.PositiveIntegerField(default=2)
    cod_available = models.BooleanField(default=True)
    express_available = models.BooleanField(default=True)

    class Meta:
        verbose_name_plural = 'Pincode Serviceabilities'
        ordering = ['pincode']

    def __str__(self):
        return f'{self.pincode} - {self.city}, {self.state}'


class CartItem(models.Model):
    """Shopping cart and Saved-For-Later items supporting both session guests and logged-in users."""

    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name='cart_items')
    session_key = models.CharField(max_length=64, blank=True, db_index=True)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    variant = models.ForeignKey(ProductVariant, on_delete=models.SET_NULL, null=True, blank=True)
    quantity = models.PositiveIntegerField(default=1, validators=[MinValueValidator(1)])
    saved_for_later = models.BooleanField(default=False)
    with_exchange = models.BooleanField(default=False)
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-added_at']

    def __str__(self):
        return f'{self.product.title} x {self.quantity}'

    @property
    def available_stock(self):
        return self.variant.stock if self.variant else self.product.stock

    @property
    def unit_price(self):
        delta = self.variant.price_delta if self.variant else Decimal('0.00')
        return max(Decimal('1.00'), self.product.selling_price + delta)

    @property
    def unit_mrp(self):
        delta = self.variant.price_delta if (self.variant and self.variant.price_delta > 0) else Decimal('0.00')
        return max(self.unit_price, self.product.mrp + delta)

    @property
    def exchange_discount(self):
        if self.with_exchange and self.product.is_exchange_available:
            return min(self.product.max_exchange_discount, self.unit_price * Decimal('0.4'))
        return Decimal('0.00')

    @property
    def line_mrp_total(self):
        return self.unit_mrp * self.quantity

    @property
    def line_total(self):
        total = (self.unit_price * self.quantity) - self.exchange_discount
        return max(Decimal('0.00'), total)


class WishlistItem(models.Model):
    """User wishlist items."""

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='wishlist_items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='wishlisted_by')
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'product')
        ordering = ['-added_at']

    def __str__(self):
        return f'{self.user.username} - {self.product.title}'


class Order(models.Model):
    """Customer order with full Flipkart lifecycle states and pricing breakdown."""

    PAYMENT_METHODS = [
        ('UPI', 'UPI (PhonePe / GPay / Paytm)'),
        ('CARD', 'Credit / Debit / ATM Card'),
        ('NETBANKING', 'Net Banking'),
        ('EMI', 'Easy EMI'),
        ('WALLET', 'Clickcart Pay Later / Wallet'),
        ('COD', 'Cash on Delivery'),
    ]

    PAYMENT_STATUSES = [
        ('PENDING', 'Pending'),
        ('PAID', 'Paid'),
        ('REFUNDED', 'Refunded'),
    ]

    STATUS_CHOICES = [
        ('PLACED', 'Order Placed'),
        ('CONFIRMED', 'Confirmed'),
        ('PACKED', 'Packed'),
        ('SHIPPED', 'Shipped'),
        ('OUT_FOR_DELIVERY', 'Out for Delivery'),
        ('DELIVERED', 'Delivered'),
        ('CANCELLED', 'Cancelled'),
        ('RETURN_REQUESTED', 'Return Requested'),
        ('RETURNED', 'Returned'),
    ]

    order_number = models.CharField(max_length=32, unique=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='orders')
    shipping_name = models.CharField(max_length=120)
    shipping_phone = models.CharField(max_length=15)
    shipping_pincode = models.CharField(max_length=6)
    shipping_address = models.TextField()
    shipping_city = models.CharField(max_length=100)
    shipping_state = models.CharField(max_length=100)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHODS, default='UPI')
    payment_status = models.CharField(max_length=15, choices=PAYMENT_STATUSES, default='PAID')
    payment_ref = models.CharField(max_length=80, blank=True)

    subtotal = models.DecimalField(max_digits=10, decimal_places=2)
    product_discount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    coupon_code = models.CharField(max_length=30, blank=True)
    coupon_discount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    supercoins_used = models.PositiveIntegerField(default=0)
    supercoins_discount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    platform_fee = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal('3.00'))
    delivery_fee = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal('0.00'))
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    supercoins_earned = models.PositiveIntegerField(default=0)

    status = models.CharField(max_length=25, choices=STATUS_CHOICES, default='CONFIRMED')
    cancellation_reason = models.CharField(max_length=255, blank=True)
    return_reason = models.CharField(max_length=255, blank=True)
    estimated_delivery = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.order_number

    @property
    def status_step_index(self):
        mapping = {
            'PLACED': 0,
            'CONFIRMED': 1,
            'PACKED': 2,
            'SHIPPED': 3,
            'OUT_FOR_DELIVERY': 4,
            'DELIVERED': 5,
        }
        return mapping.get(self.status, -1)

    @property
    def can_cancel(self):
        return self.status in {'PLACED', 'CONFIRMED', 'PACKED', 'SHIPPED'}

    @property
    def can_return(self):
        return self.status == 'DELIVERED'


class OrderItem(models.Model):
    """Snapshot of a purchased product inside an Order."""

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True, related_name='order_items')
    seller = models.ForeignKey(SellerProfile, on_delete=models.SET_NULL, null=True, related_name='order_items')
    product_title = models.CharField(max_length=255)
    product_image = models.CharField(max_length=255, blank=True)
    variant_label = models.CharField(max_length=100, blank=True)
    unit_mrp = models.DecimalField(max_digits=10, decimal_places=2)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField(default=1)
    with_exchange = models.BooleanField(default=False)
    exchange_discount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    line_total = models.DecimalField(max_digits=10, decimal_places=2)
    item_status = models.CharField(max_length=25, choices=Order.STATUS_CHOICES, default='CONFIRMED')

    def __str__(self):
        return f'{self.order.order_number} - {self.product_title}'


class Review(models.Model):
    """Customer rating and review for a product."""

    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='reviews')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reviews')
    rating = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    title = models.CharField(max_length=120)
    comment = models.TextField()
    is_verified_purchase = models.BooleanField(default=False)
    helpful_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('product', 'user')
        ordering = ['-helpful_count', '-created_at']

    def __str__(self):
        return f'{self.product.title} ({self.rating}★ by {self.user.username})'


class ProductQuestion(models.Model):
    """Customer Q&A section on product detail page."""

    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='questions')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='product_questions')
    question = models.CharField(max_length=300)
    answer = models.TextField(blank=True)
    answered_by = models.CharField(max_length=120, blank=True)
    upvotes = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    answered_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-upvotes', '-created_at']

    def __str__(self):
        return self.question


class SuperCoinTransaction(models.Model):
    """Ledger of SuperCoins earned and redeemed."""

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='supercoin_transactions')
    amount = models.IntegerField()
    reason = models.CharField(max_length=200)
    order = models.ForeignKey(Order, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.user.username}: {self.amount:+d} ({self.reason})'


class Notification(models.Model):
    """In-app notifications for orders, deals, and SuperCoins."""

    CATEGORIES = [
        ('ORDER', 'Order Update'),
        ('OFFER', 'Exclusive Offer'),
        ('COIN', 'SuperCoins'),
        ('SYSTEM', 'System'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    title = models.CharField(max_length=150)
    message = models.TextField()
    category = models.CharField(max_length=15, choices=CATEGORIES, default='SYSTEM')
    link_url = models.CharField(max_length=255, blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.user.username} - {self.title}'


class SupportTicket(models.Model):
    """24x7 Customer Care support tickets."""

    TOPICS = [
        ('ORDER', 'Order & Delivery Issue'),
        ('RETURN', 'Return, Refund & Replacement'),
        ('PAYMENT', 'Payments, UPI & SuperCoins'),
        ('ACCOUNT', 'Account & Clickcart Plus'),
        ('SELLER', 'Seller & Listing Support'),
    ]

    STATUSES = [
        ('OPEN', 'Open'),
        ('IN_PROGRESS', 'In Progress'),
        ('RESOLVED', 'Resolved'),
    ]

    ticket_number = models.CharField(max_length=24, unique=True)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='support_tickets')
    email = models.EmailField()
    order_number = models.CharField(max_length=32, blank=True)
    topic = models.CharField(max_length=20, choices=TOPICS, default='ORDER')
    subject = models.CharField(max_length=180)
    message = models.TextField()
    status = models.CharField(max_length=20, choices=STATUSES, default='OPEN')
    admin_reply = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.ticket_number} - {self.subject}'


class RecentlyViewed(models.Model):
    """Tracks recently viewed products for personalized recommendations."""

    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name='recently_viewed')
    session_key = models.CharField(max_length=64, blank=True, db_index=True)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    viewed_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-viewed_at']

    def __str__(self):
        return f'{self.product.title} viewed at {self.viewed_at}'
