{'name': 'migration for webcoop', 
   'summary': 'tool for inital data migration.Approve every unapproved member,account,loan', 
   'author': 'suzuki daisuke (ESL)', 
   'category': 'Tools', 
   'depends': ['wc_account','wc_loan'], 
   'init_xml': [], 
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'migration.xml',
    ],
   'installable': True,    'application': True, 
   'auto_install': False, 
   'qweb': []}