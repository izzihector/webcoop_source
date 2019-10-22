
from odoo import models, fields, api, _
from odoo.exceptions import Warning, ValidationError, UserError
import odoo.addons.decimal_precision as dp
from datetime import datetime
from dateutil.relativedelta import relativedelta
import logging
from telnetlib import theNULL

_logger = logging.getLogger(__name__)
DF = "%Y-%m-%d"
EPS = 0.00001

class LoanPayReconciliation(models.Model):
    _name = "wc.loan.payment.reconciliation"
    _description = "For Bulk Payment "
    _inherit = [ 'mail.thread' ]
    _order = "date desc, name"

    search_wiz_id = fields.Integer()
    
    company_id = fields.Many2one('res.company', string='Branch', readonly=True,
        default=lambda self: self.env['res.company']._company_default_get('wc.loan.payment.reconciliation'))

    name = fields.Char("Reconciliation Name", required=True,
        track_visibility='onchange', readonly=True, states={'draft': [('readonly', False)]})
 
#     bank_reconciliation_number = fields.Char("Bank Reconciliation Number",required=True,
#         track_visibility='onchange', readonly=True, states={'draft': [('readonly', False)]})

    def get_first_open_date(self):
        company_id = self.env.user.company_id.id
        return self.env['wc.posting'].get_first_open_date(company_id)
     
    date = fields.Date("Date", required=True,
        track_visibility='onchange',
        default=get_first_open_date,
        readonly=True, states={'draft': [('readonly', False)]}, index=True)

    #[TODO] consider direct journal create ,instead of adjustment bank reconciliation 
    is_bank_recon = fields.Boolean('Bank Reconciliation'
                                   ,track_visibility='onchange'
                                   ,help="Check this flag in case the payment is done on bank")
    

    amount = fields.Float("Total Amount", readonly=True,compute='compute_total',store=True)
    
    note = fields.Text(string='Notes', track_visibility='onchange', states={'draft': [('readonly', False)]})
    
    search_condition_str = fields.Text(string='Search Condition', track_visibility='onchange')
    
    state = fields.Selection([
        ('draft','Draft'),
        ('cancelled','Cancelled'),
        ('confirmed','Confirmed'),
        ('partial_reversed','Reversed Partially'),
        ('reversed','Reversed'),
    ], string='State', default=lambda self: 'draft',
        track_visibility='onchange', readonly=True)

    payment_reconciliation_lines_tmp = fields.Many2many(
        'wc.loan.pay.reconcile.line.tmp','wc_loan_reconcile_line_tmp_rel'
        ,string='Target Loans', states={'draft': [('readonly', False)]})

    payment_reconciliation_lines = fields.One2many(
        'wc.loan.pay.reconcile.line','reconcile_id'
        ,string='Reconciled Loans' , states={'draft': [('readonly', False)]})

    member_count = fields.Integer('Member Count', readonly=True,compute='compute_total',store=True)
    loan_count = fields.Integer('Loan Count', readonly=True,compute='compute_total',store=True)
#     loan_detail_count  = fields.Integer('Loan Detail Count', readonly=True,compute='compute_total')

    posting_id = fields.Many2one('wc.posting'
                                 ,track_visibility='onchange'
                                 , string='Posting Ref',
        required=False, readonly=True, ondelete="set null")

    reverse_posting_id = fields.Many2one('wc.posting'
                                 ,track_visibility='onchange'
                                 , string='Posting Ref',
        required=False, readonly=True, ondelete="set null")

    reversed_date = fields.Date('Reversed Date')
    
    @api.constrains('payment_reconciliation_lines')
    def check_if_lines_existing(self):
        if len(self.payment_reconciliation_lines_tmp) == 0 and self.state=='draft':
            raise UserError(_("No lines are selected."))
        if len(self.payment_reconciliation_lines) == 0 and self.state != 'draft':
            raise UserError(_("No lines are selected."))

    
    @api.depends('payment_reconciliation_lines_tmp','state')
    def compute_total(self):
        for recon in self:
            if recon.state == 'draft':
                lines = recon.payment_reconciliation_lines_tmp
            else:
                lines = recon.payment_reconciliation_lines
                
            recon.amount = sum(line.amount_due for line in lines)
            recon.loan_count = len(lines.mapped('loan_id'))
            recon.member_count = len(lines.mapped('member_id'))
                
    @api.multi
    def cancel(self):
        for rec in self:
            if rec.state!='draft':
                raise Warning(_("You can only cancel a draft record."))

            self.copy_from_temp_to_actual()
            self.unlink_tmp()
            rec.state = 'cancelled'
            for ln in rec.payment_reconciliation_lines:
                ln.is_canceled = True

        
    
                
    def check_before_confirmed(self):
        self.ensure_one()
        if self.date != self.env['wc.posting'].get_first_open_date(self.env.user.company_id.id):
            raise UserError(_("Date is unmatched with posting date"))
        if len(self.payment_reconciliation_lines_tmp)==0:
            raise UserError(_("Please select target loan."))
        

#     @api.multi
#     def write(self, vals):
#         res = super(LoanPayReconciliation, self).write(vals)
#         self.copy_from_temp_to_actual()

        
    def proceed_reconcile(self):
        self.ensure_one()
        self.check_before_confirmed()
        self.copy_from_temp_to_actual()
        self.create_and_confirm_payment_from_payment_recon()
        self.state = "confirmed"
        self.unlink_tmp()
          
        return {
            'type': 'ir.actions.act_window',
            'name': 'Loan Payment Reconciliation',
            'res_model': 'wc.loan.payment.reconciliation',
            'view_type': 'form',
            'target': 'self',
            'view_mode': 'tree,form',
        }
    
#     def back_to_draft(self):
#         self.ensure_one()
        
    def reverse_reconcile(self):
#         self.ensure_one()
        recon_lines = self.payment_reconciliation_lines
        for line in recon_lines:
            if line.is_reversed:
                raise UserError(_("Cannot reverse ,because this reconcile data contains reversed payment data."))
            payment = line.payment_ids[0]
            payment.with_context(tracking_disable=True).reverse_payment()
        self.reversed_date = self.get_first_open_date()
        self.state = 'reversed'

                
    def copy_from_temp_to_actual(self):
        self.ensure_one()
        _logger.debug("craete payment reconcile line from tmp data start ids =%s " % self.payment_reconciliation_lines_tmp.ids)
        
        tmp_lines = self.payment_reconciliation_lines_tmp.sorted(key=lambda r: (r.loan_id.member_id ,r.loan_id))

        for tmp_line in tmp_lines:
            tmp_line.each_paymentline_check()

            val = {
                'reconcile_id':self.id,
                'member_id':tmp_line.member_id.id,
                'loan_id':tmp_line.loan_id.id,
                'company_id':tmp_line.company_id.id,
                'amount_due':tmp_line.amount_due,
                'principal_due':tmp_line.principal_due,
                'interest_due':tmp_line.interest_due,
                'penalty_due':tmp_line.penalty_due,
                'others_due':tmp_line.others_due
            }
            self.payment_reconciliation_lines = [(0,0,val)]

        _logger.debug("craete payment reconcile line from tmp data end ids =%s " % self.payment_reconciliation_lines_tmp.ids)
    

    def unlink_tmp(self):
        #unling tmp data
        self.ensure_one()
        tmp_data = self.env['wc.loan.pay.reconcile.line.tmp'].search([('create_uid','=',self._uid)])
        tmp_data.unlink()

    
    def create_and_confirm_payment_from_payment_recon(self):
        self.ensure_one()

        _logger.debug("craete and confirm payment from reconciliation start ids =%s " % self.payment_reconciliation_lines.ids)
        i=0
        for line in self.payment_reconciliation_lines:

            i += 1
            val = {
                'name': 'Batch Reconcile %s %s #%d' % (self.name, self.date, i),
                'payment_reconciliation_id':self.id,
                'payment_reconciliation_line_id':line.id,
                'loan_id': line.loan_id.id,
                'date': self.date,
                'principal_amount':line.principal_due,
                'interest_amount':line.interest_due,
                'penalty_amount':line.penalty_due,
                'others_amount':line.others_due,
                'principal_amount':line.principal_due,
                'amount':line.amount_due,
                'is_manual_compute':True,
            }
            _logger.debug("confirm_payment: line=%s", val)
            pay = self.env['wc.loan.payment'].with_context(tracking_disable=True).create(val)
            pay.with_context(tracking_disable=True).confirm_payment()

        _logger.debug("craete and confirm payment from reconciliation end ids =%s " % self.payment_reconciliation_lines.ids)
        
        
        
