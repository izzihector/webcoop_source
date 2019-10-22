{
    'name': 'Web Coop - Ver1.4 ',
    'version': "1.4",
    'category': "Generic Modules",
    'license':"Other proprietary",
    'summary': "Upgrade ver 1.4",
    'description': """
    |   ver10.0.1.4
    |     f562:Bulk payment feature
    |     b564:[bug]Restructured loan has still balance. Balance should become zero in case of restructured
    |     f569:Add amount rate per principal on deduction , by compute field
    |     f571:Add no. of payment to calculate maturity
    |     b578:[bug]If manual payment , amount value on payment tree is zero.Incorrect
    |     b580:[bug]No error message appears when payment confirm under condition of no soa line
    """,
    'author': 'E-supportlink,ltd',
    'depends': [
        'wc_upgrade_ver10_0_1_3','wc_loan_payment_reconciliation'
    ],
    'data': [
#        "b578/payment_view_ex.xml",
        "f571/loan_view_ex.xml",
        "f571/loan_type_view_ex.xml",
        "f569/deduction_view_ex.xml"
    ],
    'demo': [],
    'qweb': [],
    'test': [],
    'installable': True,
    'application': True,
    'auto_install':False,
}