# -*- coding: utf-8 -*-
{
    'name': 'Web Coop - Loans',
    'version': "1.1",
    'category': "Generic Modules",
    'author': 'Esupportlink',
    'summary': "Loans Module for Web Coop System",
    'description': """
     |  Loans Module for Web Coop System
     |  ver10.0.1.1 -20190904fix bug532 (system error at calculation of next due(1.create new loan , 2.select loan type ,3.erase amortization start , then error happened) )
       """,
    'depends': [
        'wc',
        'wc_member',
        'wc_account',
        'wc_collection',
        'wc_coa',
    ],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'loan_type_view.xml',
        'loan_view.xml',
        'detail_view.xml',
        'deduction_view.xml',
        'payment_view.xml',
        'adjustment_view.xml',
        'member_view.xml',
        'collection_view.xml',
        'account_view.xml',
        'loan_tag_view.xml',

        'report/loan_report.xml',
        'report/loan_report_wizard.xml',

        'report/disclosure_report.xml',
        'report/voucher_report.xml',
        'report/soa_report.xml',
        'report/release_report.xml',
        'report/loan_aging_report.xml',
    ],
    'demo': [
        'user_demo.xml',
        'loan_type_demo.xml',
        'loan_demo.xml',
    ],
    'qweb': [],
    'test': [],
    'installable': True,
    'application': True,
    'auto_install':False,
}
