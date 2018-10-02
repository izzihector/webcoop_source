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
EPS = 0.00001

class Struct(object):
    def __init__(self, **entries):
        self.__dict__.update(entries)

class CollectionDetail(models.Model):
    _inherit = "wc.collection.line"
    code = fields.Char()


class Collections(models.Model):
    _inherit = "wc.collection"

    @api.model
    def get_loan_lines(self, c, lines):
        keys = [
            'penalty',
            'interest',
            'others',
            'principal',
        ]
        if c.member_id:
            seq = 1000

            process_loans = set()

            cbu_due = 0.0
            savings_due = 0.0
            #self.gen_line_account(c, cbu_due, savings_due)

            for loan in c.member_id.loan_ids:
                process_loans.add(loan.id)
                if loan.state in ['approved','past-due']:
                    due = {}
                    for k in keys:
                        due[k] = 0.0
                    for det in loan.details:
                        due['principal'] += max(0.0, det.principal_due - det.principal_paid)
                        due['interest'] += max(0.0, det.interest_due - det.interest_paid)
                        due['penalty'] += max(0.0, det.penalty_adjusted - det.penalty_paid)
                        due['others'] += max(0.0, det.others_due - det.others_paid)

                    for k in keys:
                        if due[k]>EPS: #k=='principal' or due[k]>EPS:
                            lines.append(( 0, False, {
                                'collection_id' : c.id,
                                'sequence': seq,
                                'name': 'Payment %s %s %s' % (loan.code, loan.loan_type_id.description, k.title()),
                                'loan_id': loan.id,
                                'amount_due': due[k],
                                #'code': 'loan',
                                'code': k,
                                'collection_type': 'loan_payment',
                            }))
                            seq += 1

        _logger.debug("**get_lines loans: %s", lines)
        return lines


    @api.multi
    def confirm_loan(self):

        hfields = [
            'name',
            'collection_id',
            'loan_id',
            'date',
            'or_number',
        ]

        dfields = [
            'principal',
            'interest',
            'penalty',
            'others',
        ]

        payment_obj = self.env['wc.loan.payment']
        #add to loan transactions
        for rec in self:
            #pp = {
            #    'id': False,
            #    'date': "%s" % rec.date,
            #}
            #p = Struct(**pp)
            loan_ids = {}
            for line in rec.line_ids:
                if line.collection_type=='loan_payment' and line.amount!=0.0 and not line.is_deleted:

                    loan_id = line.loan_id.id
                    if loan_id not in loan_ids:
                        loan_ids[loan_id] = {
                            'company_id': rec.company_id.id,
                            'name': 'Collection %s' % rec.name,
                            'collection_id': rec.id,
                            'loan_id': loan_id,
                            'date': rec.date,
                            'or_number': rec.name,
                            'principal': 0.0,
                            'interest': 0.0,
                            'penalty': 0.0,
                            'others': 0.0,
                            'line_ids': [],
                        }

                    loan_ids[loan_id][line.code] += line.amount
                    loan_ids[loan_id]['line_ids'].append(line.id)

            _logger.debug("confirm loan-coll-sep %s: loans=%s", rec.name, loan_ids)

            for k in loan_ids:
                coll = loan_ids[k]
                distributions = []

                pdata = {}
                for hf in hfields:
                    pdata[hf] = coll[hf]

                amt = 0.0
                for df in dfields:
                    if coll[df] < -EPS:
                        raise ValidationError(_("%s payment cannot be less than 0.") % df.title())
                    amt += coll[df]

                details = False
                if amt>EPS:
                    details = self.env['wc.loan.detail'].search([
                        ('loan_id','=',k),
                        ('total_due','>',0.0),
                        ('state','!=','del'),
                    ], order='date_due')

                if details:
                    pdata.update({
                        'amount': amt,
                        #'state': 'confirmed',
                        #'distributions': distributions,
                    })
                    _logger.debug("add loan payment: %s", pdata)
                    p = payment_obj.create(pdata)

                    penalty = coll['penalty']
                    pen_lines, penalty2 = payment_obj.get_penalty_lines(p, details, penalty)
                    distributions += pen_lines
                    if penalty2>EPS:
                        raise ValidationError(_("Penalty payment is more than due."))

                    interest = coll['interest']
                    int_lines, interest2 = payment_obj.get_interest_lines(p, details, interest)
                    distributions += int_lines
                    if interest2>EPS:
                        raise ValidationError(_("Interest payment is more than due."))

                    others = coll['others']
                    oth_lines, others2, dtrans_lines = payment_obj.get_other_lines(p, details, others)
                    distributions += oth_lines
                    if others2>EPS:
                        raise ValidationError(_("Others payment is more than due. Over = %s") % others2)

                    principal = coll['principal']
                    principal_balance = p.loan_id.principal_balance
                    if (principal-principal_balance)>EPS:
                        raise ValidationError(_("Principal payment is more than balance.\nBalance = %s") % principal_balance)
                    pcp_lines, pamt = payment_obj.get_principal_lines(p, details, principal)
                    distributions += pcp_lines

                    #create trans
                    payment_obj.post_create_trans(p, distributions, pcp_lines, dtrans_lines, pamt)

                    lines = self.env['wc.collection.line'].browse(coll['line_ids'])
                    lines.write({
                        'loan_payment_id': p.id
                    })


    @api.multi
    def cancel_collection_loan(self):
        #add to account transactions
        #dt = fields.Date.context_today(self)
        for rec in self:
            loans = {}
            for line in rec.line_ids:
                if line.collection_type=='loan_payment' and line.loan_payment_id and line.amount!=0.0 and not line.is_deleted:
                    loans[line.loan_payment_id.id] = line.loan_payment_id
                    #line.loan_payment_id.cancel()

            #_logger.debug("add loan payment: %s", pdata)
            for k in loans:
                p = loans[k]
                p.cancel()
