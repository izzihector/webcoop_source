# -*- coding: utf-8 -*-
{
    'name': 'Web Coop - Membership',
    'version': "1.0",
    'category': "Generic Modules",
    'author': 'Esupportlink',
    'summary': "Membership module for Web Coop System",
    'description': "Membership module for Web Coop System",
    'depends': [
        'wc',
    ],
    'init_xml': [],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'member_data.xml',
        'member_view.xml',
        'dependent_view.xml',
    ],
    'demo': [
        'user_demo.xml',
        'member_demo.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
    'qweb': [],
}
