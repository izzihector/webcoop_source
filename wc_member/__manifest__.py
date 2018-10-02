# -*- coding: utf-8 -*-
###############################################
# EzTech Software & Consultancy Inc. (c) 2017
###############################################
{
    'name': 'Web Coop - Membership',
    'version': "1.0",
    'category': "Generic Modules",
    'summary': "Membership module for Web Coop System",
    'description': "Membership module for Web Coop System",
    'author': 'EzTech Software & Consultancy Inc.',
    'website': 'http://www.eztechsoft.com',
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
