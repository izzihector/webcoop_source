
from odoo import models, fields, api, _
from odoo.exceptions import Warning, ValidationError
import odoo.addons.decimal_precision as dp
from datetime import datetime
from dateutil.relativedelta import relativedelta
import logging

_logger = logging.getLogger(__name__)
DF = "%Y-%m-%d"

class Loan(models.Model):
    _inherit = "wc.loan"
    
#     reconcile_search_ids = fields.Many2many()
    payment_rebate_ids = fields.One2many('wc.loan.payment.rebate','loan_id',  ondelete='restrict')
    rebate_amount = fields.Float('Rebate Total',compute='compute_rebate')
    rebatable_amount = fields.Float('Rebatable amount',compute='compute_rebatable_amount')

    @api.model
    def _get_rebatable_payment_type(self):
        return self.loan_type_id.rebatable_payment_type

#     rebatable_payment_type = fields.Selection([
#         ('interest_only', 'interest_only'),
#         ('int_penalty', 'int_penalty')],
#         default=lambda self:self._get_rebatable_payment_type,
#         readonly=True)
    rebatable_payment_type = fields.Selection([
        ('interest_only', 'interest_only'),
        ('int_penalty', 'int_penalty')])


    @api.onchange('loan_type_id')
    def set_rebatable_payment_type(self):
        self.ensure_one()
        if self.loan_type_id:
            self.rebatable_payment_type = self._get_rebatable_payment_type()
        else:
            self.rebatable_payment_type = False

    @api.multi
    @api.depends('payment_rebate_ids','payment_rebate_ids.amount')
    def compute_rebate(self):
        for loan in self:
            if len(loan.payment_rebate_ids) > 0:
                amt = sum(a.amount for a in loan.payment_rebate_ids)
                loan.rebate_amount = amt
    
    
    @api.depends('details.interest_paid','details.penalty_paid',
                 'payment_rebate_ids','payment_rebate_ids.state')
    def compute_rebatable_amount(self):
        for loan in self:
            loan.rebatable_amount = loan.get_rebatable_amount()

    def get_rebatable_amount(self):
        loan=self
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
            if a.state =="confirmed":
                amt -= a.amount

        
        return amt
    

    @api.multi
    def add_payment_rebate(self):
        view_id = self.env.ref('wc_loan_payment_rebate.view_loan_payment_rebate_form').id
        context = self._context.copy()
        context.update({
            'default_loan_id': self.id,
        })
        return {
            'name':'Payment',
            'view_type':'form',
            'view_mode':'form',
            'views' : [(view_id,'form')],
            'res_model':'wc.loan.payment.rebate',
            'view_id':view_id,
            'type':'ir.actions.act_window',
            #'res_id':self.loan_id.id,
            'target':'current',
            #'target':'new',
            'context':context,
        }
       
       
        