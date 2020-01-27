# -*- coding: utf-8 -*-
{
    'name': 'Web Coop - Interbranch Deposit and Withdrawal',
    'version': "1.0",
    'category': "Generic Modules",
    'summary': "Inter-branch deposit account entry module.",
    'author': 'Esupportlink',
    'description': "Inter-branch deposit account entry module.",
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
