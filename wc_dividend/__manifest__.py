# -*- coding: utf-8 -*-
{
    'name': 'Web Coop - Dividend Calculation',
    'version': "1.0",
    'category': "Generic Modules",
    'author': 'Esupportlink',
    'summary': "Dividend Module for Web Coop System",
    'description': "Dividend Module for Web Coop System",
    'depends': [
        'wc',
        'wc_account',
        'wc_loan',
        'account_accountant',
    ],
    'init_xml': [],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'dividend_view.xml',
    ],
    'demo': [],
    'installable': True,
    'application': True,
    'auto_install': False,
    'qweb': [],
}
