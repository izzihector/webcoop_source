# -*- coding: utf-8 -*-
{
    'name': 'Web Coop - Security Enhancements',
    'version': "1.0",
    'category': "Generic Modules",
    'author': 'Esupportlink',
    'summary': "Web Coop security enhancements to Odoo framework.",
    'description': "Web Coop security enhancements to Odoo framework.",
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
