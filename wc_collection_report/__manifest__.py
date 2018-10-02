# -*- coding: utf-8 -*-
###############################################
# EzTech Software & Consultancy Inc. (c) 2017
###############################################
{
    'name': 'Web Coop - Collection Report',
    'version': "1.0",
    'category': "Generic Modules",
    'summary': "Collection reporting for Web Coop System",
    'description': "Collection reporting for Web Coop System",
    'author': 'EzTech Software & Consultancy Inc.',
    'website': 'http://www.eztechsoft.com',
    'depends': [
        'wc_posting',
    ],
    'data': [
        'report_view.xml',
        'report_per_teller.xml',
        'report_per_or.xml',
    ],
    'demo': [
    ],
    'qweb': [],
    'test': [],
    'installable': True,
    'application': True,
    'auto_install':False,
}
