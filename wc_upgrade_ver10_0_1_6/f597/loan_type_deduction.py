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


class Deductions(models.Model):
    _inherit = "wc.loan.type.deduction"
    
    deduction_type = fields.Selection([('cbu','Deposit on CBU Account'),('sa','Deposit on Saving Account')])
    deduction_target_account_type = fields.Many2one('wc.account.type')

    deduction_target_account_type_disp = fields.Many2one('wc.account.type',compute='compute_disp')
    gl_account_id_disp = fields.Many2one('account.account',string='GL Account',compute='compute_disp')
    code_disp = fields.Char("Code",compute='compute_disp')


    @api.depends('deduction_target_account_type','gl_account_id','code')
    def compute_disp(self):
        for ded in self:
            ded.deduction_target_account_type_disp = ded.deduction_target_account_type
            ded.gl_account_id_disp = ded.gl_account_id
            ded.code_disp = ded.code

#need to avoid interest and     
    @api.multi
    @api.constrains('code')
    def validate_deduction_code_for_cbu_sa(self):
        for r in self:
            if r.code =='CBU' and r.deduction_type != 'cbu':
                raise ValidationError(_("Please select cbu in deduction type in case of CBU depsit deduction."))
            if r.code =='SA' and r.deduction_type != 'sa':
                raise ValidationError(_("Please select sa in deduction type in case of CBU depsit deduction."))

    
    #b597
    @api.onchange('deduction_type')
    def on_deduction_deposit_type(self):
        for ded in self:
            if ded.deduction_type == 'cbu':
                ded.code = 'CBU'
                res = self.env['wc.account.type'].search([('category','=','cbu')])
                if len(res)==0:
                    raise ValidationError(_("CBU account type is not registered"))
                elif len(res)==1:
                    ded.deduction_target_account_type = res[0]
                else:
                    ded.deduction_target_account_type = False
     
            elif ded.deduction_type == 'sa':
                ded.code = 'SA'
                res = self.env['wc.account.type'].search([('category','=','sa')])
                if len(res)==0:
                    raise ValidationError(_("Saving account type is not registered"))
                elif len(res)==1:
                    ded.deduction_target_account_type = res[0] 
                else:
                    ded.deduction_target_account_type = False
            else:
                ded.code = False
                ded.deduction_target_account_type = False
     
    @api.onchange('deduction_target_account_type')
    def onchange_deduction_target(self):
        for ded in self:
            type= ded.deduction_target_account_type
            if type:
                ded.gl_account_id = type.get_dep_account_id()
            else:
                ded.gl_account_id = False

    @api.model
    def create(self,values):
        a = self.deduction_target_account_type
        res = super(Deductions,self).create(values)
        return res
            


