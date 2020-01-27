# -*- coding: utf-8 -*-
{
    'name': 'Web Coop - Micro-Insurance',
    'version': "1.0",
    'category': "Generic Modules",
    'author': 'Esupportlink',
    'summary': "Micro-Insurance Management Module for Web Coop System",
    'description': "Micro-Insurance Management Module for Web Coop System",
    'depends': [
        'wc',
        'wc_member',
        #'wc_collection',
    ],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'insurance_view.xml',
        #'member_view.xml',
        #'collection_view.xml',
    ],
    'demo': [
        'insurance_demo.xml',
        'user_demo.xml',
        #'demo_data.xml',
        #'loan_type_demo.xml',
        #'loan_demo.xml',
    ],
    'qweb': [],
    'test': [],
    'installable': True,
    'application': True,
    'auto_install':False,
}
