# -*- coding: utf-8 -*-
###############################################
# EzTech Software & Consultancy Inc. (c) 2017
###############################################
{
    'name': 'Web Coop - Loans Straight Interest (EPR)',
    'version': "1.0",
    'category': "Generic Modules",
    'summary': "Straight (EPR) interest rate computation.",
    'description': "Enables loan types with straight (EPR) interest rate computation.",
    'author': 'EzTech Software & Consultancy Inc.',
    'website': 'http://www.eztechsoft.com',
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
