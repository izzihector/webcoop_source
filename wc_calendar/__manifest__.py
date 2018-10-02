# -*- coding: utf-8 -*-
###############################################
# EzTech Software & Consultancy Inc. (c) 2017
###############################################
{
    'name': 'Web Coop - Calendar',
    'version': "1.0",
    'category': "Generic Modules",
    'summary': "Holiday Calendar.",
    'description': "Holiday Calendar.",
    'author': 'EzTech Software & Consultancy Inc.',
    'website': 'http://www.eztechsoft.com',
    'depends': [
        'wc','wc_loan_epr',
    ],
    'data': [
        'security/ir.model.access.csv',
        'holiday_view.xml',
    ],
    'demo': [],
    'qweb': [],
    'test': [],
    'installable': True,
    'application': True,
    'auto_install':False,
}
