{
    'name': 'Web Coop - Ver1.6',
    'version': "1.6",
    'category': "Generic Modules",
    'license':"Other proprietary",
    'summary': "Upgrade ver 1.6",
    'description': """
    |   ver10.0.1.6
    |     f597:Enable to select saving account type in deduction items 
    |     f599:Show each account type balance summary on membership form
    """,
    'author': 'E-supportlink,ltd',
    'depends': [
        'wc_upgrade_ver10_0_1_5','wc_loan_consolidation'
    ],
    'data': [
        'f599/member_view_ex.xml',
        'f597/loan_type_view_ex.xml'
    ],
    'demo': [],
    'qweb': [],
    'test': [],
    'installable': True,
    'application': True,
    'auto_install':False,
}