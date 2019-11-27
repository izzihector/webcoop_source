# -*- coding: utf-8 -*-

from odoo import api, fields, models
from odoo import tools, _
from odoo.exceptions import ValidationError, Warning
from odoo.modules.module import get_module_resource
from datetime import datetime
from dateutil.relativedelta import relativedelta
import logging

_logger = logging.getLogger(__name__)
DF = "%Y-%m-%d"

account_number_length = 6

class AccountType(models.Model):
    _inherit = "wc.account.type"

    @api.model
    def create(self, values):
        if values['category']=='cbu':
            res = self.env['wc.account.type'].search(['category','=','cbu'])
            if len(res) > 0:
                raise ValidationError(_("Cannot multiple CBU account type."))

        return super(AccountType, self).create(values)



    def get_dep_account_id(self):
        self.ensure_one()
        acc = self

        if acc.gl_account_id:
            account_id = acc.gl_account_id
        elif acc.category=='cbu':
            account_id = acc.company_id.cbu_deposit_account_id
        elif acc.category=='sa':
            account_id = acc.company_id.sa_deposit_account_id
        elif acc.category=='td':
            account_id = acc.company_id.td_deposit_account_id
        else:
            raise Warning(_("Default deposit products GL account is not defined in Companies/Branch/Account Settings."))

        return account_id