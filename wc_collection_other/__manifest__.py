# -*- coding: utf-8 -*-
###############################################
# EzTech Software & Consultancy Inc. (c) 2017
###############################################
{
    'name': 'Web Coop - Other Collection',
    'version': "1.0",
    'category': "Generic Modules",
    'summary': "Extension collection entry that include other miscellaneous payments.",
    'description': "Extension collection entry that include other miscellaneous payments.",
    'author': 'EzTech Software & Consultancy Inc.',
    'website': 'http://www.eztechsoft.com',
    'depends': [
        'wc_collection',
        'account',
    ],
    'data': [
        'security/ir.model.access.csv',
        'security/security.xml',
        'octype_view.xml',
        'collection_view.xml',
    ],
    'demo': [],
    'qweb': [],
    'test': [],
    'installable': True,
    'application': True,
    'auto_install':False,
}
