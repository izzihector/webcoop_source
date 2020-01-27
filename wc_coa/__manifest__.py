# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Chart of Account - Web Coop',
    'category': 'Localization',
    'author': 'Esupportlink',
    'description': "Chart of Account for Web Coop",
    'depends': [
        'account',
        'base_iban',
        #'base_vat',
        'l10n_multilang',
        'report',
    ],
    'data': [
        'data/account_chart_template_data.xml',
        'data/coa_data.xml',
        'data/account_chart_template_after_data.xml',
        #'data/account_tax_data.xml',
        #'data/fiscal_templates_data.xml',
        'data/account_chart_template_data.yml',
        #'data/res_company_data.xml',
        'data/report_data.yml',
    ],
    #'post_init_hook': 'load_translations',
}
