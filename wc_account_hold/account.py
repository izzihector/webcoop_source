# -*- coding: utf-8 -*-
###############################################
# EzTech Software & Consultancy Inc. (c) 2017
###############################################

from odoo import api, fields, models
from odoo import tools, _
from odoo.exceptions import ValidationError, Warning
from odoo.modules.module import get_module_resource
from datetime import datetime
from dateutil.relativedelta import relativedelta
import logging

_logger = logging.getLogger(__name__)
DF = "%Y-%m-%d"

class Account(models.Model):
    _inherit = "wc.account"

    hold_amount = fields.Float("Hold Amount", digits=(12,2), track_visibility='onchange')
    hold_date = fields.Date("Hold Date", track_visibility='onchange')

    @api.multi
    @api.constrains('hold_amount')
    def _check_hold_amount(self):
        for r in self:
            if r.hold_amount < 0.0:
                raise Warning(_("Hold amount cannot be less than zero."))


class AccountTransaction(models.Model):
    _inherit = "wc.account.transaction"

    @api.multi
    def confirm(self):
        for r in self:
            if r.state == 'draft' and r.account_id.hold_amount>0.0 and r.account_id.hold_date:
                newbal = r.account_id.balance + r.deposit - r.withdrawal
                if newbal < r.account_id.hold_amount and r.date <= r.account_id.hold_date:
                    raise ValidationError(_("New balance will be less than amount on hold.\nOn-hold = %s") % r.account_id.hold_amount)

        return super(AccountTransaction, self).confirm()
