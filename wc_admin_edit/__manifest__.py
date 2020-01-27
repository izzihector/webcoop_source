# -*- coding: utf-8 -*-

{
    'name': 'Web Coop - Admin Edit',
    'version': "1.0",
    'category': "Generic Modules",
    'author': 'Esupportlink',
    'summary': "Admin transaction editing module for Web Coop System",
    'description': "Admin transaction editing module for Web Coop System",
    'depends': [
        'wc_posting',
    ],
    'init_xml': [],
    'data': [
        #'security/security.xml',
        #'security/ir.model.access.csv',
        'inherit_view.xml',
        'loan_view.xml',
        'account_view.xml',
    ],
    'demo': [
        #'member_demo.xml',
        #'account_demo.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
    'qweb': [],
}
