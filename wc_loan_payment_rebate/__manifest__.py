{
    'name': 'Web Coop - loan rebate',
    'version': "1.0",
    'category': "Generic Modules",
    'license':"Other proprietary",
    'summary': "Upgrade ver 1.0",
    'description': """
        |     f574: Rebate(refund) feature 
            """,
    'author': 'E-supportlink,ltd',
    'depends': [
        'wc_member','wc_loan','wc_loan_manual_payment','wc_account','wc_posting','wc_upgrade_ver10_0_1_2'
    ],
    'data': [
        'f574/security/security.xml',
        'f574/security/ir.model.access.csv',
        'f574/payment_rebate_view_ex.xml',
        'f574/loan_type_view_ex.xml',
        'f574/loan_view_ex.xml',
        'f574/res_company_view_ex.xml',
        'f574/posting_view_ex.xml',
    ],
    'demo': [],
    'qweb': [],
    'test': [],
    'installable': True,
    'application': True,
    'auto_install':False,
}