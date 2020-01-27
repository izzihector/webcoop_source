# -*- coding: utf-8 -*-
{
    'name': 'Web Coop - Excel Report',
    'version': "1.0",
    'category': "Generic Modules",
    'author': 'Esupportlink',
    'summary': "Reporting module using Excel output for Web Coop System",
    'description': "Reporting module using Excel output for Web Coop System",
    'depends': [
        'wc',
        'wc_coa',
        'account_accountant',
    ],
    'init_xml': [],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        #'res_company_view.xml',
        'excel_report_view.xml',
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
