# -*- coding: utf-8 -*-
###############################################
# EzTech Software & Consultancy Inc. (c) 2017
###############################################
{
    'name': 'Web Coop - Interbranch Deposit and Withdrawal',
    'version': "1.0",
    'category': "Generic Modules",
    'summary': "Inter-branch deposit account entry module.",
    'description': "Inter-branch deposit account entry module.",
    'author': 'EzTech Software & Consultancy Inc.',
    'website': 'http://www.eztechsoft.com',
    'depends': [
        'wc_account',
        'wc_account_hold',
        'wc_posting',
    ],
    'init_xml': [],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'trcode_data.xml',
        'res_company_view.xml',
        'account_view.xml',
        'posting_view.xml',
    ],
    'demo': [],
    'installable': True,
    'application': True,
    'auto_install': False,
    'qweb': [],
}
