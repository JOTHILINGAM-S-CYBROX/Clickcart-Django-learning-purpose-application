from django.contrib import admin
from .models import (
    Address,
    Banner,
    Brand,
    CartItem,
    Category,
    Coupon,
    CustomerProfile,
    Notification,
    Order,
    OrderItem,
    PincodeServiceability,
    Product,
    ProductQuestion,
    ProductVariant,
    RecentlyViewed,
    Review,
    SellerProfile,
    SuperCoinTransaction,
    SupportTicket,
    WishlistItem,
)


class ProductVariantInline(admin.TabularInline):
    model = ProductVariant
    extra = 1


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ('product_title', 'variant_label', 'unit_price', 'quantity', 'line_total')


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'parent', 'display_order', 'is_featured')
    list_filter = ('is_featured', 'parent')
    search_fields = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}


@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_assured')
    search_fields = ('name',)
    prepopulated_fields = {'slug': ('name',)}


@admin.register(SellerProfile)
class SellerProfileAdmin(admin.ModelAdmin):
    list_display = ('store_name', 'user', 'pickup_pincode', 'rating', 'is_verified')
    list_filter = ('is_verified',)
    search_fields = ('store_name', 'user__username', 'gstin')


@admin.register(CustomerProfile)
class CustomerProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'phone', 'supercoins', 'is_plus_member', 'wallet_balance')
    list_filter = ('is_plus_member',)
    search_fields = ('user__username', 'user__email', 'phone')


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = (
        'title',
        'category',
        'brand',
        'selling_price',
        'mrp',
        'stock',
        'is_assured',
        'is_deal_of_day',
        'is_active',
    )
    list_filter = ('category', 'brand', 'is_assured', 'is_deal_of_day', 'is_trending', 'is_active')
    search_fields = ('title', 'sku', 'short_description')
    prepopulated_fields = {'slug': ('title',)}
    inlines = [ProductVariantInline]


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('order_number', 'user', 'total_amount', 'payment_method', 'payment_status', 'status', 'created_at')
    list_filter = ('status', 'payment_method', 'payment_status')
    search_fields = ('order_number', 'user__username', 'shipping_name', 'shipping_phone')
    inlines = [OrderItemInline]


@admin.register(Banner)
class BannerAdmin(admin.ModelAdmin):
    list_display = ('title', 'placement', 'display_order', 'is_active')
    list_filter = ('placement', 'is_active')


@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display = ('code', 'discount_type', 'discount_value', 'min_order_value', 'is_plus_only', 'valid_until', 'is_active')
    list_filter = ('discount_type', 'is_plus_only', 'is_active')
    search_fields = ('code', 'title')


@admin.register(PincodeServiceability)
class PincodeServiceabilityAdmin(admin.ModelAdmin):
    list_display = ('pincode', 'city', 'state', 'delivery_days', 'cod_available', 'express_available')
    search_fields = ('pincode', 'city', 'state')


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('product', 'user', 'rating', 'is_verified_purchase', 'created_at')
    list_filter = ('rating', 'is_verified_purchase')
    search_fields = ('product__title', 'user__username', 'title')


@admin.register(ProductQuestion)
class ProductQuestionAdmin(admin.ModelAdmin):
    list_display = ('product', 'user', 'question', 'answered_by', 'created_at')
    search_fields = ('product__title', 'question', 'answer')


@admin.register(SupportTicket)
class SupportTicketAdmin(admin.ModelAdmin):
    list_display = ('ticket_number', 'email', 'topic', 'subject', 'status', 'created_at')
    list_filter = ('topic', 'status')
    search_fields = ('ticket_number', 'email', 'subject', 'order_number')


admin.site.register(Address)
admin.site.register(CartItem)
admin.site.register(WishlistItem)
admin.site.register(SuperCoinTransaction)
admin.site.register(Notification)
admin.site.register(RecentlyViewed)
