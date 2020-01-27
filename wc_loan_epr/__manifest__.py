# -*- coding: utf-8 -*-
{
    'name': 'Web Coop - Loans Straight Interest (EPR)',
    'version': "1.0",
    'category': "Generic Modules",
    'author': 'Esupportlink',
    'summary': "Straight (EPR) interest rate computation.",
    'description': "Enables loan types with straight (EPR) interest rate computation.",
    'depends': [
        'wc_loan',
    ],
    'data': [
        #'security/security.xml',
        #'security/ir.model.access.csv',
        'loan_type_view.xml',
    ],
    'demo': [],
    'qweb': [],
    'test': [],
    'installable': True,
    'application': True,
    'auto_install':False,
}
