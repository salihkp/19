{
    'name': 'Manufacturing Pallet Barcode',
    'version': '19.0.3.0.0',
    'summary': 'إدارة الطبليات والباركود في أوامر التصنيع',
    'description': """
        موديول لإدارة الطبليات (Pallets) المرتبطة بأوامر التصنيع.
        - إنشاء طبليات من داخل أمر التصنيع
        - تتبع حالة الستيكر (بستيكر / بدون ستيكر)
        - طباعة باركود لكل طبلية حسب حالتها
        - باركود مختلف قبل وبعد لصق الستيكر
        - استهلاك الستيكر من المخزون عند التأكيد
        - دعم البحث بالباركود (Barcode Scanner)
        - تسجيل العمليات في الـ Chatter
    """,
    'author': 'islam Mohamed aLi',
    'category': 'Manufacturing',
    'depends': ['base', 'mrp', 'stock', 'product', 'mail', 'sale'],
    'data': [
        'security/ir.model.access.csv',
        'wizard/mrp_pallet_wizard_views.xml',
        'wizard/mrp_pick_package_wizard_views.xml',
        'views/product_template_views.xml',
        'views/mrp_production_views.xml',
        'views/stock_package_views.xml',
        'reports/pallet_barcode_report.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
