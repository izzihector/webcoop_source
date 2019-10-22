
from odoo import models, fields, api, _
from odoo.exceptions import Warning, ValidationError,UserError
import odoo.addons.decimal_precision as dp
from datetime import datetime
from dateutil.relativedelta import relativedelta
import logging

_logger = logging.getLogger(__name__)
DF = "%Y-%m-%d"
EPS = 0.00001

class LoanPaySearchWizard(models.TransientModel):
    _name = "wc.loan.pay.search.wizard"
    _description = "Search"

    company_id = fields.Many2one('res.company', string='Branch', readonly=True,
        default=lambda self: self.env['res.company']._company_default_get('wc.loan.pay.search.wizard'))
    
    loan_type_id = fields.Many2one('wc.loan.type')
#     due_date_from = fields.Date('Due Date From')
    due_date_to = fields.Date('Due Date To')    
    name = fields.Char(readonly=True,default='Payment Target Search')
    member_id = fields.Many2one('wc.member')
    

    member_count = fields.Integer('Member Count', readonly=True)
    loan_count = fields.Integer('Loan Count', readonly=True)

    is_include_lumpsum = fields.Boolean('Include Lumpsum Loan',default=False
                                        ,help="Please set off in this flag basically because you should re-calculate interest depending on the received date ,in case of lumpsum ")


    def get_domain_for_recon_search(self): 
        domain = []
        domain.append(('loan_id.company_id','=',self.company_id.id))
        #in case of reversed payment , the status of loan detail is paid(when daily posting the status becomes due again
#        domain.append(('state','in',['due','next_due','paid']))
        domain.append(('loan_id.state','in',['approved','past-due']))
        domain.append(('total_due','>',0))
 
        if self.loan_type_id:
            domain.append(('loan_id.loan_type_id','=',self.loan_type_id.id))        
#         if self.due_date_from:
# #             date_from = fields.Date.from_string(self.due_date_from).strftime("%B %d, %Y")
#             date_from = self.due_date_from
#             domain.append(('date_due','>=',date_from))        
        if self.due_date_to:
#             date_to = fields.Date.from_string(self.due_date_to).strftime("%B %d, %Y")            
            date_to = self.due_date_to
            domain.append(('date_due','<=',date_to))
        if self.member_id:
            domain.append(('member_id','=',self.member_id.id))
        if not self.is_include_lumpsum:
            domain.append(('loan_id.payment_schedule','!=','lumpsum'))
            
        return domain

    def search_target(self):
        
        domain = self.get_domain_for_recon_search()
        lines = self.env['wc.loan.detail'].search(domain)
        loans = self.env['wc.loan.detail'].search(domain).mapped('loan_id')
        
        #remove current tmp if there are rec having same reconcile_id_w
        same_rec = self.env['wc.loan.pay.reconcile.line.tmp'].search([('reconcile_id_w','=',self.id)])
        if same_rec:
            same_rec.unlink()
        
        i = 0
        for loan in loans:
            i += 1
            domain2 = self.get_domain_for_recon_search()
            domain2.append(('loan_id','=',loan.id))
            lines_for_the_loan =lines.search(domain2)

            amount_due=0.0
            principal_due=0.0
            interest_due=0.0
            penalty_due=0.0
            others_due=0.0
            
            for det in lines_for_the_loan:
                amount_due += max(0.0,det.total_due)
                principal_due += max(0.0, det.principal_due - det.principal_paid)
                interest_due  += max(0.0, det.interest_due - det.interest_paid)
                penalty_due += max(0.0, det.penalty_adjusted - det.penalty_paid)
                others_due += max(0.0, det.others_due - det.others_paid)
            
            val = {
                'reconcile_id_w':self.id,
                'member_id':loan.member_id.id,
                'loan_id':loan.id,
                't_loan_details':[(6,0,lines_for_the_loan.ids)],
                'company_id':loan.company_id.id,
                'amount_due':amount_due,
                'principal_due':principal_due,
                'interest_due':interest_due,
                'penalty_due':penalty_due,
                'others_due':others_due,
            }
            self.env['wc.loan.pay.reconcile.line.tmp'].create(val)
            _logger.debug("create: line=%s", val)

        search_condition_str = "(Search condition : Loan Type=%s  Due Date <=%s  Member=%s)" % (self.loan_type_id.name,self.due_date_to,self.member_id.name)
        
        return {
            'type': 'ir.actions.act_window',
            'name': 'Loan Payment Reconciliation',
            'context': {'default_search_wiz_id':self.id ,'default_search_condition_str':search_condition_str},
            'res_model': 'wc.loan.payment.reconciliation',
            'view_type': 'form',
#             'view_id':view_id and view_id.id or False,
            'target': 'self',
            'view_mode': 'form',
        }
        
        
 
class LoanPaySearchWizardTargetTmp(models.Model):
    _name = "wc.loan.pay.reconcile.line.tmp"
    reconcile_id_w = fields.Integer()
 
    company_id = fields.Many2one('res.company', string='Branch', readonly=True,
        default=lambda self: self.env['res.company']._company_default_get('wc.loan.pay.search.wizard'))
 
    payment_id = fields.Many2one('wc.loan.payment')
     
    member_id = fields.Many2one('wc.member')
    loan_id = fields.Many2one('wc.loan')
    t_loan_details = fields.Many2many('wc.loan.detail')
 
    name = fields.Char()
    amount_due = fields.Float("Amount Due", digits=(12,2), readonly=True)
    amount = fields.Float("Amount", digits=(12,2))

    principal_due = fields.Float("Principal Due", digits=(12,2), readonly=True)
    interest_due = fields.Float("Interest Due", digits=(12,2), readonly=True)
    penalty_due = fields.Float("Penalty Due", digits=(12,2), readonly=True)
    others_due = fields.Float("Other Due", digits=(12,2), readonly=True)


    def each_paymentline_check(self):
        self.ensure_one()
        total_due_inloan=sum(tloan.total_due for tloan in self.t_loan_details)
        if abs(self.amount_due - total_due_inloan)>EPS:
            raise UserError(_("target loan's due is unmatched.Please do reconcile search again."))                        
                        
                        
# class LoanPaySearchWizardTargetTmp(models.Model):
#     _name = "wc.loan.pay.reconcile.line.tmp"
#     _auto = False
# 
#     reconcile_id_w = fields.Integer()
#     company_id = fields.Many2one('res.company')    
#     payment_id = fields.Many2one('wc.loan.payment')    
#     member_id = fields.Many2one('wc.member')
#     loan_id = fields.Many2one('wc.loan')
#     t_loan_details = fields.Many2many('wc.loan.detail')
#     amount_due = fields.Float("Amount Due", digits=(12,2), readonly=True)
#     amount = fields.Float("Amount", digits=(12,2))
# 
#     @api.model_cr
#     def init(self):
#         tools.drop_view_if_exists(self._cr, 'wc_loan_pay_reconcile_line_tmp')
#         self._cr.execute ("""
#            create or replace view 
#                 wc_loan_pay_reconcile_line_tmp as 
#            select * from xxxxx where yyyy
#         """)

    
class LoanPaySearchWizardTarget(models.Model):
    _name = "wc.loan.pay.reconcile.line"

    is_selected_tmp = fields.Boolean()
    reconcile_id = fields.Many2one('wc.loan.payment.reconciliation')
    company_id = fields.Many2one('res.company', string='Branch', readonly=True,
        default=lambda self: self.env['res.company']._company_default_get('wc.loan.pay.search.wizard'))

    
    t_loan_details = fields.One2many('wc.loan.detail','payment_reconciliation_line_id')

    #2 payment line will be linked, in case of payment is reversed  
    payment_ids = fields.One2many('wc.loan.payment','payment_reconciliation_line_id')
    
    member_id = fields.Many2one('wc.member')
    loan_id = fields.Many2one('wc.loan')
    name = fields.Char()
    amount_due = fields.Float("Amount Due", digits=(12,2), readonly=True)
    amount = fields.Float("Amount", digits=(12,2))
    
    principal_due = fields.Float("Principal Due", digits=(12,2), readonly=True)
    interest_due = fields.Float("Interest Due", digits=(12,2), readonly=True)
    penalty_due = fields.Float("Penalty Due", digits=(12,2), readonly=True)
    others_due = fields.Float("Other Due", digits=(12,2), readonly=True)


    note = fields.Text(string='Notes')
    is_canceled = fields.Boolean(default=False)
    is_reversed = fields.Boolean(compute='check_is_reversed')
    reversed_date = fields.Date('Reversed Date',compute='check_is_reversed')
    
    #state = fields.Selection(related="collection_id.state", readonly=True, store=True)
#     state = fields.Selection([
#         ('draft','Draft'),
#         ('cancelled','Cancelled'),
#         ('confirmed','Confirmed'),
#     ], string='State', default=lambda self: 'draft', readonly=True)

    @api.multi
    @api.depends('payment_ids')
    def check_is_reversed(self):
        for line in self:
            for pay in line.payment_ids:
                if pay.is_reversed and pay.amount < 0:
                    line.is_reversed = True
                    line.reversed_date = pay.date

        
    def each_paymentline_check(self):
        self.ensure_one()
        total_due_inloan=sum(tloan.total_due for tloan in self.t_loan_details)
        if abs(self.amount_due - total_due_inloan)>EPS:
            raise UserError(_("target loan's due is unmatched.Please do reconcile search again."))                        

        
        
