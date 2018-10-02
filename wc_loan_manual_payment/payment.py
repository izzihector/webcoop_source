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

class LoanPayments(models.Model):
    _inherit = "wc.loan.payment"

    is_manual_compute = fields.Boolean("Manual Compute",
        readonly=True, states={'draft': [('readonly', False)]})
    principal_amount = fields.Float("Principal", digits=(12,2),
        readonly=True, states={'draft': [('readonly', False)]})
    interest_amount = fields.Float("Interest", digits=(12,2),
        readonly=True, states={'draft': [('readonly', False)]})
    penalty_amount = fields.Float("Penalty", digits=(12,2),
        readonly=True, states={'draft': [('readonly', False)]})
    amount2 = fields.Float("Total Amount", digits=(12,2), compute="compute_amount2")

    @api.depends(
        'is_manual_compute',
        'principal_amount',
        'interest_amount',
        'penalty_amount',
        'amount',
    )
    def compute_amount2(self):
        for p in self:
            if p.is_manual_compute:
                p.amount2 = p.principal_amount + p.interest_amount + p.penalty_amount
            else:
                p.amount2 = p.amount

    @api.multi
    def confirm_payment(self):
        self.ensure_one()
        if self.is_manual_compute:
            self.amount = self.principal_amount + self.interest_amount + self.penalty_amount
        else:
             self.principal_amount = 0.0
             self.interest_amount = 0.0
             self.penalty_amount = 0.0
        return super(LoanPayments, self).confirm_payment()

    @api.onchange(
        'is_manual_compute',
        'principal_amount',
        'interest_amount',
        'penalty_amount',
    )
    def oc_manual_amount(self):
        self.ensure_one()
        if self.is_manual_compute:
            self.amount2 = self.principal_amount + self.interest_amount + self.penalty_amount

    @api.model
    def get_detail_line(self, loan, date_start):
        if self.is_manual_compute:
            principal_balance = loan.principal_balance
            principal_due = self.principal_amount
            interest_due = self.interest_amount
            penalty = self.penalty_amount
            amount = principal_due + interest_due + penalty
            self.amount = amount

            nbalance = (principal_balance + interest_due + penalty)
            if (nbalance + 0.001) < amount:
                raise Warning(_("Cannot continue! Amount is more than due.\nBalance = %0.02f") % nbalance)

            vals = {
                'loan_id': loan.id,
                #'name': "Advance Payment %d" % n,
                'date_start': date_start,
                'date_due': self.date,
                'principal_balance': principal_balance,
                'principal_due': principal_due,
                'interest_due': interest_due,
                'penalty': penalty,
                'penalty_base': 0.0,
                'no_others_due': True,
                'state': 'due',
                'advance_payment_id': self.id,
                #'date_soa': fields.Date.context_today(self),
                #'sequence': n,
            }
            return vals, principal_balance, principal_due
        else:
            return super(LoanPayments, self).get_detail_line(loan, date_start)





#
