{
    'name': "Shipping API",
    'summary': """Connection layer between Odoo and other Shipping API's""",
    'description': """""",
    'author': "Christian McClanahan",
    'website': "https://github.com/RogueNAND/odoo-ship-api",
    'category': 'Inventory/Delivery',
    'application': False,
    'version': '14.0.2.2.1',
    'depends': ['delivery'],
    'data': [
        'security/ir.model.access.csv',
        'views/choose_delivery_carrier.xml',
        'views/delivery_carrier.xml',
        'views/delivery_carrier_api.xml',
        'views/delivery_carrier_api_carrier.xml',
        'views/delivery_carrier_api_carrier_service.xml',
        'views/product_packaging.xml',
        'views/product_product.xml',
        'views/res_config_settings.xml',
        'views/res_partner.xml',
        'views/res_partner_verify.xml',
        'data/data.xml',
        'data/ir_cron.xml',
    ],
    'license': 'GPL-3',
}
