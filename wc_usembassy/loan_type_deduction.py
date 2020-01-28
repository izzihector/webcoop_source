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
    #20200120 mod for lgf type deduction
    deduction_type = fields.Selection(selection_add=[('interest','Base Interest'),('lgf','Deposit on LGF Type Saving Account')]
               ,help="""
                 [CBU]:deposit on member's CBU account
                 [Saving]:deposit on member's saving account
                 [LGF]:deposit on lgf type saving
                 [Interest]:this deduction is combined with upfront interest and it is regarded as interest in loan disclosure report
                 """)
    
    #20200120 add for lgf type deduction 
    code_w_deduction_type = fields.Char(compute="compute_code_w_ded")
    
    #20200120 remove sql constrains ,so that LGF type deduction item and Saving type deduction can be set in same loan
    #instead of checking unique code , add [validate_code_constrains] logic in wc.loan.type model,
    #,so that , code 'SA' can be used in same loan type as long as the deduction type is different.
    
    _sql_constraints = [
        ('unique_code', 'check(1=1)', '')
       ]
    
    
    is_lgf_type = fields.Boolean(compute='compute_is_lgf_type')

    
    @api.depends('deduction_type')
    def compute_is_lgf_type(self):
        for ded in self:
            if ded.deduction_type == 'lgf':
                self.is_lgf_type = True
            else:
                self.is_lgf_type = False
                
        

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

            #20200120 add for lgf type
            elif ded.deduction_type == 'lgf':
                ded.code = 'SA'
                ded.factor = False
                ded.amount = False
                res = self.env['wc.account.type'].search([('category','=','sa'),('is_lgf','=',True)])
                if len(res)==0:
                    raise ValidationError(_("LGF Type Saving account type is not registered"))
                elif len(res)==1:
                    ded.deduction_target_account_type = res[0] 
                else:
                    ded.deduction_target_account_type = False
            elif ded.deduction_type == 'sa':
                res = self.env['wc.account.type'].search([('category','=','sa'),('is_lgf','=',False)])
                if len(res)==0:
                    raise ValidationError(_("Saving account type is not registered"))
                elif len(res)==1:
                    ded.deduction_target_account_type = res[0] 
                else:
                    ded.deduction_target_account_type = False


            
    
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

    @api.multi
    @api.constrains('code')
    def validate_deduction_code_for_cbu_sa(self):
        for r in self:
            if r.code =='CBU' and r.deduction_type != 'cbu':
                raise ValidationError(_("Please select cbu in deduction type in case of CBU depsit deduction."))
            if r.code =='SA' and (r.deduction_type != 'sa' and r.deduction_type != 'lgf'):
                #20200120 found bug when lgf test
#                 raise ValidationError(_("Please select sa in deduction type in case of CBU depsit deduction."))
                raise ValidationError(_("Please select saving or lgf in deduction type in case of Saving depsit deduction."))

