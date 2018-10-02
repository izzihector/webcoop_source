# -*- coding: utf-8 -*-
###############################################
# EzTech Software & Consultancy Inc. (c) 2017
###############################################

from openerp import models, fields, api, _
from openerp.exceptions import Warning, ValidationError
import openerp.addons.decimal_precision as dp
from datetime import datetime
from dateutil.relativedelta import relativedelta
import math
import logging

_logger = logging.getLogger(__name__)
DF = "%Y-%m-%d"
EPS = 0.00001

class LoanAmortization(models.Model):
    _name = "wc.loan.amortization"
    _description = "Loan Amortization Schedule"
    _order = "date_due"

    loan_id = fields.Many2one('wc.loan', 'Loan', ondelete='cascade')
    detail_id = fields.Many2one('wc.loan.detail', 'Loan detail', ondelete='set null')

    sequence = fields.Integer("Seq", readonly=True)
    date_start = fields.Date("Start Date", index=True)
    date_due = fields.Date("Due Date", index=True)
    days = fields.Integer(string="Days")
    name = fields.Char()
    principal_balance = fields.Float("Balance",digits=(12,2))
    principal_due = fields.Float("Principal Due",digits=(12,2))
    interest_due = fields.Float("Interest Due",digits=(12,2))
    others_due = fields.Float("Others Due",digits=(12,2),compute="compute_others_due")
    others_html = fields.Html("Others Breakdown",compute="compute_others_due")
    total_due = fields.Float("Total Due",digits=(12,2),compute="_compute_total_due")
    no_others_due = fields.Boolean("No Other Deductions")

    state = fields.Selection([
        ('open','Open'),
        ('processed','Processed'),
    ], string='State', default=lambda self: 'open', readonly=True)

    @api.multi
    @api.depends(
        'loan_id',
        'no_others_due',
        'loan_id.deduction_ids',
        'loan_id.deduction_ids.recurring',
        'loan_id.deduction_ids.amount',
    )
    def compute_others_due(self):
        for r in self:
            others_due = 0.0
            others_html = ""
            if not r.no_others_due:
                others_html = "<table class='ded_details'><tr><th>Code</th><th>Amount</th></tr>"
                for ded in r.loan_id.deduction_ids:
                    if ded.recurring:
                        others_due += ded.amount
                        if ded.amount:
                            others_html += "<tr><td>%s</td><td style='text-align:right'>%s</td></tr>" % (ded.code, "{:,.2f}".format(ded.amount))

                others_html += "</table>"
            r.others_due = others_due
            r.others_html = others_html

    @api.depends('principal_due', 'interest_due')
    def _compute_total_due(self):
        for r in self:
            r.total_due = r.principal_due + r.interest_due + r.others_due


    @api.multi
    def process_past_due(self, date):
        pass

    @api.multi
    def force_as_due(self):
        for a in self:
            #a.loan_id.generate_soa(a.date_due)
            loan = a.loan_id

            if loan.state == 'draft':
                raise Warning(_("Loan is still draft."))

            loan.gen_soa_details(loan, a.date_start)

            #create past-due line if still with balance
            if loan.amortizations[-1].id == a.id and loan.principal_balance > EPS:
                loan.process_past_due(loan.amortizations[-1].date_due)
                loan.state = 'past-due'


        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }



#
