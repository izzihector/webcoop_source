# -*- coding: utf-8 -*-
###############################################
# EzTech Software & Consultancy Inc. (c) 2017
###############################################
{
    'name': 'Web Coop - Collection on Loan Payment Separated',
    'version': "1.0",
    'category': "Generic Modules",
    'summary': "Separate entry for loan payments for principal, interest and penalty.",
    'description': "Separate entry for loan payments for principal, interest and penalty.",
    'author': 'EzTech Software & Consultancy Inc.',
    'website': 'http://www.eztechsoft.com',
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
