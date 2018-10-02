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

class ManualPosting(models.TransientModel):
    _name = "wc.post.wizard"
    _description = "Posting Wizard"

    date = fields.Date(default=fields.Date.context_today)
    date2 = fields.Date(default=fields.Date.context_today)
    loan_ids = fields.Many2many('wc.loan', string='Loans')
    account_ids = fields.Many2many('wc.account', string='Accounts')

    @api.multi
    def post_interest(self):

        interest_id = self.env.ref('wc_account.tr_int')
        _logger.debug("POST INTEREST start: int_ids=%s", interest_id)
        for rec in self:
            #_logger.debug("POST interest: %s to %s", rec.date, rec.date2)
            d1 = fields.Datetime.from_string(rec.date)
            d2 = fields.Datetime.from_string(rec.date2)
            while d1<=d2:
                rec.account_ids.compute_deposit_interest(d1.strftime(DF), interest_id)
                d1 += relativedelta(days=1)

        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

    @api.multi
    def post_loans(self):
        _logger.debug("POST LOANS")
        for rec in self:
            for loan in rec.loan_ids:
                loan.process_date(loan, rec.date)

        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }



#
