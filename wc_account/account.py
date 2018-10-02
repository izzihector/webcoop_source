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

ADD_MONTHS = {
    'quarterly': 3,
    'semi-annual': 6,
    'annual': 12,
}

class Account(models.Model):
    _name = "wc.account"
    _description = "Account"
    _inherit = "mail.thread"
    _order = "code"

    name = fields.Char("Name", compute="compute_name", readonly=True, store=True)
    name_no_code = fields.Char("Name", compute="compute_name")
    code = fields.Char("Account No.", track_visibility='onchange',
        default="NONE", readonly=True, required=True, index=True)

    member_id = fields.Many2one('wc.member', string='Account Holder',
        domain=[('is_approved','=',True)],
        readonly=True, states={'draft': [('readonly', False)]},
        track_visibility='onchange', ondelete="restrict", required=True)

    other_member_ids = fields.Many2many('wc.member', string='Other Joint Holders',
        domain=[('is_approved','=',True)],
        readonly=True, states={'draft': [('readonly', False)]})

    member_code = fields.Char(related="member_id.code")
    member_type = fields.Selection(related="member_id.member_type", readonly=True)

    account_type_id = fields.Many2one('wc.account.type', string='Account Type',
        readonly=True, states={'draft': [('readonly', False)]},
        track_visibility='onchange', ondelete="restrict", required=True)
    account_type = fields.Selection("Account Type", readonly=True,
        related="account_type_id.category", store=True)
    account_type_description = fields.Char("Account Type Description", readonly=True,
        related="account_type_id.description")

    interest_rate = fields.Float(readonly=True, related="account_type_id.interest_rate")

    #member_id2 = fields.Many2one('wc.member', string='Account Owner #2',
    #    domain=[('is_approved','=',True)],
    #    track_visibility='onchange', ondelete="restrict")
    company_id = fields.Many2one(related="member_id.company_id", readonly=True, store=True)

    #company_currency_id = fields.Many2one(related="member_id.company_currency_id",
    #    readonly=True, store=True)
    image = fields.Binary(compute="get_member_data")
    image_medium = fields.Binary(compute="get_member_data")
    image_small = fields.Binary(compute="get_member_data")
    center_id = fields.Many2one(related="member_id.center_id", readonly=True)
    address = fields.Char(compute="get_member_data")

    active = fields.Boolean(default=True, track_visibility='onchange')

    state = fields.Selection([
        ('draft', 'Draft'),
        ('open', 'Open'),
        ('dormant', 'Dormant'),
        ('closed', 'Closed'),
    ], 'State', default="draft", readonly=True, track_visibility='onchange')

    #time deposit date fields
    date_start = fields.Date("Start Date",track_visibility='onchange',
        readonly=True, states={'draft': [('readonly', False)]},
        default=fields.Date.context_today, index=True)

    custom_months = fields.Integer('Custom Period',
        readonly=True, states={'draft': [('readonly', False)]},
        help="Set customize number of months maturity period.",
        track_visibility='onchange')

    date_maturity = fields.Date("Maturity Date", compute="get_date_maturity",
        readonly=True, store=True)

    maintaining_balance = fields.Float("Maint. Balance", digits=(12,2),
        #readonly=True, states={'draft': [('readonly', False)]},
        track_visibility='onchange')

    note = fields.Text('Notes', track_visibility='onchange')

    total_deposit = fields.Float("Total Deposit", digits=(12,2), compute="compute_total")
    total_withdrawal = fields.Float("Total Withdrawal", digits=(12,2), compute="compute_total")
    total_onclearing = fields.Float("Total Unavailable", digits=(12,2), compute="compute_total")
    balance = fields.Float("Account Balance", digits=(12,2), compute="compute_total", store=True)

    clean_name = fields.Char("Member Name", compute="get_clean_name")

    transaction_ids = fields.One2many('wc.account.transaction', 'account_id', string='Transactions')

    #total_cbu = fields.Float("Total CBU", digits=(12,2), compute="_get_total_cbu")
    #transaction_ids = fields.One2many('wc.cbu.transaction', 'cbu_id', string='Transactions')

    @api.multi
    @api.onchange('account_type_id')
    def onchange_account_type_id(self):
        for r in self:
            if r.account_type=='sa':
                r.maintaining_balance = r.account_type_id.maintaining_balance

    @api.multi
    @api.depends('date_start','account_type_id','account_type_id.posting_schedule','custom_months')
    def get_date_maturity(self):
       for acct in self:
           if acct.account_type_id and acct.account_type_id.posting_schedule:
               if acct.custom_months>0 and acct.account_type=='td':
                   months = acct.custom_months
               else:
                   months = ADD_MONTHS.get(acct.account_type_id.posting_schedule, 12)
               dt = fields.Datetime.from_string(acct.date_start) + relativedelta(months=months)
               acct.date_maturity = dt.strftime(DF)

    @api.model
    def create(self, vals):
        acct_type = self._context.get('account_type_category', 'none')
        if acct_type == 'cbu':
            raise Warning(_("Cannot create CBU account. Use Member menu."))
        return super(Account, self).create(vals)

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        args = args or []
        records = self.browse()
        if name:
            records = self.search([('code', 'ilike', name)] + args, limit=limit)
        if not records:
            records = self.search([('name', operator, name)] + args, limit=limit)
        return records.name_get()

    @api.multi
    @api.depends(
        'transaction_ids',
        'transaction_ids.withdrawal',
        'transaction_ids.deposit',
        'transaction_ids.state'
    )
    def compute_total(self):
        for r in self:
            td = 0.0
            tw = 0.0
            tcl = 0.0
            for tr in r.transaction_ids:
                if tr.state == "clearing":
                    tcl += tr.deposit - tr.withdrawal
                elif tr.state == 'confirmed':
                    td += tr.deposit
                    tw += tr.withdrawal

            r.total_deposit = td
            r.total_withdrawal = tw
            r.total_onclearing = tcl
            r.balance = td -  tw

    @api.multi
    @api.depends('member_id')
    def get_member_data(self):
        for r in self:
            if r.member_id:
                r.image = r.member_id.partner_id.image
                r.image_medium = r.member_id.partner_id.image_medium
                r.image_small = r.member_id.partner_id.image_small
                r.address = r.member_id.partner_id.contact_address

    @api.multi
    @api.depends(
        'member_id',
        'member_id.name',
        'other_member_ids',
        'code',
        'account_type'
    )
    def compute_name(self):
        for r in self:
            names = []
            if r.member_id:
                names.append(r.member_id.name)
            if r.other_member_ids and r.account_type != 'cbu':
                #names.append(r.member_id2.name)
                names.append("et al.")
            name = " ".join(names)
            r.name_no_code = name
            if r.code:
                name = r.code + " - " + name
            r.name = name

    @api.multi
    def approve_account(self):
        for r in self:
            if r.custom_months<0:
                raise ValidationError(_("Cannot set custom months period to less than zero."))
            r.state = "open"
            if (r.code == "NONE" or not r.code):
                if r.account_type == "cbu":
                    if r.member_id.is_approved:
                        r.code = r.member_id.code
                else:
                    if r.account_type_id.sequence_id:
                        #r.code = r.account_type_id.code + "-" + r.account_type_id.sequence_id.next_by_id()
                        r.code = r.account_type_id.code + "-" + r.account_type_id.sequence_id.next_by_id()

    @api.multi
    def activate_account(self):
        trcode_id = self.env['wc.tr.code'].search([
            ('code','=','D->A')
        ], limit=1)
        if not trcode_id:
            raise Warning(_("No transaction type defined for dormant to active (D->A)."))
        for r in self:
            trans = r.transaction_ids.create({
                'account_id': r.id,
                'trcode_id': trcode_id[0].id,
            })
            trans.confirm()
            trans.approve()
            #r.state = "open"

    @api.multi
    def close_account(self):
        for r in self:
            r.state = "closed"

    @api.multi
    def open_account(self):
        for r in self:
            r.state = "open"

    @api.multi
    def create_transaction(self):
        self.ensure_one()
        domain = []
        #context = "{'default_account_id': %d, 'filter_trans_type': '%s'}" % (self.id, self.account_type)
        context = "{'default_account_id': %d}" % (self.id)
        view_id = self.env.ref('wc_account.form_transaction')
        return {
            'name': 'Create Transaction',
            'domain': domain,
            'view_id': view_id and view_id.id or False,
            'res_model': 'wc.account.transaction',
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'view_type': 'form',
            'context': context,
            #'target': 'current',
            'target': 'self',
            #'target': 'new',
        }

    @api.model
    def get_balance_at_date(self, account_id, date):
        self.ensure_one()
        trans = self.env['wc.account.transaction'].search([
            ('account_id','=',account_id),
            ('state','=','confirmed'),
            ('date','<=',date),
        ])
        balance = 0.0
        for tr in trans:
            balance += tr.deposit - tr.withdrawal
        return balance

    @api.multi
    def print_passbook(self):
        _logger.debug("print_passbook: base")
        return {}

    #ascii name
    @api.multi
    @api.depends('member_id','member_id.name')
    def get_clean_name(self):
        for r in self:
            name = ""
            if r.member_id and r.member_id.name:
                a = r.member_id.name
                enye_caps = u"\u00D1"
                enye = u"\u00F1"
                name = a.replace(enye_caps, "N").replace(enye,"n").encode('ascii','replace')
            r.clean_name = name


#
