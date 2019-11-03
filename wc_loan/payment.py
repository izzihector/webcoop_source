# -*- coding: utf-8 -*-
###############################################
# EzTech Software & Consultancy Inc. (c) 2017
###############################################

from openerp import models, fields, api, _
from openerp.exceptions import Warning, ValidationError , UserError
import openerp.addons.decimal_precision as dp
from datetime import datetime
from dateutil.relativedelta import relativedelta
import logging
import util
import time

_logger = logging.getLogger(__name__)
DF = "%Y-%m-%d"
EPS = 0.00001

#IMPLEMENTATION = True

class LoanPayments(models.Model):
    _name = "wc.loan.payment"
    _description = "Loan Payment"
    _inherit = [ 'mail.thread' ]

    _order = "date desc, name"

    company_id = fields.Many2one('res.company', string='Branch', readonly=True,
        default=lambda self: self.env['res.company']._company_default_get('wc.loan'))

    name = fields.Char("Name",required=True,
        readonly=True, states={'draft': [('readonly', False)]})
    loan_id = fields.Many2one('wc.loan', 'Loan', ondelete='restrict',
        readonly=True, states={'draft': [('readonly', False)]})
    payment_schedule = fields.Selection('Payment Schedule',related='loan_id.payment_schedule', readonly=True)
    or_number = fields.Char("O.R. Number",
        readonly=True, states={'draft': [('readonly', False)]})
    check_number = fields.Char("Check No.",
        readonly=True, states={'draft': [('readonly', False)]})
    date = fields.Date("Date", required=True, default=fields.Date.context_today,
        readonly=True, states={'draft': [('readonly', False)]}, index=True)
    member_id = fields.Many2one('wc.member', string='Member',
        readonly=True, related='loan_id.member_id')
    amount = fields.Float("Amount", digits=(12,2))
    posted_amount = fields.Float("Posted Amount", digits=(12,2),
        store=False, compute="_compute_posted_amount")
    unposted_amount = fields.Float("Unposted Amount", digits=(12,2),
        store=False, compute="_compute_posted_amount")
    note = fields.Text(string='Notes')
    active = fields.Boolean(default=True)
    #posted = fields.Boolean(store=True, compute="get_posted")

    loan_state = fields.Selection(related="loan_id.state", readonly="1")

    collection_id = fields.Many2one('wc.collection', string='Collection Ref', readonly=True)
    is_reversed = fields.Boolean("Reversed")
    #advance_detail_id = fields.Many2one('wc.loan.detail', 'Adv. Payment Loan detail', readonly=True)
    #is_advance = fields.Boolean('Advance Payment', default=lambda self: self.loan_id.payment_schedule=='lumpsum')

    state = fields.Selection([
        ('draft','Draft'),
        #('cancelled','Cancelled'),
        ('confirmed','Confirmed'),
        #('semi-posted','Semi-Posted'),
        #('posted','Posted'),
    ], string='State', default=lambda self: 'draft',
        track_visibility='onchange', readonly=True)

    distributions = fields.One2many('wc.loan.payment.distribution', 'payment_id',
        'Payments Distribution')

    advance_detail_ids = fields.One2many('wc.loan.detail','advance_payment_id','Adv. Payment Bill', readony=True)

    #@api.depends(
    #    'distributions',
    #    'distributions.amount',
    #)
    #def get_posted(self):
    #    for p in self:
    #        if len(p.distributions):
    #            p.posted = True
    #        else:
    #            p.posted = False

    @api.depends(
        'date',
        'advance_detail_ids'
        'loan_id',
        'loan_id.payment_schedule',
        'loan_id.state',
        'loan_id.date_maturity',
    )
    def X_compute_advance(self):
        for p in self:
            if (
                   p.loan_id.payment_schedule=='lumpsum' and
                   (
                       p.date<p.loan_id.date_maturity or
                       len(p.advance_detail_ids)>0
                   )
            ):
                p.is_advance = True
            else:
                p.is_advance = False

    @api.depends('amount','distributions','distributions.amount')
    def _compute_posted_amount(self):
        for p in self:
            t = 0.0
            if p.state not in ['draft', 'cancelled']:
                for d in p.distributions:
                    t += d.amount
            p.posted_amount = t
            p.unposted_amount = p.amount - t

    #@api.constrains('amount','is_reversed')
    #def _check_zero_values(self):
    #    self.ensure_one()
    #    if self.amount <= 0.0 and not self.is_reversed:
    #        raise ValidationError(_("Amount must be more than zero."))

    @api.multi
    def cancel2(self):
        #todo create reverse entry for cancel
        for r in self:
            if r.collection_id:
                raise Warning(_("Cannot cancel payment from collection. Use collection menu to cancel this payment."))
            else:
                r.cancel()

    @api.multi
    def cancel(self):
        #todo create reverse entry for cancel
        for r in self:
            if r.loan_state=='closed':
                raise Warning(_("You cannot cancel payment for closed loan."))

            r.state = 'cancelled'
            if r.loan_state=='paid':
                r.loan_id = 'approved'

            details = self.env['wc.loan.detail'].search([
                ('loan_id','=',r.loan_id.id),
                ('total_due','>',0.0),
                ('state','=','paid'),
            ])
            for det in details:
                det.state = 'due'

    ###################################

    @api.model
    def get_penalty_lines(self, p, details, pamt):
        res = []
        for det in details:
            if pamt<=EPS:
                break
            penalty_bal = det.penalty + det.adjustment - det.penalty_paid
            if penalty_bal > 0.0:
                amt = min(pamt, penalty_bal)
                pamt -= amt
                vals = {
                    'payment_id': p.id,
                    'detail_id': det.id,
                    'payment_type': 'penalty',
                    'code': 'PEN',
                    'amount': amt,
                }
                _logger.debug("create: pamt=%0.2f %s", pamt, vals)
                res.append([0, 0, vals])

        return res, pamt

    @api.model
    def get_interest_lines(self, p, details, pamt):
        res = []
        for det in details:
            if pamt<=EPS:
                break
            interest_bal = det.interest_due - det.interest_paid
            if interest_bal > 0.0:
                amt = min(pamt, interest_bal)
                pamt -= amt
                vals = {
                    'payment_id': p.id,
                    'detail_id': det.id,
                    'payment_type': 'interest',
                    'code': 'INT',
                    'amount': amt,
                }
                _logger.debug("create: pamt=%0.2f %s", pamt, vals)
                res.append([0, 0, vals])

        return res, pamt


    #for lumpsum and recuring deduction items, 
    #the recuring deduction is appeared only time on payment date , so meaning it will be used as one time additional due
    #but instead need to consider advance payment for lumpsum
    @api.model
    def get_other_lines_for_lumpsum(self, p, details, pamt,target_detail):
        res = []
        dtrans_lines = []
        dep_acct_trans_obj = self.env['wc.account.transaction']
        trcode_cbu = dep_acct_trans_obj.get_deposit_code_cbu()
        trcode_sa = dep_acct_trans_obj.get_deposit_code_sa()
        context = {'ir_sequence_date': p.date}

        #get other due's balance
        others_bal = 0.0
        for det in details:
            others_bal += det.others_due - det.others_paid

        others_paid_dict_remake = {}
        #make others_paid_dict from every details
        for det in details:
            others_paid_dict = det.get_others_paid_dict(det)
            #re-make others_paid_dict
            for ded in det.loan_id.deduction_ids:
                paid_on_code = others_paid_dict.get(ded.code, 0.0)
                if others_paid_dict_remake.get(ded.code):
                    others_paid_dict_remake[ded.code] += paid_on_code
                else:
                    others_paid_dict_remake[ded.code] = paid_on_code
                    
            
        #select detail as allocate destination, basically it should be on current line
#         target_detail 
        
        #make payment distribution lines and account transaction line in case of cbu,sa
        #  per distribution
        for ded in det.loan_id.deduction_ids:
            if pamt <=EPS: break
            if ded.recurring:
#                 paid = others_paid_dict.get(ded.code, 0.0)
                paid = others_paid_dict_remake.get(ded.code, 0.0)
                due = ded.amount - paid
                deposit_account_id = ded.deposit_account_id and ded.deposit_account_id.id
                gl_account_id = ded.gl_account_id and ded.gl_account_id.id
                if due > 0.0:
                    amt = min(due, pamt)
                    pamt -= amt
                    vals = {
                        'payment_id': p.id,
#                         'detail_id': det.id,
                        'detail_id': target_detail.id,
                        'payment_type': 'others',
                        'code': ded.code,
                        'amount': amt,
                        'deposit_account_id' : deposit_account_id,
                        'gl_account_id': gl_account_id,
                    }
                    _logger.debug("create: pamt=%0.2f %s", pamt, vals)
                    res.append([0, 0, vals])
                    #p.distributions.create(vals)

                    if deposit_account_id:
                        if ded.deposit_account_id.account_type=='cbu':
                            trtype_id = trcode_cbu.id
                        else:
                            trtype_id = trcode_sa.id
                        vals = {
                            'company_id': p.company_id.id,
                            'account_id': deposit_account_id,
                            'date': p.date,
                            'deposit': amt,
                            'trcode_id': trtype_id,
                            'reference': p.or_number or 'loan payment',
                            'loan_id': det.loan_id.id,
                            'teller_id': self.env.user.id,
                            'confirm_date': fields.Datetime.now(),
                            'state': 'confirmed',
                            'name': self.env['ir.sequence'].with_context(**context).next_by_code('wc.account.transaction'),
                        }
                        dtrans_lines.append(vals)
                        _logger.debug("create dep trans: %s", vals)
                        #rec = dep_acct_trans_obj.sudo().create()
                        #rec.confirm()

        return res, pamt, dtrans_lines


    @api.model
    def get_other_lines(self, p, details, pamt):
        res = []
        dtrans_lines = []
        dep_acct_trans_obj = self.env['wc.account.transaction']
        trcode_cbu = dep_acct_trans_obj.get_deposit_code_cbu()
        trcode_sa = dep_acct_trans_obj.get_deposit_code_sa()
        context = {'ir_sequence_date': p.date}

        for det in details:
            if pamt<=EPS:
                break
            others_bal = det.others_due - det.others_paid
            if others_bal>0.0:

                others_paid_dict = det.get_others_paid_dict(det)

                for ded in det.loan_id.deduction_ids:
                    if pamt == 0: break
                    if ded.recurring:
                        paid = others_paid_dict.get(ded.code, 0.0)
                        due = ded.amount - paid
                        deposit_account_id = ded.deposit_account_id and ded.deposit_account_id.id
                        gl_account_id = ded.gl_account_id and ded.gl_account_id.id
                        if due > 0.0:
                            amt = min(due, pamt)
                            pamt -= amt
                            vals = {
                                'payment_id': p.id,
                                'detail_id': det.id,
                                'payment_type': 'others',
                                'code': ded.code,
                                'amount': amt,
                                'deposit_account_id' : deposit_account_id,
                                'gl_account_id': gl_account_id,
                            }
                            _logger.debug("create: pamt=%0.2f %s", pamt, vals)
                            res.append([0, 0, vals])
                            #p.distributions.create(vals)

                            if deposit_account_id:
                                if ded.deposit_account_id.account_type=='cbu':
                                    trtype_id = trcode_cbu.id
                                else:
                                    trtype_id = trcode_sa.id
                                vals = {
                                    'company_id': p.company_id.id,
                                    'account_id': deposit_account_id,
                                    'date': p.date,
                                    'deposit': amt,
                                    'trcode_id': trtype_id,
                                    'reference': p.or_number or 'loan payment',
                                    'loan_id': det.loan_id.id,
                                    'teller_id': self.env.user.id,
                                    'confirm_date': fields.Datetime.now(),
                                    'state': 'confirmed',
                                    'name': self.env['ir.sequence'].with_context(**context).next_by_code('wc.account.transaction'),
                                }
                                dtrans_lines.append(vals)
                                _logger.debug("create dep trans: %s", vals)
                                #rec = dep_acct_trans_obj.sudo().create()
                                #rec.confirm()

        return res, pamt, dtrans_lines

    @api.model
    def get_principal_lines(self, p, details, pamt):
        res = []
        for det in details:
            if pamt<=EPS:
                break
            principal_bal = det.principal_due - det.principal_paid
            if principal_bal > 0.0:
                amt = min(pamt, principal_bal)
                pamt -= amt
                vals = {
                    'payment_id': p.id,
                    'detail_id': det.id,
                    'payment_type': 'principal',
                    'code': 'PCP',
                    'amount': amt,
                }
                _logger.debug("create: pamt=%0.2f %s", pamt, vals)
                res.append([0, 0, vals])
                #pdist = p.distributions.create(vals)
        return res, pamt

    @api.model
    def post_create_trans(self, p, dist_lines, pcp_lines, dtrans_lines, pamt):
        _logger.debug("post_create_trans: pamt=%0.2f", pamt)
        if pamt > EPS:
            if pcp_lines:
                lpcp = pcp_lines[-1][2]
                lpcp.update({
                    'amount': lpcp.get('amount', 0.0) + pamt
                })
            else:
                d2 = self.env['wc.loan.detail'].search([
                    ('loan_id','=',p.loan_id.id)
                ], order='date_due desc', limit=1)
                if d2:
                    vals = {
                        'payment_id': p.id,
                        'detail_id': d2[0].id,
                        'payment_type': 'principal',
                        'code': 'PCP',
                        'amount': pamt,
                    }
                    _logger.debug("All det paid, create: pamt=%0.2f %s", pamt, vals)
                    dist_lines.append([0, 0, vals])

        if dtrans_lines:
            #fields = dtrans_lines[0].keys()
            sql = util.prepare_insert_sql2(self.env.cr, self._uid, "wc_account_transaction", dtrans_lines)
            t1 = time.time()
            _logger.debug("add trans batch: count=%s sql=%s\n", len(dtrans_lines), sql)
            #self.env.cr.executemany(sql, dtrans_lines)
            self.env.cr.execute(sql)
            self.env['wc.account.transaction'].invalidate_cache()
            _logger.debug("add trans batch: time=%s", time.time() - t1)
            #recompute total
            ids = [ln['account_id'] for ln in dtrans_lines]
            accounts = self.env['wc.account'].sudo().browse(ids)
            accounts.compute_total()

        if dist_lines:
            p.distributions = dist_lines
            _logger.debug("**Payment posted.")
            p.state = 'confirmed'
            p.loan_id.check_if_paid()
        else:
            raise Warning(_("Cannot post payment. Invalid billing/SOA details."))

    ###################################

    @api.model
    def post_payment_per_soa_line(self, p):
        _logger.debug("Post Payment: pstate=%s lstate=%s", p.state, p.loan_id.state)

        if p.state=='draft' and p.loan_id.state in ['approved','past-due'] :

            details = self.env['wc.loan.detail'].search([
                ('loan_id','=',p.loan_id.id),
                ('total_due','>',0.0),
                ('state','!=','del'),
            ], order='date_due')
            if not details:
                return

            dist_lines = []
            pamt = p.amount - p.posted_amount

            #penalty
            if p.loan_id.is_collect_penalty:
                lines, pamt = self.get_penalty_lines(p, details, pamt)
                dist_lines += lines

            #interest due
            lines, pamt = self.get_interest_lines(p, details, pamt)
            dist_lines += lines

            #others due
            lines, pamt, dtrans_lines = self.get_other_lines(p, details, pamt)
            dist_lines += lines

            #principal due
            pcp_lines, pamt = self.get_principal_lines(p, details, pamt)
            dist_lines += pcp_lines

            #create trans
            self.post_create_trans(p, dist_lines, pcp_lines, dtrans_lines, pamt)


    @api.model
    def Xpost_payment_per_soa_line(self, p):
        _logger.debug("Post Payment: pstate=%s lstate=%s", p.state, p.loan_id.state)
        dep_acct_trans_obj = self.env['wc.account.transaction']
        trcode_cbu = dep_acct_trans_obj.get_deposit_code_cbu()
        trcode_sa = dep_acct_trans_obj.get_deposit_code_sa()

        if p.state=='draft' and p.loan_id.state in ['approved','past-due'] :

            details = self.env['wc.loan.detail'].search([
                ('loan_id','=',p.loan_id.id),
                ('total_due','>',0.0),
                ('state','!=','del'),
            ], order='date_due')

            pamt = p.amount - p.posted_amount
            posted = False

            #penalty
            if p.loan_id.is_collect_penalty:
                for det in details:
                    if pamt == 0: break
                    penalty_bal = det.penalty + det.adjustment - det.penalty_paid
                    if penalty_bal > 0.0:
                        amt = min(pamt, penalty_bal)
                        pamt -= amt
                        vals = {
                            'payment_id': p.id,
                            'detail_id': det.id,
                            'payment_type': 'penalty',
                            'code': 'PEN',
                            'amount': amt,
                        }
                        _logger.debug("create: pamt=%0.2f %s", pamt, vals)
                        p.distributions.create(vals)
                        posted = True

            #interest due
            for det in details:
                if pamt == 0: break
                interest_bal = det.interest_due - det.interest_paid
                if interest_bal > 0.0:
                    amt = min(pamt, interest_bal)
                    pamt -= amt
                    vals = {
                        'payment_id': p.id,
                        'detail_id': det.id,
                        'payment_type': 'interest',
                        'code': 'INT',
                        'amount': amt,
                    }
                    _logger.debug("create: pamt=%0.2f %s", pamt, vals)
                    p.distributions.create(vals)
                    posted = True

            #others
            for det in details:
                if pamt == 0: break

                others_bal = det.others_due - det.others_paid
                if others_bal>0.0:

                    others_paid_dict = det.get_others_paid_dict(det)

                    for ded in det.loan_id.deduction_ids:
                        if pamt == 0: break
                        if ded.recurring:
                            paid = others_paid_dict.get(ded.code, 0.0)
                            due = ded.amount - paid
                            deposit_account_id = ded.deposit_account_id and ded.deposit_account_id.id
                            gl_account_id = ded.gl_account_id and ded.gl_account_id.id
                            if due > 0.0:
                                amt = min(due, pamt)
                                pamt -= amt
                                vals = {
                                    'payment_id': p.id,
                                    'detail_id': det.id,
                                    'payment_type': 'others',
                                    'code': ded.code,
                                    'amount': amt,
                                    'deposit_account_id' : deposit_account_id,
                                    'gl_account_id': gl_account_id,
                                }
                                _logger.debug("create: pamt=%0.2f %s", pamt, vals)
                                p.distributions.create(vals)

                                if deposit_account_id:
                                    if ded.deposit_account_id.account_type=='cbu':
                                        trtype_id = trcode_cbu.id
                                    else:
                                        trtype_id = trcode_sa.id
                                    res = dep_acct_trans_obj.sudo().create({
                                        'account_id': deposit_account_id,
                                        'date': p.date,
                                        'deposit': amt,
                                        'trcode_id': trtype_id,
                                        'reference': 'loan payment',
                                        'loan_id': det.loan_id.id,
                                        'teller_id': self.env.user.id,
                                    })
                                    res.confirm()

                                posted = True

            #principal
            pdist = None
            for det in details:
                if pamt == 0: break
                principal_bal = det.principal_due - det.principal_paid
                if principal_bal > 0.0:
                    amt = min(pamt, principal_bal)
                    pamt -= amt
                    vals = {
                        'payment_id': p.id,
                        'detail_id': det.id,
                        'payment_type': 'principal',
                        'code': 'PCP',
                        'amount': amt,
                    }
                    _logger.debug("create: pamt=%0.2f %s", pamt, vals)
                    pdist = p.distributions.create(vals)
                    posted = True

            _logger.debug("Remaining pamt=%0.2f", pamt)
            if pamt > EPS:
                if pdist:
                    pdist.write({ 'amount': pdist.amount + pamt })
                else:
                    d2 = self.env['wc.loan.detail'].search([
                        ('loan_id','=',p.loan_id.id)
                    ], order='date_due desc', limit=1)
                    if d2:
                        vals = {
                            'payment_id': p.id,
                            'detail_id': d2[0].id,
                            'payment_type': 'principal',
                            'code': 'PCP',
                            'amount': pamt,
                        }
                        _logger.debug("All det paid, create: pamt=%0.2f %s", pamt, vals)
                        p.distributions.create(vals)
                        posted = True

            if posted:
                _logger.debug("**Payment posted.")
                p.state = 'confirmed'
                p.loan_id.check_if_paid()
            else:
                raise Warning(_("Cannot post payment. Invalid billing/SOA details."))

#b586 bug fix: before penalty and other due was not considered
#     def get_detail_line(self, loan, date_start):
    @api.model
    def get_detail_line(self, loan, date_start , detdel_id):
        #used only for lumpsum
        #b586 mod
#         principal_balance = loan.principal_balance
        principal_balance = detdel_id.principal_balance
        original_due_date = detdel_id.date_due
        
        #b586 mod start
#         interest_due = loan.compute_interest(principal_balance, date_start, self.date)
        principal_bal,interest_bal,penalty_bal,others_bal,total_bal \
        = self.get_current_balance(detdel_id)
        
#         principal_due = self.amount - interest_due
        new_interest_due=0.0
        remain_principal = 0.0
        penalty_recon = 0.0
        interest_recon = 0.0
        others_recon = 0.0
        principal_recon = 0.0
        target_bal = 0.0
        total_due = 0.0
        #check if the amount is over penalty
        pamt = self.amount
        #get reconcile amount accordance with priority
        penalty_recon,pamt = self.get_partial_recon_info(penalty_bal,pamt)
        interest_recon,pamt = self.get_partial_recon_info(interest_bal,pamt)
        others_recon,pamt  = self.get_partial_recon_info(others_bal,pamt)
        principal_recon,pamt  = self.get_partial_recon_info(principal_bal,pamt)
        if pamt > EPS:
            raise Warning(_("Cannot continue! Amount is more than due.\nBalance = %0.02f") % total_bal)
        total_due = total_bal -(penalty_recon+interest_recon+others_recon+principal_recon)
        total_due_without_int = total_bal - interest_bal - (penalty_recon+others_recon+principal_recon)
        remain_principal = principal_balance - principal_recon
        #calculate interest again by remain_principal and remain_date

       #b586 mod end

        #b586 del start    
#         if (nbalance + EPS) < self.amount:
#             raise Warning(_("Cannot continue! Amount is more than due.\nBalance = %0.02f") % nbalance)        
#         vals = {
#             'loan_id': loan.id,
#             #'name': "Advance Payment %d" % n,
#             'date_start': date_start,
#             'date_due': self.date,
#             'principal_balance': principal_balance,
#             'principal_due': principal_due,
#             'interest_due': interest_due,
#             'penalty': 0.0,
#             'penalty_base': 0.0,
#             'no_others_due': True,
#             'state': 'due',
#             'advance_payment_id': self.id,
#             #'date_soa': fields.Date.context_today(self),
#             #'sequence': n,
#         }
        #b586 del end
        #b586 add satrt
        vals1 = {
            'loan_id': loan.id,
            'date_start': date_start,
            'date_due': self.date,
            'principal_balance': principal_balance,
            'principal_due': principal_recon,#b586 add
            'interest_due': interest_recon,#b586 add
            'state': 'due',
#             'no_others_due':  detdel_id.no_others_due,
#             'no_others_due':True,
            'advance_payment_id': self.id,
            }
        
        new_date_start = self.date
        new_date_due = original_due_date        
        if new_date_start > loan.date_maturity:
            if loan.state=='approved':
                loan.state = 'past-due'
            d = fields.Date.from_string(self.date) + relativedelta(days=30)
            new_date_due =  d.strftime(DF)
        if self.loan_id.is_interest_epr:
            new_interest_due = interest_bal - interest_recon
        else:
            new_interest_due = self.loan_id.compute_interest(remain_principal, new_date_start, new_date_due)
        
        vals2 = {
            'loan_id': loan.id,
            'date_start': new_date_start,
            'date_due': new_date_due,
            'principal_balance': remain_principal,
            'principal_due': remain_principal,
            'interest_due': new_interest_due,
            'penalty': 0.0,
            'penalty_base': 0.0,
#             'no_others_due':  detdel_id.no_others_due,
#             'no_others_due':True,
            'state': 'next_due',
        }
        #for set partial payment data
        vals3 = {
            'principal_recon':principal_recon,
            'interest_recon':interest_recon,
            'others_recon':others_recon,
            'penalty_recon':penalty_recon,
            'total_due':total_due,
            'total_due_without_int':total_due_without_int,
        }

        #b586
#         return vals, principal_balance, principal_due 
        return vals1,vals2, vals3

    def get_partial_recon_info(self,target_bal,amount):
        if amount - target_bal < EPS:
            target_recon = amount
            new_amount = 0
        else:
            target_recon = target_bal
            new_amount = amount - target_bal
        return target_recon , new_amount

    def get_partial_recon_with_check(self,target_bal_name,target_bal,amount):
        if amount - target_bal < EPS:
            target_recon = amount
            new_amount = 0
        else:
            raise UserError(_("%s amount is more than the due %s.") % (target_bal_name,target_bal))
        return target_recon , new_amount


    @api.multi
    def confirm_payment(self):
        self.ensure_one()
        _logger.debug("**confirm_payment: amt=%0.2f", self.amount)
        if self.amount <= 0.0:
            raise ValidationError(_("Amount must be more than zero.\nAmount=%s") % (self.amount))

        if self.date < self.loan_id.last_payment_date:
            raise Warning(_("Cannot post payment with date before from last."))

        loan = self.loan_id

        #if loan.state=='approved' and loan.payment_schedule=='lumpsum' and self.date<loan.date_maturity:
        #lumpsum, non-straight
        if loan.state in ['approved','past-due'] and loan.payment_schedule=='lumpsum':
            _logger.debug("**create_advance_payment")

            if self.date<loan.date_start:
                raise Warning(_("Cannot pay before date start."))

            #create advance bill
            det_obj = self.env['wc.loan.detail']
            n = 0
            date_start = self.loan_id.date_start
            detdel_id = False
            for d in loan.details:
                if d.date_due<self.date:
                    if d.state!='reversed' and d.date_due!=loan.date_maturity:
                        date_start = d.date_due
#b586 mod
#                     n += 1
                n += 1
                if d.state=='next_due':
                    d.state='del'
                    detdel_id = d
            _logger.debug("get previous balance")

            #inherited for manual computation
            #b586
#             vals, principal_balance, principal_due = self.get_detail_line(loan, date_start)
            vals1, vals2, vals3 = self.get_detail_line(loan, date_start,detdel_id)
            
            #b586
#             vals.update({
#                 'name': "Payment %d" % n,
#                 'sequence': n,
#             })
#             _logger.debug("create detail: %s", vals)
#             loan.details = [[0,0, vals]]
            #update original loan.detail line
#             newdet = self.env['wc.loan.detail'].create(vals)
#             loan.details = [(4,newdet.id)]


#xxxxxx            
#             original_name = detdel_id.name
#             vals1.update({
#                 'name': "Payment %d" % n,
#                 'sequence': n,
#             })
#             detdel_id.write(vals1)
#             _logger.debug("create detail: %s", vals1)            
# 
#             #self.post_payment()
# 
#             #b586
# #             self.post_payment_per_soa_line(self)
#             self.principal_amount = vals3['principal_recon']
#             self.interest_amount = vals3['interest_recon']
#             self.penalty_amount = vals3['penalty_recon']
#             self.others_amount = vals3['others_recon']
# 
#             if total_bal < EPS:
#                 self.manual_post_payment(self)
#                 self.loan_id.check_if_paid()
#                 return
#             
#             newdet = self.env['wc.loan.detail'].create(vals2)
#             loan.details = [(4,newdet.id)]
#             
#             #call manual_post_payment with partial payment data regardless is_manual_payment
# #             p = self.copy()
#             newdet.sequence = n + 1
#             newdet.name = original_name
#             self.manual_post_payment(self)
            #b586 e
            #xxxxxxxxxxxxxxx

#yyyyyyyyyyyyyyyyyy
            original_name = detdel_id.name
            original_no_others_due_flg = detdel_id.no_others_due

            #b240
#             if vals3['total_due_without_int'] < EPS:
#                 vals1.update({
#                     'name': "Payment %d" % n,
#                     'sequence': n,
#                     'no_others_due':original_no_others_due_flg,
#                     #if the last payment , no_others_due flg has to be succeeded to this payment loan detail line
#                 })
#                 detdel_id.unlink()
#                 _logger.debug("unlink detail: %s", detdel_id.id)
#             else:
#                 vals1.update({
#                     'name': "Payment %d" % n,
#                     'sequence': n,
#                     'no_others_due':True,
#                 })
#                 vals2.update({
#                     'state':'next_due',
#                     'sequence':n+1
#                 })
#                 detdel_id.write(vals2)
#                 _logger.debug("create detail: %s", vals2)            

            vals1.update({
                'name': "Payment %d" % n,
                'sequence': n,
                'no_others_due':True,
            })
            vals2.update({
                'state':'next_due',
                'sequence':n+1
            })
            detdel_id.write(vals2)
            _logger.debug("create detail: %s", vals2)            


            newdet = self.env['wc.loan.detail'].create(vals1)
            loan.details = [(4,newdet.id)]
            
            #call manual_post_payment with partial payment data regardless is_manual_payment
            
            #b586
#             self.post_payment_per_soa_line(self)
            self.principal_amount = vals3['principal_recon']
            self.interest_amount = vals3['interest_recon']
            self.penalty_amount = vals3['penalty_recon']
            self.others_amount = vals3['others_recon']

#             self.manual_post_payment(self)
            self.manual_post_payment_special(self,newdet)
            self.loan_id.check_if_paid()            
            
            
#yyyyyyyyyyyyyyyyy


#             #b586
#             newdet = self.env['wc.loan.detail'].browse(res)
#             #b586 end

#b586_2
#b586 Todo:consider to move this to common function            
#             if self.date > loan.date_maturity:
#                 #202 - check if paid already
#                 if loan.state=='approved':
#                     loan.state = 'past-due'
#                 d = fields.Date.from_string(self.date) + relativedelta(days=30)
#                 d1 = self.date
#                 d2 = d.strftime(DF)
#                 detdel_id.date_start = self.date
#                 detdel_id.date_due = d2
#             else:
#                 d1 = self.date
#                 d2 = d.date_due
            

#b586_2
#             #b586 start update current line with remaining info
#             #get new principal
#             newbal = principal_balance - principal_due

            #b586
#             interest_due = loan.compute_interest(newbal, d1, d2)
#             #fix 240
#             if detdel_id:
#                 detdel_id.state = 'next_due'
#                 detdel_id.date_start = self.date
#                 detdel_id.principal_balance = newbal
#                 detdel_id.principal_due = newbal
#                 detdel_id.interest_due = interest_due

#b586_2
# #b586 start
#                 detdel_id.others_due = newdet.others_due - newdet.others_paid
# #b586 end

#b586_2
#             #b586
#             if total_bal < EPS:
#                 loan.details = [(2,detdel_id.id)]



        else:
            self.post_payment_per_soa_line(self)
            #self.post_payment()

    @api.multi
    def post_payment(self):
        for p in self:
            self.post_payment_per_soa_line(p)
            #p.loan_id.check_if_paid()

#b586 add s
    def get_current_balance(self , detail_data = False):
        #compute balances
        self.ensure_one()
        penalty_bal = 0.0
        interest_bal = 0.0
        others_bal = 0.0
        principal_bal = 0.0
        total_bal = 0.0

        if self.state=='draft' and self.loan_id.state in ['approved','past-due'] :
#             details = self.env['wc.loan.detail'].search([
#                 ('loan_id','=',self.loan_id.id),
#                 ('total_due','>',0.0),
#                 ('state','!=','del'),
#             ], order='date_due')

#             details = self.env['wc.loan.detail'].search([
#                 ('loan_id','=',self.loan_id.id),
#                 ('total_due','>',0.0)
#             ], order='date_due')
            details = self.env['wc.loan.detail'].search([
                ('loan_id','=',self.loan_id.id),
            ], order='date_due')
            
            if details:
                for det in details:
                    penalty_bal += det.penalty + det.adjustment - det.penalty_paid
                    interest_bal += det.interest_due - det.interest_paid
                    others_bal += det.others_due - det.others_paid
                    principal_bal += det.principal_due - det.principal_paid
                    
            if self.loan_id.payment_schedule =='lumpsum':
                if not detail_data:
                    #get last detail line
                    for det in self.loan_id.details:
                        if det.state == "next_due":
                            detail_data = det
                            break
                if detail_data:
                    if self.loan_id.is_interest_epr:
                        interest_bal = detail_data.interest_due - detail_data.interest_paid
                    else:
                        interest_bal = self.loan_id.compute_interest(principal_bal, detail_data.date_start, self.date)
            
            total_bal = principal_bal + interest_bal + penalty_bal + others_bal
        return principal_bal,interest_bal,penalty_bal,others_bal,total_bal
                    
#b586 add e


class LoanPaymentDistribution(models.Model):
    _name = "wc.loan.payment.distribution"
    _description = "Loan Payment Distribution"

    payment_id = fields.Many2one('wc.loan.payment', 'Loan Payment', ondelete='cascade')
    detail_id = fields.Many2one('wc.loan.detail', 'Loan Detail', ondelete='restrict')
    deposit_account_id = fields.Many2one('wc.account', string='CBU/Dep. Account', ondelete="restrict")
    gl_account_id = fields.Many2one('account.account', string='GL Account', ondelete="restrict")

    name = fields.Char(related="detail_id.name")
    amount = fields.Float("Amount",digits=(12,2))
    code = fields.Char("Code", index=True)
    payment_type = fields.Selection([
        ('penalty','Penalty'),
        ('interest','Interest'),
        ('principal','Principal'),
        ('others','Others'),
    ], string='Payment Type', index=True)


class Loan(models.Model):
    _inherit = "wc.loan"

    @api.multi
    def check_if_paid(self):
        for loan in self:
            if loan.state in ['approved','past-due']:
                _logger.debug("**check if paid %s", loan.name)
                #process details to paid
                for det in loan.details:
                    if det.state!='reversed' and det.state!='paid' and det.total_due<=0.0:
                        det.state = 'paid'

                if 0:
                    all_amort_processed = True
                    for amort in loan.amortizations:
                        if amort.state!='processed':
                            all_amort_processed = False
                            _logger.debug("**all_amort_processed: False")
                            break
                    _logger.debug("**all_amort_processed: balance=%0.2f", loan.principal_balance)

                #if all_amort_processed and loan.principal_balance<=EPS:
                if loan.principal_balance<=EPS and loan.total_due<=EPS:
                    loan.state='paid'






#
