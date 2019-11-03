{
    'name': 'Web Coop - Ver1.5 ',
    'version': "1.5",
    'category': "Generic Modules",
    'license':"Other proprietary",
    'summary': "Upgrade ver 1.5",
    'description': """
    |   ver10.0.1.5
    |     f574:Rebate feature
    |     b563:Avoid to input reserved deduction items 
    |     b589:Account of other person can be selected in loan deduction form
    |     b590 add other due field on soa report
    |     f595:show current due when manual payment
    """,
    'author': 'E-supportlink,ltd',
    'depends': [
        'wc_upgrade_ver10_0_1_4','wc_loan_payment_rebate'
    ],
    'data': [
#        "b578/payment_view_ex.xml",
        "f595/payment_view_ex.xml","b563_b589/deduction_view_ex.xml",
        "b590/loan_report.xml","b590/soa_report.xml",
    ],
    'demo': [],
    'qweb': [],
    'test': [],
    'installable': True,
    'application': True,
    'auto_install':False,
}