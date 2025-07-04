{
    'name': 'Theme Lego',
    'summary': 'Design Web Pages with Theme Lego',
    'description': 'Theme Lego is an ideal choice for your Odoo 16.' 
               'This theme promises to offer a refreshing experience with Odoo,'
               'enhancing its functionality and aesthetics."',
    'category': 'Theme',
    'version': '16.0.1.0.0',
    'author': 'Cybrosys Techno Solutions',
    'company': 'Cybrosys Techno Solutions',
    'maintainer': 'Cybrosys Techno Solutions',
    'website': "https://www.cybrosys.com",
    'depends': ['website_sale_wishlist',
                'website_sale_comparison'],
    'data': [
        'views/footer_templates.xml',
        'views/shop_templates.xml',
        'views/add_to_cart_templates.xml',
        'views/payment_templates.xml',
        'views/login_templates.xml',
        'views/header_templates.xml',
        'views/address_templates.xml',
        'views/deal_back_views.xml',
        'views/snippets/snippet_templates.xml'
    ],
    'assets': {
        'web.assets_frontend': [
            "/theme_lego/static/src/css/owl.carousel.min.css",
            "/theme_lego/static/src/css/owl.theme.default.min.css",
            "/theme_lego/static/src/css/style.css",
            "/theme_lego/static/src/js/owl.carousel.js",
            "/theme_lego/static/src/js/owl.carousel.min.js",
            "/theme_lego/static/src/js/index.js",
            "/theme_lego/static/src/js/deal.js",
        ],
    },
    'images': [
        'static/description/banner.png',
        'static/description/theme_screenshot.png'
    ],
    'license': 'LGPL-3',
    'installable': True,
    'application': True,
    'auto_install': False,
}
