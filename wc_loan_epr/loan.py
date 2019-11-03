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

class Loan(models.Model):
    _inherit = "wc.loan"

    bulk_principal_payment = fields.Boolean("Bulk Principal Pay",
        readonly=True, states={'draft': [('readonly', False)]},
        help="Pay principal on the last payment.")

    is_interest_epr = fields.Boolean("Straight Interest", related="loan_type_id.is_interest_epr")

    #rate_label = fields.Char(compute="compute_rate_label")
    #advance_interest = fields.Float("Advance Interest", readonly=True)

    @api.onchange('loan_type_id')
    def oc_loan_type_id(self):
       self.ensure_one()
       self.bulk_principal_payment = self.loan_type_id.bulk_principal_payment
       return super(Loan, self).oc_loan_type_id()

#########################################
#this module is overwritten by ver10_0_1_2 , don't use this
    @api.multi
    def generate_amortization_simple_interest(self, round_to_peso=True):
        for loan in self:
            if loan.is_interest_epr:
                #loan.generate_amortization_straight_interest(self, round_to_peso=loan.loan_type_id.round_to_peso):
                loan.generate_amortization_straight_interest()
                loan.term_payments = len(loan.amortizations)
            else:
                super(Loan, loan).generate_amortization_simple_interest(round_to_peso=round_to_peso)
#########################################

    @api.multi
    @api.depends(
        #'date',
        'maturity',
        'maturity_period',
        'date_start',
        'payment_schedule',
        'amortizations',
        #'is_360_day_year'
    )
    def compute_date_maturity(self):
        for loan in self:
            super(Loan, loan).compute_date_maturity()
            if loan.is_interest_epr:
                loan.term_payments = len([a for a in loan.amortizations if a.date_due<=loan.date_maturity])

    @api.model
    def get_skip_dates(self, date_start):
        return []

#########################################
#this module is overwritten by ver10_0_1_2 , don't use this
    @api.multi
    def generate_amortization_straight_interest(self):
        for loan in self:
            if loan.state != 'draft':
                continue

            skip_days = [6]
            if loan.loan_type_id.skip_saturday:
                skip_days.append(5)

            #get holidays
            skip_dates = set(self.get_skip_dates(loan.date_start))

            self.details.unlink()
            self.amortizations.unlink()
            tbalance = loan.amount

            try:
                days_in_year = float(loan.days_in_year)
            except:
                days_in_year = 365.0

            d1 = fields.Datetime.from_string(loan.date_start)
            d0 = d1
            dend = fields.Datetime.from_string(loan.date_maturity)
            days = (dend - d1).days

            if loan.maturity_period=='months' and loan.payment_schedule in ['half-month','month','quarter','semi-annual','year']:
                tinterest = round(loan.amount * loan.interest_rate * loan.maturity / 1200.0, 2)
            else:
                tinterest = round(loan.amount * loan.interest_rate * days / (days_in_year * 100.0), 2)

            round_to_peso = loan.loan_type_id.round_to_peso

            _logger.debug("**gen straight amort 1: %s d1=%s dend=%s days=%s",
                loan.name, d1, dend, days
            )

            lines = []
            n = 0
            while d1 < dend:
                if loan.payment_schedule=='lumpsum':
                    d2 = dend
                else:
                    d2, dx = self.get_next_due(d1, loan.payment_schedule, n+1, d0, loan=loan)

                d2 = min(d2, dend)
                d2s = d2.strftime(DF)

                #skip sunday if schedule is daily
                if not (loan.payment_schedule=="day" and (d2.weekday() in skip_days or d2s in skip_dates)):
                    days = (d2 - d1).days
                    n += 1
                    lines.append([0, 0, {
                        'loan_id': loan.id,
                        'date_start': d1.strftime(DF),
                        'date_due': d2.strftime(DF),
                        'name': "Schedule %d" % n,
                        'days': days,
                        #'principal_balance': 0,
                        #'principal_due': 0,
                        #'interest_due': 0,
                        'sequence': n,
                    }])
                d0 = d1
                d1 = d2

            if loan.bulk_principal_payment:
                lprincipal = 0.0
            else:
                lprincipal = round(loan.amount/n, 2)

            if round_to_peso:
                linterest = round(tinterest/n, 0)
                while linterest * n > tinterest:
                    linterest -= 1.0
                lprincipal = round(lprincipal, 0)
                while lprincipal * n > loan.amount:
                    lprincipal -= 1.0
            else:
                linterest = round(tinterest/n, 2)

            #is_with_advance_interest = False
            adv_interest_record = False
            if loan.payment_schedule != "day":
                for ded in loan.deduction_ids:
                    if ded.code.upper()[:3] == 'ADV' and ded.net_include:
                        if adv_interest_record:
                            raise UserError(_("Cannot define two advance interest deductions at the same time."))
                        adv_interest_record = ded

            _logger.debug("**gen straight amort: %s tinterest=%s linterest=%s n=%s",
                loan.name, tinterest, linterest, n
            )

            pbal = loan.amount
            if lines:
                for ln in lines[:-1]:
                    ln[2].update({
                        'principal_balance': pbal,
                        'principal_due': lprincipal,
                        'interest_due': linterest,
                    })
                    pbal -= lprincipal
                    tinterest -= linterest

                lines[-1][2].update({
                    'principal_balance': pbal,
                    'principal_due': pbal,
                    'interest_due': tinterest,
                })

                if adv_interest_record:
                    try:
                        ns = adv_interest_record.code[3:].strip()
                        if len(ns)==0:
                            n = 1
                        else:
                            n = int(ns)
                    except:
                        n = 1

                    nlines = len(lines)
                    if n>nlines:
                        n = nlines
                        #raise UserError(_("Advance interest is more than amortization lines."))

                    amt = 0.0
                    while n>0:
                        line = lines[nlines-1][2]
                        amt += line['interest_due']
                        line.update({
                            'interest_due': False,
                        })
                        nlines -=1
                        n -= 1

                    adv_interest_record.factor = 0.0
                    adv_interest_record.amount = amt

                loan.amortizations = lines
#####################################################


    @api.model
    def compute_interest(self, principal_balance, date1, date2, default_amount=0.0):
        self.ensure_one()
        if self.loan_type_id.is_interest_epr:
            return default_amount
        else:
            return super(Loan, self).compute_interest(principal_balance, date1, date2, default_amount=default_amount)

    @api.model
    def compute_principal_due(self, default_principal_due, interest_due, c):
        self.ensure_one()
        if self.loan_type_id.is_interest_epr:
            return default_principal_due
        else:
            return super(Loan, self).compute_principal_due(default_principal_due, interest_due, c)




#
