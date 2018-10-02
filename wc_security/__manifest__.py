# -*- coding: utf-8 -*-
###############################################
# EzTech Software & Consultancy Inc. (c) 2017
###############################################
{
    'name': 'Web Coop - Security Enhancements',
    'version': "1.0",
    'category': "Generic Modules",
    'summary': "Web Coop security enhancements to Odoo framework.",
    'description': "Web Coop security enhancements to Odoo framework.",
    'author': 'EzTech Software & Consultancy Inc.',
    'website': 'http://www.eztechsoft.com',
    'depends': [
        'base',
        'document',
        'mail',
    ],
    'init_xml': [],
    'data': [
        #'security/security.xml',
        #'security/ir.model.access.csv',
        "template_view.xml",
    ],
    'demo': [
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
    'qweb': [],
}
