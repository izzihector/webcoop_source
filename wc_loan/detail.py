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

class LoanDetails(models.Model):
    _name = "wc.loan.detail"
    _description = "Loan Detail"
    _inherit = "wc.loan.amortization"
    _order = "date_due"

    loan_id = fields.Many2one('wc.loan', 'Loan', ondelete='cascade')

    #penalty_base = fields.Float("Penalty",digits=(12,2))
    penalty = fields.Float("Penalty",digits=(12,2))
    adjustment = fields.Float("Adjustment",digits=(12,2),compute="_compute_adjustment",store=True)
    penalty_adjusted = fields.Float("Adjusted Penalty",digits=(12,2),compute="_compute_total_paid", store=False)
    principal_paid = fields.Float("Principal Paid",digits=(12,2),compute="_compute_total_paid",store=True)
    interest_paid = fields.Float("Interest Paid",digits=(12,2),compute="_compute_total_paid",store=True)
    penalty_paid = fields.Float("Penalty Paid",digits=(12,2),compute="_compute_total_paid",store=True)
    others_paid = fields.Float("Others Paid",digits=(12,2),compute="_compute_total_paid",store=True)
    others_paid_dict = fields.Char("Others Detail",digits=(12,2),compute="_compute_total_paid",store=True)
    others_html = fields.Html("Others Breakdown",compute="_compute_others_html")
    penalty_base = fields.Float("Penalty Base",digits=(12,2),compute="_compute_total_paid",store=True)
    total_due = fields.Float("Total Due",digits=(12,2),compute="_compute_total_paid",store=True)
    days = fields.Integer(string="PD", help="Past due in days") #,compute="_compute_days")

    state = fields.Selection([
        ('next_due','Next Due'),
        ('due','Due'),
        ('paid','Paid'),
        ('reversed','Reversed'),
        ('del','To be deleted'),
    ], string='State', default=lambda self: 'next_due', readonly=False)

    payment_date = fields.Date("Payment Date", compute="compute_payment")
    payment_amount = fields.Float("Payment Amount", digits=(12,2), compute="compute_payment")

    advance_payment_id = fields.Many2one('wc.loan.payment', 'Advance Payment')
    #is_principal_first = fields.Boolean("Principal First", readonly=True)

    distributions = fields.One2many('wc.loan.payment.distribution', 'detail_id', 'Payments Distribution')
    adjustments = fields.One2many('wc.loan.adjustment', 'detail_id', 'Adjustment')
    #deduction_ids = fields.One2many('wc.loan.detail.deduction', 'detail_id', 'Recurring Payments')

    @api.depends(
        'distributions',
        'distributions.payment_id',
        'distributions.payment_id.date'
    )
    def compute_payment(self):
        for r in self:
            is_date_set = False
            tamt = 0.0
            for p in r.distributions:
                if p.payment_id and p.payment_id.date and not is_date_set:
                    r.payment_date = p.payment_id.date
                    is_date_set = True
                tamt += p.amount
            r.payment_amount = tamt

    @api.model
    def get_others_paid_dict(self, det):
        try:
            others_paid_dict = eval(det.others_paid_dict)
        except:
            _logger.debug("*get_others_paid_dict error: %s", det.others_paid_dict)
            others_paid_dict = {}
        return others_paid_dict

    @api.depends(
        'others_paid_dict',
        'others_paid',
        'others_due',
    )
    def _compute_others_html(self):
        for det in self:
            others_paid_dict = det.get_others_paid_dict(det)
            others_html = ""
            if not det.no_others_due:
                for ded in det.loan_id.deduction_ids:
                    if ded.recurring:
                        paid = others_paid_dict.get(ded.code, 0.0)
                        if ded.amount or paid:
                            others_html += "<tr>"
                            others_html += "<td>%s</td>" % ded.code
                            others_html += "<td style='text-align:right;'>%s</td>" %  "{:,.2f}".format(ded.amount)
                            others_html += "<td style='text-align:right;'>%s</td>" %  "{:,.2f}".format(paid)
                            others_html += "</tr>"
                if others_html:
                    others_html2 = "<table class='ded_details'>"
                    others_html2 += "<tr>"
                    others_html2 += "<th>Code</th>"
                    others_html2 += "<th style='text-align:right;'>Due</th>"
                    others_html2 += "<th style='text-align:right;'>Paid</th>"
                    others_html2 += "</tr>" + others_html
                    others_html2 += "</table>"
                    det.others_html = others_html2

    @api.depends(
        'principal_due',
        'interest_due',
        'penalty',
        'adjustment',
        'distributions',
        'distributions.amount',
        'distributions.payment_type',
        'distributions.payment_id',
        'distributions.payment_id.state',
        'distributions.code',
    )
    def _compute_total_paid(self):
        for det in self:
            total = {
                'penalty': 0.0,
                'interest': 0.0,
                'principal': 0.0,
                'others': 0.0,
            }
            others_paid_dict = {}
            for p in det.distributions:
                if p.payment_id.state not in ['cancelled','draft']:
                    total[p.payment_type] += p.amount
                    others_paid_dict[p.code] = others_paid_dict.get(p.code, 0.0) + p.amount

            _logger.debug("Paid Total: %s", total)
            #pbase = det.principal_due + det.interest_due - total['interest'] - total['principal']
            pbase = det.principal_due - total['principal']
            det.penalty_paid = total['penalty']
            det.interest_paid = total['interest']
            det.principal_paid = total['principal']
            det.others_paid = total['others']
            det.others_paid_dict = "%s" % others_paid_dict
            det.penalty_base = pbase
            tdue = (
                max(det.principal_due - total['principal'], 0.0)
                + max(det.interest_due - total['interest'], 0.0)
                + max(det.penalty + det.adjustment - total['penalty'], 0.0)
                + max(det.others_due - total['others'], 0.0)
            )
            det.penalty_adjusted = det.penalty + det.adjustment
            if tdue > 0.0:
                det.total_due = tdue
            else:
                det.total_due = 0

    @api.depends('adjustments','adjustments.amount','adjustments.detail_id')
    def _compute_adjustment(self):
        for det in self:
            adjustment = 0.0
            for adj in det.adjustments:
                adjustment += adj.amount
            det.adjustment = adjustment

    @api.multi
    def add_adjustment(self):
        #self.ensure_one()
        if self.state == 'paid':
            return {}
        else:
            view_id = self.env.ref('wc_loan.add_adjustment_form').id
            context = self._context.copy()
            context.update({
                'default_loan_id': self.loan_id.id,
                'default_detail_id': self.id,
            })
            return {
                'name':'Add Adjustment',
                'view_type':'form',
                'view_mode':'form',
                'views' : [(view_id,'form')],
                'res_model':'wc.loan.adjustment.wizard',
                'view_id':view_id,
                'type':'ir.actions.act_window',
                'target':'new',
                'context':context,
            }



#
