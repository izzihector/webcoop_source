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

class AccountTransaction(models.Model):
    _name = "wc.account.transaction"
    _inherit = "mail.thread"
    _description = "Account Transactions"
    _order = "date desc, name desc"

    account_id = fields.Many2one('wc.account', string='Account',
        index=True, required=True, ondelete="restrict")

    company_id = fields.Many2one(related="account_id.company_id", store=True)

    account_type_id = fields.Many2one(string='Account Type',
        readonly=True, related="account_id.account_type_id")
    account_type = fields.Char(compute="compute_account_type")
    trans_type = fields.Char(compute="compute_account_type")

    #member_id = fields.Many2one(related="cbu_id.member_id", store=True)
    #member_code = fields.Char('Member ID', related="cbu_id.code", store=True)
    hname = fields.Char("Name", compute="compute_hname")

    name = fields.Char("Number", readonly=True, default="DRAFT", track_visibility='onchange')
    date = fields.Date(track_visibility='onchange',
        readonly=True, states={'draft': [('readonly', False)]},
        default=fields.Date.context_today, required=True, index=True)

    confirm_date = fields.Datetime('Timestamp', readonly=True,
        default=fields.Datetime.now)

    reference = fields.Char("Reference",
        readonly=True, states={'draft': [('readonly', False)]}, track_visibility='onchange')
    check_number = fields.Char("Check Number", help="Enter check number or CASH for cash transaction.",
        readonly=True, states={'draft': [('readonly', False)]},
        track_visibility='onchange')

    collection_id = fields.Many2one('wc.collection', string='Collection Ref',
        readonly=True, ondelete="restrict")

    from_loan = fields.Boolean("From Loan",
        readonly=True, states={'draft': [('readonly', False)]})

    trcode_id = fields.Many2one('wc.tr.code', string='Transaction Code',
        readonly=True, states={'draft': [('readonly', False)]},
        track_visibility='onchange', required=True, ondelete="restrict", index=True)

    trcode = fields.Char(related="trcode_id.code", store=True, index=True)
    trcode_description = fields.Char(related="trcode_id.description", readonly=True)
    is_deposit = fields.Boolean(related="trcode_id.is_deposit", readonly=True)
    is_withdrawal = fields.Boolean(related="trcode_id.is_withdrawal", readonly=True)

    #company_currency_id = fields.Many2one(related='account_id.company_id.company_currency_id', store=True)
    deposit = fields.Float(digits=(12,2),
        #readonly=True, states={'draft': [('readonly', False)]},
        track_visibility='onchange')
    withdrawal = fields.Float(digits=(12,2),
        #readonly=True, states={'draft': [('readonly', False)]},
        track_visibility='onchange')
    teller_id = fields.Many2one('res.users', string="Teller",
        default=lambda self: self._uid, readonly=True,
        track_visibility='onchange', ondelete="restrict")
    is_printed = fields.Boolean('Printed', track_visibility='onchange')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('for-approval', 'For Approval'),
        ('cancelled', 'Cancelled'),
        ('clearing', 'Unavailable'),
        ('confirmed', 'Confirmed'),
        #('posted', 'GL Posted'),
    ], 'State', index=True, default="draft", readonly=True, track_visibility='onchange')
    note = fields.Text('Notes', track_visibility='onchange')

    @api.one
    @api.constrains('deposit','withdrawal','trcode_id')
    def _check_zero_values(self):
        trcode = self.trcode_id and self.trcode_id.code or "XXXXX"
        zero_amount = (self.deposit<=0.0 and self.withdrawal<=0.0)
        if zero_amount and (trcode not in ['A->D','D->A','INT']) and not self.env.user._is_superuser():
            raise ValidationError(_("Deposit or Withdrawal amount must be more than 0."))
        if self.withdrawal>self.account_id.balance:
            _logger.debug("**Error withdrawal: bal=%0.2f wamt=%0.2f", self.withdrawal, self.account_id.balance)
            raise ValidationError(_("Cannot withdraw more than balance."))

    @api.multi
    @api.depends('account_id','account_id.account_type_id','account_id.account_type_id.category')
    def compute_account_type(self):
        for r in self:
            acct_type = r.account_id and r.account_id.account_type_id.category
            r.account_type = acct_type
            r.trans_type = (acct_type=='cbu') and 'cbu' or 'sa'

    @api.onchange('account_type')
    def oc_account_id(self):
        self.ensure_one()
        if self.account_type == 'cbu':
            domain = { 'trcode_id': [('trans_type','=','cbu')] }
        else:
            domain = { 'trcode_id': [('trans_type','!=','cbu')] }
        _logger.info("***Change trcode domain: %s", domain)
        return { 'domain': domain }

    @api.onchange('trcode_id')
    def oc_account_id(self):
       self.ensure_one()
       self.withdrawal = 0.0
       self.deposit = 0.0

    @api.multi
    @api.depends('name','account_id')
    def compute_hname(self):
        for r in self:
            r.hname = "%s-%s" % (r.account_id.name, r.name)

    @api.multi
    def clear_check(self):
        for r in self:
            if r.state == 'clearing':
                r.state = 'confirmed'

    def approve(self):
        for r in self:
            if r.state == 'for-approval':
                new_state = 'confirmed'
                if r.trcode_id.code == 'D->A' and r.account_id.state == 'dormant':
                    r.account_id.state = 'open'
                elif r.trcode_id.code == 'A->D' and r.account_id.state == 'open':
                    r.account_id.state = 'dormant'
                r.state = new_state
                r.confirm_date = fields.Datetime.now()

    @api.multi
    def confirm(self):
        for r in self:
            if r.state == 'draft':
                new_state = 'confirmed'
                context = {'ir_sequence_date': r.date}
                r.name = self.env['ir.sequence'].with_context(**context).next_by_code('wc.account.transaction')
                if r.trcode_id.code in ['LCKD','RCKD']:
                    new_state = 'clearing'
                elif r.trcode_id.code == 'A->D' and r.account_id.state == 'open':
                    new_state = 'for-approval'
                elif r.trcode_id.code == 'D->A' and r.account_id.state == 'dormant':
                    new_state = 'for-approval'
                elif r.trcode_id.code in ['3000','CM00','XPLT','RCHK','A->D','D->A']:
                    new_state = 'for-approval'

                #mark for approval if withdrawal more than maintaining
                if r.withdrawal>0.0 and (r.account_id.balance-r.withdrawal)<r.account_id.maintaining_balance:
                    new_state = 'for-approval'

                elif r.withdrawal >= r.account_id.account_type_id.withdrawal_limit:
                    new_state = 'for-approval'

                elif r.deposit >= r.account_id.account_type_id.deposit_limit:
                    new_state = 'for-approval'

                r.state = new_state
                r.confirm_date = fields.Datetime.now()

    @api.multi
    def cancel(self):
        for r in self:
            if (r.state in ['for-approval','draft']) or self.env.user._is_superuser():
                if r.name=='DRAFT':
                    r.name = 'CANCELLED'
                r.state = 'cancelled'

    @api.multi
    def print_line(self):
        self.ensure_one()
        return self.account_id.print_passbook()

    @api.model
    def get_deposit_code_cbu(self):
        trcode_cbu = self.env.ref('wc_account.tr_deposit')
        if not trcode_cbu:
            res = self.env['wc.tr.code'].search([
                ('trans_type','=','cbu'),
                ('is_deposit','=',True),
            ])
            if not res:
                raise Warning(_("Cannot confirm transaction. No CBU deposit transaction type present."))
            trcode_cbu = res[0]
        return trcode_cbu

    @api.model
    def get_deposit_code_sa(self):
        trcode_csd = self.env.ref('wc_account.tr_csd')
        if not trcode_csd:
            res = self.env['wc.tr.code'].search([
                ('trans_type','=','sa'),
                ('is_deposit','=',True),
            ])
            if not res:
                raise Warning(_("Cannot confirm transaction. No account deposit transaction type present."))
            trcode_csd = res[0]
        return trcode_csd


#add 20191102 , create deposit transaction util
    #[Todo]test create_and_confirm_deposit_transaction_util
    def create_and_confirm_deposit_transaction_util(self,dep_account,amount,ref=False,loan=False):
        vals = self.get_val_for_create_deposit_transaction(dep_account,amount,ref,loan)
        context = {'ir_sequence_date': self.env['wc.posting'].get_new_posting_date()}
        vals['confirm_date'] = fields.Datetime.now()
        vals['state'] = 'confirmed'
        vals['name'] = self.env['ir.sequence'].with_context(**context).next_by_code('wc.account.transaction'),
        return self.create(vals)
    
    def create_deposit_transaction_util(self,dep_account,amount,ref=False,loan=False):
        vals = self.get_val_for_create_deposit_transaction(dep_account,amount,ref,loan)
        return self.create(vals)

    def get_val_for_create_deposit_transaction(self,dep_account,amount,ref=False,loan=False):
        date=self.env['wc.posting'].get_new_posting_date()
        trcode_cbu = self.get_deposit_code_cbu()
        trcode_sa = self.get_deposit_code_sa()

        if dep_account.account_type=='cbu':
            trtype_id = trcode_cbu.id
        else:
            trtype_id = trcode_sa.id
        
        if loan:
            loan_id = loan.id
        else:
            loan_id = False
            
        vals = {
            'company_id': self.env.user.company_id.id,
            'account_id': dep_account.id,
            'date': date,
            'deposit': amount,
            'trcode_id': trtype_id,
            'reference': ref,
            'loan_id': loan_id,
            'teller_id': self.env.user.id,
        }
        return vals

    def create_deposit_deposit_reverse_transaction_util(self,dep_account,amount,ref=False,loan=False):
        vals = self.get_val_for_create_deposit_reverse_transaction(dep_account,amount,ref,loan)
        return self.create(vals)

    def get_val_for_create_deposit_reverse_transaction(self,account,amount,ref=False,loan=False):
        date=self.env['wc.posting'].get_new_posting_date()
        trcode_cbu = self.env.ref('wc_account.tr_adjustment')
        vals={}
        if not trcode_cbu:
            res = self.env['wc.tr.code'].search([
                ('trans_type','=','cbu'),
                ('name','ilike','Adjustment'),
            ])
            if not res:
                raise Warning(_("Cannot confirm transaction. No CBU adjustment transaction type present."))
            trcode_cbu = res[0]
        trcode_sa = self.env.ref('wc_account.tr_cm00')
        if not trcode_sa:
            res = self.env['wc.tr.code'].search([
                ('trans_type','=','sa'),
                ('name','ilike','Memo'),
            ])
            if not res:
                raise Warning(_("Cannot confirm transaction. No account adjustment transaction type present."))
            trcode_sa = res[0]
        if account:
            if account.account_type=='cbu':
                trtype_id = trcode_cbu.id
            else:
                trtype_id = trcode_sa.id
            if loan:
                loan_id = loan.id
            else:
                loan_id = False
                
            vals = {
                'account_id': account.id,
                'withdrawal': amount,
                'date': date,
                'trcode_id': trtype_id,
                'reference': ref,
                'loan_id': loan_id,
                'teller_id': self.env.user.id,
            }
            
        return vals
