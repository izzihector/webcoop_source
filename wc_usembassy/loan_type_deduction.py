# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
import odoo.addons.decimal_precision as dp
from datetime import datetime
from dateutil.relativedelta import relativedelta
import math
import logging
EPS = 0.00001

_logger = logging.getLogger(__name__)
DF = "%Y-%m-%d"

#add fields and  for [f600]

class Deductions(models.Model):
    _inherit = "wc.loan.type.deduction"
    
    #this Interest flag is special feature for usemb, this is not good practice because interest should be calculated by interest rate and term
    deduction_type = fields.Selection(selection_add=[('interest','Base Interest')]
               ,help="""
                 [CBU]:deposit on member's CBU account
                 [Saving]:deposit on member's saving account")
                 [Interest]:this deduction is combined with upfront interest and it is regarded as interest in loan disclosure report
                 """)

    @api.onchange('deduction_type')
    def on_deduction_deposit_type(self):
        super(Deductions,self).on_deduction_deposit_type()
        for ded in self:
            if ded.deduction_type == 'interest':
                ded.code = 'BASE-INT'
#                 if ded.loan_type_id==False or ded.loan_type_id.interest_income_account_id==False:
                if ded.loan_type_id==False or ded.loan_type_id.interest_income_account_id==False or ded.loan_type_id.interest_income_account_id.id==False:
                    ded.gl_account_id = self.env.user.company_id.interest_income_account_id.id
                else:
                    ded.gl_account_id = self.loan_type_id.interest_income_account_id.id
    
    @api.constrains('deduction_type','gl_account_id','loan_type_id.interest_income_account_id')
    def validate_gl_account_for_interest(self):
        if self.deduction_type == 'interest':
            if self.loan_type_id==False or self.loan_type_id.interest_income_account_id==False:
                if self.gl_account_id == self.env.user.company_id.interest_income_account_id.id:
                    raise ValidationError(_("Interest income gl account is not matched with BASE-INT deduction's gl account"))
            else:
                if self.gl_account_id == self.loan_type_id.interest_income_account_id.id:
                    raise ValidationError(_("Interest income gl account is not matched with BASE-INT deduction's gl account"))

    @api.onchange('deduction_target_account_type')
    def onchange_deduction_target(self):
        for ded in self:
            if ded.deduction_type != 'interest':
                super(Deductions,ded).onchange_deduction_target()
            
    #f600
    @api.multi
    @api.constrains('code')
    def validate_deduction_code_for_base_int(self):
        for r in self:
            if r.code =='BASE-INT' and r.deduction_type != 'interest':
                raise ValidationError(_("Please select interest in deduction type in case of interest advance deduction."))
 