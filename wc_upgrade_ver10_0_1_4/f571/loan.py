# -*- coding: utf-8 -*-


from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime
from dateutil.relativedelta import relativedelta
import logging

_logger = logging.getLogger(__name__)
DF = "%Y-%m-%d"
EPS = 0.00001

#IMPLEMENTATION = True

class Loan(models.Model):
    _inherit = "wc.loan"
    
    term_payments_for_input = fields.Integer("Payment Count",
              readonly=True, states={'draft': [('readonly', False)]})

    
    
    schedule_making_type = fields.Selection(
        [('periods', 'By Maturity Period'),('count', 'By Payment Count')],
        string='Schedule Generate Type',
        help="""
        Select [By Maturity Period] in case making schedule from maturity period and payment scheudle.
        Select [By Payment Count] in case you want to make schedule from payment schedule and count of payment.
        You cannot select [By Payment Count] ,in case of payment schedule is [days][half-month][lumpsum].
        """,
              readonly=True, states={'draft': [('readonly', False)]})
     
    @api.constrains('payment_schedule')
    def check_schedule_making_type(self):
        for rec in self:
            if rec.schedule_making_type == 'count':
                if rec.payment_schedule == "days" or \
                   rec.payment_schedule == "half-month" or \
                   rec.payment_schedule == "Lumpsum":
                    raise UserError(_("In case of [%s] schedule, you cannot use [By Terms] as Schedule Generate Type.") % (rec.payment_schedule))
            
            

    @api.onchange('loan_type_id')
    def oc_loan_type_id(self):
        super(Loan,self).oc_loan_type_id()
        
        self.term_payments_for_input = self.loan_type_id.term_payments_for_input
        self.schedule_making_type = self.loan_type_id.schedule_making_type
        
        
#     
#     @api.onchange('term_payments_for_input','schedule_making_type')
#     def oc_term_payments_for_input(self):
#         for rec in self:
#             self.compute_date_maturity_from_inputterm()
        
        
    def compute_date_maturity_from_inputterm(self):
        rec = self
        
        if rec.schedule_making_type == "count":
            if rec.payment_schedule:
                if rec.payment_schedule == "day" or \
                    rec.payment_schedule == "half-month" or \
                    rec.payment_schedule == "lumpsum":
                    return "force_to_period",False,False
                
                t = rec.term_payments_for_input
                if (rec.payment_schedule=='day'):
                    raise Warning(_("You cannot change this ,in case of day schedule."))
                elif (rec.payment_schedule=='week'):
                    mat = t
                    peri = "weeks"
                elif (rec.payment_schedule=='half-month'):
                    raise Warning(_("You cannot change this ,in case of day semi-monthly schedule."))
                elif (rec.payment_schedule=='15-days'):
                    mat = t * 15
                    peri = "days"
                elif (rec.payment_schedule=='month'):
                    mat = t
                    peri = "months"
                elif (rec.payment_schedule=='30-days'):
                    mat = t * 30
                    peri = "days"
                elif (rec.payment_schedule=='quarter'):
                    mat = t * 3
                    peri = "months"
                elif (rec.payment_schedule=='semi-annual'):
                    mat = t * 6
                    peri = "months"
                elif (rec.payment_schedule=='year'):
                    mat = t * 12
                    peri = "months"
                elif (rec.payment_schedule=='x-days'):
                    mat = t * rec.payment_schedule_xdays
                    peri = "days"

                return "change",mat,peri
            else:
                return "stay",False,False
            
        elif rec.schedule_making_type == "periods":
            return "periods",False,False
        else:
            return False,False,False

    @api.onchange('term_payments_for_input',
                  'payment_schedule',
                  'payment_schedule_xdays',
                  'schedule_making_type')
    def oc_for_schedule_making_type(self):
        for rec in self:
            result,mat,peri = rec.compute_date_maturity_from_inputterm()
            if result=="stay":
                continue
            elif result=="change":
                rec.maturity = mat
                rec.maturity_period = peri
            elif result == "force_to_period":
                return {'value':{'schedule_making_type':'periods',
                                 'term_payments_for_input':False}}
            elif result=="periods":
                rec.term_payments_for_input = False
            else:
                rec.term_payments_for_input = False
                rec.maturity = False
                rec.maturity_period = False
                

        
    @api.multi
    def move_to_restructured(self):
        self.ensure_one()
        #self.check_gl_accounts_setup()
 
        pcp_amount = self.principal_balance
        int_amount = 0.0
        penalty_amount = 0.0
        for d in self.details:
            int_amount += d.interest_due - d.interest_paid
            penalty_amount += d.penalty + d.adjustment - d.penalty_paid
 
        lines = []
 
        if pcp_amount:
            val = {
                'sequence': 1,
                'code': 'PCP',
                'name': 'Restructured Principal',
                'recurring': False,
                'net_include': True,
                'factor': 0.0,
                'amount': pcp_amount,
                'gl_account_id': self.get_ar_account_id(),
            }
            lines.append( (0, False, val) )
 
        if int_amount:
            val = {
                'sequence': 2,
                'code': 'INT',
                'name': 'Restructured Interest',
                'recurring': False,
                'net_include': True,
                'factor': 0.0,
                'amount': int_amount,
                'gl_account_id': self.get_interest_income_account_id(),
            }
            lines.append( (0, False, val) )
 
        if penalty_amount:
            val = {
                'sequence': 3,
                'code': 'PEN',
                'name': 'Restructured Penalty',
                'recurring': False,
                'net_include': True,
                'factor': 0.0,
                'amount': penalty_amount,
                'gl_account_id': self.company_id.penalty_account_id.id,
            }
            lines.append( (0, False, val) )
        
        #refactoring 20191018, for future modify.In order to minimize affection in case of adding new field on loan.
        #in case of new field add,only [copy_and_create_restructured_loan] module need to be modified.
        res = self.copy_and_create_restructured_loan(lines)

#         #modify start b561  
#         res = self.create({
#             'restructured_from_id': self.id,
#             'loan_type_id': self.loan_type_id.id,
#             'maturity': self.maturity,
#             'payment_schedule': self.payment_schedule,
#             'term_payments': self.term_payments,
#             'is_fixed_payment_amount': self.is_fixed_payment_amount,
#             'interest_rate': self.interest_rate,
#             'amount': self.amount,
#             'term_payments': self.term_payments,
#             'company_id': self.company_id.id,
#             'member_id': self.member_id.id,
#             'comaker_ids': self.comaker_ids,
#             'deduction_ids': lines,
#             'payment_schedule_xdays': self.payment_schedule_xdays,#add this line f561
#             
#         })
#         #modify end b561  
 
        self.restructured_to_id = res.id
        self.state = 'restructured'
 
        view_id = self.env.ref('wc_loan.view_loan').id
        context = self._context.copy()
        #context.update({
        #    'default_restructured_to_id': self.id,
        #})
        return {
            'res_id':res.id,
            'name':'New Loan',
            'view_type':'form',
            'view_mode':'form',
            'views' : [(view_id,'form')],
            'res_model':'wc.loan',
            'view_id':view_id,
            'type':'ir.actions.act_window',
            'target':'current',
            #'target':'new',
            'context':context,
        }

#refactoring from move_to_restructure module (20192018)
    @api.multi
    def copy_and_create_restructured_loan(self,lines=[]):
        self.ensure_one()

        #modify start b561  ,f571
        res = self.create({
            'restructured_from_id': self.id,
            'loan_type_id': self.loan_type_id.id,
            'maturity': self.maturity,
            'payment_schedule': self.payment_schedule,
            'term_payments': self.term_payments,
            'term_payments_for_input':self.term_payments_for_input,#add this line f571
            'schedule_making_type':self.schedule_making_type,#add this line f571
            'is_fixed_payment_amount': self.is_fixed_payment_amount,
            'interest_rate': self.interest_rate,
            'amount': self.amount,
            'term_payments': self.term_payments,
            'company_id': self.company_id.id,
            'member_id': self.member_id.id,
            'comaker_ids': self.comaker_ids,
            'deduction_ids': lines,
            'penalty_rate': self.penalty_rate,#add this line b596
            'payment_schedule_xdays': self.payment_schedule_xdays,#add this line f561
            
        })
        
        return res
        #modify end b561  ,f571
            
            