# -*- coding: utf-8 -*-
{
    'name': 'Web Coop - Collections',
    'version': "1.0",
    'category': "Generic Modules",
    'author': 'Esupportlink',
    'summary': "Compounded collection base module for Web Coop System",
    'description': "Compounded collection base module for Web Coop System",
    'depends': [
        'wc','wc_member','wc_microinsurance',
    ],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'collection_view.xml',
        'insurance_view.xml',
        'member_view.xml',
    ],
    'demo': [
        'user_demo.xml',
    ],
    'qweb': [],
    'test': [],
    'installable': True,
    'application': True,
    'auto_install':False,
}
