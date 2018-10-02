# -*- coding: utf-8 -*-
###############################################
# EzTech Software & Consultancy Inc. (c) 2017
###############################################
{
    'name': 'Web Coop - Loans Multi-Payment',
    'version': "1.0",
    'category': "Generic Modules",
    'summary': "Multi-Payment Loan Module for Web Coop System",
    'description': "Multi-Payment Loan Module for Web Coop System",
    'author': 'EzTech Software & Consultancy Inc.',
    'website': 'http://www.eztechsoft.com',
    'depends': [
        'wc_posting',
    ],
    'data': [
        #'security/security.xml',
        #'security/ir.model.access.csv',
        "payment_view.xml",
        "loan_type_view.xml",
    ],
    'demo': [],
    'qweb': [],
    'test': [],
    'installable': True,
    'application': True,
    'auto_install':False,
}
