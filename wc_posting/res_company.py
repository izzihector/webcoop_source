# -*- coding: utf-8 -*-
###############################################
# EzTech Software & Consultancy Inc. (c) 2017
###############################################

from odoo import api, fields, models
from odoo import tools, _
from odoo.exceptions import ValidationError, Warning
from odoo.modules.module import get_module_resource
from datetime import datetime
from dateutil.relativedelta import relativedelta
import logging

_logger = logging.getLogger(__name__)
DF = "%Y-%m-%d"

class Company(models.Model):
    _inherit = "res.company"

    editable_loan_date = fields.Boolean("Editable Loan Date",
        help="Make loan dates editable. Activate only during initial implementation stage.")

    start_date = fields.Date("Beginning Date", default="2017-12-31")

    posting_journal_id = fields.Many2one('account.journal', string='Journal', ondelete="restrict")
    #deposit
    cash_account_id = fields.Many2one('account.account', string='Cash', ondelete="restrict")
    check_account_id = fields.Many2one('account.account', string='Bank', ondelete="restrict")
    sa_deposit_account_id = fields.Many2one('account.account', string='Savings Account', ondelete="restrict")
    td_deposit_account_id = fields.Many2one('account.account', string='Time Deposit', ondelete="restrict")
    interest_account_id = fields.Many2one('account.account', string='Interest Deposit', ondelete="restrict")
    cbu_deposit_account_id = fields.Many2one('account.account', string='CBU', ondelete="restrict")

    #loan
    ar_account_id = fields.Many2one('account.account', string='Receivable', ondelete="restrict")
    ar_pd_account_id = fields.Many2one('account.account', string='Receivable P.Due', ondelete="restrict")
    ap_account_id = fields.Many2one('account.account', string='Payable', ondelete="restrict")
    interest_income_account_id = fields.Many2one('account.account', string='Interest Income', ondelete="restrict")
    penalty_account_id = fields.Many2one('account.account', string='Penalty', ondelete="restrict")

    ##delete later
    banking_journal_id = fields.Many2one('account.journal', string='Journal', ondelete="restrict")
    loan_journal_id = fields.Many2one('account.journal', string='Journal', ondelete="restrict")
    service_fee_account_id = fields.Many2one('account.account', string='Service Fee', ondelete="restrict")
    notarial_fee_account_id = fields.Many2one('account.account', string='Notarial Fee', ondelete="restrict")
    appraisal_fee_account_id = fields.Many2one('account.account', string='Appraisal Fee', ondelete="restrict")
    filing_fee_account_id = fields.Many2one('account.account', string='Filing Fee', ondelete="restrict")
    loan_protection_account_id = fields.Many2one('account.account', string='Loan Protection', ondelete="restrict")
    other_deduction_account_id = fields.Many2one('account.account', string='Other Deduction', ondelete="restrict")

    #test = fields.Char()

    @api.multi
    def write(self, vals):
        res = super(Company, self).write(vals)

        if vals.get('editable_loan_date'):
            self.env['wc.loan'].invalidate_cache()
            self.env['wc.loan.payment'].invalidate_cache()

        return res

    @api.model
    def get_open_date(self):
        self.ensure_one()
        dates = self.env['wc.posting'].sudo().search([
            ('company_id','=', self.id),
            ('state','=','open'),
        ], limit=1, order="name asc")
        if dates:
            return dates[0].name
        else:
            raise Warning(_("There is no open date found. Please create a new posting date."))


    @api.model
    def get_last_closed_date(self):
        self.ensure_one()
        dates = self.env['wc.posting'].sudo().search([
            ('company_id','=', self.id),
            ('state','in',['closed','posted']),
        ], limit=1, order="name desc")
        if dates:
            return dates[0].name
        else:
            return fields.Date.context_today(self)

#
