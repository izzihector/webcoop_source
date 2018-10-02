# -*- coding: utf-8 -*-
###############################################
# EzTech Software & Consultancy Inc. (c) 2017
###############################################
{
    'name': 'Web Coop - Posting',
    'version': "1.0",
    'category': "Generic Modules",
    'summary': "Transaction posting module for Web Coop System",
    'description': "Transaction posting module for Web Coop System",
    'author': 'EzTech Software & Consultancy Inc.',
    'website': 'http://www.eztechsoft.com',
    'depends': [
        #'web',
        'wc',
        'wc_account',
        'wc_loan',
        'wc_microinsurance',
        'wc_collection',
        'wc_collection_other',
        'account_accountant',
    ],
    'init_xml': [],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        #'post_wizard_view.xml',
        'res_company_view.xml',
        'posting_view.xml',
        'deposit_transaction_view.xml',
        'loan_view.xml',
        'loan_payment_view.xml',
        'account_view.xml',
        'insurance_view.xml',
        'collection_view.xml',
        'wizard/daily_collection_view.xml',
    ],
    'demo': [
        #'member_demo.xml',
        #'account_demo.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
    'qweb': [],
}
