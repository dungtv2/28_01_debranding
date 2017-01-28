# -*- coding: utf-8 -*-
{
    'name': "Backend Debranding Configuration",

    'summary': """Backend Debranding Configuration""",

    'description': """
        Cat remover at your service
        - Replace logo, title, favicon
        - Remove 'Your odoo is not supported' banner
    """,

    'author': "Mr.Great",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/master/openerp/addons/base/module/module_data.xml
    # for the full list
    'category': 'Sale',
    'version': '1.0',

    # any module necessary for this one to work correctly
    'depends': ['base', 'web', 'mail', 'im_odoo_support', 'account'],
    'conflicts': [],

    # always loaded
    'price': 119,
    'currency': 'EUR',
    'data': [
        # 'security/ir.model.access.csv',
        'static/src/xml/debranding_config_view.xml',
        'static/src/xml/res_partner_view.xml',
        'templates.xml',
    ],
    'qweb': [
        "static/src/xml/base.xml"
    ],
    'images': [
        'images/de.jpg',
    ],
}
