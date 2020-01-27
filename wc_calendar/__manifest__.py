# -*- coding: utf-8 -*-
{
    'name': 'Web Coop - Calendar',
    'version': "1.0",
    'category': "Generic Modules",
    'author': 'Esupportlink',
    'summary': "Holiday Calendar.",
    'description': "Holiday Calendar.",
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
