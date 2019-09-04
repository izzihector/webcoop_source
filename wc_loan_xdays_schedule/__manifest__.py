{
    'name': 'Web Coop - Loans X-days Schedule',
    'version': "1.1",
    'category': "Generic Modules",
    'license':"Other proprietary",
    'summary': "Multi-Payment Loan Module for Web Coop System",
    'description': """
      | Add manually x days period for loan schedule
      | version 10.0.1.0  create this module for add feature of x days schedule for flexible scheduling
    """,
    'author': 'E-supportlink,ltd',
    'depends': [
        'wc_loan',
    ],
    'data': [
        "loan_type_view_ex.xml",
        "loan_view_ex.xml",
    ],
    'demo': [],
    'qweb': [],
    'test': [],
    'installable': True,
    'application': True,
    'auto_install':False,
}
