
from odoo import models, fields, api, _
from odoo.exceptions import Warning, ValidationError
import odoo.addons.decimal_precision as dp
from datetime import datetime
from dateutil.relativedelta import relativedelta
import logging

_logger = logging.getLogger(__name__)
DF = "%Y-%m-%d"
EPS = 0.00001

#IMPLEMENTATION = True

class LoanPaymentRebate(models.Model):
    _name = "wc.loan.payment.rebate"
    _description = "Loan Payment Rebate"
    _inherit = [ 'mail.thread' ]

    _order = "date desc, name"

    company_id = fields.Many2one('res.company', string='Branch', readonly=True,
        default=lambda self: self.env['res.company']._company_default_get('wc.loan'))

    name = fields.Char("Name",required=True,
        readonly=True, states={'draft': [('readonly', False)]})

    loan_id = fields.Many2one('wc.loan', 'Loan', ondelete='restrict',
        readonly=True, states={'draft': [('readonly', False)]})
    
#     or_number = fields.Char("O.R. Number",
#         readonly=True, states={'draft': [('readonly', False)]})

#     check_number = fields.Char("Check No.",
#         readonly=True, states={'draft': [('readonly', False)]})

    def get_first_open_date(self):
        company_id = self.env.user.company_id.id
        return self.env['wc.posting'].get_first_open_date(company_id)

    date = fields.Date("Date", required=True, default=get_first_open_date,
        readonly=True, states={'draft': [('readonly', False)]}, index=True)

    member_id = fields.Many2one('wc.member', string='Member',
        readonly=True, related='loan_id.member_id')

    amount = fields.Float("Amount", digits=(12,2))

    note = fields.Text(string='Detail Reason')

    active = fields.Boolean(default=True)
    #posted = fields.Boolean(store=True, compute="get_posted")

    loan_state = fields.Selection(related="loan_id.state", readonly="1")

    is_reversed = fields.Boolean("Reversed")

    @api.model
    def _get_default_account(self):
        company_id = self.env.user.company_id
        return company_id.loan_payment_debate_account_id
    
    deb_gl_account_id = fields.Many2one('account.account',required=True,
                                    default=lambda self:self._get_default_account(), 
                                    string='GL Account(debit)',help="set account title for the rebate (this account reflects on debit account ,credit side is cash account anytime.)", ondelete="set null")
#     cre_gl_account_id =  fields.Many2one('account.account', 
#                                          string='GL Account(credit)', ondelete="restrict")
    deposit_account_id = fields.Many2one('wc.account', string='CBU/Saving Account', ondelete="restrict")

    is_rebate_to_member_account = fields.Boolean('Check if rebate to Member saving/cbu account, uncheck if cash.')
    
    rebatable_amount = fields.Float(related="loan_id.rebatable_amount")
    
    posting_id = fields.Many2one('wc.posting'
                                 ,track_visibility='onchange'
                                 , string='Posting Ref',
        required=False, readonly=True, ondelete="set null")

#     reverse_posting_id = fields.Many2one('wc.posting'
#                                  ,track_visibility='onchange'
#                                  , string='Posting Ref',
#         required=False, readonly=True, ondelete="set null")

    state = fields.Selection([
        ('draft','Draft'),
        ('cancelled','Cancelled'),
        ('confirmed','Confirmed')
    ], string='State', default='draft',
        track_visibility='onchange', readonly=True)


    def get_rebatable_amount_without_self(self):
        self.ensure_one()
        rebate=self
        loan = rebate.loan_id
        amt=0.0
        
        if len(loan.details) > 0:
            if loan.rebatable_payment_type == 'interest_only':
                amt = sum(a.interest_paid for a in loan.details)
            elif loan.rebatable_payment_type == 'int_penalty':
                amt = sum(a.interest_paid+a.penalty_paid for a in loan.details)
            else:
                amt = sum(a.interest_paid for a in loan.details)
            
        #add upfront advance interest 20191105
        for ded in loan.deduction_ids:
            if ded.code == "ADV-INT":
                amt += ded.amount 
    
            
        for a in loan.payment_rebate_ids:
#             if a.state =="confirmed":
            if a.state =="confirmed" and a.id != rebate.id:
                amt -= a.amount
        return amt


    @api.multi
    def cancel(self):
        for r in self:
            if (r.state in ['draft']):
                r.state = 'cancelled'


    
    @api.constrains('amount','rebatable_amount','state')
    def check_if_amount_possible(self):
        if self.amount > self.get_rebatable_amount_without_self():
            raise ValidationError(_("Cannot input amount over rebatable amount."))
        if self.amount <EPS and not self.is_reversed and self.state != 'cancelled':
            raise ValidationError(_("Please input the amount more than zero."))
        if -self.amount <EPS and self.is_reversed:
            raise ValidationError(_("Cannot reverse."))

        
#todo: test simultanously update of payment
        
    def confirm_payment_rebate(self):
        self.ensure_one()
        if self.state != "draft":
            return
        else:
            self.state = "confirmed"
            
        _logger.debug("**confirm_payment_rebate: amt=%0.2f", self.amount)

        dep_account = self.deposit_account_id
        ref = "loan rebate [%s]" % (self.name)
        loan = self.loan_id
        
        if dep_account:
            tra = self.env['wc.account.transaction']
            rec = tra.create_deposit_transaction_util(dep_account,self.amount,ref,loan)
            rec.confirm()
            rec.approve()


    def do_reverse_payment_rebate(self):
        self.ensure_one()

        if self.state != "confirmed" or self.is_reversed:
            return
        else:
            self.is_reversed = True
        
        _logger.debug("**revesre_payment_rebate: amt=%0.2f", self.amount)

        dep_account = self.deposit_account_id
        ref = "reverse loan rebate [%s]" % (self.name)
        loan = self.loan_id
        
        if dep_account:
            tra = self.env['wc.account.transaction']
            rec = tra.create_deposit_deposit_reverse_transaction_util(dep_account,self.amount,ref,loan)
            rec.confirm()
            rec.approve()

    def get_copy_val_for_reverse_rebate(self):
        vals ={
            'company_id':self.env.user.company_id.id,
            'loan_id': self.loan_id.id,
            'loan_id': self.loan_id.id,
            'amount': -self.amount,
            'is_rebate_to_member_account':self.is_rebate_to_member_account,
            'deposit_account_id':self.deposit_account_id.id,
            'deb_gl_account_id':self.deb_gl_account_id.id,
            'name': 'Reverse Payment %s' % self.name,
            'is_reversed': True,
            'state': 'confirmed',
            'note':'Reverse of %s' % (self.name)
        }
        return vals


    
    def reverse_payment_rebate(self):
        self.ensure_one()
        self.do_reverse_payment_rebate()

        vals = self.get_copy_val_for_reverse_rebate()
        rec = self.create(vals)
        

#when confirm ,
#make account transaction , refer to payment confirm



#when reverse
#make account transaction , refer to payment confirm
