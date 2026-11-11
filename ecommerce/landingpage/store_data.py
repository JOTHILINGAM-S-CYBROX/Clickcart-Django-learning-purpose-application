"""
DB-free in-memory store for Clickcart (Flipkart-featured e-commerce platform).
All catalog data, users, carts, wishlists, orders, reviews, Q&A, SuperCoins,
notifications, and support tickets live in-memory in a thread-safe store
so the application runs without any database or migrations.
"""

from datetime import date, datetime, timedelta
from decimal import Decimal
import copy
import threading
import uuid

STORE_LOCK = threading.RLock()

CATEGORIES = [
    {
        'name': 'Top Offers',
        'slug': 'top-offers',
        'icon_image': 'landingpage/images/cat-offers.svg',
        'tagline': 'Big Saving Deals & Steals',
    },
    {
        'name': 'Mobiles & Tablets',
        'slug': 'mobiles',
        'icon_image': 'landingpage/images/cat-mobiles.svg',
        'tagline': '5G Flagships & Tablets',
    },
    {
        'name': 'Electronics',
        'slug': 'electronics',
        'icon_image': 'landingpage/images/cat-electronics.svg',
        'tagline': 'Laptops, Audio & Cameras',
    },
    {
        'name': 'TVs & Appliances',
        'slug': 'appliances',
        'icon_image': 'landingpage/images/cat-appliances.svg',
        'tagline': '4K QLED TVs & Home Tech',
    },
    {
        'name': 'Fashion',
        'slug': 'fashion',
        'icon_image': 'landingpage/images/cat-fashion.svg',
        'tagline': 'Footwear, Apparel & Bags',
    },
    {
        'name': 'Beauty',
        'slug': 'beauty',
        'icon_image': 'landingpage/images/cat-beauty.svg',
        'tagline': 'Skincare & Grooming',
    },
    {
        'name': 'Home & Furniture',
        'slug': 'home-furniture',
        'icon_image': 'landingpage/images/cat-home.svg',
        'tagline': 'Sofas, Chairs & Kitchen',
    },
    {
        'name': 'Grocery',
        'slug': 'grocery',
        'icon_image': 'landingpage/images/cat-grocery.svg',
        'tagline': 'Daily Pantry Essentials',
    },
    {
        'name': 'Books & More',
        'slug': 'books-sports',
        'icon_image': 'landingpage/images/cat-sports.svg',
        'tagline': 'Bestsellers & Gear',
    },
]

CATEGORY_MAP = {c['slug']: c for c in CATEGORIES}

HERO_BANNERS = [
    {
        'id': 1,
        'title': 'BIG SAVING DAYS',
        'subtitle': 'Up to 75% Off on Smartphones, Laptops, TVs & Fashion',
        'badge_text': 'EXTRA 10% HDFC BANK DISCOUNT',
        'cta_text': 'Shop Top Deals',
        'target_url': '/products/?deal=1',
        'image_path': 'landingpage/images/banner-bigbillion.svg',
    },
    {
        'id': 2,
        'title': 'FLAGSHIP 5G FEST',
        'subtitle': 'iPhone 16 Pro, Galaxy S25 Ultra & OnePlus 13R with Exchange Bonus',
        'badge_text': 'UP TO ₹25,000 EXCHANGE BONUS',
        'cta_text': 'Explore Mobiles',
        'target_url': '/products/?category=mobiles',
        'image_path': 'landingpage/images/banner-mobiles.svg',
    },
    {
        'id': 3,
        'title': 'END OF SEASON FASHION',
        'subtitle': 'Min 50% Off on Sneakers, Denim Jackets, Kurtas & Handbags',
        'badge_text': 'CLICKCART ASSURED STYLES',
        'cta_text': 'Shop Fashion',
        'target_url': '/products/?category=fashion',
        'image_path': 'landingpage/images/banner-fashion.svg',
    },
    {
        'id': 4,
        'title': 'MEGA TECH UPGRADE',
        'subtitle': 'MacBook Air M3, Sony WH-1000XM5 & 4K QLED Smart TVs',
        'badge_text': 'NO-COST EMI STARTING ₹1,999/MO',
        'cta_text': 'Shop Electronics',
        'target_url': '/products/?category=electronics',
        'image_path': 'landingpage/images/banner-electronics.svg',
    },
]

BANK_OFFERS = [
    {
        'bank': 'HDFC Bank',
        'badge': '10% INSTANT DISCOUNT',
        'detail': 'Up to ₹1,750 off on Credit & Debit Card EMI transactions above ₹5,000',
        'color': '#1D4ED8',
    },
    {
        'bank': 'Axis Bank Clickcart Card',
        'badge': '5% UNLIMITED CASHBACK',
        'detail': 'Flat 5% cashback on all Clickcart purchases + ₹500 welcome voucher',
        'color': '#9D174D',
    },
    {
        'bank': 'Clickcart SuperCoins Pay',
        'badge': 'SAVE EXTRA WITH COINS',
        'detail': 'Redeem SuperCoins on every checkout & earn up to 100 coins per order',
        'color': '#B45309',
    },
]

COUPONS = [
    {
        'code': 'SAVE10',
        'title': '10% Instant Discount',
        'description': 'Get 10% off up to ₹1,500 on orders of ₹999 or more.',
        'discount_type': 'PERCENT',
        'discount_value': 10,
        'max_discount': 1500,
        'min_order_value': 999,
        'is_plus_only': False,
    },
    {
        'code': 'CLICK500',
        'title': 'Flat ₹500 Off',
        'description': 'Save flat ₹500 on orders above ₹4,999 across all categories.',
        'discount_type': 'FLAT',
        'discount_value': 500,
        'max_discount': 500,
        'min_order_value': 4999,
        'is_plus_only': False,
    },
    {
        'code': 'FIRST150',
        'title': 'Flat ₹150 Welcome Bonus',
        'description': 'Flat ₹150 off on minimum purchase of ₹499.',
        'discount_type': 'FLAT',
        'discount_value': 150,
        'max_discount': 150,
        'min_order_value': 499,
        'is_plus_only': False,
    },
    {
        'code': 'PLUS20',
        'title': 'Clickcart Plus Exclusive 20% Off',
        'description': 'Up to ₹2,500 off on orders ₹1,499+ exclusively for Plus members.',
        'discount_type': 'PERCENT',
        'discount_value': 20,
        'max_discount': 2500,
        'min_order_value': 1499,
        'is_plus_only': True,
    },
]

PINCODES = {
    '560001': {'city': 'Bengaluru', 'state': 'Karnataka', 'delivery_days': 1, 'cod_available': True, 'express': True},
    '641001': {'city': 'Coimbatore', 'state': 'Tamil Nadu', 'delivery_days': 2, 'cod_available': True, 'express': True},
    '600001': {'city': 'Chennai', 'state': 'Tamil Nadu', 'delivery_days': 1, 'cod_available': True, 'express': True},
    '400001': {'city': 'Mumbai', 'state': 'Maharashtra', 'delivery_days': 1, 'cod_available': True, 'express': True},
    '110001': {'city': 'New Delhi', 'state': 'Delhi', 'delivery_days': 1, 'cod_available': True, 'express': True},
    '500001': {'city': 'Hyderabad', 'state': 'Telangana', 'delivery_days': 2, 'cod_available': True, 'express': True},
    '700001': {'city': 'Kolkata', 'state': 'West Bengal', 'delivery_days': 2, 'cod_available': True, 'express': False},
    '411001': {'city': 'Pune', 'state': 'Maharashtra', 'delivery_days': 2, 'cod_available': True, 'express': True},
    '380001': {'city': 'Ahmedabad', 'state': 'Gujarat', 'delivery_days': 3, 'cod_available': True, 'express': False},
    '302001': {'city': 'Jaipur', 'state': 'Rajasthan', 'delivery_days': 3, 'cod_available': True, 'express': False},
}

REGION_HINTS = {
    '1': ('Delhi NCR', 'Delhi', 2),
    '2': ('Lucknow', 'Uttar Pradesh', 3),
    '3': ('Ahmedabad', 'Gujarat', 3),
    '4': ('Mumbai Metro', 'Maharashtra', 2),
    '5': ('Hyderabad', 'Telangana', 2),
    '6': ('Chennai / Coimbatore', 'Tamil Nadu', 2),
    '7': ('Kolkata', 'West Bengal', 3),
    '8': ('Patna', 'Bihar', 4),
}


def _make_variants(vtype, items):
    out = []
    for idx, item in enumerate(items, start=1):
        out.append({
            'id': idx,
            'variant_type': vtype,
            'name': item[0],
            'color_hex': item[1],
            'price_delta': item[2],
            'stock': item[3],
        })
    return out


def _initial_products():
    raw = [
        {
            'id': 1,
            'slug': 'apple-iphone-16-pro-128gb',
            'sku': 'CC-IPH16P',
            'title': 'Apple iPhone 16 Pro (Desert Titanium, 128 GB)',
            'brand': 'Apple',
            'category_slug': 'mobiles',
            'seller_name': 'SuperComNet Retail',
            'seller_rating': 4.8,
            'mrp': 119900,
            'selling_price': 109900,
            'stock': 18,
            'is_assured': True,
            'is_cod_available': False,
            'is_exchange_available': True,
            'max_exchange_discount': 25000,
            'warranty_summary': '1 Year Apple Care Official Brand Warranty',
            'return_policy_days': 7,
            'delivery_days': 1,
            'is_fast_delivery': True,
            'is_deal_of_day': True,
            'is_trending': True,
            'primary_image': 'landingpage/images/prod-iphone.svg',
            'gallery_images': [
                'landingpage/images/prod-iphone.svg',
                'landingpage/images/prod-pixel.svg',
                'landingpage/images/prod-galaxy.svg',
            ],
            'short_description': 'A18 Pro Chip, 48MP Fusion Camera, 120Hz ProMotion OLED Display & Grade 5 Titanium.',
            'description': 'Engineered with aerospace-grade titanium, iPhone 16 Pro packs the breakthrough A18 Pro chip, 4K 120fps Dolby Vision video capture, Camera Control button, and all-day battery life.',
            'highlights': [
                '128 GB ROM | Expandable up to 1 TB variant',
                '15.93 cm (6.3 inch) Super Retina XDR ProMotion Display',
                '48MP + 48MP + 12MP Triple Pro Camera | 12MP Front Camera',
                'A18 Pro Bionic 6-Core Processor with Hardware Ray Tracing',
                'USB-C with USB 3 transfer speeds & MagSafe 25W Wireless Charging',
            ],
            'specifications': {
                'Display': '6.3-inch LTPO Super Retina XDR OLED, 120Hz',
                'Processor': 'Apple A18 Pro (3nm)',
                'Rear Camera': '48MP Fusion + 48MP Ultra Wide + 12MP 5x Telephoto',
                'Battery & Charging': 'Up to 27 hrs video playback, USB-C Fast Charge',
                'Build & Water Resistance': 'Grade 5 Titanium, Ceramic Shield, IP68',
            },
            'variants': _make_variants('STORAGE', [
                ('128 GB · Desert Titanium', '#C4A484', 0, 18),
                ('256 GB · Natural Titanium', '#9CA3AF', 10000, 12),
                ('512 GB · Black Titanium', '#1E293B', 30000, 6),
            ]),
            'rating_avg': 4.8,
            'rating_count': 4280,
            'sold_count': 1520,
        },
        {
            'id': 2,
            'slug': 'samsung-galaxy-s25-ultra-5g',
            'sku': 'CC-S25U',
            'title': 'Samsung Galaxy S25 Ultra 5G (Titanium Blue, 256 GB, 12 GB RAM)',
            'brand': 'Samsung',
            'category_slug': 'mobiles',
            'seller_name': 'TrueCom Retail',
            'seller_rating': 4.7,
            'mrp': 129999,
            'selling_price': 107999,
            'stock': 22,
            'is_assured': True,
            'is_cod_available': True,
            'is_exchange_available': True,
            'max_exchange_discount': 24000,
            'warranty_summary': '1 Year Manufacturer Warranty for Device & 6 Months for In-Box Accessories',
            'return_policy_days': 7,
            'delivery_days': 1,
            'is_fast_delivery': True,
            'is_deal_of_day': True,
            'is_trending': True,
            'primary_image': 'landingpage/images/prod-galaxy.svg',
            'gallery_images': [
                'landingpage/images/prod-galaxy.svg',
                'landingpage/images/prod-iphone.svg',
            ],
            'short_description': '200MP Quad Tele Camera, Built-in S Pen, Snapdragon 8 Elite & Galaxy AI Suite.',
            'description': 'Experience flagship perfection with the Galaxy S25 Ultra featuring Gorilla Armor 2 anti-reflective display, built-in S Pen, 200MP pro-grade camera system, and 5000mAh fast charging battery.',
            'highlights': [
                '12 GB RAM | 256 GB Storage',
                '17.53 cm (6.9 inch) Quad HD+ Dynamic AMOLED 2X 120Hz',
                '200MP + 50MP + 50MP + 10MP | 12MP Front Camera',
                '5000 mAh Battery with 45W Super Fast Charging',
                'Integrated S Pen & Galaxy AI Live Translate',
            ],
            'specifications': {
                'Display': '6.9-inch QHD+ Dynamic AMOLED 2X, 2600 nits',
                'Processor': 'Snapdragon 8 Elite for Galaxy',
                'Battery': '5000 mAh, 45W Wired + 15W Wireless',
                'S Pen': 'Built-in Low Latency Stylus',
                'OS': 'Android 15 with One UI 7 (7 Years Updates)',
            },
            'variants': _make_variants('COLOR', [
                ('Titanium Silverblue', '#60A5FA', 0, 22),
                ('Titanium Black', '#0F172A', 0, 14),
                ('Titanium Gray (512GB)', '#6B7280', 12000, 9),
            ]),
            'rating_avg': 4.7,
            'rating_count': 3190,
            'sold_count': 980,
        },
        {
            'id': 3,
            'slug': 'oneplus-13r-5g-nebula-noir',
            'sku': 'CC-OP13R',
            'title': 'OnePlus 13R 5G (Nebula Noir, 256 GB, 12 GB RAM)',
            'brand': 'OnePlus',
            'category_slug': 'mobiles',
            'seller_name': 'Clickcart Official Retail',
            'seller_rating': 4.6,
            'mrp': 44999,
            'selling_price': 39999,
            'stock': 35,
            'is_assured': True,
            'is_cod_available': True,
            'is_exchange_available': True,
            'max_exchange_discount': 12000,
            'warranty_summary': '1 Year Manufacturer Warranty',
            'return_policy_days': 7,
            'delivery_days': 2,
            'is_fast_delivery': True,
            'is_deal_of_day': True,
            'is_trending': True,
            'primary_image': 'landingpage/images/prod-oneplus.svg',
            'gallery_images': [
                'landingpage/images/prod-oneplus.svg',
                'landingpage/images/prod-pixel.svg',
            ],
            'short_description': '6000mAh Silicon-Carbon Battery, 80W SUPERVOOC, Snapdragon 8 Gen 3 & 1.5K ProXDR.',
            'description': 'Flagship speed meets marathon endurance. The OnePlus 13R delivers ultra-smooth 120Hz LTPO visuals, 50MP Sony LYT-700 OIS main camera, and a massive 6000mAh battery.',
            'highlights': [
                '12 GB LPDDR5X RAM | 256 GB UFS 4.0 ROM',
                '17.22 cm (6.78 inch) 1.5K 120Hz ProXDR Display',
                '50MP Sony OIS + 50MP Telephoto + 8MP Ultra Wide',
                '6000 mAh Battery with 80W SUPERVOOC Charger in Box',
            ],
            'specifications': {
                'Processor': 'Snapdragon 8 Gen 3 Mobile Platform',
                'Battery': '6000 mAh with 80W Fast Charger',
                'Display': '6.78-inch LTPO 4.1 AMOLED, 4500 nits peak',
                'Connectivity': 'Dual 5G SIM, Wi-Fi 7, IR Blaster',
            },
            'variants': _make_variants('STORAGE', [
                ('12GB / 256GB · Nebula Noir', '#1F2937', 0, 35),
                ('16GB / 512GB · Astral Trail', '#E5E7EB', 5000, 16),
            ]),
            'rating_avg': 4.6,
            'rating_count': 2850,
            'sold_count': 1840,
        },
        {
            'id': 4,
            'slug': 'google-pixel-9-obsidian',
            'sku': 'CC-PIX9',
            'title': 'Google Pixel 9 5G (Obsidian, 256 GB, 12 GB RAM)',
            'brand': 'Google',
            'category_slug': 'mobiles',
            'seller_name': 'SuperComNet Retail',
            'seller_rating': 4.7,
            'mrp': 79999,
            'selling_price': 67999,
            'stock': 14,
            'is_assured': True,
            'is_cod_available': True,
            'is_exchange_available': True,
            'max_exchange_discount': 18000,
            'warranty_summary': '1 Year Google India Warranty',
            'return_policy_days': 7,
            'delivery_days': 2,
            'is_fast_delivery': True,
            'is_deal_of_day': False,
            'is_trending': True,
            'primary_image': 'landingpage/images/prod-pixel.svg',
            'gallery_images': [
                'landingpage/images/prod-pixel.svg',
                'landingpage/images/prod-iphone.svg',
            ],
            'short_description': 'Google Tensor G4, Gemini Built-in, Actua Display & 50MP Octa PD Camera.',
            'description': 'Designed for effortless AI productivity and iconic photography, Google Pixel 9 combines Magic Editor, Add Me, Best Take, and 7 years of Pixel Drops.',
            'highlights': [
                '12 GB RAM | 256 GB Storage',
                '6.3-inch Actua OLED 120Hz Display',
                '50MP Wide + 48MP Ultrawide Rear Camera',
                'Google Tensor G4 with Titan M2 Security',
            ],
            'specifications': {
                'Processor': 'Google Tensor G4',
                'Display': '6.3-inch OLED, Gorilla Glass Victus 2',
                'Battery': '4700 mAh, Fast Wireless Charging',
                'Software': '7 Years OS & Security Updates',
            },
            'variants': _make_variants('COLOR', [
                ('Obsidian', '#111827', 0, 14),
                ('Porcelain', '#F3F4F6', 0, 10),
                ('Peony Pink', '#F472B6', 1000, 8),
            ]),
            'rating_avg': 4.5,
            'rating_count': 1430,
            'sold_count': 610,
        },
        {
            'id': 5,
            'slug': 'apple-macbook-air-m3-13-inch',
            'sku': 'CC-MBAM3',
            'title': 'Apple MacBook Air M3 (13.6 inch, 16 GB RAM, 256 GB SSD, Midnight)',
            'brand': 'Apple',
            'category_slug': 'electronics',
            'seller_name': 'Apple Authorized Retail',
            'seller_rating': 4.9,
            'mrp': 114900,
            'selling_price': 97990,
            'stock': 15,
            'is_assured': True,
            'is_cod_available': False,
            'is_exchange_available': True,
            'max_exchange_discount': 20000,
            'warranty_summary': '1 Year Apple Limited Warranty',
            'return_policy_days': 7,
            'delivery_days': 2,
            'is_fast_delivery': True,
            'is_deal_of_day': True,
            'is_trending': True,
            'primary_image': 'landingpage/images/prod-macbook.svg',
            'gallery_images': ['landingpage/images/prod-macbook.svg', 'landingpage/images/prod-ipad.svg'],
            'short_description': 'Supercharged by Apple M3, 18-Hour Battery, Liquid Retina Display & Fanless Design.',
            'description': 'Blazing fast and whisper-quiet, the 13.6-inch MacBook Air with M3 chip and 16GB unified memory handles coding, 4K editing, and multitasking effortlessly.',
            'highlights': [
                'Apple M3 8-Core CPU & 8-Core GPU',
                '16 GB Unified Memory | 256 GB NVMe SSD',
                '13.6-inch Liquid Retina Display with True Tone',
                'MagSafe 3 Charging + 2x Thunderbolt Ports + 1080p FaceTime HD',
            ],
            'specifications': {
                'Processor': 'Apple M3 Chip (16-core Neural Engine)',
                'Memory & Storage': '16 GB Unified RAM | 256 GB SSD',
                'Weight': '1.24 kg Ultra-Thin Aluminum Unibody',
                'Battery Life': 'Up to 18 Hours Wireless Web',
            },
            'variants': _make_variants('COLOR', [
                ('Midnight · 256GB', '#1E293B', 0, 15),
                ('Starlight · 512GB', '#E5E7EB', 18000, 9),
                ('Space Gray · 256GB', '#64748B', 0, 11),
            ]),
            'rating_avg': 4.9,
            'rating_count': 2140,
            'sold_count': 870,
        },
        {
            'id': 6,
            'slug': 'asus-rog-strix-g16-rtx4060',
            'sku': 'CC-ROG16',
            'title': 'ASUS ROG Strix G16 Intel Core i7 13th Gen (16 GB/1 TB SSD/RTX 4060 8 GB)',
            'brand': 'ASUS',
            'category_slug': 'electronics',
            'seller_name': 'OmniTech Retail',
            'seller_rating': 4.6,
            'mrp': 143990,
            'selling_price': 114990,
            'stock': 10,
            'is_assured': True,
            'is_cod_available': True,
            'is_exchange_available': True,
            'max_exchange_discount': 18000,
            'warranty_summary': '1 Year Onsite Warranty',
            'return_policy_days': 7,
            'delivery_days': 2,
            'is_fast_delivery': True,
            'is_deal_of_day': False,
            'is_trending': True,
            'primary_image': 'landingpage/images/prod-asus.svg',
            'gallery_images': ['landingpage/images/prod-asus.svg', 'landingpage/images/prod-macbook.svg'],
            'short_description': '16-inch FHD+ 165Hz ROG Nebula Display, Tri-Fan Cooling & NVIDIA RTX 4060.',
            'description': 'Built for esports and heavy creative rendering, featuring Intel Core i7-13650HX, MUX Switch with NVIDIA Advanced Optimus, and Per-Key RGB keyboard.',
            'highlights': [
                'Intel Core i7-13650HX (14 Cores, up to 4.9 GHz)',
                'NVIDIA GeForce RTX 4060 8 GB GDDR6 (140W TGP)',
                '16 GB DDR5 RAM | 1 TB PCIe 4.0 SSD',
                '16-inch 165Hz 100% sRGB Dolby Vision Display',
            ],
            'specifications': {
                'CPU': 'Intel Core i7 13th Gen 13650HX',
                'GPU': 'NVIDIA RTX 4060 8GB GDDR6',
                'Cooling': 'Tri-Fan Liquid Metal Thermal Grizzly',
                'Battery': '90Wh 4-Cell Fast Charge',
            },
            'variants': _make_variants('STORAGE', [
                ('16GB / 1TB SSD · Eclipse Gray', '#27272A', 0, 10),
                ('32GB / 1TB SSD · Volt Green', '#16A34A', 9000, 5),
            ]),
            'rating_avg': 4.6,
            'rating_count': 890,
            'sold_count': 410,
        },
        {
            'id': 7,
            'slug': 'sony-wh-1000xm5-anc-headphones',
            'sku': 'CC-SONYXM5',
            'title': 'SONY WH-1000XM5 Wireless Industry Leading Noise Cancelling Headphones',
            'brand': 'Sony',
            'category_slug': 'electronics',
            'seller_name': 'Clickcart Official Retail',
            'seller_rating': 4.8,
            'mrp': 34990,
            'selling_price': 24990,
            'stock': 28,
            'is_assured': True,
            'is_cod_available': True,
            'is_exchange_available': False,
            'max_exchange_discount': 0,
            'warranty_summary': '1 Year Sony India Warranty',
            'return_policy_days': 7,
            'delivery_days': 1,
            'is_fast_delivery': True,
            'is_deal_of_day': True,
            'is_trending': True,
            'primary_image': 'landingpage/images/prod-sony-wh.svg',
            'gallery_images': ['landingpage/images/prod-sony-wh.svg'],
            'short_description': '8 Microphones ANC, 30 Hours Battery, Multipoint Bluetooth 5.2 & LDAC Hi-Res Audio.',
            'description': 'Powered by two processors controlling eight microphones, the Sony WH-1000XM5 delivers crystal-clear call quality and unrivaled noise cancellation.',
            'highlights': [
                'Best-in-Class Multi-Microphone Active Noise Cancellation',
                'Up to 30 Hours Playback | 3 Min Charge = 3 Hours Playback',
                'Ultra-lightweight Soft Fit Leather Earcups',
                'Multipoint Connection (Pair 2 Devices Simultaneously)',
            ],
            'specifications': {
                'Driver Unit': '30mm Precision Carbon Fiber Dome',
                'Bluetooth': 'v5.2 with LDAC, AAC, SBC',
                'Battery Life': '30 Hours (ANC ON) / 40 Hours (ANC OFF)',
                'Weight': '250 g',
            },
            'variants': _make_variants('COLOR', [
                ('Midnight Black', '#0F172A', 0, 28),
                ('Platinum Silver', '#CBD5E1', 0, 19),
                ('Smoky Pink', '#EC4899', 500, 12),
            ]),
            'rating_avg': 4.7,
            'rating_count': 3640,
            'sold_count': 2100,
        },
        {
            'id': 8,
            'slug': 'apple-ipad-air-m2-11-inch',
            'sku': 'CC-IPADM2',
            'title': 'Apple iPad Air M2 (11 inch, 128 GB, Wi-Fi, Blue)',
            'brand': 'Apple',
            'category_slug': 'mobiles',
            'seller_name': 'Apple Authorized Retail',
            'seller_rating': 4.8,
            'mrp': 59900,
            'selling_price': 54900,
            'stock': 20,
            'is_assured': True,
            'is_cod_available': True,
            'is_exchange_available': True,
            'max_exchange_discount': 15000,
            'warranty_summary': '1 Year Apple Warranty',
            'return_policy_days': 7,
            'delivery_days': 2,
            'is_fast_delivery': True,
            'is_deal_of_day': False,
            'is_trending': False,
            'primary_image': 'landingpage/images/prod-ipad.svg',
            'gallery_images': ['landingpage/images/prod-ipad.svg'],
            'short_description': 'Apple M2 Chip, Landscape 12MP Ultra Wide Camera & Apple Pencil Pro Support.',
            'description': 'Designed for creators, students, and mobile pros with a bright 11-inch Liquid Retina display, Wi-Fi 6E, and desktop-class M2 performance.',
            'highlights': [
                '11-inch Liquid Retina P3 Wide Color Display',
                'Apple M2 8-Core CPU & 9-Core GPU',
                'Supports Apple Pencil Pro & Magic Keyboard',
                'Touch ID in Top Button & All-Day Battery',
            ],
            'specifications': {
                'Display': '11-inch IPS Liquid Retina',
                'Chip': 'Apple M2',
                'Storage': '128 GB',
                'Connectivity': 'Wi-Fi 6E, USB-C',
            },
            'variants': _make_variants('STORAGE', [
                ('128 GB · Blue', '#3B82F6', 0, 20),
                ('256 GB · Space Gray', '#475569', 10000, 11),
            ]),
            'rating_avg': 4.8,
            'rating_count': 1120,
            'sold_count': 540,
        },
        {
            'id': 9,
            'slug': 'samsung-galaxy-watch-7-44mm',
            'sku': 'CC-GW7',
            'title': 'Samsung Galaxy Watch 7 (44mm, Bluetooth + AI Health, Green)',
            'brand': 'Samsung',
            'category_slug': 'electronics',
            'seller_name': 'TrueCom Retail',
            'seller_rating': 4.6,
            'mrp': 32999,
            'selling_price': 24999,
            'stock': 30,
            'is_assured': True,
            'is_cod_available': True,
            'is_exchange_available': False,
            'max_exchange_discount': 0,
            'warranty_summary': '1 Year Samsung India Warranty',
            'return_policy_days': 7,
            'delivery_days': 2,
            'is_fast_delivery': True,
            'is_deal_of_day': False,
            'is_trending': True,
            'primary_image': 'landingpage/images/prod-watch.svg',
            'gallery_images': ['landingpage/images/prod-watch.svg'],
            'short_description': '3nm Exynos W1000 Processor, Dual-Frequency GPS, Sapphire Crystal & Energy Score.',
            'description': 'Track sleep apnea, heart rate zones, and body composition with Samsung BioActive Sensor and Galaxy AI insights.',
            'highlights': [
                'Sapphire Crystal Super AMOLED Display',
                '3nm Penta-Core Processor for Ultra-Smooth Wear OS',
                'Dual-Frequency GPS (L1+L5) & 5ATM + IP68 Waterproof',
            ],
            'specifications': {
                'Case Size': '44mm Armor Aluminum',
                'Display': '1.5-inch Super AMOLED',
                'Sensors': 'BioActive ECG, BIA, SpO2, Skin Temp',
                'Water Rating': '5ATM + IP68',
            },
            'variants': _make_variants('SIZE', [
                ('44mm · Green', '#15803D', 0, 30),
                ('40mm · Cream', '#F5F5F4', -2000, 18),
            ]),
            'rating_avg': 4.5,
            'rating_count': 740,
            'sold_count': 390,
        },
        {
            'id': 10,
            'slug': 'canon-eos-r50-mirrorless-camera',
            'sku': 'CC-CANR50',
            'title': 'Canon EOS R50 Mirrorless Camera with RF-S 18-45mm f/4.5-6.3 IS STM Kit',
            'brand': 'Canon',
            'category_slug': 'electronics',
            'seller_name': 'PhotoMart Pro',
            'seller_rating': 4.7,
            'mrp': 75995,
            'selling_price': 61990,
            'stock': 9,
            'is_assured': True,
            'is_cod_available': True,
            'is_exchange_available': False,
            'max_exchange_discount': 0,
            'warranty_summary': '2 Years Canon India Warranty',
            'return_policy_days': 7,
            'delivery_days': 3,
            'is_fast_delivery': False,
            'is_deal_of_day': False,
            'is_trending': False,
            'primary_image': 'landingpage/images/prod-canon.svg',
            'gallery_images': ['landingpage/images/prod-canon.svg'],
            'short_description': '24.2MP APS-C CMOS Sensor, 4K 30p Oversampled Video & Dual Pixel CMOS AF II.',
            'description': 'Compact mirrorless powerhouse built for vloggers and photographers with subject detection autofocus and vari-angle touchscreen.',
            'highlights': [
                '24.2MP APS-C CMOS Sensor + DIGIC X Processor',
                '4K UHD 30p Video (Oversampled from 6K)',
                '15 fps Electronic Shutter Continuous Shooting',
                'Includes RF-S 18-45mm IS STM Kit Lens',
            ],
            'specifications': {
                'Sensor': '24.2MP APS-C CMOS',
                'Autofocus': 'Dual Pixel CMOS AF II (651 Zones)',
                'Video': '4K 30p / FHD 120p',
                'Weight': '375 g (Body Only)',
            },
            'variants': _make_variants('COLOR', [
                ('Black Kit (18-45mm)', '#111827', 0, 9),
                ('White Kit (18-45mm)', '#F8FAFC', 1000, 4),
            ]),
            'rating_avg': 4.7,
            'rating_count': 410,
            'sold_count': 220,
        },
        {
            'id': 11,
            'slug': 'samsung-55-inch-4k-qled-smart-tv',
            'sku': 'CC-TV55Q',
            'title': 'Samsung 138 cm (55 inch) QLED 4K Ultra HD Smart Tizen TV (Dolby Atmos)',
            'brand': 'Samsung',
            'category_slug': 'appliances',
            'seller_name': 'OmniTech Retail',
            'seller_rating': 4.6,
            'mrp': 89900,
            'selling_price': 54990,
            'stock': 12,
            'is_assured': True,
            'is_cod_available': False,
            'is_exchange_available': True,
            'max_exchange_discount': 8000,
            'warranty_summary': '2 Years Comprehensive Panel Warranty',
            'return_policy_days': 10,
            'delivery_days': 3,
            'is_fast_delivery': False,
            'is_deal_of_day': True,
            'is_trending': True,
            'primary_image': 'landingpage/images/prod-tv.svg',
            'gallery_images': ['landingpage/images/prod-tv.svg'],
            'short_description': '100% Color Volume Quantum Dot, Quantum Processor Lite 4K & AirSlim Design.',
            'description': 'Transform your living room into a cinema with crisp 4K QLED colors, Q-Symphony sound, and built-in Netflix, Prime Video, and JioCinema apps.',
            'highlights': [
                '3840 x 2160 4K Ultra HD QLED Display',
                '40W Object Tracking Sound Lite + Dolby Digital Plus',
                '3 HDMI Ports & 2 USB Ports | SolarCell Remote',
                'Free Wall-Mount Installation within 48 Hours',
            ],
            'specifications': {
                'Screen Size': '55 inch (138 cm) AirSlim',
                'Resolution': '4K Ultra HD (3840 x 2160)',
                'Refresh Rate': '60Hz Motion Xcelerator',
                'Smart OS': 'Samsung Tizen OS with Built-in Alexa',
            },
            'variants': _make_variants('SIZE', [
                ('55 inch (138 cm)', '#1E293B', 0, 12),
                ('43 inch (108 cm)', '#334155', -14000, 18),
                ('65 inch (163 cm)', '#0F172A', 24000, 6),
            ]),
            'rating_avg': 4.6,
            'rating_count': 1980,
            'sold_count': 860,
        },
        {
            'id': 12,
            'slug': 'lg-322l-convertible-frost-free-refrigerator',
            'sku': 'CC-LGREF322',
            'title': 'LG 322 L Frost Free Double Door 3 Star Convertible Refrigerator (Shiny Steel)',
            'brand': 'LG',
            'category_slug': 'appliances',
            'seller_name': 'OmniTech Retail',
            'seller_rating': 4.5,
            'mrp': 46999,
            'selling_price': 34490,
            'stock': 16,
            'is_assured': True,
            'is_cod_available': True,
            'is_exchange_available': True,
            'max_exchange_discount': 6000,
            'warranty_summary': '1 Year Product & 10 Years Compressor Warranty',
            'return_policy_days': 10,
            'delivery_days': 3,
            'is_fast_delivery': False,
            'is_deal_of_day': False,
            'is_trending': False,
            'primary_image': 'landingpage/images/prod-fridge.svg',
            'gallery_images': ['landingpage/images/prod-fridge.svg'],
            'short_description': 'Smart Inverter Compressor, Convertible Freezer-to-Fridge & Door Cooling+.',
            'description': 'Designed for modern Indian families with uniform Door Cooling+, toughened glass shelves, and Auto Smart Connect to home inverter.',
            'highlights': [
                '322 L Capacity: Ideal for 3–5 Member Families',
                'Smart Inverter Compressor for Silent Energy Efficiency',
                'Stabilizer-Free Operation (100V–310V)',
            ],
            'specifications': {
                'Capacity': '322 Litres',
                'Energy Rating': '3 Star BEE',
                'Compressor': 'Smart Inverter Compressor',
                'Type': 'Frost Free Double Door Convertible',
            },
            'variants': _make_variants('COLOR', [
                ('Shiny Steel', '#94A3B8', 0, 16),
                ('Dazzle Steel', '#475569', 1500, 9),
            ]),
            'rating_avg': 4.5,
            'rating_count': 1240,
            'sold_count': 630,
        },
        {
            'id': 13,
            'slug': 'bosch-7kg-ai-front-load-washer',
            'sku': 'CC-BOSCH7',
            'title': 'Bosch 7 kg 5 Star AI ActiveWater Plus Front Load Washing Machine with Built-in Heater',
            'brand': 'Bosch',
            'category_slug': 'appliances',
            'seller_name': 'SuperComNet Retail',
            'seller_rating': 4.7,
            'mrp': 43990,
            'selling_price': 29990,
            'stock': 14,
            'is_assured': True,
            'is_cod_available': True,
            'is_exchange_available': True,
            'max_exchange_discount': 4500,
            'warranty_summary': '2 Years Comprehensive & 12 Years Motor Warranty',
            'return_policy_days': 10,
            'delivery_days': 3,
            'is_fast_delivery': False,
            'is_deal_of_day': False,
            'is_trending': True,
            'primary_image': 'landingpage/images/prod-washer.svg',
            'gallery_images': ['landingpage/images/prod-washer.svg'],
            'short_description': 'Anti-Stain Hygiene Steam, 1200 RPM EcoSilence Drive & SpeedPerfect Wash.',
            'description': 'German-engineered washing performance that removes 99.9% bacteria using Anti-Bacteria Steam while cutting wash time by up to 65%.',
            'highlights': [
                '7 kg Fully Automatic Front Load | 1200 RPM Spin',
                'In-Built Water Heater + Anti-Tangle SoftCare Drum',
                'Reload Function to Add Forgotten Clothes Mid-Wash',
            ],
            'specifications': {
                'Capacity': '7 kg',
                'Energy Rating': '5 Star',
                'Max Spin Speed': '1200 RPM',
                'Motor': 'EcoSilence Drive Brushless Motor',
            },
            'variants': _make_variants('SIZE', [
                ('7 kg · Classic White', '#F8FAFC', 0, 14),
                ('8 kg · Silver Inox', '#94A3B8', 4500, 8),
            ]),
            'rating_avg': 4.6,
            'rating_count': 1670,
            'sold_count': 710,
        },
        {
            'id': 14,
            'slug': 'lg-1-5-ton-5-star-ai-dual-inverter-ac',
            'sku': 'CC-LGAC15',
            'title': 'LG 1.5 Ton 5 Star AI Dual Inverter Split AC (Copper, 6-in-1 Convertible, 2025 Model)',
            'brand': 'LG',
            'category_slug': 'appliances',
            'seller_name': 'OmniTech Retail',
            'seller_rating': 4.6,
            'mrp': 85990,
            'selling_price': 44990,
            'stock': 19,
            'is_assured': True,
            'is_cod_available': False,
            'is_exchange_available': True,
            'max_exchange_discount': 6000,
            'warranty_summary': '1 Year Product, 5 Years PCB & 10 Years Compressor Warranty',
            'return_policy_days': 10,
            'delivery_days': 2,
            'is_fast_delivery': True,
            'is_deal_of_day': True,
            'is_trending': True,
            'primary_image': 'landingpage/images/prod-ac.svg',
            'gallery_images': ['landingpage/images/prod-ac.svg'],
            'short_description': 'VIRAAT Mode 110% Cooling, HD Filter with Anti-Virus & 100% Copper Condenser.',
            'description': 'Beat peak Indian summers at 55°C ambient temperatures with AI Convertible 6-in-1 cooling and Ocean Black Fin anti-corrosion protection.',
            'highlights': [
                '1.5 Ton 5 Star BEE 2025 Rating (Saves up to 25% Power)',
                '100% Copper Condenser with Ocean Black Fin Protection',
                '4-Way Air Swing & Low Noise 26 dB Sleep Mode',
            ],
            'specifications': {
                'Capacity': '1.5 Ton (Up to 180 sq.ft)',
                'Energy Rating': '5 Star ISEER 5.20',
                'Condenser': '100% Copper',
                'Refrigerant': 'Eco-Friendly R-32',
            },
            'variants': _make_variants('SIZE', [
                ('1.5 Ton · 5 Star', '#E0F2FE', 0, 19),
                ('1.0 Ton · 5 Star', '#F0F9FF', -7000, 11),
            ]),
            'rating_avg': 4.6,
            'rating_count': 2340,
            'sold_count': 1150,
        },
        {
            'id': 15,
            'slug': 'nike-air-zoom-pegasus-41-running-shoes',
            'sku': 'CC-NIKEP41',
            'title': 'NIKE Air Zoom Pegasus 41 Men Running Shoes (Volt Orange / White)',
            'brand': 'Nike',
            'category_slug': 'fashion',
            'seller_name': 'Wizrob Fashion',
            'seller_rating': 4.5,
            'mrp': 11895,
            'selling_price': 7499,
            'stock': 42,
            'is_assured': True,
            'is_cod_available': True,
            'is_exchange_available': False,
            'max_exchange_discount': 0,
            'warranty_summary': '90 Days Brand Manufacturing Warranty',
            'return_policy_days': 14,
            'delivery_days': 2,
            'is_fast_delivery': True,
            'is_deal_of_day': True,
            'is_trending': True,
            'primary_image': 'landingpage/images/prod-nike.svg',
            'gallery_images': ['landingpage/images/prod-nike.svg'],
            'short_description': 'ReactX Foam Midsole + Dual Air Zoom Units for Responsive Daily Mileage.',
            'description': 'Experience energized return on every stride with lightweight engineered mesh upper, ReactX cushioning, and signature waffle rubber traction.',
            'highlights': [
                'Dual Air Zoom Units (Forefoot & Heel)',
                'Breathable Engineered Mesh Upper',
                '13% More Responsive ReactX Midsole Foam',
            ],
            'specifications': {
                'Outer Material': 'Engineered Breathable Mesh',
                'Sole Material': 'Waffle Traction Rubber',
                'Closure': 'Lace-Up',
                'Occasion': 'Running & Gym Training',
            },
            'variants': _make_variants('SIZE', [
                ('UK 7', '#EA580C', 0, 10),
                ('UK 8', '#EA580C', 0, 14),
                ('UK 9', '#EA580C', 0, 12),
                ('UK 10', '#EA580C', 0, 6),
            ]),
            'rating_avg': 4.5,
            'rating_count': 1840,
            'sold_count': 1420,
        },
        {
            'id': 16,
            'slug': 'levis-iconic-slim-fit-denim-jacket',
            'sku': 'CC-LEVIJKT',
            'title': "Levi's Men Solid Slim-Fit Indigo Trucker Denim Jacket",
            'brand': "Levi's",
            'category_slug': 'fashion',
            'seller_name': 'Wizrob Fashion',
            'seller_rating': 4.4,
            'mrp': 5599,
            'selling_price': 2699,
            'stock': 50,
            'is_assured': True,
            'is_cod_available': True,
            'is_exchange_available': False,
            'max_exchange_discount': 0,
            'warranty_summary': 'No Warranty (14 Days Easy Size Exchange)',
            'return_policy_days': 14,
            'delivery_days': 2,
            'is_fast_delivery': True,
            'is_deal_of_day': False,
            'is_trending': True,
            'primary_image': 'landingpage/images/prod-jacket.svg',
            'gallery_images': ['landingpage/images/prod-jacket.svg'],
            'short_description': '100% Cotton Non-Stretch Authentic Trucker Denim with Metal Shank Buttons.',
            'description': "Timeless layering staple from Levi's featuring twin chest flap pockets, adjustable waist tabs, and durable double-stitched seams.",
            'highlights': [
                '100% Pure Cotton Heavyweight Denim',
                'Classic Point Collar & Full Button Placket',
                'Machine Wash Cold Inside-Out',
            ],
            'specifications': {
                'Fabric': '100% Cotton Denim',
                'Fit': 'Regular / Slim Trucker Fit',
                'Pattern': 'Solid Indigo Wash',
                'Sleeves': 'Full Sleeve',
            },
            'variants': _make_variants('SIZE', [
                ('M (Chest 40)', '#1E3A8A', 0, 18),
                ('L (Chest 42)', '#1E3A8A', 0, 20),
                ('XL (Chest 44)', '#1E3A8A', 0, 12),
            ]),
            'rating_avg': 4.4,
            'rating_count': 2590,
            'sold_count': 1950,
        },
        {
            'id': 17,
            'slug': 'biba-embroidered-festive-kurta-set',
            'sku': 'CC-BIBAKUR',
            'title': 'BIBA Women Floral Embroidered Chanderi Kurta, Palazzo & Dupatta Set',
            'brand': 'BIBA',
            'category_slug': 'fashion',
            'seller_name': 'Ethnic Elegance',
            'seller_rating': 4.5,
            'mrp': 4999,
            'selling_price': 1999,
            'stock': 38,
            'is_assured': True,
            'is_cod_available': True,
            'is_exchange_available': False,
            'max_exchange_discount': 0,
            'warranty_summary': '14 Days Easy Return & Size Exchange',
            'return_policy_days': 14,
            'delivery_days': 2,
            'is_fast_delivery': True,
            'is_deal_of_day': True,
            'is_trending': False,
            'primary_image': 'landingpage/images/prod-kurta.svg',
            'gallery_images': ['landingpage/images/prod-kurta.svg'],
            'short_description': 'Breathable Cotton-Silk Chanderi Blend with Zari Embroidery & Organza Dupatta.',
            'description': 'Graceful festive three-piece ensemble tailored for weddings, Diwali, and celebrations with intricate yoke embroidery.',
            'highlights': [
                '3-Piece Set: Straight Kurta + Wide Palazzo + Printed Dupatta',
                'Soft Cotton Lining for All-Day Comfort',
                'Intricate Zari & Thread Yoke Embroidery',
            ],
            'specifications': {
                'Fabric': 'Chanderi Silk Blend with Cotton Lining',
                'Color': 'Magenta Rose & Gold',
                'Occasion': 'Festive & Party Wear',
                'Care': 'Gentle Hand Wash',
            },
            'variants': _make_variants('SIZE', [
                ('S', '#BE185D', 0, 10),
                ('M', '#BE185D', 0, 15),
                ('L', '#BE185D', 0, 13),
            ]),
            'rating_avg': 4.5,
            'rating_count': 1480,
            'sold_count': 1120,
        },
        {
            'id': 18,
            'slug': 'allen-solly-structured-tote-handbag',
            'sku': 'CC-ASTOTE',
            'title': 'Allen Solly Women Structured Textured Tote Handbag (Tan Brown)',
            'brand': 'Allen Solly',
            'category_slug': 'fashion',
            'seller_name': 'Wizrob Fashion',
            'seller_rating': 4.3,
            'mrp': 3499,
            'selling_price': 1449,
            'stock': 45,
            'is_assured': True,
            'is_cod_available': True,
            'is_exchange_available': False,
            'max_exchange_discount': 0,
            'warranty_summary': '6 Months Manufacturer Warranty',
            'return_policy_days': 14,
            'delivery_days': 2,
            'is_fast_delivery': True,
            'is_deal_of_day': False,
            'is_trending': False,
            'primary_image': 'landingpage/images/prod-handbag.svg',
            'gallery_images': ['landingpage/images/prod-handbag.svg'],
            'short_description': 'Spacious 14-inch Laptop-Friendly Office Tote with Zip Closure & Inner Organizers.',
            'description': 'Crafted from premium cruelty-free pebbled faux leather, this structured tote effortlessly carries work essentials in style.',
            'highlights': [
                'Fits up to 14-inch Laptop + Notebook + Pouch',
                '3 Internal Compartments + Quick-Access Zip Pocket',
                'Gold-Tone Hardware & Reinforced Shoulder Straps',
            ],
            'specifications': {
                'Material': 'Premium Textured Vegan Leather',
                'Closure': 'Top Zip Closure',
                'Dimensions': '38 x 14 x 29 cm',
            },
            'variants': _make_variants('COLOR', [
                ('Cognac Tan', '#92400E', 0, 45),
                ('Classic Black', '#111827', 100, 22),
            ]),
            'rating_avg': 4.3,
            'rating_count': 960,
            'sold_count': 780,
        },
        {
            'id': 19,
            'slug': 'wakefit-3-seater-fabric-sofa-teal',
            'sku': 'CC-WKSOFA',
            'title': 'Wakefit Napper 3 Seater Fabric Sofa (Emerald Teal, Solid Pine Frame)',
            'brand': 'Wakefit',
            'category_slug': 'home-furniture',
            'seller_name': 'Wakefit Home Official',
            'seller_rating': 4.6,
            'mrp': 29999,
            'selling_price': 18499,
            'stock': 8,
            'is_assured': True,
            'is_cod_available': False,
            'is_exchange_available': False,
            'max_exchange_discount': 0,
            'warranty_summary': '3 Years Manufacturer Warranty on Frame & Foam',
            'return_policy_days': 10,
            'delivery_days': 5,
            'is_fast_delivery': False,
            'is_deal_of_day': False,
            'is_trending': True,
            'primary_image': 'landingpage/images/prod-sofa.svg',
            'gallery_images': ['landingpage/images/prod-sofa.svg'],
            'short_description': 'High-Density 32-ILD Foam Cushions, 400 GSM Upholstery & Free Carpenter Installation.',
            'description': 'Engineered for zero sagging over years of family lounging, featuring kiln-dried pine wood and stain-resistant fabric.',
            'highlights': [
                '32-ILD High-Resilience Multi-Layer Cushioning',
                'Kiln-Dried Pine Wood Frame (Termite Resistant)',
                'Free Delivery & Carpenter Assembly Included',
            ],
            'specifications': {
                'Seating Capacity': '3 Seater',
                'Frame Material': 'Solid Pine Wood',
                'Upholstery': '400 GSM Breathable Polyester',
                'Dimensions': '198 x 81 x 86 cm',
            },
            'variants': _make_variants('COLOR', [
                ('Emerald Teal', '#0F766E', 0, 8),
                ('Charcoal Gray', '#374151', 0, 12),
            ]),
            'rating_avg': 4.6,
            'rating_count': 1320,
            'sold_count': 490,
        },
        {
            'id': 20,
            'slug': 'greensoul-ergonomic-mesh-office-chair',
            'sku': 'CC-GSCHAIR',
            'title': 'Green Soul Zodiac Pro High-Back Ergonomic Mesh Office Chair (2D Lumbar Support)',
            'brand': 'Green Soul',
            'category_slug': 'home-furniture',
            'seller_name': 'Green Soul Official',
            'seller_rating': 4.5,
            'mrp': 18990,
            'selling_price': 8499,
            'stock': 24,
            'is_assured': True,
            'is_cod_available': True,
            'is_exchange_available': False,
            'max_exchange_discount': 0,
            'warranty_summary': '3 Years Warranty on Hydraulics & Base',
            'return_policy_days': 10,
            'delivery_days': 3,
            'is_fast_delivery': True,
            'is_deal_of_day': True,
            'is_trending': True,
            'primary_image': 'landingpage/images/prod-chair.svg',
            'gallery_images': ['landingpage/images/prod-chair.svg'],
            'short_description': 'Breathable Korean Mesh, 135° Synchro Tilt Lock & Adjustable Headrest + Armrests.',
            'description': 'Designed for 8+ hour WFH and coding sessions with dynamic lumbar spine support and heavy-duty Class-4 gas lift.',
            'highlights': [
                'Adjustable Headrest, 2D Armrests & Lumbar Pillow',
                'BIFMA Certified Class-4 Gas Lift (Up to 125 kg)',
                '135° Recline with Multi-Position Tilt Lock',
            ],
            'specifications': {
                'Back Material': 'Breathable Korean Nylon Mesh',
                'Max Weight': '125 kg',
                'Base': 'Heavy-Duty Metal Wheel Base',
                'Assembly': '15-Minute DIY Kit Included',
            },
            'variants': _make_variants('COLOR', [
                ('All Black', '#0F172A', 0, 24),
                ('Slate Grey', '#64748B', 300, 14),
            ]),
            'rating_avg': 4.5,
            'rating_count': 2910,
            'sold_count': 1640,
        },
        {
            'id': 21,
            'slug': 'preethi-zodiac-mg218-750w-mixer-grinder',
            'sku': 'CC-PREETHI',
            'title': 'Preethi Zodiac MG-218 750W Mixer Grinder with Master Chef Food Processor Jar (5 Jars)',
            'brand': 'Preethi',
            'category_slug': 'home-furniture',
            'seller_name': 'Clickcart Official Retail',
            'seller_rating': 4.7,
            'mrp': 11950,
            'selling_price': 6499,
            'stock': 32,
            'is_assured': True,
            'is_cod_available': True,
            'is_exchange_available': False,
            'max_exchange_discount': 0,
            'warranty_summary': '2 Years Product & 5 Years Vega W5 Motor Warranty',
            'return_policy_days': 7,
            'delivery_days': 2,
            'is_fast_delivery': True,
            'is_deal_of_day': False,
            'is_trending': False,
            'primary_image': 'landingpage/images/prod-mixer.svg',
            'gallery_images': ['landingpage/images/prod-mixer.svg'],
            'short_description': 'Grinds Turmeric in 2 Mins, Kneads Atta in 1 Min + 3-in-1 Fresh Juicer Jar.',
            'description': 'India’s trusted heavy-duty kitchen companion with Vega W5 750W motor, 5 versatile stainless steel & polycarbonate jars, and safety indicator.',
            'highlights': [
                '750W Vega W5 Motor (Tested for 2150 Hours Continuous Run)',
                'Includes 5 Jars: 1.5L, 1.0L, 0.5L, Juicer & Food Processor',
                'Kneads Dough, Chops, Slices, Grates & Juices',
            ],
            'specifications': {
                'Power': '750 Watts',
                'Jars Included': '5 Jars',
                'Speed Settings': '3 Speed + Pulse',
                'Safety': 'Overload Protector & Safety Lock',
            },
            'variants': _make_variants('PACK', [
                ('5 Jars · Black/Red', '#DC2626', 0, 32),
            ]),
            'rating_avg': 4.6,
            'rating_count': 5420,
            'sold_count': 3100,
        },
        {
            'id': 22,
            'slug': 'minimalist-10-vitamin-c-face-serum',
            'sku': 'CC-MINVITC',
            'title': 'Minimalist 10% Vitamin C + Acetyl Glucosamine Face Serum for Glowing Skin (30 ml)',
            'brand': 'Minimalist',
            'category_slug': 'beauty',
            'seller_name': 'Clickcart Beauty Hub',
            'seller_rating': 4.7,
            'mrp': 699,
            'selling_price': 549,
            'stock': 85,
            'is_assured': True,
            'is_cod_available': True,
            'is_exchange_available': False,
            'max_exchange_discount': 0,
            'warranty_summary': 'Dermatologically Tested · 24 Months Shelf Life',
            'return_policy_days': 7,
            'delivery_days': 1,
            'is_fast_delivery': True,
            'is_deal_of_day': False,
            'is_trending': True,
            'primary_image': 'landingpage/images/prod-serum.svg',
            'gallery_images': ['landingpage/images/prod-serum.svg'],
            'short_description': 'Stable Ethyl Ascorbic Acid 10% for Brightening, Dark Spot Reduction & Fragrance-Free Care.',
            'description': 'Formulated with stable 10% Ethyl Ascorbic Acid (86% pure Vitamin C) and 1% Acetyl Glucosamine to boost radiance without irritation.',
            'highlights': [
                'Fragrance-Free, Paraben-Free & Non-Comedogenic',
                'Visibly Reduces Dullness & Pigmentation in 4 Weeks',
                'Suitable for All Skin Types (Daily AM/PM)',
            ],
            'specifications': {
                'Volume': '30 ml Dropper Bottle',
                'Key Actives': '10% Ethyl Ascorbic Acid + Centella Water',
                'Skin Type': 'Normal, Oily, Dry & Sensitive',
            },
            'variants': _make_variants('PACK', [
                ('30 ml Single Bottle', '#9333EA', 0, 85),
                ('Pack of 2 (60 ml)', '#7E22CE', 450, 40),
            ]),
            'rating_avg': 4.6,
            'rating_count': 12450,
            'sold_count': 6800,
        },
        {
            'id': 23,
            'slug': 'tata-sampann-organic-almonds-pulses-combo',
            'sku': 'CC-GROC5KG',
            'title': 'Tata Sampann California Almonds & Unpolished Organic Pantry Combo (2 kg Pack)',
            'brand': 'Tata Sampann',
            'category_slug': 'grocery',
            'seller_name': 'Clickcart Supermart',
            'seller_rating': 4.8,
            'mrp': 1499,
            'selling_price': 949,
            'stock': 64,
            'is_assured': True,
            'is_cod_available': True,
            'is_exchange_available': False,
            'max_exchange_discount': 0,
            'warranty_summary': '9 Months Best Before · Fresh Harvest Batch',
            'return_policy_days': 3,
            'delivery_days': 1,
            'is_fast_delivery': True,
            'is_deal_of_day': True,
            'is_trending': False,
            'primary_image': 'landingpage/images/prod-grocery.svg',
            'gallery_images': ['landingpage/images/prod-grocery.svg'],
            'short_description': '100% Pure Unpolished Pulses & Premium Crunch California Almonds Value Saver Pack.',
            'description': 'Curated daily essentials pack with zero artificial polish, rich natural protein, and airtight resealable freshness pouches.',
            'highlights': [
                'Includes 500g Premium Almonds + 1.5kg Unpolished Toor & Moong Dal',
                'Hygienically Packed with Zero Additives',
                'Next-Day Morning Grocery Delivery Available',
            ],
            'specifications': {
                'Total Net Weight': '2 kg',
                'Diet Type': '100% Vegetarian',
                'Shelf Life': '9 Months',
            },
            'variants': _make_variants('PACK', [
                ('2 kg Saver Combo', '#15803D', 0, 64),
                ('4 kg Family Mega Pack', '#166534', 820, 28),
            ]),
            'rating_avg': 4.7,
            'rating_count': 4120,
            'sold_count': 2890,
        },
        {
            'id': 24,
            'slug': 'atomic-habits-james-clear-paperback',
            'sku': 'CC-BOOKAH',
            'title': 'Atomic Habits by James Clear (International Bestseller Paperback Edition)',
            'brand': 'Penguin',
            'category_slug': 'books-sports',
            'seller_name': 'BookWorld India',
            'seller_rating': 4.8,
            'mrp': 799,
            'selling_price': 419,
            'stock': 120,
            'is_assured': True,
            'is_cod_available': True,
            'is_exchange_available': False,
            'max_exchange_discount': 0,
            'warranty_summary': 'Original Genuine Publisher Print Guaranteed',
            'return_policy_days': 7,
            'delivery_days': 1,
            'is_fast_delivery': True,
            'is_deal_of_day': False,
            'is_trending': True,
            'primary_image': 'landingpage/images/prod-book.svg',
            'gallery_images': ['landingpage/images/prod-book.svg'],
            'short_description': 'An Easy & Proven Way to Build Good Habits & Break Bad Ones — Over 20M Copies Sold.',
            'description': 'Transform your daily routines with tiny 1% improvements. James Clear distills practical neuroscience and behavioral psychology into an actionable framework.',
            'highlights': [
                'Author: James Clear | Publisher: Penguin Random House',
                '320 Pages · Crisp White Authentic Print',
                'Includes Free Clickcart Bookmark',
            ],
            'specifications': {
                'Language': 'English',
                'Binding': 'Paperback (320 Pages)',
                'ISBN-13': '9781847941831',
            },
            'variants': _make_variants('PACK', [
                ('Paperback Edition', '#1E3A8A', 0, 120),
                ('Hardcover Collector Edition', '#0F172A', 350, 35),
            ]),
            'rating_avg': 4.9,
            'rating_count': 18600,
            'sold_count': 9400,
        },
    ]

    for p in raw:
        p['category_name'] = CATEGORY_MAP[p['category_slug']]['name']
        p['reviews'] = [
            {
                'id': p['id'] * 100 + 1,
                'user_name': 'Karthik R.',
                'rating': 5,
                'title': 'Worth every rupee! Genuine & super fast delivery',
                'comment': f"Ordered {p['title'][:40]} during the sale and received it in original sealed packaging. Performance and build quality exceeded expectations.",
                'is_verified_purchase': True,
                'helpful_count': 42,
                'created_at': '3 days ago',
            },
            {
                'id': p['id'] * 100 + 2,
                'user_name': 'Sneha Nair',
                'rating': 4,
                'title': 'Great value with Clickcart Bank Offer',
                'comment': 'Smooth checkout experience and timely delivery. Saved extra using instant bank discount and SuperCoins.',
                'is_verified_purchase': True,
                'helpful_count': 19,
                'created_at': '1 week ago',
            },
        ]
        p['questions'] = [
            {
                'id': p['id'] * 100 + 1,
                'user_name': 'Vikram S.',
                'question': 'Is this an original brand warranty product with GST invoice?',
                'answer': f"Yes! Sold by {p['seller_name']} with 100% genuine brand seal, GST tax invoice, and {p['warranty_summary']}.",
                'answered_by': p['seller_name'],
                'upvotes': 27,
            },
            {
                'id': p['id'] * 100 + 2,
                'user_name': 'Ananya M.',
                'question': 'Is Cash on Delivery and easy replacement available?',
                'answer': f"Easy {p['return_policy_days']}-day replacement is available. COD depends on your delivery pincode.",
                'answered_by': 'Clickcart Support',
                'upvotes': 14,
            },
        ]
    return raw


def enrich_product(p):
    """Return product dict copy with computed properties for templates."""
    mrp = int(p['mrp'])
    sp = int(p['selling_price'])
    disc = int(round(((mrp - sp) / mrp) * 100)) if mrp > sp and mrp > 0 else 0
    coins = min(100, max(2, (sp // 100) * 2))
    emi = max(99, int(round(sp / 12)))
    est_date = (date.today() + timedelta(days=int(p.get('delivery_days', 2)))).strftime('%a, %d %b')

    reviews = p.get('reviews', [])
    counts = {5: 0, 4: 0, 3: 0, 2: 0, 1: 0}
    for r in reviews:
        counts[max(1, min(5, int(r['rating'])))] += 1
    total_rev = max(1, len(reviews))
    breakdown = [
        {'star': star, 'count': counts[star], 'pct': int(round((counts[star] / total_rev) * 100))}
        for star in (5, 4, 3, 2, 1)
    ]

    p['discount_percent'] = disc
    p['savings_amount'] = max(0, mrp - sp)
    p['supercoins_reward'] = coins
    p['emi_per_month'] = emi
    p['estimated_delivery_str'] = est_date
    p['rating_breakdown'] = breakdown
    p['highlights_list'] = p.get('highlights', [])
    return p


class MemoryStore:
    def __init__(self):
        self.products = _initial_products()
        self.next_product_id = len(self.products) + 1
        self.next_review_id = 9000
        self.next_question_id = 9000
        self.next_ticket_id = 1001

        # Users keyed by email (lowercase)
        self.users = {
            'aarav@clickcart.in': {
                'id': 'u-aarav',
                'name': 'Aarav Sharma',
                'email': 'aarav@clickcart.in',
                'password': 'click123',
                'phone': '9876543210',
                'gender': 'M',
                'is_plus_member': False,
                'is_seller': False,
                'store_name': '',
                'supercoins': 85,
                'wallet_balance': 3500,
                'addresses': [
                    {
                        'id': 'addr-1',
                        'full_name': 'Aarav Sharma',
                        'phone': '9876543210',
                        'pincode': '560001',
                        'locality': 'MG Road, Indiranagar',
                        'street_address': '42, 12th Main Road, HAL 2nd Stage',
                        'city': 'Bengaluru',
                        'state': 'Karnataka',
                        'landmark': 'Near Metro Station',
                        'address_type': 'HOME',
                        'is_default': True,
                    },
                    {
                        'id': 'addr-2',
                        'full_name': 'Aarav Sharma (Office)',
                        'phone': '9876543210',
                        'pincode': '641001',
                        'locality': 'Race Course Road',
                        'street_address': 'Tech Park Tower B, 4th Floor',
                        'city': 'Coimbatore',
                        'state': 'Tamil Nadu',
                        'landmark': 'Opposite Cosmopolitan Club',
                        'address_type': 'WORK',
                        'is_default': False,
                    },
                ],
                'cart': [],
                'saved_for_later': [],
                'wishlist': [1, 7],
                'compare': [],
                'recently_viewed': [1, 5, 15],
                'applied_coupon': '',
                'use_supercoins': False,
                'orders': [
                    {
                        'order_number': 'CC-20261108-7842',
                        'created_at': '08 Nov 2026, 02:15 PM',
                        'status': 'SHIPPED',
                        'payment_method': 'UPI',
                        'payment_status': 'PAID',
                        'shipping_name': 'Aarav Sharma',
                        'shipping_phone': '9876543210',
                        'shipping_pincode': '560001',
                        'shipping_address': '42, 12th Main Road, HAL 2nd Stage, MG Road, Indiranagar',
                        'shipping_city': 'Bengaluru',
                        'shipping_state': 'Karnataka',
                        'subtotal': 24990,
                        'product_discount': 10000,
                        'coupon_code': 'SAVE10',
                        'coupon_discount': 1500,
                        'supercoins_used': 0,
                        'supercoins_discount': 0,
                        'platform_fee': 3,
                        'delivery_fee': 0,
                        'total_amount': 23493,
                        'supercoins_earned': 50,
                        'estimated_delivery': (date.today() + timedelta(days=1)).strftime('%a, %d %b %Y'),
                        'cancellation_reason': '',
                        'return_reason': '',
                        'items': [
                            {
                                'product_id': 7,
                                'title': 'SONY WH-1000XM5 Wireless Industry Leading Noise Cancelling Headphones',
                                'image': 'landingpage/images/prod-sony-wh.svg',
                                'variant_label': 'Midnight Black',
                                'unit_mrp': 34990,
                                'unit_price': 24990,
                                'quantity': 1,
                                'with_exchange': False,
                                'exchange_discount': 0,
                                'line_total': 24990,
                            }
                        ],
                    },
                    {
                        'order_number': 'CC-20261022-4190',
                        'created_at': '22 Oct 2026, 11:40 AM',
                        'status': 'DELIVERED',
                        'payment_method': 'CARD',
                        'payment_status': 'PAID',
                        'shipping_name': 'Aarav Sharma',
                        'shipping_phone': '9876543210',
                        'shipping_pincode': '560001',
                        'shipping_address': '42, 12th Main Road, HAL 2nd Stage, MG Road, Indiranagar',
                        'shipping_city': 'Bengaluru',
                        'shipping_state': 'Karnataka',
                        'subtotal': 419,
                        'product_discount': 380,
                        'coupon_code': '',
                        'coupon_discount': 0,
                        'supercoins_used': 0,
                        'supercoins_discount': 0,
                        'platform_fee': 3,
                        'delivery_fee': 40,
                        'total_amount': 462,
                        'supercoins_earned': 8,
                        'estimated_delivery': 'Delivered on 24 Oct 2026',
                        'cancellation_reason': '',
                        'return_reason': '',
                        'items': [
                            {
                                'product_id': 24,
                                'title': 'Atomic Habits by James Clear (International Bestseller Paperback Edition)',
                                'image': 'landingpage/images/prod-book.svg',
                                'variant_label': 'Paperback Edition',
                                'unit_mrp': 799,
                                'unit_price': 419,
                                'quantity': 1,
                                'with_exchange': False,
                                'exchange_discount': 0,
                                'line_total': 419,
                            }
                        ],
                    },
                ],
                'coin_transactions': [
                    {'amount': 50, 'reason': 'Order Reward #CC-20261108-7842', 'date': '08 Nov 2026'},
                    {'amount': 35, 'reason': 'Welcome & First Order SuperCoins Bonus', 'date': '22 Oct 2026'},
                ],
                'notifications': [
                    {
                        'id': 'n-1',
                        'title': 'Order Shipped: SONY WH-1000XM5',
                        'message': 'Your order #CC-20261108-7842 is out from Bengaluru Hub and arrives tomorrow.',
                        'category': 'ORDER',
                        'link_url': '/orders/CC-20261108-7842/',
                        'is_read': False,
                        'created_at': '2 hours ago',
                    },
                    {
                        'id': 'n-2',
                        'title': 'Big Saving Days Live Now!',
                        'message': 'Use code SAVE10 for extra 10% instant discount across Mobiles, Tech & Fashion.',
                        'category': 'OFFER',
                        'link_url': '/products/?deal=1',
                        'is_read': False,
                        'created_at': 'Today, 10:00 AM',
                    },
                ],
                'tickets': [
                    {
                        'ticket_number': 'TKT-1000',
                        'topic': 'ORDER',
                        'order_number': 'CC-20261022-4190',
                        'subject': 'GST Invoice Copy Request',
                        'message': 'Please share downloadable tax invoice for my book order.',
                        'status': 'RESOLVED',
                        'reply': 'You can view and print your GST tax invoice directly from Order Details > Tax Invoice.',
                        'created_at': '25 Oct 2026',
                    }
                ],
            },
            'priya@clickcart.in': {
                'id': 'u-priya',
                'name': 'Priya Menon',
                'email': 'priya@clickcart.in',
                'password': 'click123',
                'phone': '9845012345',
                'gender': 'F',
                'is_plus_member': True,
                'is_seller': False,
                'store_name': '',
                'supercoins': 240,
                'wallet_balance': 8500,
                'addresses': [
                    {
                        'id': 'addr-p1',
                        'full_name': 'Priya Menon',
                        'phone': '9845012345',
                        'pincode': '600001',
                        'locality': 'Anna Nagar West',
                        'street_address': '18, 2nd Avenue, Block C',
                        'city': 'Chennai',
                        'state': 'Tamil Nadu',
                        'landmark': 'Near Tower Park',
                        'address_type': 'HOME',
                        'is_default': True,
                    }
                ],
                'cart': [],
                'saved_for_later': [],
                'wishlist': [2, 17],
                'compare': [],
                'recently_viewed': [2, 17, 22],
                'applied_coupon': '',
                'use_supercoins': False,
                'orders': [],
                'coin_transactions': [
                    {'amount': 240, 'reason': 'Clickcart Plus Loyalty Tier Balance', 'date': '01 Nov 2026'},
                ],
                'notifications': [
                    {
                        'id': 'n-p1',
                        'title': 'Clickcart Plus Active: Free Priority Delivery',
                        'message': 'Enjoy zero shipping fees and exclusive PLUS20 coupon (20% off)!',
                        'category': 'COIN',
                        'link_url': '/plus/',
                        'is_read': False,
                        'created_at': 'Yesterday',
                    }
                ],
                'tickets': [],
            },
            'seller@clickcart.in': {
                'id': 'u-seller',
                'name': 'SuperComNet Seller',
                'email': 'seller@clickcart.in',
                'password': 'click123',
                'phone': '9900112233',
                'gender': 'O',
                'is_plus_member': True,
                'is_seller': True,
                'store_name': 'SuperComNet Retail',
                'supercoins': 150,
                'wallet_balance': 15000,
                'addresses': [
                    {
                        'id': 'addr-s1',
                        'full_name': 'SuperComNet Hub',
                        'phone': '9900112233',
                        'pincode': '560001',
                        'locality': 'Whitefield Industrial Area',
                        'street_address': 'Plot 14, EPIP Zone',
                        'city': 'Bengaluru',
                        'state': 'Karnataka',
                        'landmark': 'Near ITPL Gate 2',
                        'address_type': 'WORK',
                        'is_default': True,
                    }
                ],
                'cart': [],
                'saved_for_later': [],
                'wishlist': [],
                'compare': [],
                'recently_viewed': [],
                'applied_coupon': '',
                'use_supercoins': False,
                'orders': [],
                'coin_transactions': [],
                'notifications': [],
                'tickets': [],
            },
        }
        self.guests = {}

    def get_guest_bucket(self, visitor_id):
        if visitor_id not in self.guests:
            self.guests[visitor_id] = {
                'id': visitor_id,
                'name': 'Guest Shopper',
                'email': '',
                'phone': '',
                'gender': '',
                'is_authenticated': False,
                'is_plus_member': False,
                'is_seller': False,
                'store_name': '',
                'supercoins': 0,
                'wallet_balance': 0,
                'addresses': [],
                'cart': [],
                'saved_for_later': [],
                'wishlist': [],
                'compare': [],
                'recently_viewed': [],
                'applied_coupon': '',
                'use_supercoins': False,
                'orders': [],
                'coin_transactions': [],
                'notifications': [
                    {
                        'id': 'n-g1',
                        'title': 'Welcome to Clickcart!',
                        'message': 'Sign in with Demo Account (aarav@clickcart.in) to access SuperCoins, Wallet & Saved Orders.',
                        'category': 'SYSTEM',
                        'link_url': '/login/',
                        'is_read': False,
                        'created_at': 'Just now',
                    }
                ],
                'tickets': [],
            }
        return self.guests[visitor_id]


STORE = MemoryStore()

ORDER_FLOW = ['PLACED', 'CONFIRMED', 'PACKED', 'SHIPPED', 'OUT_FOR_DELIVERY', 'DELIVERED']


def get_visitor_id(request):
    vid = request.session.get('cc_visitor_id')
    if not vid:
        vid = f'guest-{uuid.uuid4().hex[:10]}'
        request.session['cc_visitor_id'] = vid
    return vid


def get_active_account(request):
    """Return active user dict (logged-in user or guest bucket) + auth flag."""
    with STORE_LOCK:
        email = request.session.get('cc_user_email')
        if email and email in STORE.users:
            u = STORE.users[email]
            u['is_authenticated'] = True
            return u
        vid = get_visitor_id(request)
        return STORE.get_guest_bucket(vid)


def get_all_products():
    with STORE_LOCK:
        return [enrich_product(copy.deepcopy(p)) for p in STORE.products]


def get_product_by_id(pid):
    with STORE_LOCK:
        for p in STORE.products:
            if p['id'] == int(pid):
                return enrich_product(copy.deepcopy(p))
    return None


def get_product_by_slug(slug):
    with STORE_LOCK:
        for p in STORE.products:
            if p['slug'] == slug:
                return enrich_product(copy.deepcopy(p))
    return None


def lookup_pincode(pincode_str):
    code = (pincode_str or '').strip()
    if len(code) != 6 or not code.isdigit() or code[0] in ('0', '9'):
        return None
    if code in PINCODES:
        info = dict(PINCODES[code])
        info['pincode'] = code
    else:
        city, state, days = REGION_HINTS.get(code[0], ('Metro City', 'India', 3))
        info = {
            'pincode': code,
            'city': city,
            'state': state,
            'delivery_days': days,
            'cod_available': True,
            'express': days <= 2,
        }
    info['estimated_date'] = (date.today() + timedelta(days=info['delivery_days'])).strftime('%a, %d %b')
    return info


def compute_cart_summary(account):
    """Compute live cart items and Flipkart-style price breakdown."""
    with STORE_LOCK:
        prod_map = {p['id']: p for p in STORE.products}
        items = []
        total_mrp = 0
        subtotal = 0
        total_exchange = 0
        total_qty = 0

        for entry in account['cart']:
            prod = prod_map.get(entry['product_id'])
            if not prod:
                continue
            variant = None
            delta = 0
            variant_label = ''
            if entry.get('variant_id'):
                for v in prod.get('variants', []):
                    if v['id'] == entry['variant_id']:
                        variant = v
                        delta = int(v['price_delta'])
                        variant_label = v['name']
                        break

            unit_price = max(1, int(prod['selling_price']) + delta)
            unit_mrp = max(unit_price, int(prod['mrp']) + max(0, delta))
            qty = max(1, int(entry.get('quantity', 1)))
            with_exch = bool(entry.get('with_exchange')) and prod.get('is_exchange_available', False)
            exch_disc = min(int(prod.get('max_exchange_discount', 0)), int(unit_price * 0.4)) if with_exch else 0

            line_mrp = unit_mrp * qty
            line_sub = unit_price * qty
            line_total = max(0, line_sub - exch_disc)

            total_mrp += line_mrp
            subtotal += line_total
            total_exchange += exch_disc
            total_qty += qty

            items.append({
                'item_id': entry['item_id'],
                'product': enrich_product(copy.deepcopy(prod)),
                'variant': variant,
                'variant_label': variant_label,
                'quantity': qty,
                'with_exchange': with_exch,
                'exchange_discount': exch_disc,
                'unit_price': unit_price,
                'unit_mrp': unit_mrp,
                'line_mrp': line_mrp,
                'line_total': line_total,
                'available_stock': variant['stock'] if variant else prod['stock'],
            })

        saved_items = []
        for entry in account['saved_for_later']:
            prod = prod_map.get(entry['product_id'])
            if prod:
                variant_label = ''
                delta = 0
                if entry.get('variant_id'):
                    for v in prod.get('variants', []):
                        if v['id'] == entry['variant_id']:
                            variant_label = v['name']
                            delta = int(v['price_delta'])
                            break
                saved_items.append({
                    'item_id': entry['item_id'],
                    'product': enrich_product(copy.deepcopy(prod)),
                    'variant_label': variant_label,
                    'unit_price': max(1, int(prod['selling_price']) + delta),
                })

        product_discount = max(0, total_mrp - (subtotal + total_exchange))

        # Coupon calculation
        coupon_code = account.get('applied_coupon', '').strip().upper()
        coupon_discount = 0
        coupon_msg = ''
        if coupon_code and subtotal > 0:
            matched = next((c for c in COUPONS if c['code'] == coupon_code), None)
            if not matched:
                coupon_msg = 'Invalid coupon code.'
                account['applied_coupon'] = ''
                coupon_code = ''
            elif subtotal < matched['min_order_value']:
                coupon_msg = f"Add ₹{matched['min_order_value'] - subtotal} more to use {coupon_code}."
                account['applied_coupon'] = ''
                coupon_code = ''
            elif matched['is_plus_only'] and not account.get('is_plus_member'):
                coupon_msg = f"{coupon_code} is exclusive to Clickcart Plus members."
                account['applied_coupon'] = ''
                coupon_code = ''
            else:
                if matched['discount_type'] == 'PERCENT':
                    coupon_discount = min(matched['max_discount'], int(round((subtotal * matched['discount_value']) / 100)))
                else:
                    coupon_discount = min(matched['discount_value'], subtotal)
                coupon_msg = f"Coupon {coupon_code} applied! Saved ₹{coupon_discount}."

        # SuperCoins redemption (1 coin = ₹1, up to 10% of payable or balance)
        coins_used = 0
        coins_discount = 0
        if account.get('use_supercoins') and account.get('supercoins', 0) > 0 and subtotal > 0:
            max_redeem = min(int(account['supercoins']), max(0, int((subtotal - coupon_discount) * 0.1)))
            if max_redeem > 0:
                coins_used = max_redeem
                coins_discount = max_redeem

        platform_fee = 3 if items else 0
        is_free_delivery = (not items) or account.get('is_plus_member') or subtotal >= 499
        delivery_fee = 0 if is_free_delivery else 40
        payable_total = max(0, subtotal - coupon_discount - coins_discount + platform_fee + delivery_fee)
        total_savings = product_discount + total_exchange + coupon_discount + coins_discount
        coins_to_earn = min(100, max(2, (payable_total // 100) * (4 if account.get('is_plus_member') else 2))) if items else 0

        return {
            'items': items,
            'saved_items': saved_items,
            'item_count': total_qty,
            'total_mrp': total_mrp,
            'subtotal': subtotal,
            'product_discount': product_discount,
            'exchange_discount': total_exchange,
            'coupon_code': coupon_code,
            'coupon_discount': coupon_discount,
            'coupon_msg': coupon_msg,
            'supercoins_used': coins_used,
            'supercoins_discount': coins_discount,
            'platform_fee': platform_fee,
            'delivery_fee': delivery_fee,
            'payable_total': payable_total,
            'total_savings': total_savings,
            'coins_to_earn': coins_to_earn,
        }


def add_item_to_cart(account, product_id, variant_id=None, quantity=1, with_exchange=False):
    with STORE_LOCK:
        prod = next((p for p in STORE.products if p['id'] == int(product_id)), None)
        if not prod:
            return False, 'Product not found.'
        if variant_id is None and prod.get('variants'):
            variant_id = prod['variants'][0]['id']
        for entry in account['cart']:
            if entry['product_id'] == prod['id'] and entry.get('variant_id') == variant_id:
                entry['quantity'] = min(10, entry['quantity'] + int(quantity))
                if with_exchange:
                    entry['with_exchange'] = True
                return True, f"Updated quantity for {prod['title'][:36]}..."
        account['cart'].insert(0, {
            'item_id': uuid.uuid4().hex[:8],
            'product_id': prod['id'],
            'variant_id': variant_id,
            'quantity': max(1, min(10, int(quantity))),
            'with_exchange': bool(with_exchange) and prod.get('is_exchange_available', False),
        })
        return True, f"Added {prod['title'][:36]}... to your cart!"


def merge_guest_into_user(visitor_id, user_account):
    with STORE_LOCK:
        guest = STORE.guests.get(visitor_id)
        if not guest:
            return
        for item in guest['cart']:
            add_item_to_cart(
                user_account,
                item['product_id'],
                variant_id=item.get('variant_id'),
                quantity=item.get('quantity', 1),
                with_exchange=item.get('with_exchange', False),
            )
        for pid in guest['wishlist']:
            if pid not in user_account['wishlist']:
                user_account['wishlist'].append(pid)
        for pid in guest['compare']:
            if pid not in user_account['compare'] and len(user_account['compare']) < 4:
                user_account['compare'].append(pid)
        for pid in guest['recently_viewed']:
            if pid not in user_account['recently_viewed']:
                user_account['recently_viewed'].append(pid)
        STORE.guests.pop(visitor_id, None)

