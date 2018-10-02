# -*- coding: utf-8 -*-
###############################################
# EzTech Software & Consultancy Inc. (c) 2017
###############################################

from openerp import models, fields, api, _
from openerp.exceptions import Warning
import openerp.addons.decimal_precision as dp
from datetime import datetime
from dateutil.relativedelta import relativedelta
import logging
import time

_logger = logging.getLogger(__name__)
DF = "%Y-%m-%d"
EPS = 0.0000001

class ObjStruct(object):
    def __init__(self, d):
        for a, b in d.items():
            if isinstance(b, (list, tuple)):
               setattr(self, a, [obj(x) if isinstance(x, dict) else x for x in b])
            else:
               setattr(self, a, obj(b) if isinstance(b, dict) else b)


def add_total(total, vars):
    for k in vars:
        a = vars[k]
        if type(a) in (float, int):
            total[k] = total.get(k, 0.0) + a
        else:
            total[k] = a
    return total

def nfmt(a):
    if type(a) in (float, int):
        return "{0:,.2f}".format(a)
    else:
        return ""

class ReportWizard(models.TransientModel):
    _name = 'wc.loan.report.wizard'
    _description = 'Loan Report Wizard'

    #company_id = fields.Many2one('res.company', string='Branch',
    #    default=lambda self: self.env['res.company']._company_default_get('wc.loan'))

    date1 = fields.Date("Date From", required=False)
    date2 = fields.Date("Date To", required=False) #, default=fields.Date.context_today)
    maturity_date_as_of = fields.Date("Matured as of")

    @api.model
    def get_filter(self):
        self.ensure_one()
        filters = [
            ('state','not in',['draft','cancelled']),
        ]
        if self.date1:
            filters.append(('date','>=',self.date1))
        if self.date2:
            filters.append(('date','<=',self.date2))
        return filters

    @api.multi
    def release_report(self):
        self.ensure_one()
        data = {}
        res = self.env['wc.loan'].search(self.get_filter(), order="date")
        data['doc_ids'] = res.ids
        data['form'] = self.read(['date1', 'date2'])[0]
        _logger.debug("print_report: data=%s", data)
        return self.env['report'].with_context(landscape=True).get_action(self, 'wc_loan.report_release', data=data)

    @api.multi
    def release_per_product_report(self):
        self.ensure_one()
        data = {}
        res = self.env['wc.loan'].search(self.get_filter(), order="date")
        data['doc_ids'] = res.ids
        data['form'] = self.read(['date1', 'date2'])[0]
        _logger.debug("print_report: data=%s", data)
        return self.env['report'].with_context(landscape=True).get_action(self, 'wc_loan.report_release_per_product', data=data)

    @api.multi
    def consolidated_release_per_product_report(self):
        self.ensure_one()
        data = {}
        res = self.env['wc.loan'].search(self.get_filter())
        data['doc_ids'] = res.ids
        data['form'] = self.read(['date1', 'date2'])[0]
        _logger.debug("consolidated_release_per_product_report: data=%s", data)
        return self.env['report'].with_context(landscape=False).get_action(self, 'wc_loan.report_consolidated_release_per_product', data=data)

    @api.multi
    def aging_report(self):
        self.ensure_one()
        data = {}
        data['form'] = self.read(['date1', 'date2', 'maturity_date_as_of'])[0]
        return self.env['report'].with_context(landscape=True).get_action(self, 'wc_loan.report_aging', data=data)

    @api.multi
    def delinquency_report(self):
        self.ensure_one()
        data = {}
        data['form'] = self.read(['date1', 'date2', 'maturity_date_as_of'])[0]
        return self.env['report'].with_context(landscape=False).get_action(self, 'wc_loan.report_delinquency', data=data)


class ReportRelease(models.AbstractModel):
    _name = 'report.wc_loan.report_release'

    @api.model
    def render_html(self, docids, data=None):
        report_obj = self.env['report']
        report = report_obj._get_report_from_name('wc_loan.report_release')
        #company_id = self.env['res.company'].browse(data['form']['company_id'][0])

        if not docids:
            ids = data['doc_ids']
        else:
            ids = docids

        _logger.debug("report_release: data=%s",data)

        if not data:
            date1 = fields.Date.from_string(fields.Date.context_today(self))
            date2 = fields.Date.from_string(fields.Date.context_today(self))
        else:
            date1 = fields.Date.from_string(data['form']['date1'])
            date2 = fields.Date.from_string(data['form']['date2'])

        docargs = {
            'doc_ids': ids,
            'doc_model': self.env['wc.loan'],
            'docs': self.env['wc.loan'].browse(ids),
            'time': time,
            'data': data,
            'date1': date1 and date1.strftime("%B %d, %Y"),
            'date2': date2 and date2.strftime("%B %d, %Y"),
        }

        _logger.debug("report_release: args=%s",docargs)
        return report_obj.render('wc_loan.report_release', docargs)



class ReportReleasePerProduct(models.AbstractModel):
    _name = 'report.wc_loan.report_release_per_product'

    @api.model
    def render_html(self, docids, data=None):
        report_obj = self.env['report']
        report = report_obj._get_report_from_name('wc_loan.report_release_per_product')
        #company_id = self.env['res.company'].browse(data['form']['company_id'][0])

        if not docids:
            ids = data['doc_ids']
        else:
            ids = docids

        docs = self.env['wc.loan'].browse(ids)
        loan_products = {}
        for o in docs:
            if o.loan_type_id.description not in loan_products:
                loan_products[o.loan_type_id.description] = []
            loan_products[o.loan_type_id.description].append(o)

        if not data:
            date1 = fields.Date.from_string(fields.Date.context_today(self))
            date2 = fields.Date.from_string(fields.Date.context_today(self))
        else:
            date1 = fields.Date.from_string(data['form']['date1'])
            date2 = fields.Date.from_string(data['form']['date2'])

        docargs = {
            #'doc_ids': ids,
            #'doc_model': self.env['wc.loan'],
            'docs': loan_products,
            'docs_keys': sorted(loan_products.keys()),
            'time': time,
            'data': data,
            'date1': date1 and date1.strftime("%B %d, %Y"),
            'date2': date2 and date2.strftime("%B %d, %Y"),
        }

        _logger.debug("report_release_per_product: args=%s",docargs)
        return report_obj.render('wc_loan.report_release_per_product', docargs)


class ReportConsolidatedReleasePerProduct(models.AbstractModel):
    _name = 'report.wc_loan.report_consolidated_release_per_product'

    @api.model
    def render_html(self, docids, data=None):
        report_obj = self.env['report']
        report = report_obj._get_report_from_name('wc_loan.report_consolidated_release_per_product')
        #company_id = self.env['res.company'].browse(data['form']['company_id'][0])

        if not docids:
            ids = data['doc_ids']
        else:
            ids = docids

        docs = self.env['wc.loan'].browse(ids)
        loan_products = {}
        for o in docs:
            k = o.loan_type_id.description
            if k not in loan_products:
                loan_products[k] = {
                    'name': k,
                    'amount': 0.0,
                    'male': 0,
                    'female': 0,
                    'total': 0,
                }

            line = loan_products[k]

            if o.member_id.gender=='female':
                add_male = 0
                add_female = 1
            else:
                add_male = 1
                add_female = 0

            line.update({
                'amount': line.get('amount', 0.0) + o.amount,
                'male': line.get('male', 0) + add_male,
                'female': line.get('female', 0) + add_female,
                'total': line.get('total', 0) + 1,
            })

        lines = []
        for k in loan_products:
            lines.append(loan_products[k])

        if not data:
            date1 = fields.Date.from_string(fields.Date.context_today(self))
            date2 = fields.Date.from_string(fields.Date.context_today(self))
        else:
            date1 = fields.Date.from_string(data['form']['date1'])
            date2 = fields.Date.from_string(data['form']['date2'])

        docargs = {
            #'doc_ids': ids,
            #'doc_model': self.env['wc.loan'],
            'docs': sorted(lines, key=lambda line: line.get('amount',0.0), reverse=True),
            'time': time,
            'data': data,
            'date1': date1 and date1.strftime("%B %d, %Y"),
            'date2': date2 and date2.strftime("%B %d, %Y"),
        }

        _logger.debug("report_consolidated_release_per_product: args=%s",docargs)
        return report_obj.render('wc_loan.report_consolidated_release_per_product', docargs)


class LoanAgingReport(models.AbstractModel):
    _name = 'report.wc_loan.report_aging'
    @api.model
    def render_html(self, docids, data=None):
        report_obj = self.env['report']
        report = report_obj._get_report_from_name('wc_loan.report_aging')
        maturity_date_as_of = data['form']['maturity_date_as_of']
        filters = [
            ('state','not in',['draft','cancelled','paid']),
        ]
        lc_date = self.env.user.company_id.get_last_closed_date()
        if maturity_date_as_of:
            filters.append(('date_maturity','<=',maturity_date_as_of))
            title = "AGING OF LOANS BY MATURITY"
            as_of = fields.Date.from_string(maturity_date_as_of).strftime('%B %d, %Y')
        else:
            title = "AGING OF LOANS"
            #as_of = fields.Date.from_string(fields.Date.context_today(self)).strftime('%B %d, %Y')
            as_of = fields.Date.from_string(lc_date).strftime('%B %d, %Y')
            filters.append(('date','<=',lc_date))

        docs = self.env['wc.loan'].search(filters)

        docargs = {
            #'doc_ids': data['doc_ids'],
            'doc_model': report.model,
            'docs': docs.sorted(key=lambda r: "%s-%s" % (r.member_id.name, r.date)),
            'date_as_of': lc_date,
            'add_total': add_total,
            'nfmt': nfmt,
            'title': title,
            'as_of': as_of,
        }
        _logger.debug("LoanAgingReport: args=%s",docargs)
        return report_obj.render('wc_loan.report_aging', docargs)


class LoanDeliquencyReport(models.AbstractModel):
    _name = 'report.wc_loan.report_delinquency'
    @api.model
    def render_html(self, docids, data=None):
        report_obj = self.env['report']
        report = report_obj._get_report_from_name('wc_loan.report_delinquency')

        maturity_date_as_of = data['form']['maturity_date_as_of']
        filters = [
            ('state','not in',['draft','cancelled','paid']),
        ]
        if maturity_date_as_of:
            filters.append(('date_maturity','<=',maturity_date_as_of))
            title = "AGING OF LOANS SUMMARY BY MATURITY"
            as_of = fields.Date.from_string(maturity_date_as_of).strftime('%B %d, %Y')
            show_percent = True
        else:
            title = "LOANS DELIQUENCY RATE"
            as_of = fields.Date.from_string(fields.Date.context_today(self)).strftime('%B %d, %Y')
            show_percent = True

        docs = self.env['wc.loan'].search(filters)

        date_as_of = fields.Date.context_today(self)
        kdues = [
            'current',
            'pd_30',
            'pd_60',
            'pd_90',
            'pd_180',
            'pd_365',
            'pd_over1y',
        ]

        res = {}
        res['notdue'] = 0.0
        res['tpdue'] = 0.0
        res['balance'] = 0.0
        for k in kdues:
            res[k] = 0.0

        for o in docs:
            d = o.get_aging_data(date_as_of)
            res['balance'] += o.principal_balance
            for k in kdues:
                due = d.get(k, 0.0)
                res[k] += due
                if k!="current":
                    res['tpdue'] += due

        res['notdue'] = max(res['balance'] - res['tpdue'] - res['current'], 0.0)

        if res['balance']==0.0:
            res['balance'] = EPS

        docargs = {
            #'doc_ids': data['doc_ids'],
            'doc_model': report.model,
            'date_as_of': date_as_of,
            'res': ObjStruct(res),
            'nfmt': nfmt,
            'show_percent': show_percent,
            'title': title,
            'as_of': as_of,
        }
        _logger.debug("LoanDeliquencyReport: args=%s",docargs)
        return report_obj.render('wc_loan.report_delinquency', docargs)
