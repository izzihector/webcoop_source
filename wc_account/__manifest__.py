# -*- coding: utf-8 -*-
{
    'name': 'Web Coop - Savings',
    'version': "1.0",
    'category': "Generic Modules",
    'author': 'Esupportlink',
    'summary': "Savings Module for Web Coop System",
    'description': "Savings Module for Web Coop System",
    'depends': [
        'wc','wc_member','wc_collection','wc_coa',
    ],
    'init_xml': [],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',

        'trcode_data.xml',
        'account_type_data.xml',
        'transaction_data.xml',

        'account_view.xml',
        'account_cbu_view.xml',
        'member_view.xml',
        'trcode_view.xml',
        'account_type_view.xml',
        'transaction_view.xml',
        'collection_view.xml',
        'passbook_view.xml',
        'ctd_view.xml',

        'account_tran_report_wizard.xml',
        'account_tran_report_view.xml',
    ],
    'demo': [
        'member_demo.xml',
        'account_demo.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
    'qweb': [],
}
