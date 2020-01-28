
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
    _inherit = "wc.loan.payment.rebate"

    #20200122 add for usembassy's consolidate rebate
    is_rebate_at_consolidation = fields.Boolean('Rebate at loan consolidation')
    rebate_target_consolidated_loan_id = fields.Many2one('wc.loan')
    
    amount_disp = fields.Float("Amount",digits=(12,2),compute="simple_display_amount")
#     amount = fields.Float("Amount", digits=(12,2))
    
    @api.depends('amount')
    def simple_display_amount(self):
        for a in self:
            a.amount_disp = a.amount
    
    @api.onchange('date','loan_id')
    def onchange_date(self):
        for rebate in self:
            if rebate.loan_id and rebate.date:
                loan = rebate.loan_id
                a,b, amt = loan.get_rebate_amount_at_date(rebate.date)
                self.amount = amt

    def get_first_open_date(self):
        company_id = self.env.user.company_id.id
        return self.env['wc.posting'].get_first_open_date(company_id)

                
#     @api.model
#     def create(self,values):
#         rebate = super(LoanPaymentRebate,self).create(values)
#         if rebate.state == 'draft' and not (rebate.amount == rebate.amount_tmp):
#             rebate.amount = rebate.amount_tmp
#         return rebate
#     
#     
#     @api.multi
#     def write(self,values):
#         res = super(LoanPaymentRebate,self).write(values)
#         if self.state == 'draft' and not (self.amount == self.amount_tmp):
#             self.amount = self.amount_tmp
#         return res
    
    

