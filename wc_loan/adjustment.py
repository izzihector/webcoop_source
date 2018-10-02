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

class LoanAdjustment(models.Model):
    _name = "wc.loan.adjustment"
    _description = "Loan Adjustment"
    #_inherit = [ 'mail.thread' ]
    order = "date desc, name"

    company_id = fields.Many2one('res.company', string='Branch', readonly=True,
        default=lambda self: self.env['res.company']._company_default_get('wc.loan'))

    loan_id = fields.Many2one('wc.loan', 'Loan', ondelete='restrict')
    detail_id = fields.Many2one('wc.loan.detail', 'Loan Detail', ondelete='restrict', index=True)

    name = fields.Char("Name", related="detail_id.name", readonly=True)
    member_id = fields.Many2one(related="loan_id.member_id", readonly=True)

    date = fields.Date("Date", default=fields.Date.context_today, index=True)
    amount = fields.Float("Adjustment", digits=(12,2))
    note = fields.Text(string='Notes')

    penalty = fields.Float("Penalty", digits=(12,2), compute="_compute_adjustment",
        related="detail_id.penalty", readonly=True)

    total_adjustment = fields.Float("Total Adjustments", digits=(12,2), compute="_compute_adjustment", store=False)
    penalty_adjusted = fields.Float("Adjusted Penalty", digits=(12,2), compute="_compute_adjustment", store=False)

    @api.depends('amount','detail_id','detail_id.penalty','detail_id.adjustments.amount')
    def _compute_adjustment(self):
        for rec in self:
            adjustments = self.env['wc.loan.adjustment'].search([
                ('detail_id','=',rec.detail_id.id),
                ('id','!=',rec.id),
            ])
            tadj = sum([adj.amount for adj in adjustments])
            rec.total_adjustment = tadj + rec.amount
            rec.penalty_adjusted = rec.penalty + tadj + rec.amount

#wizard
class LoanAdjustmentWizard(models.TransientModel):
    _name = "wc.loan.adjustment.wizard"
    _description = "Loan Payment Wizard"

    loan_id = fields.Many2one('wc.loan', 'Loan')
    detail_id = fields.Many2one('wc.loan.detail', 'Loan Detail')
    date = fields.Date("Date", default=fields.Date.context_today, required=True)
    amount = fields.Float("Adjustment", digits=(12,2))
    note = fields.Text(string='Notes')

    penalty = fields.Float("Penalty", digits=(12,2), related="detail_id.penalty", readonly=True)
    total_adjustment = fields.Float("Total Adjustments", digits=(12,2), compute="_compute_adjustment", store=False)
    penalty_adjusted = fields.Float("Adjusted Penalty", digits=(12,2), compute="_compute_adjustment", store=False)

    @api.depends('amount','detail_id','detail_id.penalty','detail_id.adjustments.amount')
    def _compute_adjustment(self):
        for rec in self:
            adjustments = self.env['wc.loan.adjustment'].search([
                ('detail_id','=',rec.detail_id.id),
            ])
            tadj = sum([adj.amount for adj in adjustments])
            _logger.debug("Adjustments: %s tadj=%0.2f", adjustments, tadj)
            rec.total_adjustment = tadj + rec.amount
            rec.penalty_adjusted = rec.penalty + tadj + rec.amount

    @api.multi
    def confirm_adjustment(self):
        if self.amount != 0.0:
            self.env['wc.loan.adjustment'].create({
                'loan_id': self.loan_id.id,
                'detail_id':self.detail_id.id,
                'date': self.date,
                'amount': self.amount,
                'note': self.note,
            })
        return {'type': 'ir.actions.act_window_close'}
        """
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }
        """





#
