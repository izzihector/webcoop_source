# -*- coding: utf-8 -*-
###############################################
# EzTech Software & Consultancy Inc. (c) 2017
###############################################
{
    'name': 'Web Coop - Base',
    'version': "1.0",
    'category': "Generic Modules",
    'summary': "Base module for Online Cooperative Information System",
    'description': "Base module for Online Cooperative Information System",
    'author': 'EzTech Software & Consultancy Inc.',
    'website': 'http://www.eztechsoft.com',
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
