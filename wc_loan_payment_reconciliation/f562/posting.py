# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo import tools, _
from odoo.exceptions import ValidationError, Warning
from odoo.modules.module import get_module_resource
from datetime import datetime
from dateutil.relativedelta import relativedelta
import logging
# from util import *
from ...wc_posting import util
import time


_logger = logging.getLogger(__name__)
DF = "%Y-%m-%d"
EPS = 0.00001

class Posting(models.Model):
    _inherit = "wc.posting"

    payment_reconcile_header_ids = fields.One2many('wc.loan.payment.reconciliation', 
         'posting_id',readonly=True, string='Payment Reconciliation Header')

    payment_reverse_reconcile_header_ids = fields.One2many('wc.loan.payment.reconciliation', 
         'reverse_posting_id',readonly=True, string='Payment Reverse Reconciliation Header')


    #[TODO] consider direct journal create ,instead of adjustment bank reconciliation 
    @api.model
    def adjustment_move_lines_for_bank_reconcile(self, rec, moves):
 
        #check if the payment is reconciliation
        for recon_header in rec.payment_reconcile_header_ids:
            #if , the payment is related to reconcile and the payment is done on bank, change ttype to check so that debit account becomes bank account
            jv_journal_id, cr_journal_id, cd_journal_id = self.get_journals()
 
            if recon_header.is_bank_recon:
                collector_id = recon_header.create_uid.partner_id.id
                #add journal entry for offset
                date = rec.name
                vals = {
                    'date': date,
                    'journal_id':jv_journal_id.id,
                    'account_id': rec.company_id.cash_account_id.id,
                    'name': "Bulk Payment Reconcile Adjustment (%s)" % (recon_header.name),
#                    'partner_id': collector_id,
                    'debit': 0,
                    'credit': recon_header.amount,
                }
 
                vals2 = {
                    'date': date,
                    'journal_id':jv_journal_id.id,
                    'account_id': rec.company_id.check_account_id.id,
                    'name': "Bulk Payment Reconcile Adjustment (%s)" % (recon_header.name),
#                    'partner_id': collector_id,
                    'debit': recon_header.amount,
                    'credit': 0,
                }
                moves['jv'][0]['lines'].append([0, 0, vals])
                moves['jv'][0]['lines'].append([0, 0, vals2])
 
        #check if reversed reconciliation and different is existing 


    #[TODO] consider direct journal create ,instead of adjustment bank reconciliation 
    def adjustment_move_lines_for_bank_reconcile_reverse(self, rec, moves):
 
        #check if the payment is reconciliation
        for reverse_recon_header in rec.payment_reverse_reconcile_header_ids:
            #if , the payment is related to reconcile and the payment is done on bank, change ttype to check so that debit account becomes bank account
            jv_journal_id, cr_journal_id, cd_journal_id = self.get_journals()
 
            if reverse_recon_header.is_bank_recon:
                collector_id = reverse_recon_header.write_uid.partner_id.id
                #add journal entry for offset
                date = rec.name
                vals = {
                    'date': date,
                    'journal_id':jv_journal_id.id,
                    'account_id': rec.company_id.cash_account_id.id,
                    'name': "Bulk Payment Reconcile Adjustment (%s)" % (reverse_recon_header.name),
#                    'partner_id': collector_id,
                    'debit': reverse_recon_header.amount,
                    'credit': 0,
                }
 
                vals2 = {
                    'date': date,
                    'journal_id':jv_journal_id.id,
                    'account_id': rec.company_id.check_account_id.id,
                    'name': "Bulk Payment Reconcile Adjustment (%s)" % (reverse_recon_header.name),
#                    'partner_id': collector_id,
                    'debit': 0,
                    'credit': reverse_recon_header.amount,
                }
                moves['jv'][0]['lines'].append([0, 0, vals])
                moves['jv'][0]['lines'].append([0, 0, vals2])        

    @api.multi
    def set_draft(self):
        for rec in self:
            for recon_header in rec.sudo().payment_reconcile_header_ids:
                recon_header.posting_id = False
            for reverse_recon_header in rec.sudo().payment_reverse_reconcile_header_ids:
                reverse_recon_header.reverse_posting_id = False

        return super(Posting, self).set_draft()

    @api.multi
    def add_details(self):
        for rec in self:
            for recon_header in rec.sudo().payment_reconcile_header_ids:
                recon_header.posting_id = False
            #reconcile header
            recon_headers = self.env['wc.loan.payment.reconciliation'].sudo().search([
                ('company_id','=',rec.company_id.id),
                ('date','=',rec.name),
                ('state','in',['confirmed','reversed']),
                ('posting_id','=',False),
            ])
            for recon_header in recon_headers:
                if abs(recon_header.amount) > EPS:
                    recon_header.posting_id = rec.id
                    
            #reconcile reverse
            for reverse_recon_header in rec.sudo().payment_reverse_reconcile_header_ids:
                reverse_recon_header.reverse_posting_id = False

            reverse_recon_headers = self.env['wc.loan.payment.reconciliation'].sudo().search([
                ('company_id','=',rec.company_id.id),
                ('reversed_date','=',rec.name),
                ('state','=','reversed'),
                ('reverse_posting_id','=',False),
            ])
            for reverse_recon_header in reverse_recon_headers:
                if abs(reverse_recon_header.amount) > EPS:
                    reverse_recon_header.reverse_posting_id = rec.id

        return super(Posting, self).add_details()


    #[TODO] consider direct journal create ,instead of adjustment bank reconciliation 
    @api.model
    def get_move_lines(self, rec, moves):
        res = super(Posting, self).get_move_lines(rec, moves)
        self.adjustment_move_lines_for_bank_reconcile(rec, moves)
        self.adjustment_move_lines_for_bank_reconcile_reverse(rec, moves)
 
        return res


    def check_before_close(self):
        trans = self.env['wc.loan.payment.reconciliation'].sudo().search([
            ('state','in',['draft']),
            ('company_id','=',self.env.user.company_id.id)
        ])
        if trans:
            raise ValidationError(_("Unprocecced record is remaining in %s!.") % ('Bulk Payment Reconciliation'))

                
    @api.multi
    def close_date(self):
        self.check_before_close()
        super(Posting,self).close_date()
