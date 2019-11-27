
{
    'name': 'Web Coop - Us Embassy feature',
    'version': "1.0",
    'category': "Generic Modules",
    'summary': "Us Embassy feature",
    'description': """
                    1.Allow Bulk import and approve for account transaction,
                    2.Add custom field on membership form,
                    3.special deduction type for base interest
                    4.special loan disclosure layout
                   """,
    'author': 'Esupportlink.',
    'depends': [
        'wc_account','wc','wc_posting','wc_member','wc_upgrade_ver10_0_1_6','wc_dividend_patern1'
    ],
    'init_xml': [],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'acc_transaction_bulkapproval.xml',
        'account_transaction_view.xml',
        'member_view_ex.xml',
        'account_view.xml',
        'disclosure_report.xml'
    ],
    'demo': [],
    'installable': True,
    'application': True,
    'auto_install': False,
    'qweb': [],
}
