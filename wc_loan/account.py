# -*- coding: utf-8 -*-
###############################################
# EzTech Software & Consultancy Inc. (c) 2017
###############################################

from openerp import models, fields, api, _
from openerp.exceptions import Warning
import openerp.addons.decimal_precision as dp
from datetime import datetime
from dateutil.relativedelta import relativedelta
import logging

_logger = logging.getLogger(__name__)
DF = "%Y-%m-%d"


class AccountTransaction(models.Model):
    _inherit = "wc.account.transaction"

    loan_id = fields.Many2one('wc.loan', string='Loan',
        readonly=True, ondelete="restrict")

    loan_code =  fields.Char("Loan Ref", related="loan_id.code", readonly=True)


class Account(models.Model):
    _inherit = "wc.account"

    @api.multi
    def close_account(self):
        #check if there is loan active attached to this account
        deductions = self.env['wc.loan.deduction'].search([
            ('deposit_account_id','in',self.ids)
        ])

        for ded in deductions:
            if ded.loan_id.state in ['approved','past-due']:
                raise Warning(
                    _("Cannot close account.\nThere are still loans connected to this account.\nLoan %s") % (
                        ded.loan_id.name
                    )
                )

        return super(Account, self).close_account()





#
