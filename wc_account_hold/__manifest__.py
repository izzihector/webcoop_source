# -*- coding: utf-8 -*-
###############################################
# EzTech Software & Consultancy Inc. (c) 2017
###############################################
{
    'name': 'Web Coop - Savings Hold',
    'version': "1.0",
    'category': "Generic Modules",
    'summary': "Hold amount feature for savings module",
    'description': "Hold amount feature for savings module",
    'author': 'EzTech Software & Consultancy Inc.',
    'website': 'http://www.eztechsoft.com',
    'depends': [
        'wc_account'
    ],
    'init_xml': [],
    'data': [
        #'security/security.xml',
        #'security/ir.model.access.csv',
        'account_view.xml',
    ],
    'demo': [],
    'installable': True,
    'application': True,
    'auto_install': False,
    'qweb': [],
}
