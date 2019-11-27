# -*- coding: utf-8 -*-
###############################################
# EzTech Software & Consultancy Inc. (c) 2017
###############################################

from openerp import models, fields, api, _
from openerp.exceptions import Warning, ValidationError
import openerp.addons.decimal_precision as dp
from datetime import datetime
from dateutil.relativedelta import relativedelta
import math
import logging
EPS = 0.00001

_logger = logging.getLogger(__name__)
DF = "%Y-%m-%d"

class Deductions(models.Model):
    _name = "wc.loan.deduction"
    _description = "Loan"
    _order = "sequence"

    sequence = fields.Integer()
    loan_id = fields.Many2one('wc.loan', string='Loan', readonly=True, ondelete="restrict")
    member_id = fields.Many2one(related="loan_id.member_id", readonly=True)
    state = fields.Selection(related="loan_id.state")
    name = fields.Char("Name")
    code = fields.Char("Code", index=True)
    recurring = fields.Boolean("Recurring", help="Enable if deduction is collected every payment cycle.")
    net_include = fields.Boolean("Net Include", default=True, help="Enable if deducted from loan amount to compute net.")
    factor = fields.Float("Factor %", digits=(12,4))
    amount = fields.Float("Amount", digits=(12,2))
    deposit_account_id = fields.Many2one('wc.account', string='CBU/Dep. Account', ondelete="restrict")
    gl_account_id = fields.Many2one('account.account', string='GL Account', ondelete="set null")
    note =  fields.Char("Notes")

    @api.multi
    @api.onchange('factor')
    def onchange_factor(self):
        for r in self:
            if r.factor != 0.0:
                r.amount = round(r.loan_id.amount * r.factor/100.0, 2)

    @api.multi
    @api.onchange('amount')
    def onchange_amount(self):
        for r in self:
            #if r.loan_id.amount>0.0:
            amt = round(r.loan_id.amount * r.factor/100.0, 2)
            if r.amount!=amt:
                #r.factor = round(100.0 * r.amount/r.loan_id.amount, 2)
                r.factor = 0.0


class Loan(models.Model):
    _inherit = "wc.loan"

    total_deduction = fields.Float("Total Deductions", digits=(12,2), compute="compute_deductions")
    net_amount = fields.Float("Net Amount", digits=(12,2), compute="compute_deductions")
    cbu_deposit = fields.Float("CBU Deposit", digits=(12,2), compute="compute_deductions")
    savings_deposit = fields.Float("Savings Deposit", digits=(12,2), compute="compute_deductions")

    @api.multi
    def write(self, vals):
        res = super(Loan, self).write(vals)
        if 'amount' in vals or 'loan_type_id' in vals or 'member_id' in vals:
            self.generate_deductions()
        return res

    @api.model
    def create(self, vals):
        res = super(Loan, self).create(vals)
        res.generate_deductions()
        return res

    @api.multi
    @api.depends('deduction_ids','deduction_ids.amount')
    def compute_deductions(self):
        for loan in self:
            tamt = 0.0
            cbu = 0.0
            savings = 0.0
            for ded in loan.deduction_ids:
                if ded.net_include:
                    tamt += ded.amount
                    if ded.code=='cbu':
                        cbu = ded.amount
                    elif ded.code=='sa':
                        savings = ded.amount

            loan.total_deduction = tamt
            loan.net_amount = loan.amount - tamt
            loan.cbu_deposit = cbu
            loan.savings_deposit = savings

    @api.model
    def get_deductions(self, loan):
        deductions = super(Loan, self).get_deductions(loan)
        for d in loan.loan_type_id.deduction_ids:
            factor = False
            amount = False
            if d.amount>0.0:
                factor = False
                amount = d.amount
            elif d.factor>0.0:
                factor = d.factor
                amount = round(loan.amount * d.factor/100.0, 2)

            val = {
                'sequence': d.sequence,
                'loan_id': loan.id,
                'code': d.code,
                'name': d.name,
                'recurring': d.recurring,
                'net_include': d.net_include,
                'factor': factor,
                'amount': amount,
                'gl_account_id': d.gl_account_id.id,
            }

            acct_id = False

            if d.code in ['cbu','CBU']:
                for acct in loan.member_id.cbu_account_ids:
                    if acct.state in ['open','dormant']:
                        acct_id = acct.id
                        break
                if not acct_id:
                    #raise Warning(_("No member CBU account found."))
                    #fix #258: skip deduction if no CBU found
                    continue

            elif d.code in ['sa','SA']:
                for dacct in loan.member_id.account_ids:
                    #add f597 start, if deduction_target_account_type is existing in wc.loan.type.deduction model
                    if 'deduction_target_account_type' in self.env['wc.loan.type.deduction']._fields:
                        if dacct.account_type == 'sa' \
                           and dacct.state in ['open','dormant'] \
                           and dacct.account_type_id == d.deduction_target_account_type:
                            acct_id = dacct.id
                            break
                    else:
                    #add f597 end
                        if dacct.account_type == 'sa' and dacct.state in ['open','dormant']:
                            acct_id = dacct.id
                            break
                if not acct_id:
                    #raise Warning(_("No member savings account found."))
                    #fix #258: skip deduction if no deposit account found
                    continue
            val.update({
                'deposit_account_id': acct_id
            })

            _logger.debug("**gen_deductions: %s", val)
            deductions.append( (0, False, val.copy()) )

        return deductions

    @api.multi
    def generate_deductions(self):
        res = super(Loan, self).generate_deductions()
        for loan in self:
            if loan.state=='draft' and loan.loan_type_id and loan.amount>0.0:
                for ded in loan.deduction_ids:
                    #do not delete deductions for restructured loans
                    if ded.code not in ['PCP','INT','PEN']:
                        ded.unlink()
                deductions = self.get_deductions(loan)
                if deductions:
                    _logger.debug("**all_deductions: %s", deductions)
                    loan.deduction_ids = deductions

        return res


"""
class LoanDetailDeduction(models.Model):
    _name = "wc.loan.detail.deduction"
    _description = "Loan Detail Recurring Deductions"
    _order = "sequence"

    sequence = fields.Integer()
    detail_id = fields.Many2one('wc.loan.detail', 'Loan detail', ondelete='restrict')
    deduction_id = fields.Many2one('wc.loan.deduction', 'Loan Deduction', ondelete='restrict')
    name = fields.Char()
    code = fields.Char()
    paid = fields.Boolean()
    amount = fields.Float("Amount",digits=(12,2))
"""
