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

#TODO: defined in config
account_number_length = 6

class LoanTypeDeductions(models.Model):
    _name = "wc.loan.type.deduction"
    _description = "Loan"
    _order = "sequence"

    loan_type_id = fields.Many2one('wc.loan.type', string='Loan type', readonly=True, ondelete="restrict")
    sequence = fields.Integer("Seq")
    name = fields.Char("Name", required=True)
    code = fields.Char("Code", required=True, index=True)
    recurring = fields.Boolean("Recurring",
        help="Enable if deduction is collected every payment cycle.")
    net_include = fields.Boolean("Net Include", default=True,
        help="Enable if deducted from loan amount to compute net.")
    factor = fields.Float("Factor %", digits=(12,4))
    amount = fields.Float("Amount", digits=(12,2))

    gl_account_id = fields.Many2one('account.account', string='GL Account', ondelete="set null")

    _sql_constraints = [
        ('unique_code', 'unique(loan_type_id, code)', 'The deduction code must be unique for each loan type!')
    ]

class LoanType(models.Model):
    _name = "wc.loan.type"
    _description = "Loan Type"
    _inherit = [
        'mail.thread',
    ]
    _order = "code"

    company_id = fields.Many2one('res.company', string='Branch', readonly=True,
        default=lambda self: self.env['res.company']._company_default_get('wc.loan.type'))

    code = fields.Char("Code", required=True, track_visibility='onchange')
    description = fields.Char("Description", required=True, track_visibility='onchange')
    name = fields.Char(compute="compute_name", store=True)

    interest_rate = fields.Float("Interest Rate %", digits=(12,4), track_visibility='onchange')
    penalty_rate = fields.Float("Penalty Rate %", digits=(12,4), default=12, track_visibility='onchange')

    payment_schedule = fields.Selection([
        ('day', 'Daily'),
        ('week', 'Weekly'),
        ('half-month', 'Semi-monthly'),
        ('15-days', '15-days'),
        ('month', 'Monthly'),
        ('30-days', '30-days'),
        ('quarter', 'Quarterly'),
        ('semi-annual', 'Semi-annual'),
        ('year', 'Yearly'),
        ('lumpsum', 'Lump Sum'),
    ], 'Payment Schedule', required=True, track_visibility='onchange')

    is_penalty_on_interest = fields.Boolean("Penalty on Interest", default=True,
        track_visibility='onchange',
        help="Include interest due on penalty calculation.")

    is_end_of_month_penalty = fields.Boolean("End of Month Penalty", default=True,
        track_visibility='onchange',
        help="Compute penalty only at end of month.")

    is_fixed_payment_amount = fields.Boolean("Fixed Amount", default=True,
        track_visibility='onchange',
        help="Payment amount per period is fixed.")

    is_360_day_year = fields.Boolean("Use 360-day Year", default=True,
        track_visibility='onchange',
        help="In computation use 360 days for a year.")

    days_in_year = fields.Selection([
            ('365', '365 days'),
            ('360', '360 days'),
            ('336', '336 days'),
        ], 'Days in Year', default="365", required=True,
        track_visibility='onchange',
        help="Number of days on a year. Used for interest computation.")

    maturity = fields.Integer("Maturity", help="Maturity in months or days", track_visibility='onchange')
    maturity_period = fields.Selection([
            ('days', 'days'),
            ('weeks', 'weeks'),
            ('months', 'months'),
        ], 'Maturity Period', required=True, default='months', track_visibility='onchange')

    ar_account_id = fields.Many2one('account.account',
        track_visibility='onchange',
        string='Receivable Current', ondelete="set null")

    ar_pd_account_id = fields.Many2one('account.account',
        track_visibility='onchange',
        string='Receivable P.Due', ondelete="set null")

    ap_account_id = fields.Many2one('account.account',
        track_visibility='onchange',
        string='Payable', ondelete="set null")

    interest_income_account_id = fields.Many2one('account.account',
        track_visibility='onchange',
        string='Interest Income', ondelete="set null")

    penalty_account_id = fields.Many2one('account.account',
        track_visibility='onchange',
        string='Penalty', ondelete="set null")

    note =  fields.Text("Notes", track_visibility='onchange')

    sequence_id = fields.Many2one('ir.sequence', string='Sequence',
        track_visibility='onchange', ondelete="restrict", readonly=True)

    deduction_ids = fields.One2many('wc.loan.type.deduction', 'loan_type_id', 'Deductions', copy=True)

    _sql_constraints = [
        ('unique_code', 'unique(code,company_id)', 'The loan type code must be unique per branch!')
    ]

    @api.multi
    @api.depends('code','description')
    def compute_name(self):
        for r in self:
            r.name = "%s - %s" % (r.code, r.description)

    @api.model
    def create(self, vals):
        rec = super(LoanType, self).create(vals)
        seq = self.env['ir.sequence'].sudo().create({
            'code': "wc.loan.type.%s" % rec.code,
            'name': "Loan Sequence %s" % rec.code,
            'number_next': 1,
            'number_increment': 1,
            'padding': account_number_length,
            'company_id': rec.company_id.id,
        })
        rec.sequence_id = seq
        return rec

    @api.multi
    def copy(self, default=None):
        self.ensure_one()
        self.env.cr.execute("SELECT MAX(id) as mx FROM wc_loan_type")
        res = self.env.cr.fetchone()[0] or 0
        default = dict(
            default or {},
            code= '%s copy#%d' % (self.code, res+1),
            description=_('%s (copy)') % self.description,
        )
        return super(LoanType, self).copy(default)


#
