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
#from util import *

_logger = logging.getLogger(__name__)
DF = "%Y-%m-%d"
EPS = 0.00001

#IMPLEMENTATION = True

class Loan(models.Model):
    _name = "wc.loan"
    _description = "Loan"
    _inherit = [
        'mail.thread',
    ]
    _order = "date desc"

    #sequence = fields.Integer(default=10)
    company_id = fields.Many2one('res.company', string='Branch', readonly=True,
        default=lambda self: self.env['res.company']._company_default_get('wc.loan'))

    name = fields.Char("Loan No.", compute="compute_name")
    code = fields.Char("Loan No.", readonly=True, default="DRAFT", copy=False)

    loan_type_id = fields.Many2one('wc.loan.type', 'Loan Type',
        ondelete='restrict', required=True)
        #readonly=True, states={'draft': [('readonly', False)]})

    purpose = fields.Char("Purpose", readonly=True, states={'draft': [('readonly', False)]})

    member_id = fields.Many2one('wc.member', 'Maker', ondelete='restrict',
        required=True,
        #copy=False,
        domain=[('is_approved','=',True)],
        readonly=True, states={'draft': [('readonly', False)]})
    member_code = fields.Char(related="member_id.code")
    member_name = fields.Char("Maker", compute="compute_name")

    center_id = fields.Many2one(related="member_id.center_id", readonly=True)
    account_officer_id = fields.Many2one(related="member_id.account_officer_id", readonly=True)

    comaker_ids = fields.Many2many('wc.member', string='Co-makers',
        domain=[('is_approved','=',True)],
        readonly=True, states={'draft': [('readonly', False)]})
    comaker_count = fields.Integer("Co-makers", compute="count_comaker",
        readonly=True, states={'draft': [('readonly', False)]})

    amount = fields.Float("Loan Amount", digits=(12,2), required=True,
        readonly=True, states={'draft': [('readonly', False)]})
    interest_rate = fields.Float("Interest Rate %", digits=(12,4),
        readonly=True, states={'draft': [('readonly', False)]})
    penalty_rate = fields.Float("Penalty Rate %", digits=(12,4),
        readonly=True, states={'draft': [('readonly', False)]})

    maturity = fields.Integer("Maturity", help="Maturity in months or days",
        readonly=True, states={'draft': [('readonly', False)]})
    maturity_period = fields.Selection([
            ('days', 'days'),
            ('weeks', 'weeks'),
            ('months', 'months'),
        ], 'Maturity Period', required=True,
        readonly=True, states={'draft': [('readonly', False)]}, default='months')

    #not used delete later
    payment_interval = fields.Integer("Payment Interval", help="Payment interval in months",
        readonly=True, states={'draft': [('readonly', False)]})

    payment_schedule = fields.Selection([
            ('day', 'Daily'),
            ('week', 'Weekly'),
            ('half-month', 'Semi-monthly'),
            ('15-days', '15-days'),
            ('30-days', '30-days'),
            ('month', 'Monthly'),
            ('quarter', 'Quarterly'),
            ('semi-annual', 'Semi-annual'),
            ('year', 'Yearly'),
            ('lumpsum', 'Lump Sum'),
        ], 'Payment Schedule', required=True, track_visibility='onchange', default="half-month",
        readonly=True, states={'draft': [('readonly', False)]})

    gp_principal = fields.Integer("G.P. Principal", help="Grace period for principal in months",
        readonly=True, states={'draft': [('readonly', False)]})
    gp_interest = fields.Integer("G.P. Interest", help="Grace period for interest in months",
        readonly=True, states={'draft': [('readonly', False)]})

    date_application = fields.Date("Application Date",
        required=True,
        default=fields.Date.context_today,
        copy=False,
        readonly=True, states={'draft': [('readonly', False)]})

    date = fields.Date("Approval Date",
        #required=True,
        default=fields.Date.context_today,
        copy=False,
        readonly=True, states={'draft': [('readonly', False)]})

    date_start = fields.Date("Amortization Start", required=True,
        default=fields.Date.context_today,
        copy=False,
        readonly=True, states={'draft': [('readonly', False)]})

    date_first_due = fields.Date("First Due Date", compute="compute_date_first_due")

    date_maturity = fields.Date("Maturity Date", compute="compute_date_maturity", store=True)
    term_payments = fields.Integer("No. of Payments", compute="compute_date_maturity", stored=True)
    is_fixed_payment_amount = fields.Boolean("Fixed Amount", default=True,
        readonly=True, states={'draft': [('readonly', False)]},
        help="Payment amount per period is fixed.")

    is_360_day_year = fields.Boolean("Use 360-day Year",
        help="In computation use 360 days for a year.")

    is_collect_penalty = fields.Boolean("Collect Penalty", track_visibility='onchange',
        default=True, help="Automatically collect penalty on loan payments.")

    is_check_payment = fields.Boolean("Pay with check")
    check_number = fields.Char("Check Number")

    days_in_year = fields.Selection([
            ('365', '365 days'),
            ('360', '360 days'),
            ('336', '336 days'),
        ], 'Days in Year', default="365", required=True,
        readonly=True, states={'draft': [('readonly', False)]},
        help="Number of days on a year. Used for interest computation.")

    #is_past_due_switch = fields.Boolean("Past due switch", readonly=True)
    #add_months = fields.Integer("Interval Months",
    #    readonly=True, states={'draft': [('readonly', False)]})

    ldate_soa = fields.Date("Next Due Date", compute="_compute_totals2", store=True)
    date_soa = fields.Date("Last Statement Date", default=fields.Date.context_today)

    note = fields.Text(string='Notes')
    active = fields.Boolean(default=True)

    state = fields.Selection([
        ('draft','Draft'),
        ('cancelled','Cancelled'),
        #('for_approval','For Approval'),
        ('approved','Approved'),
        ('paid','Paid'),
        ('past-due','Past Due'),
        ('restructured','Restructured'),
        ('closed','Closed'),
    ], string='State',
        default=lambda self: 'draft',
        copy=False,
        track_visibility='onchange', readonly=True)

    restructured_to_id = fields.Many2one('wc.loan',
        string='Restructured To', readonly=True)
    restructured_from_id = fields.Many2one('wc.loan',
        string='Restructured From', readonly=True)

    #summary
    total_due = fields.Float("Total Due", digits=(12,2),
        store=False, compute="_compute_totals2")
    principal_due = fields.Float("Principal Due", digits=(12,2),
        store=False, compute="_compute_totals2")
    interest_due = fields.Float("Interest Due", digits=(12,2),
        store=False, compute="_compute_totals2")
    others_due = fields.Float("Others Due", digits=(12,2),
        store=False, compute="_compute_totals2")
    penalty_due = fields.Float("Penalty Due", digits=(12,2),
        store=False, compute="_compute_totals2")
    total_balance = fields.Float("Total Balance", digits=(12,2),
        store=False, compute="_compute_totals2")
    interest_balance = fields.Float("Interest Balance", digits=(12,2),
        store=False, compute="_compute_totals2")
    interest_total = fields.Float("Total Interest", digits=(12,2),
        store=False, compute="_compute_totals2")
    others_total = fields.Float("Total Others", digits=(12,2),
        store=False, compute="_compute_totals2")
    last_payment_date = fields.Date("Last Payment Date",
        store=False, compute="_compute_lpdate")
    last_amortization_date_due = fields.Date(compute="get_last_amortization_date", store=True)

    principal_balance = fields.Float("Principal Balance", digits=(12,2),
        help = "Outstanding principal amount.",
        compute="_compute_totals2", store=True)

    principal_paid = fields.Float("Principal Paid", digits=(12,2),
        compute="_compute_totals2", store=True)

    principal_pdue = fields.Float("Past Due Principal", digits=(12,2),
        help = "Past due principal amount.",
        compute="_compute_totals", store=True)
    #principal_pc_balance = fields.Float("% Principal Balance", digits=(12,2),
    #    help = "Past due principal amount.",
    #    compute="_compute_totals", store=True)

    cycle_add = fields.Integer(related="member_id.cycle_add", track_visibility='onchange')
    cycle = fields.Integer("Cycle", compute="compute_cycle")

    prepared_by_id = fields.Many2one('res.users', string="Prepared By",
        default=lambda self: self.env.user.id,
        track_visibility='onchange', ondelete="set null")

    checked_by_id = fields.Many2one('res.users', string="Checked By",
        track_visibility='onchange', ondelete="set null")

    approved_by_id = fields.Many2one('res.users', string="Approved By",
        track_visibility='onchange', ondelete="set null", readonly=True)

    released_by_id = fields.Many2one('res.users', string="Released By",
        track_visibility='onchange', ondelete="set null")

    disbursement_voucher_number = fields.Char("Disbursement Voucher No.",
        track_visibility='onchange')

    details = fields.One2many('wc.loan.detail', 'loan_id', 'Loan SOA', readonly=False)
    payments = fields.One2many('wc.loan.payment', 'loan_id', 'Loan Payments')
    adjustments = fields.One2many('wc.loan.adjustment', 'loan_id', 'Adjustments')
    amortizations = fields.One2many('wc.loan.amortization',
        'loan_id', 'Loan Amortization Schedule',
        #readonly=True, states={'draft': [('readonly', False)]},
        track_visibility='onchange')
    deduction_ids = fields.One2many('wc.loan.deduction', 'loan_id', 'Loan Deductions')

    tag_ids = fields.Many2many('wc.loan.tag', 'loan_tag_rel', 'loan_id', 'tag_id', string='Tags')

    @api.depends('payments','payments.date','payments.is_reversed')
    def _compute_lpdate(self):
        for r in self:
            last_payment_date = False
            for p in r.payments:
                if not p.is_reversed:
                    if not last_payment_date:
                        last_payment_date = p.date
                    else:
                        last_payment_date = max(last_payment_date, p.date)
            r.last_payment_date = last_payment_date

    @api.depends('date','member_id')
    def compute_cycle(self):
        for r in self:
            if isinstance(r.id, models.NewId):
                r.cycle = 1 + r.cycle_add
            else:
                res = self.search([
                    ('member_id','=', r.member_id.id),
                    ('date','<=', r.date),
                    ('state','!=', 'draft'),
                    ('id','<', r.id),
                ])
                r.cycle = len(res) + 1 + r.cycle_add

    @api.model
    def get_deduction_data(self, loan_id, loan_amount, deduction_id):
        return {}

    #@api.multi
    #@api.constrains('date','date_start')
    #def _check_dates(self):
    #    for r in self:
    #        if r.date > r.date_start:
    #            raise ValidationError(_("Amortization start date must be later or equal to the approval date."))

    @api.multi
    @api.constrains('maturity','amount','interest_rate','date','date_start')
    def _check_zero_values(self):
        for r in self:
            if r.maturity<=0:
                raise ValidationError(_("Maturity must be more than zero.."))
            if r.amount<=0:
                raise ValidationError(_("Loan amount must be more than zero."))
            #0% interest is valid
            #if r.interest_rate<=0:
            #    raise ValidationError(_("Interest rate must be more than zero.."))

    @api.multi
    def generate_deductions(self):
        pass

    @api.model
    def get_deductions(self, loan):
        return []

    @api.onchange('amount')
    def oc_amount(self):
       self.ensure_one()
       if self.amount>=50000.00:
           self.is_check_payment = True
       else:
           self.is_check_payment = False

    @api.onchange('loan_type_id')
    def oc_loan_type_id(self):
       self.ensure_one()
       self.interest_rate = self.loan_type_id.interest_rate
       self.penalty_rate = self.loan_type_id.penalty_rate
       self.maturity = self.loan_type_id.maturity
       self.maturity_period = self.loan_type_id.maturity_period
       self.payment_schedule = self.loan_type_id.payment_schedule
       self.is_fixed_payment_amount = self.loan_type_id.is_fixed_payment_amount
       #self.is_360_day_year = self.loan_type_id.is_360_day_year
       self.days_in_year = self.loan_type_id.days_in_year

    @api.multi
    @api.depends('payment_schedule','date_start')
    def compute_date_first_due(self):
       for r in self:
           mdate = fields.Datetime.from_string(r.date_start)
           mdate, days = self.get_next_due(mdate, r.payment_schedule, 1, mdate, loan=r)
           if mdate:
               r.date_first_due = mdate.strftime(DF)

    @api.multi
    @api.depends('comaker_ids')
    def count_comaker(self):
        for r in self:
            loans = 0
            for m in r.comaker_ids:
                if m.id!=r.member_id.id:
                    loans += 1
            r.comaker_count = loans

    @api.depends('code', 'member_id', 'member_id.name', 'comaker_ids', 'comaker_ids.name')
    def compute_name(self):
        for r in self:
            member_name = r.member_id.name
            if r.comaker_ids:
                member_name += " et al."

            r.name = "%s - %s" % (r.code, member_name)
            r.member_name = member_name

    @api.model
    def get_others_due_dict(self, loan):
        res = {}
        for det in loan.details:
            if not det.no_others_due:
                others_paid_dict = det.get_others_paid_dict(det)
                for ded in det.loan_id.deduction_ids:
                    if ded.recurring:
                        paid = others_paid_dict.get(ded.code, 0.0)
                        if ded.amount or paid:
                            res[ded.code] = res.get(ded.code,0.0) + ded.amount - paid
        return res

    @api.depends(
        'amortizations',
        'amortizations.date_due',
    )
    def get_last_amortization_date(self):
        for loan in self:
            last_amortization_date_due = False
            for am in loan.amortizations:
                last_amortization_date_due = am.date_due
            loan.last_amortization_date_due = last_amortization_date_due

    @api.depends(
        'date_start',
        'state',

        'details',
        'details.state',
        'details.date_due',
        'details.principal_due',
        'details.principal_paid',
        'details.interest_due',
        'details.interest_paid',
        'details.penalty',
        'details.adjustment',
        'details.penalty_paid',
        'details.others_due',
        'details.others_paid',

        'amortizations',
        'amortizations.state',
        'amortizations.interest_due',
        'amortizations.date_due',
    )
    def _compute_totals2(self):
        for loan in self:
            total_due = 0.0
            principal_due = 0.0
            interest_due = 0.0
            others_due = 0.0
            penalty_due = 0.0
            interest_balance = 0.0
            interest_total = 0.0
            principal_balance = loan.amount
            others_total = 0.0
            #last_amortization_date_due = False
            for am in loan.amortizations:
                if am.state=='open':
                    interest_balance += am.interest_due
                interest_total += am.interest_due
                others_total += am.others_due
                #last_amortization_date_due = am.date_due

            is_last_bill = False
            ldate_soa = loan.date_start
            for d in loan.details:
                if d.principal_due + 0.005 >= principal_balance:
                    is_last_bill = True
                interest_balance += d.interest_due - d.interest_paid
                total_due += d.total_due
                pdue = d.principal_due - d.principal_paid
                principal_balance -= d.principal_paid
                if pdue > 0.0:
                    principal_due += pdue
                interest_due += d.interest_due - d.interest_paid
                penalty_due += d.penalty + d.adjustment - d.penalty_paid
                others_due += d.others_due - d.others_paid
                ldate_soa = d.date_due

                #_logger.debug("*TEST: last=%s pbal=%s int=%s pdue=%s",
                #    is_last_bill, principal_balance, interest_due, d.principal_due)

            if is_last_bill:
                interest_balance = interest_due

            loan.principal_balance = principal_balance
            loan.interest_balance = interest_balance
            loan.total_balance = principal_balance + interest_balance

            loan.total_due = total_due
            loan.principal_due = principal_due
            loan.interest_due = interest_due
            loan.penalty_due = penalty_due
            loan.others_due = others_due
            loan.interest_total = interest_total
            loan.others_total = others_total
            loan.ldate_soa = ldate_soa
            loan.principal_paid = loan.amount - principal_balance
            #loan.last_amortization_date_due = last_amortization_date_due

    @api.multi
    @api.depends(
        'maturity',
        'maturity_period',
        'date_start',
        'payment_schedule',
        #'is_360_day_year'
    )
    def compute_date_maturity(self):
        for rec in self:
            _logger.debug("Onchange date=%s sch=%s",rec.date,rec.payment_schedule)
            if rec.date_start:
                if rec.maturity_period=='months':
                    dt0 = fields.Datetime.from_string(rec.date_start)
                    dt = dt0 + relativedelta(months=rec.maturity)
                    rec.date_maturity = dt.strftime(DF)
                    days = (dt - dt0).days
                    if (rec.payment_schedule=='day'):
                        n = days
                    elif (rec.payment_schedule=='week'):
                        n = math.ceil(days/7.0)
                    elif (rec.payment_schedule=='half-month'):
                        n = rec.maturity * 2
                    elif (rec.payment_schedule=='15-days'):
                        n = math.ceil(days/15.0)
                    elif (rec.payment_schedule=='month'):
                        n = rec.maturity
                    elif (rec.payment_schedule=='30-days'):
                        n = math.ceil(days/30.0)
                    elif (rec.payment_schedule=='quarter'):
                        n = math.ceil(rec.maturity/3.0)
                    elif (rec.payment_schedule=='semi-annual'):
                        n = math.ceil(rec.maturity/6.0)
                    elif (rec.payment_schedule=='year'):
                        n = math.ceil(rec.maturity/12.0)
                    else:
                        n = 1
                    rec.term_payments = n

                elif rec.maturity_period=='days':
                    dt0 = fields.Datetime.from_string(rec.date_start)
                    dt = dt0 + relativedelta(days=rec.maturity)
                    rec.date_maturity = dt.strftime(DF)
                    days = (dt - dt0).days
                    if (rec.payment_schedule=='day'):
                        n = days
                    elif (rec.payment_schedule=='week'):
                        n = math.ceil(rec.maturity/7.0)
                    elif (rec.payment_schedule=='half-month'):
                        #n = math.ceil(rec.maturity/15.2083334)
                        n = math.ceil(rec.maturity * 24.0 / 365.0)
                    elif (rec.payment_schedule=='15-days'):
                        n = math.ceil(rec.maturity/15.0)
                    elif (rec.payment_schedule=='month'):
                        #n = math.ceil(rec.maturity/30.4166667)
                        n = math.ceil(rec.maturity * 12.0 / 365.0)
                    elif (rec.payment_schedule=='30-days'):
                        n = math.ceil(rec.maturity/30.0)
                    elif (rec.payment_schedule=='quarter'):
                        n = math.ceil(rec.maturity/91.25)
                    elif (rec.payment_schedule=='semi-annual'):
                        n = math.ceil(rec.maturity/182.5)
                    elif (rec.payment_schedule=='year'):
                        n = math.ceil(rec.maturity/365.0)
                    else:
                        n = 1
                    rec.term_payments = n

                elif rec.maturity_period=='weeks':
                    dt0 = fields.Datetime.from_string(rec.date_start)
                    dt = dt0 + relativedelta(days=7*rec.maturity)
                    rec.date_maturity = dt.strftime(DF)
                    days = (dt - dt0).days
                    if (rec.payment_schedule=='day'):
                        n = days
                    elif (rec.payment_schedule=='week'):
                        n = rec.maturity
                    elif (rec.payment_schedule=='half-month'):
                        n = math.ceil(rec.maturity * (24.0 * 7.0) / 365.0)
                    elif (rec.payment_schedule=='15-days'):
                        n = math.ceil(rec.maturity * 7.0 / 15.0)
                    elif (rec.payment_schedule=='month'):
                        n = math.ceil(rec.maturity * (12.0 * 7.0) / 365.0)
                    elif (rec.payment_schedule=='30-days'):
                        n = math.ceil(rec.maturity * 7.0 / 30.0)
                    elif (rec.payment_schedule=='quarter'):
                        n = math.ceil(rec.maturity * 7.0 / 91.25)
                    elif (rec.payment_schedule=='semi-annual'):
                        n = math.ceil(rec.maturity * 7.0 / 182.5)
                    elif (rec.payment_schedule=='year'):
                        n = math.ceil(rec.maturity * 7.0 / 365.0)
                    else:
                        n = 1
                    rec.term_payments = n

    @api.multi
    def add_payment(self):
        view_id = self.env.ref('wc_loan.view_loan_payment_form').id
    	context = self._context.copy()
        context.update({
            'default_loan_id': self.id,
        })
    	return {
            'name':'Payment',
            'view_type':'form',
            'view_mode':'form',
            'views' : [(view_id,'form')],
            'res_model':'wc.loan.payment',
            'view_id':view_id,
            'type':'ir.actions.act_window',
            #'res_id':self.loan_id.id,
            'target':'current',
            #'target':'new',
            'context':context,
        }

    # SOA ##################################################################
    @api.model
    def gen_soa_details(self, loan, date_as_of, no_penalty=False, is_principal_first=False):
        #get amortization schedule
        amortizations = self.env['wc.loan.amortization'].search([
            ('loan_id','=',loan.id),
            ('state','=','open'),
            ('date_start','<=',date_as_of),
            #('date_due','>',loan.ldate_soa),
        ], order="date_due")

        try:
            days_in_year = float(loan.days_in_year)
        except:
            days_in_year = 365.0

        adate = None

        loan_start = fields.Datetime.from_string(loan.date_start)
        loan_start1 = loan_start + relativedelta(days=1)
        end_of_month = False

        if amortizations:
            adue = fields.Datetime.from_string(amortizations[0].date_start)
            if loan.payment_schedule=='week':
                month_count = 1 + int(math.floor((adue - loan_start1).days / 28))
                mstart = loan_start + relativedelta(days=month_count * 28)
            else:
                month_count = 1 + relativedelta(adue, loan_start1).months
                mstart = loan_start + relativedelta(months=month_count)
            _logger.debug("**0 months=%s mstart=%s adue=%s", month_count, mstart, adue)

        for amortization in amortizations:
            #check if the amort is at end of month
            adue = fields.Datetime.from_string(amortization.date_start)
            _logger.debug("** months=%s mstart=%s adue=%s", month_count, mstart, adue)
            if adue >= mstart:
                if adue>loan_start:
                    end_of_month = True
                month_count += 1
                if loan.payment_schedule=='week':
                    mstart = loan_start + relativedelta(days=month_count * 28)
                else:
                    mstart = loan_start + relativedelta(months=month_count)
                _logger.debug("*** months=%s mstart=%s adue=%s", month_count, mstart, adue)
            else:
                end_of_month = False

            #_logger.debug("Create SOA: %s", amortization.date_due)
            details = self.env['wc.loan.detail'].search([
                ('loan_id','=',loan.id),
                ('date_due','<',amortization.date_due),
            ])

            pdays = 0
            principal_balance = loan.amount
            penalty_base = 0.0
            penalty_base2 = 0.0
            #tpdue = 0.0

            for det in details:
                total = {
                    'penalty': 0.0,
                    'interest': 0.0,
                    'principal': 0.0,
                    'others': 0.0,
                }
                for p in det.distributions:
                    total[p.payment_type] += p.amount

                principal_balance -= total['principal']
                det_principal_balance = max(0.0, det.principal_due - total['principal'])
                det_interest_balance = max(0.0, det.interest_due - total['interest'])
                penalty_base += det_principal_balance
                penalty_base2 += det_principal_balance + det_interest_balance

                #new_state = None
                write_vals = {}

                b = fields.Datetime.from_string(det.date_due)
                a = fields.Datetime.from_string(det.date_start)
                pdays = (b-a).days

                if abs(det.total_due)<EPS and det.state!='paid':
                    write_vals.update({
                        'state': 'paid',
                        'days': 0,
                    })
                elif abs(det.total_due)>=0.005 and det.state in ['paid','next_due']:
                    write_vals.update({
                        'state': 'due',
                        'days': pdays,
                    })

                if write_vals:
                    _logger.debug("wc.loan.detail write: %s", write_vals)
                    det.write(write_vals)

                #tpdue += max(0.0, det.principal_due - total['principal'])

            idays = ( fields.Datetime.from_string(amortization.date_due)
                - fields.Datetime.from_string(amortization.date_start) ).days

            no_others_due = amortization.no_others_due

            if principal_balance > 0.0:
                if penalty_base<=principal_balance:
                    pbal = principal_balance
                else:
                    pbal = 0.0
                    no_others_due = True

                _logger.debug("**due compute: principal_balance=%0.2f tpdue=%0.2f",
                    principal_balance, penalty_base
                )

                principal_due = min(amortization.principal_due, pbal)

                #advanced principal, more than due
                if loan.principal_balance<principal_due:
                    principal_due = 0.0

                #new_bal = loan.amount - tprincipal_paid

                #interest_due = round(principal_balance * loan.interest_rate * idays / (days_in_year * 100.0), 2)
                interest_due = loan.compute_interest(
                    principal_balance,
                    amortization.date_start,
                    amortization.date_due,
                    default_amount=amortization.interest_due
                )

            else:
                loan.state = 'paid'
                break
                #principal_due = 0.0
                #interest_due = 0.0

            #penalty
            if loan.loan_type_id.is_penalty_on_interest:
                penalty_base = penalty_base2

            _logger.debug("penalty: base=%0.2f days=%0.2f", penalty_base, idays)

            #compute penalty always if is_end_of_month_penalty is false
            if (not loan.loan_type_id.is_end_of_month_penalty) \
                    or loan.date_maturity<amortization.date_due:
                end_of_month = True

            if end_of_month and penalty_base>0.0 and no_penalty==False:
                #penalty = round(penalty_base * loan.penalty_rate * idays / (days_in_year * 100.0), 2)
                #penalty = round(penalty_base * loan.penalty_rate / 100.0, 2)
                penalty = loan.compute_penalty(loan, penalty_base, idays, days_in_year)
            else:
                penalty = 0.0

            vals = {
                'loan_id': loan.id,
                'name': amortization.name,
                'date_start': amortization.date_start,
                'date_due': amortization.date_due,
                'principal_balance': principal_balance,
                'principal_due': principal_due,
                'interest_due': interest_due,
                'penalty': penalty,
                'penalty_base': penalty_base,
                'no_others_due': no_others_due,
                'state': 'next_due',
                #'is_principal_first': is_principal_first,
                #'date_soa': fields.Date.context_today(self),
                'sequence': amortization.sequence,
            }
            det = self.env['wc.loan.detail'].create(vals)
            _logger.debug("Created SOA line: %s %s", amortization.date_due, vals)
            amortization.state = 'processed'
            adate = amortization.date_due

    #@api.model
    #def create

    @api.model
    def generate_soa(self, date_as_of):
        _logger.debug("Generate SOA: date=%s", date_as_of)
        loans = self.search([ ('state','=','approved') ])
        for loan in loans:
            self.gen_soa_details(loan, date_as_of)

    # AMORTIZATION ##################################################################
    @api.model
    def compute_principal_due(self, default_principal_due, interest_due, c):
        if (self.is_fixed_payment_amount):
            principal_due = round(c - interest_due, 2)
        else:
            principal_due = default_principal_due
        return principal_due

    @api.multi
    def generate_amortization_simple_interest(self, round_to_peso=True):

        for loan in self:

            if loan.state == 'draft': # and loan.term_payments>0:

                _logger.debug("Simple interest: %s", loan)
                #delete details first
                self.details.unlink()
                self.amortizations.unlink()
                tbalance = loan.amount

                #if loan.is_360_day_year:
                #    days_in_year = 360.0
                #else:
                #    days_in_year = 365.0
                try:
                    days_in_year = float(loan.days_in_year)
                except:
                    days_in_year = 365.0

                #d1 = fields.Datetime.from_string(loan.date)
                d1 = fields.Datetime.from_string(loan.date_start)
                d0 = d1
                #d2 = d1 + relativedelta(months=loan.payment_interval)
                dend = fields.Datetime.from_string(loan.date_maturity)
                i = 1

                payments = loan.term_payments
                principal_due = 0.0

                default_principal_due = round(loan.amount / payments, 2)

                if loan.interest_rate == 0.0:
                    c = default_principal_due
                else:
                    d2, days = self.get_next_due(d1, loan.payment_schedule, i, d0, loan=loan)
                    r = loan.interest_rate * days / (days_in_year * 100.0)
                    c = loan.amount * r / (1.0 - 1.0 / ((1+r)**payments))
                    if round_to_peso:
                        c = math.ceil(c)

                for i in range(1, loan.term_payments):
                    d2, dx = self.get_next_due(d1, loan.payment_schedule, i, d0, loan=loan)
                    days = (d2 - d1).days
                    #interest_due = round(tbalance * loan.interest_rate * days / (days_in_year * 100.0), 2)
                    interest_due = loan.compute_interest(
                        tbalance,
                        d1.strftime(DF),
                        d2.strftime(DF)
                    )
                    principal_due = self.compute_principal_due(default_principal_due, interest_due, c)
                    #if (loan.is_fixed_payment_amount):
                    #    principal_due = round(c - interest_due, 2)
                    #else:
                    #    principal_due = default_principal_due

                    if principal_due!=0.0 or interest_due!=0.0:
                        vals = {
                            'loan_id': loan.id,
                            'date_start': d1.strftime(DF),
                            'date_due': d2.strftime(DF),
                            'name': "Schedule %d" % i,
                            'days': days,
                            'principal_balance': tbalance,
                            'principal_due': principal_due,
                            'interest_due': interest_due,
                            'sequence': i,
                        }
                        _logger.debug("create vals=%s", vals)
                        loan.amortizations.create(vals)
                        tbalance = tbalance - principal_due

                    d0 = d1
                    d1 = d2
                    i += 1

                days = (dend - d1).days
                #interest_due = round(tbalance * loan.interest_rate * days / (days_in_year * 100.0), 2)
                interest_due = loan.compute_interest(
                    tbalance,
                    d1.strftime(DF),
                    dend.strftime(DF)
                )

                vals = {
                    'loan_id': loan.id,
                    'date_start': d1.strftime(DF),
                    'date_due': dend.strftime(DF),
                    'name': "Schedule %d" % i,
                    'days': days,
                    'principal_balance': tbalance,
                    'principal_due': tbalance,
                    'interest_due': interest_due,
                    'sequence': i,
                }
                _logger.debug("create vals=%s", vals)
                loan.amortizations.create(vals)

    @api.multi
    def generate_schedule(self):
        #for loan in self:
            #loan.generate_deductions()
        return self.generate_amortization_simple_interest(round_to_peso=True)

    @api.multi
    def move_to_for_approval(self):
        for r in self:
            if not r.amortizations:
                self.generate_schedule()
            r.state = 'for_approval'

    @api.multi
    def import_approve(self):
        for r in self:
            r.interest_rate = r.loan_type_id.interest_rate
            r.penalty_rate = r.loan_type_id.penalty_rate
            r.maturity = r.loan_type_id.maturity
            r.payment_schedule = r.loan_type_id.payment_schedule
            r.is_fixed_payment_amount = r.loan_type_id.is_fixed_payment_amount
            r.generate_schedule()
            r.generate_deductions()
            if r.code=='DRAFT' or not r.code:
                r.code = r.loan_type_id.code + "-" + r.loan_type_id.sequence_id.next_by_id()
            self.gen_soa_details(r, r.date_start)
            r.state = 'approved'

    @api.multi
    def move_to_approved(self):
        for r in self:
            if r.state=='draft': # and not r.amortizations:
                r.generate_schedule()

            if r.code=='DRAFT' or not r.code:
                r.code = r.loan_type_id.code + "-" + r.loan_type_id.sequence_id.next_by_id()
            self.gen_soa_details(r, r.date_start)
            #self.gen_soa_details(r, r.date)
            r.state = 'approved'
            r.approved_by_id = self.env.user.id

    @api.multi
    def move_to_closed(self):
        for r in self:
            r.state = 'closed'

    #@api.multi
    #def check_gl_accounts_setup(self):
    #    if not self.env.user.company_id.ar_account_id:
    #        raise Warning(_("Default loan receivable GL account is not defined in Companies/Branch/Account Settings."))
    #
    #    if not self.env.user.company_id.ap_account_id:
    #        raise Warning(_("Default loan payable GL account is not defined in Companies/Branch/Account Settings."))
    #
    #    if not self.env.user.company_id.penalty_account_id:
    #        raise Warning(_("Default penalty GL account is not defined in Companies/Branch/Account Settings."))
    #
    #    if not self.env.user.company_id.interest_income_account_id:
    #        raise Warning(_("Default interest income GL account is not defined in Companies/Branch/Account Settings."))

    #@api.model
    #def get_ar_pd_account_id(self):
    #    if self.loan_type_id.ar_pd_account_id.id:
    #        res = self.loan_type_id.ar_pd_account_id.id
    #    else:
    #        res = False
    #    return res

    @api.model
    def get_ar_account_id(self):
        if self.state=='past-due' and self.loan_type_id.ar_pd_account_id:
            res = self.loan_type_id.ar_pd_account_id.id
        elif self.loan_type_id.ar_account_id.id:
            res = self.loan_type_id.ar_account_id.id
        else:
            res = False
        return res

    @api.model
    def get_ap_account_id(self):
        if self.loan_type_id.ap_account_id:
            res = self.loan_type_id.ap_account_id.id
        else:
            res = False
        return res

    @api.model
    def get_interest_income_account_id(self):
        if self.loan_type_id.interest_income_account_id:
            res = self.loan_type_id.interest_income_account_id.id
        else:
            res = False
        return res

    @api.model
    def get_penalty_account_id(self):
        if self.loan_type_id.penalty_account_id:
            res = self.loan_type_id.penalty_account_id.id
        else:
            res = False
        return res

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

        res = self.create({
            'restructured_from_id': self.id,
            'loan_type_id': self.loan_type_id.id,
            'maturity': self.maturity,
            'payment_schedule': self.payment_schedule,
            'term_payments': self.term_payments,
            'is_fixed_payment_amount': self.is_fixed_payment_amount,
            'interest_rate': self.interest_rate,
            'amount': self.amount,
            'term_payments': self.term_payments,
            'company_id': self.company_id.id,
            'member_id': self.member_id.id,
            'comaker_ids': self.comaker_ids,
            'deduction_ids': lines,
        })

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

    @api.multi
    def move_to_cancelled(self):
        for loan in self:
            loan.state = 'cancelled'
            if loan.code=='DRAFT':
                loan.code = 'CANCELLED'

    @api.multi
    def back_to_draft(self):
        for loan in self:
            if loan.state=='cancelled':
                loan.state = 'draft'
                if loan.code=='CANCELLED':
                    loan.code = 'DRAFT'
            else:
                raise Warning(_("Can only set to draft cancelled loan applications."))

    @api.multi
    def unlink(self):
        for rec in self:
            if rec.state != 'draft':
                raise Warning(_('You cannot delete a non-draft record.'))
        return super(Loan, self).unlink()


    @api.model
    def compute_interest(self, principal_balance, date1, date2, default_amount=False):
        self.ensure_one()
        try:
            days_in_year = float(self.days_in_year)
        except:
            days_in_year = 365.0

        idays = ( fields.Datetime.from_string(date2) - fields.Datetime.from_string(date1) ).days
        return round(principal_balance * self.interest_rate * idays / (days_in_year * 100.0), 2)

    @api.model
    def get_next_due(self, d1, payment_schedule, i=0, d0=None, loan=False):
        #returned days is used only for fixed amount payments.
        if (payment_schedule=='day'):
            d2 = d1 + relativedelta(days=1)
            days = 1
        elif (payment_schedule=='week'):
            d2 = d1 + relativedelta(days=7)
            days = 7
        elif (payment_schedule=='half-month'):
            if loan:
                d00 = fields.Datetime.from_string(loan.date_start)
                if ((i % 2)==1):
                    dd0 = d00 + relativedelta(months=(i+1)/2)
                    d2 = d1 + relativedelta(days=(dd0-d1).days/2)
                else:
                    d2 = d00 + relativedelta(months=i/2)
            else:
                if ((i % 2)==1):
                    d2 = d1 + relativedelta(days=15)
                else:
                    d2 = d0 + relativedelta(months=1)
            days = 365.0/24
        elif (payment_schedule=='15-days'):
            d2 = d1 + relativedelta(days=15)
            days = 15
        elif (payment_schedule=='month'):
            if loan:
                d00 = fields.Datetime.from_string(loan.date_start)
                d2 = d00 + relativedelta(months=i)
            else:
                d2 = d1 + relativedelta(months=i)
            days = 365.0/12
        elif (payment_schedule=='30-days'):
            d2 = d1 + relativedelta(days=30)
            days = 30
        elif (payment_schedule=='quarter'):
            if loan:
                d00 = fields.Datetime.from_string(loan.date_start)
                d2 = d00 + relativedelta(months=i*3)
            else:
                d2 = d1 + relativedelta(months=3)
            days = 365.0/4
        elif (payment_schedule=='semi-annual'):
            if loan:
                d00 = fields.Datetime.from_string(loan.date_start)
                d2 = d00 + relativedelta(months=i*6)
            else:
                d2 = d1 + relativedelta(months=6)
            days = 365.0/2
        elif (payment_schedule=='year'):
            if loan:
                d00 = fields.Datetime.from_string(loan.date_start)
                d2 = d00 + relativedelta(months=i*12)
            else:
                d2 = d1 + relativedelta(months=12)
            days = 365.0
        #elif (payment_schedule=='lumpsum'):
        #    d2 = d1 + relativedelta(months=12)
        #    days = 365.0
        else:
            d2 = d1
            days = 1
        return d2, days

    @api.model
    def num2amt(self, pnum, join=True):
        '''words = {} convert an integer number into words'''
        units = ['','one','two','three','four','five','six','seven','eight','nine']
        teens = ['','eleven','twelve','thirteen','fourteen','fifteen','sixteen', \
                 'seventeen','eighteen','nineteen']
        tens = ['','ten','twenty','thirty','forty','fifty','sixty','seventy', \
                'eighty','ninety']
        thousands = ['','thousand','million','billion','trillion','quadrillion', \
                     'quintillion','sextillion','septillion','octillion', \
                     'nonillion','decillion','undecillion','duodecillion', \
                     'tredecillion','quattuordecillion','sexdecillion', \
                     'septendecillion','octodecillion','novemdecillion', \
                     'vigintillion']
        words = []

        num = int(pnum)
        cents = (pnum-num) * 100

        if num==0: words.append('zero')
        else:
            numStr = '%d'%num
            numStrLen = len(numStr)
            groups = (numStrLen+2)/3
            numStr = numStr.zfill(groups*3)
            for i in range(0,groups*3,3):
                h,t,u = int(numStr[i]),int(numStr[i+1]),int(numStr[i+2])
                g = groups-(i/3+1)
                if h>=1:
                    words.append(units[h])
                    words.append('hundred')
                if t>1:
                    words.append(tens[t])
                    if u>=1: words.append(units[u])
                elif t==1:
                    if u>=1: words.append(teens[u])
                    else: words.append(tens[t])
                else:
                    if u>=1: words.append(units[u])
                if (g>=1) and ((h+t+u)>0): words.append(thousands[g]) #+',')

        words.append("AND %d/100" % cents)

        if join: return ' '.join(words)
        return words

    @api.model
    def compute_penalty(self, loan, penalty_base, idays, days_in_year):
        #penalty = round(penalty_base * loan.penalty_rate * idays / (days_in_year * 100.0), 2)
        return round(penalty_base * loan.penalty_rate / 100.0, 2)

#
