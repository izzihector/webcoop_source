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

account_number_length = 6

class AccountType(models.Model):
    _name = "wc.account.type"
    _description = "Account Type"
    _inherit = "mail.thread"
    _order = "code"

    company_id = fields.Many2one('res.company', string='Branch', readonly=True,
        default=lambda self: self.env['res.company']._company_default_get('wc.account.type'))

    ctd_signatory = fields.Char(related="company_id.ctd_signatory")

    code = fields.Char("Code", required=True, track_visibility='onchange')
    description = fields.Char("Description", required=True, track_visibility='onchange')
    name = fields.Char(compute="compute_name", store=True)

    category = fields.Selection([
        ('sa', 'Savings'),
        ('td', 'Time Deposit'),
        ('cbu', 'CBU'),
    ], 'Category', required=True, default="sa", track_visibility='onchange')

    #is_time_deposit = fields.Boolean("Time Deposit", track_visibility='onchange')
    maintaining_balance = fields.Float("Maintaining Balance", digits=(12,2), track_visibility='onchange')
    interest_level = fields.Float("Balance to earn interest", digits=(12,2), track_visibility='onchange')

    deposit_limit = fields.Float("Deposit Limit",
        help="Amount limit before needing branch manager's approval.",
        default=50000, digits=(12,2), track_visibility='onchange')
    withdrawal_limit = fields.Float("Withdraw Limit",
        help="Amount limit before needing branch manager's approval.",
        default=10000, digits=(12,2), track_visibility='onchange')

    interest_rate = fields.Float("Interest Rate %", digits=(12,2), track_visibility='onchange')
    posting_schedule = fields.Selection([
        ('quarterly', 'Quarterly'),
        ('semi-annual', 'Semi-Annual'),
        ('annual', 'Annual'),
        #('custom', 'Monthly'),
    ], 'Posting Schedule', required=True, default="quarterly", track_visibility='onchange')

    dormant_months = fields.Integer("Dormant Time", track_visibility='onchange')
    dormant_penalty = fields.Float("Dormant Penalty", digits=(12,2), track_visibility='onchange')
    note =  fields.Text("Notes", track_visibility='onchange')

    #is_no_interest_below_balance = fields.Boolean("No interest below maintaining balance", track_visibility='onchange')
    is_autorollover = fields.Boolean("Auto Rollover", default=True, track_visibility='onchange')

    sequence_id = fields.Many2one('ir.sequence', string='Sequence',
        track_visibility='onchange', ondelete="restrict", readonly=True)

    gl_account_id = fields.Many2one('account.account', string='GL Account', ondelete="set null")
    gl_withdraw_account_id = fields.Many2one('account.account', string='GL Acct Withdrawal', ondelete="set null")
    gl_interest_account_id = fields.Many2one('account.account', string='GL Acct Interest', ondelete="set null")

    _sql_constraints = [
        ('unique_code', 'unique(code, company_id)', 'The savings product type code must be unique per branch!')
    ]

    @api.model
    def create(self, vals):
        rec = super(AccountType, self).create(vals)
        seq = self.env['ir.sequence'].sudo().create({
            'code': "wc.account.type.%s" % rec.code,
            'name': "Account Sequence %s" % rec.code,
            'number_next': 1,
            'number_increment': 1,
            'padding': account_number_length,
            'company_id': False,
        })
        rec.sequence_id = seq
        return rec

    @api.multi
    @api.depends('code','description')
    def compute_name(self):
        for r in self:
            r.name = "%s - %s" % (r.code, r.description)

    @api.multi
    def copy(self, default=None):
        self.ensure_one()
        self.env.cr.execute("SELECT MAX(id) as mx FROM wc_account_type")
        res = self.env.cr.fetchone()[0] or 0
        default = dict(
            default or {},
            code= '%s copy#%d' % (self.code, res+1),
            description=_('%s (copy)') % self.description,
        )
        return super(AccountType, self).copy(default)






#
