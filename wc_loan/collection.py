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

class CollectionDetail(models.Model):
    _inherit = "wc.collection.line"

    loan_id = fields.Many2one('wc.loan', string='Loan', readonly=True, ondelete="restrict")
    loan_payment_id = fields.Many2one('wc.loan.payment', string='Loan Payment', readonly=True, ondelete="restrict")


class Collections(models.Model):
    _inherit = "wc.collection"

    @api.model
    def get_lines(self, c):
        lines = super(Collections, self).get_lines(c)
        return self.get_loan_lines(c, lines)

    @api.model
    def get_loan_lines(self, c, lines):
        if c.member_id:
            seq = 1000

            process_loans = set()

            cbu_due = 0.0
            savings_due = 0.0
            #self.gen_line_account(c, cbu_due, savings_due)

            for loan in c.member_id.loan_ids:
                process_loans.add(loan.id)
                if loan.state in ['approved','past-due']:
                    tdue = 0.0
                    for det in loan.details:
                        tdue += det.total_due
                    if tdue>0.0:
                        lines.append(( 0, False, {
                            'collection_id' : c.id,
                            'sequence': seq,
                            'name': 'Payment %s %s' % (loan.code, loan.loan_type_id.description),
                            'loan_id': loan.id,
                            'amount_due': tdue,
                            #'code': 'loan',
                            'collection_type': 'loan_payment',
                        }))
                        seq += 1

            for loan in c.member_id.comaker_loan_ids:
                if loan.state in ['approved','past-due']:
                    tdue = 0.0
                    for det in loan.details:
                        tdue += det.total_due
                    if loan.id not in process_loans and tdue>0.0:
                        process_loans.add(loan.id)
                        lines.append(( 0, False, {
                            'collection_id' : c.id,
                            'sequence': seq,
                            'name': 'Payment %s %s (comaker)' % (loan.code, loan.loan_type_id.description),
                            'loan_id': loan.id,
                            'amount_due': tdue,
                            #'code': 'loan',
                            'collection_type': 'loan_payment',
                        }))
                        seq += 1

        _logger.debug("**get_lines loans: %s", lines)
        return lines


    @api.multi
    def confirm(self):
        res = super(Collections, self).confirm()
        self.confirm_loan()
        return res


    @api.multi
    def confirm_loan(self):
        payment_obj = self.env['wc.loan.payment']
        #add to loan transactions
        for rec in self:
            for line in rec.line_ids:
                if line.collection_type=='loan_payment' and line.amount!=0.0 and not line.is_deleted:
                    res2 = payment_obj.create({
                        'name': 'Collection %s' % rec.name,
                        'collection_id': rec.id,
                        'loan_id': line.loan_id.id,
                        'date': line.date,
                        'or_number': rec.name,
                        'amount': line.amount,
                        #'state': 'confirmed',
                    })
                    res2.confirm_payment()
                    line.loan_payment_id = res2.id

    @api.multi
    def cancel(self):
        self.cancel_collection_loan()
        return super(Collections, self).cancel()

    @api.multi
    def cancel_collection_loan(self):
        #add to account transactions
        dt = fields.Date.context_today(self)
        for rec in self:
            for line in rec.line_ids:
                if line.collection_type=='loan_payment' and line.loan_payment_id and line.amount!=0.0 and not line.is_deleted:
                    line.loan_payment_id.cancel()
