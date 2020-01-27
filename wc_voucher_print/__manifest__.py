# -*- coding: utf-8 -*-
{
    'name': 'Web Coop - Voucher Printing',
    'category': 'Localization',
    'author': 'Esupportlink',
    'summary': "Printing of GL account voucher.",
    'description': "Printing of GL account voucher.",
    'depends': [
        'wc',
        'account_accountant',
        'report',
    ],
    'data': [
        'voucher_report.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
    'qweb': [],
}
