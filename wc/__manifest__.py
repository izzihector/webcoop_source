# -*- coding: utf-8 -*-
{
    'name': 'Web Coop - Base',
    'version': "1.0",
    'category': "Generic Modules",
    'summary': "Base module for Online Cooperative Information System",
    'author': 'Esupportlink',
    'description': "Base module for Online Cooperative Information System",
    'depends': [
        'base', 'mail', 'document',
    ],
    'init_xml': [],
    'data': [
        'security/security.xml',
        #'security/ir.model.access.csv',
        'menu_view.xml',
        'res_company_view.xml',
        'report_view.xml',
    ],
    'demo': [
        'res_company_demo.xml',
        'user_demo.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
    'qweb': [],
}
