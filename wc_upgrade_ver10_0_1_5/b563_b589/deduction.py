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
    _inherit = "wc.loan.deduction"

    is_created_by_manual = fields.Boolean('')

    #b589
    @api.onchange('code')
    def on_change_ded_code(self):
        self.ensure_one()
        
        member_id = self.loan_id.member_id.id
        domain_str="""
           ['|',('account_type','=','%s'),('account_type','=','%s'),'|'
           ,('member_id','=',%s),('other_member_ids','in',%s),('state','=','open')]
           """
        if self.code and self.code.upper() == "SA" and member_id:
            domain_str = domain_str % ('sa','SA',member_id,member_id)
        elif self.code and self.code.upper() == "CBU" and member_id:
            domain_str = domain_str % ('cbu','CBU',member_id,member_id)
        else:
            domain_str = "[('member_id','=',False)]"
    
        return {'domain':{'deposit_account_id':domain_str}}
    
    #b563
    @api.constrains('is_created_by_manual','code')
    def validate_for_manual_input(self):
        self.ensure_one()
        if self.is_created_by_manual:
            if self.code.upper() in ['INT','PCP','PEN','ADV-INT']:
                raise UserError(_("Cannot use reserved deduction code [%s].") % (self.code))
            
    
