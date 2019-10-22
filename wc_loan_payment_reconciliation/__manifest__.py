{
    'name': 'Web Coop - loan bulk payment import',
    'version': "1.0",
    'category': "Generic Modules",
    'license':"Other proprietary",
    'summary': "Upgrade ver 1.0",
    'description': """
        |     f562:  Loan bulk payment
            """,
    'author': 'E-supportlink,ltd',
    'depends': [
        'wc_member','wc_loan','wc_loan_manual_payment','wc_posting'
    ],
    'data': [
        'f562/security/security.xml',
        'f562/security/ir.model.access.csv',
        'f562/payment_reconciliation_line.xml',
        'f562/payment_reconciliation_search_wizard.xml',
        'f562/payment_reconciliation.xml',
        'f562/payment_view_ex.xml',
    ],
    'demo': [],
    'qweb': [],
    'test': [],
    'installable': True,
    'application': True,
    'auto_install':False,
}