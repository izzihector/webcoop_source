# -*- coding: utf-8 -*-
###############################################
# EzTech Software & Consultancy Inc. (c) 2017
###############################################

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime
from dateutil.relativedelta import relativedelta
import math
import logging

_logger = logging.getLogger(__name__)
DF = "%Y-%m-%d"
EPS = 0.00001

class LoanPayments(models.Model):
    _inherit = "wc.loan.payment"

    @api.multi
    def Xconfirm_payment(self):
        self.ensure_one()
        _logger.debug("**confirm_payment: amt=%0.2f", self.amount)

        if not self.loan_id.is_interest_epr:
            return super(LoanPayments, self).confirm_payment()

        p = self
        loan = p.loan_id

        if loan.total_due > EPS:
            is_principal_first = False
        else:
            is_principal_first = True

        if p.state=='draft' and loan.state in ['approved','past-due']:
            while p.amount > loan.total_due:
                no_open = True
                for am in loan.amortizations:
                    if am.state == 'open':
                        _logger.debug("**process soa: %s %s", am.name, am.date_due)
                        loan.gen_soa_details(loan, am.date_start, no_penalty=True, is_principal_first=is_principal_first)
                        is_principal_first = True
                        am.state = 'processed'
                        no_open = False
                        break
                if no_open:
                    raise UserError(_("Amount is more than total due.\nTotal Due=%0.2f") % loan.total_due)

        #no_interest=no_interest
        return super(LoanPayments, self).confirm_payment()


    @api.model
    def XXconfirm_payment(self):
        self.ensure_one()
        if self.amount <= self.loan_id.total_due or (not p.loan_id.is_interest_epr):
            return super(LoanPayments, self).post_payment_per_soa_line(p)

        _logger.debug("**confirm_payment advance pcp: amt=%0.2f", self.amount)
        if self.amount <= 0.0:
            raise ValidationError(_("Amount must be more than zero.\nAmount=%s") % (self.amount))

        if self.date < self.loan_id.last_payment_date:
            raise Warning(_("Cannot post payment with date before from last."))

        p = self

        details1 = self.env['wc.loan.detail'].search([
            ('loan_id','=',p.loan_id.id),
            ('total_due','>',0.0),
            ('state','!=','del'),
            ('is_principal_first','=',False)
        ], order='date_due')

        details2 = self.env['wc.loan.detail'].search([
            ('loan_id','=',p.loan_id.id),
            ('total_due','>',0.0),
            ('state','!=','del'),
            ('is_principal_first','=',True)
        ], order='date_due')

        if not (details1 or details2):
            return

        _logger.debug("details1: %s", details1)
        _logger.debug("details2: %s", details2)

        dist_lines = []
        pamt = p.amount - p.posted_amount

        #penalty
        if p.loan_id.is_collect_penalty:
            lines, pamt = self.get_penalty_lines(p, details1, pamt)
            dist_lines += lines

        #interest due
        lines, pamt = self.get_interest_lines(p, details1, pamt)
        dist_lines += lines

        #others due
        lines, pamt, dtrans_lines = self.get_other_lines(p, details1, pamt)
        dist_lines += lines

        #principal due
        pcp_lines, pamt = self.get_principal_lines(p, details1, pamt)
        dist_lines += pcp_lines

        #append principal firsrt
        if pamt>EPS:
            pcp_lines, pamt = self.get_principal_lines(p, details2, pamt)
            dist_lines += pcp_lines

            #penalty
            if p.loan_id.is_collect_penalty:
                lines, pamt = self.get_penalty_lines(p, details2, pamt)
                dist_lines += lines

            #interest due
            lines, pamt = self.get_interest_lines(p, details2, pamt)
            dist_lines += lines

            #others due
            lines, pamt, dtrans_lines = self.get_other_lines(p, details2, pamt)
            dist_lines += lines

        #create trans
        self.post_create_trans(p, dist_lines, pcp_lines, dtrans_lines, pamt)

        #reset principal first flags
        details2.write({
            'is_principal_first': False
        })






#
