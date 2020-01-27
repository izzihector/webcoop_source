# -*- coding: utf-8 -*-

{
    'name': 'Web Coop - Collection on Loan Payment Separated',
    'version': "1.0",
    'category': "Generic Modules",
    'author': 'Esupportlink',
    'summary': "Separate entry for loan payments for principal, interest and penalty.",
    'description': "Separate entry for loan payments for principal, interest and penalty.",
    'depends': [
        'wc_loan',
        #'wc_loan_manual_payment',
    ],
    'data': [
        #'security/security.xml',
        #'security/ir.model.access.csv',
        'loan_view.xml',
    ],
    'demo': [
    ],
    'qweb': [],
    'test': [],
    'installable': True,
    'application': True,
    'auto_install':False,
}
