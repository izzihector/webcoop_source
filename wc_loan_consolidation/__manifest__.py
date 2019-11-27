# -*- coding: utf-8 -*-

{
    'name': 'Web Coop - Loan Consolidate restructure',
    'version': "1.0",
    'category': "Generic Modules",
    'summary': "Loan consolidate restructure",
    'description': "Restructure multiple loans and make new loan",
    'author': 'E-supportlink',
    'website': '',
    'depends': [
        'wc_loan','wc_upgrade_ver10_0_1_2'
    ],
    'data': [
        "loan_consolidate_view.xml",
        "loan_view_ex.xml",
        "res_company_view_ex.xml",
    ],
    'demo': [],
    'qweb': [],
    'test': [],
    'installable': True,
    'application': True,
    'auto_install':False,
}
