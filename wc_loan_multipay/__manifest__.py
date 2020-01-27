# -*- coding: utf-8 -*-
{
    'name': 'Web Coop - Loans Multi-Payment',
    'version': "1.0",
    'category': "Generic Modules",
    'author': 'Esupportlink',
    'summary': "Multi-Payment Loan Module for Web Coop System",
    'description': "Multi-Payment Loan Module for Web Coop System",
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
