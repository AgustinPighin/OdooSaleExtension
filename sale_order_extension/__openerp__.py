# -*- coding: utf-8 -*-
{
    'name': "sale_order_extension",

    'summary': """
        Extension on sale order""",

    'description': """
        Long description of module's purpose
    """,

    'author': "Agustin Pighin",
    'website': "http://droguerialatrinidad.com.ar",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/master/openerp/addons/base/module/module_data.xml
    # for the full list
    'category': 'test',
    'version': '9.0.0.1.72',
    'installable': True,
    'auto_install': False,
    'application': False,

    # any module necessary for this one to work correctly
    'depends': ['sale'],

    # always loaded
    'data': [
        'views/sale_order_line.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}