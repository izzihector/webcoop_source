
{
    'name': 'Web Coop - Us Embassy feature',
    'version': "1.0",
    'category': "Generic Modules",
    'summary': "Us Embassy feature",
    'description': """
                    1.Allow Bulk import and approve for account transaction,
                    2.Add custom field on membership form,
                   """,
    'author': 'Esupportlink.',
    'depends': [
        'wc_account','wc','wc_posting'
    ],
    'init_xml': [],
    'data': [
        'acc_transaction_bulkapproval.xml',
        'account_transaction_view.xml',
        'security/security.xml',
        'security/ir.model.access.csv',
        
    ],
    'demo': [],
    'installable': True,
    'application': True,
    'auto_install': False,
    'qweb': [],
}
