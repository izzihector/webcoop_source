
from odoo import models, fields, api, _
from odoo.exceptions import Warning, ValidationError, UserError
import odoo.addons.decimal_precision as dp
from datetime import datetime
from dateutil.relativedelta import relativedelta
import math
import logging
from pickle import FALSE
#from util import *

_logger = logging.getLogger(__name__)
DF = "%Y-%m-%d"
EPS = 0.00001

#IMPLEMENTATION = True

class Loan(models.Model):
    _inherit = "wc.loan"
    
    @api.constrains('member_id','deduction_ids.deposit_account_id')
    def check_member_and_deduction_account(self):
        self.ensure_one()
        loan = self
        member = loan.member_id
        for ded in loan.deduction_ids:
            if ded.deposit_account_id and member.id != ded.deposit_account_id.member_id.id:
                raise UserError(_("Member id is unmatched with member set in deduction items account.Please correct saving or cbu account again."))
                
    
    def unlink_recreate_deduction(self):
        self.ensure_one()
        loan = self
        if loan.restructured_from_id:
            raise UserError(_("This is restructured loan , you need to manually add deduction items."))
        
        if loan.state=='draft' and loan.loan_type_id and loan.amount>0.0:
            loan.deduction_ids.unlink()
            deductions = loan.get_deductions(loan)
            if deductions:
                _logger.debug("**all_deductions: %s", deductions)
                loan.deduction_ids = deductions


    def recompute_deduction(self):
        self.ensure_one()
        loan = self
        #recompute deduction value by updated factor and loan amount 
        #   if deduction calculation type is [factor].
        l_amount = loan.amount
        
        for d in loan.deduction_ids:
            factor = False

            if d.factor>0.0:
                factor = d.factor
                d.amount = round(l_amount * factor/100.0, 2)
    
    def generate_deductions(self):
        pass
        
        
    @api.model
    def create(self, vals):
        res = super(Loan, self).create(vals)
        res.unlink_recreate_deduction()
        return res
        