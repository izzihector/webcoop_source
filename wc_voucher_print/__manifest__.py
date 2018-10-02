# -*- coding: utf-8 -*-
###############################################
# EzTech Software & Consultancy Inc. (c) 2017
###############################################
{
    'name': 'Web Coop - Voucher Printing',
    'author': 'EzTech Software & Consultancy Inc.',
    'website': 'http://www.eztechsoft.com',
    'category': 'Localization',
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
