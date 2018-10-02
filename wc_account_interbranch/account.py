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

class IbTransaction(models.Model):
    _name = "wc.account.ibtrans"
    #_inherit = "wc.account.transaction"
    _inherit = "mail.thread"
    _description = "Interbranch Transactions"
    _order = "date desc, name desc"

    def get_first_open_date(self):
        company_id = self.env.user.company_id.id
        return self.env['wc.posting'].get_first_open_date(company_id)

    company_id = fields.Many2one('res.company', string='Branch', readonly=True,
        default=lambda self: self.env['res.company']._company_default_get('wc.account.ibtrans'))

    name = fields.Char("Number", readonly=True, default="DRAFT", track_visibility='onchange')

    posting_id = fields.Many2one('wc.posting', string='Posting Ref',
        required=False, readonly=True, ondelete="set null")

    date = fields.Date(track_visibility='onchange',
        readonly=True, default=get_first_open_date)

    ib_account_code = fields.Char("Interbranch Acct#",
        readonly=True, states={'draft': [('readonly', False)]},
        track_visibility='onchange')

    other_company_id = fields.Many2one('res.company', string='Target Branch',
        readonly=True, states={'draft': [('readonly', False)]},
        track_visibility='onchange', required=True)

    account_id = fields.Many2one('wc.account',
        string='Account Name',
        readonly=True, ondelete="restrict")

    transaction_id = fields.Many2one('wc.account.transaction',
        track_visibility='onchange',
        string='Transaction Ref', readonly=True, ondelete="restrict")

    account_type = fields.Char("Account Type", readonly=True)
    account_type2 = fields.Char("Account Type", readonly=True)
    trans_type = fields.Char(readonly=True)

    reference = fields.Char("Reference",
        readonly=True, states={'draft': [('readonly', False)]},
        track_visibility='onchange')

    trcode_id = fields.Many2one('wc.tr.code', string='Transaction Code',
        readonly=True, states={'draft': [('readonly', False)]},
        track_visibility='onchange',
        #required=True,
        ondelete="restrict")

    is_deposit = fields.Boolean(related="trcode_id.is_deposit", readonly=True)
    is_withdrawal = fields.Boolean(related="trcode_id.is_withdrawal", readonly=True)

    deposit = fields.Float(digits=(12,2), readonly=True,
        states={'draft': [('readonly', False)]}, track_visibility='onchange')
    withdrawal = fields.Float(digits=(12,2), readonly=True,
        states={'draft': [('readonly', False)]}, track_visibility='onchange')
    teller_id = fields.Many2one('res.users', string="Teller",
        default=lambda self: self._uid, readonly=True,
        track_visibility='onchange', ondelete="restrict")

    balance = fields.Float("Account Balance", digits=(12,2),
        readonly=True, track_visibility='onchange')

    new_balance = fields.Float("Future Balance", digits=(12,2), compute="get_newbalance")
    validation_data = fields.Binary(compute='compute_validation_data')

    note = fields.Text('Notes', track_visibility='onchange')

    state = fields.Selection([
            ('draft', 'Draft'),
            ('for-approval', 'For Approval'),
            ('cancelled', 'Cancelled'),
            ('confirmed', 'Confirmed'),
        ], 'State', index=True, default="draft",
        readonly=True, track_visibility='onchange')

    @api.multi
    @api.depends(
        'transaction_id',
        'state',
    )
    def compute_validation_data(self):
        for r in self:
            transaction_id = r.transaction_id.sudo()
            data = transaction_id.get_validation_data()
            #_logger.debug("compute_validation_data: %s %s", transaction_id, data)
            r.validation_data = data

    @api.onchange('trcode_id')
    def oc_account_id(self):
       self.ensure_one()
       self.withdrawal = 0.0
       self.deposit = 0.0

    @api.multi
    @api.depends('balance','deposit','withdrawal')
    def get_newbalance(self):
        for r in self:
            r.new_balance = r.balance + r.deposit - r.withdrawal

    @api.multi
    def ib_confirm(self):
        for r in self:
            if r.state == 'draft':
                if (self.deposit<=0.0 and self.withdrawal<=0.0) or not r.account_id:
                    raise ValidationError(_("Incomplete entry."))

                account_id = self.env['wc.account'].sudo().browse(r.account_id.id)
                amt = r.deposit - r.withdrawal

                if r.new_balance<0.0:
                    raise ValidationError(_("Cannot withdraw more than balance."))

                if r.account_type2=='sa' and amt<0.0 and r.new_balance < account_id.maintaining_balance:
                    raise ValidationError(_("Cannot withdraw more than maintaining balance."))

                if amt<0.0 and r.date <= account_id.hold_date and r.new_balance < account_id.hold_amount:
                    raise ValidationError(_("Cannot withdraw more than hold amount."))

                other_date = self.env['wc.posting'].sudo().get_first_open_date(r.other_company_id.id)
                if r.date!=other_date:
                    raise ValidationError(_("Posting date of target branch is not open.\nTarge branch open date = %s") % other_date)

                r.state = 'for-approval'

    @api.multi
    def ib_approve(self):
        for r in self.sudo():
            if r.state == 'for-approval':
                #account_id = self.env['wc.account'].sudo().browse(r.account_id.id)
                note = "Interbranch transaction from %s." % r.company_id.name
                if r.note:
                    note = note + "\n" + r.note
                context = {'ir_sequence_date': r.date}
                tx_id = self.env['wc.account.transaction'].sudo().create({
                    'account_id': r.account_id.id,
                    'date': r.date,
                    'reference': r.reference,
                    'trcode_id': r.trcode_id.id,
                    'deposit': r.deposit,
                    'withdrawal': r.withdrawal,
                    'teller_id': r.teller_id.id,
                    'note': note,
                    'state': 'confirmed',
                    'name': self.env['ir.sequence'].with_context(**context).next_by_code('wc.account.transaction'),
                    'other_company_id': r.company_id.id,
                })
                r.transaction_id = tx_id
                r.name = self.env['ir.sequence'].with_context(**context).next_by_code('wc.account.ibtrans')
                r.state = 'confirmed'

    @api.multi
    def ib_search(self):
        self.ensure_one()
        code = (self.ib_account_code or "").strip()
        res = self.env['wc.account'].sudo().search([
            ('code','=',code),
            ('company_id','=',self.other_company_id.id),
        ], limit=1)
        _logger.debug("ib_search %s: %s", self.ib_account_code, res)
        if res:
            #if res[0].company_id.id == self.env.user.company_id.id:
            #    raise ValidationError(_("Cannot transact with same branch.\nUse normal deposit account transactions."))
            self.account_id = res[0].id
            self.account_type = res[0].account_type_id.name
            self.account_type2 = res[0].account_type_id.category
            self.balance = res[0].balance
            self.trans_type = (self.account_type2=='cbu') and 'cbu' or 'sa'
        else:
            self.account_id = False
            self.account_type = "ACCOUNT NOT FOUND!"
            self.account_type2 = False
            self.balance = False
            self.trans_type = False

    @api.multi
    def ib_cancel(self):
        for r in self:
            if r.state in ['for-approval','draft']:
                if r.name=='DRAFT':
                    r.name = 'CANCELLED'
                r.state = 'cancelled'

    @api.multi
    def print_validation(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.report.xml',
            'report_type': 'controller',
            'report_file': '/web/content/wc.account.ibtrans/%s/validation_data/output.prx?download=true' % self.id,
        }


class AccountTransaction(models.Model):
    _inherit = "wc.account.transaction"

    other_company_id = fields.Many2one('res.company', string='Transacting Branch',
        readonly=True, track_visibility='onchange')


#
