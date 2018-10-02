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
import time

from openpyxl import load_workbook
import base64
try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO

_logger = logging.getLogger(__name__)
EPS = 0.00001

def fmt(v):
    return v and "{:,.2f}".format(v) or ""

def nformat(ln, k):
    amt = ln.get(k)
    return amt and "{:,.2f}".format(amt) or ""

class ReportWizard(models.TransientModel):
    _name = 'wc.cash.collection.wizard'
    _description = 'Wizard for Collection Report'

    #date = fields.Date(required=True, default=fields.Date.context_today)
    date = fields.Date(required=True)
    collector_id = fields.Many2one('res.users', string='Teller/Collector')
    schedule = fields.Selection([
        ('am','AM - Morning'),
        ('pm','PM - Afternoon'),
    ], string='Schedule')

    @api.multi
    def print_report(self):
        self.ensure_one()
        data = {}
        data['doc_ids'] = self.id
        data['form'] = self.read(['collector_id', 'date', 'schedule'])[0]
        _logger.debug("print_report: data=%s", data)
        return self.env['report'].with_context(landscape=True).get_action(self, 'wc_collection_report.report_cash_collection', data=data)

    @api.multi
    def print_report_or(self):
        self.ensure_one()
        data = {}
        data['doc_ids'] = self.id
        data['form'] = self.read(['collector_id', 'date', 'schedule'])[0]
        _logger.debug("print_report: data=%s", data)
        return self.env['report'].with_context(landscape=True).get_action(self, 'wc_collection_report.report_per_or', data=data)



class CashCollectionReport(models.AbstractModel):
    _name = 'report.wc_collection_report.report_cash_collection'

    @api.model
    def get_lines(self, data):
        _logger.debug("get_lines: data=%s", data)
        summary = {}
        res = {}
        filters = [
            ('date','=',data['form'].get('date')),
            ('state','in',['confirmed','reversed']),
        ]
        filters_trans = [
            ('date','=',data['form'].get('date')),
            ('state','in',['confirmed','reversed']),
        ]

        collector_id = data['form'].get('collector_id')
        if collector_id:
            filters.append(('create_uid','=',collector_id[0]))
            filters_trans.append(('teller_id','=',collector_id[0]))

        filter_schedule = data['form'].get('schedule')

        #deposit transactions
        trans = self.env['wc.account.transaction'].search(filters_trans)
        _logger.debug("trans filters=%s: %s sched=%s", filters, trans, filter_schedule)

        for r in trans:
            schedule = "pm"
            if r.collection_id and r.collection_id.schedule:
                schedule = r.collection_id.schedule
            if schedule==filter_schedule or filter_schedule==False:
                amt =  r.deposit - r.withdrawal
                if r.trcode_id.code != 'INT' and r.reference!='loan approval' and abs(amt)>EPS:
                    if r.collection_id:
                        ref = r.collection_id.name or " "
                    else:
                        ref = r.reference or " "
                    acct_type = r.account_id.account_type
                    member_id = r.account_id.member_id
                    key = "%s-%s-%s-%s" % (r.create_uid.name, ref, member_id.code, schedule)
                    if key not in res:
                        res[key] = {
                            'ref': ref,
                            'code': member_id.code or "",
                            'name': member_id.name or "",
                            'collector': r.create_uid.name,
                            'schedule': schedule,
                        }
                    res[key][acct_type] = res[key].get(acct_type,0.0) + amt

                    #get summary
                    ks = "00%s..%s" % (r.account_id.account_type, r.account_id.account_type_id.description)
                    summary[ks] = summary.get(ks, 0.0) + amt

        #loan payments
        payments = self.env['wc.loan.payment'].search(filters)
        for p in payments:
            schedule = "pm"
            if p.collection_id and p.collection_id.schedule:
                schedule = p.collection_id.schedule
            if schedule==filter_schedule or filter_schedule==False:
                ref = p.or_number or " "
                amt = 0.0
                key = "%s-%s-%s-%s" % (p.create_uid.name, ref, p.member_id.code, schedule)
                for d in p.distributions:
                    if not d.deposit_account_id:
                        amt += d.amount
                if abs(amt)>EPS:
                    if key not in res:
                        res[key] = {
                            'ref': ref,
                            'code': p.member_id.code or "",
                            'name': p.member_id.name or "",
                            'collector': p.create_uid.name,
                            'schedule': schedule,
                        }
                    res[key]['loan'] = res[key].get('loan',0.0) + amt

                    #get summary
                    ks = "01..Loan Payment"
                    summary[ks] = summary.get(ks, 0.0) + amt

        #others
        colls = self.env['wc.collection.line'].search(filters)
        for c in colls:
            schedule = "pm"
            if c.collection_id and c.collection_id.schedule:
                schedule = c.collection_id.schedule
            if schedule==filter_schedule or filter_schedule==False:
                ref = c.collection_id.name or " "
                key = "%s-%s-%s-%s" % (c.create_uid.name, ref, c.member_id.code, schedule)
                if abs(c.amount)>EPS and c.collection_type in ['insurance','others']:
                    if key not in res:
                        res[key] = {
                            'ref': ref,
                            'code': c.member_id.code or "",
                            'name': c.member_id.name or "",
                            'collector': c.create_uid.name,
                            'schedule': schedule,
                        }
                    res[key]['other'] = res[key].get('other',0.0) + c.amount

                    #get summary
                    ks = "02..%s" % (c.name)
                    summary[ks] = summary.get(ks, 0.0) + c.amount

        #compute totals
        res2 = []
        gtotal = {}
        subtotal = {}
        hkeys = ['sa','cbu','td','loan','other']
        for k in sorted(res.keys()):
            ln = res[k]
            collector = ln['collector']
            if collector not in subtotal:
                subtotal[collector] = {}
            psubtotal =  subtotal[collector]
            is_add = False
            total = 0.0
            for k2 in hkeys:
                amt = ln.get(k2, 0.0)
                #_logger.debug("ln %s: %s", k2, amt)
                if amt:
                    is_add = True
                    total += amt
                    gtotal[k2] = gtotal.get(k2,0.0) + amt
                    psubtotal[k2] = psubtotal.get(k2,0.0) + amt

            if is_add:
                ln['total'] = total
                psubtotal['total'] = psubtotal.get('total',0.0) + total
                res2.append(ln)

        for k2 in hkeys:
            gtotal['total'] =  gtotal.get('total',0.0) + gtotal.get(k2, 0.0)

        #_logger.debug("res: %s", res)
        return res2, gtotal, subtotal, summary

    @api.model
    def render_html(self, docids, data=None):

        report_obj = self.env['report']
        report = report_obj._get_report_from_name('wc_collection_report.report_cash_collection')
        lines, gtotal, subtotal, summary = self.get_lines(data)
        #headers = self.get_other_headers(docs)
        date_as_of = fields.Date.from_string(data['form'].get('date'))

        summary2 = []
        total = 0.0
        for k in sorted(summary.keys()):
            summary2.append([k.split('..')[-1], summary[k]])
            total += summary[k]

        docargs = {
            'time': time,
            'form': data['form'],
            'date_as_of': date_as_of.strftime("%B %d, %Y"),
            'lines': lines,
            'gtotal': gtotal,
            'subtotal': subtotal,
            'summary': summary2,
            'total': total,
            #'nformat': nformat,
            'fmt': fmt,
            #'docs': docs,
            #'headers': headers,
            'collector': data['form']['collector_id'] and data['form']['collector_id'][1] or "ALL"
        }
        _logger.debug("docargs: %s", docargs)
        return report_obj.render('wc_collection_report.report_cash_collection', docargs)


class CashCollectionReportPerOR(models.AbstractModel):
    _name = 'report.wc_collection_report.report_per_or'

    @api.model
    def get_lines(self, data):
        _logger.debug("get_lines: data=%s", data)
        res = {}
        filters = [
            ('date','=',data['form'].get('date')),
            ('state','in',['confirmed','reversed']),
        ]
        filters_trans = [
            ('date','=',data['form'].get('date')),
            ('state','in',['confirmed','reversed']),
            ('reference','!=','loan approval')
        ]

        filter_schedule = False

        #deposit transactions
        trans = self.env['wc.account.transaction'].search(filters_trans)
        _logger.debug("trans filters=%s: %s sched=%s", filters, trans, filter_schedule)

        for r in trans:
            amt =  r.deposit - r.withdrawal
            if (
                    r.trcode_id.code not in ['INT','CSW','2000']
                    and abs(amt)>EPS
                    and ((not r.collection_id) or r.collection_id.in_branch)
                ):
                if r.collection_id:
                    ref = r.collection_id.name or " "
                else:
                    ref = r.reference or " "
                acct_type = r.account_id.account_type
                member_id = r.account_id.member_id
                key = "%s-%s-%s" % (ref, r.create_uid.name, member_id.code)
                if key not in res:
                    res[key] = {
                        'ref': ref,
                        'code': member_id.code or "",
                        'name': member_id.name or "",
                        'collector': r.create_uid.name,
                        #'schedule': schedule,
                    }
                res[key][acct_type] = res[key].get(acct_type,0.0) + amt

        #loan payments
        payments = self.env['wc.loan.payment'].search(filters)
        for p in payments:
            if (not p.collection_id) or p.collection_id.in_branch:
                ref = p.or_number or " "
                amt = 0.0
                key = "%s-%s-%s" % (ref, p.create_uid.name, p.member_id.code)
                for d in p.distributions:
                    if not d.deposit_account_id:
                        amt += d.amount
                if abs(amt)>EPS:
                    if key not in res:
                        res[key] = {
                            'ref': ref,
                            'code': p.member_id.code or "",
                            'name': p.member_id.name or "",
                            'collector': p.create_uid.name,
                            #'schedule': schedule,
                        }
                    res[key]['loan'] = res[key].get('loan',0.0) + amt

        #others
        colls = self.env['wc.collection.line'].search(filters)
        for c in colls:
            if (not c.collection_id) or c.collection_id.in_branch:
                ref = c.collection_id.name or " "
                key = "%s-%s-%s" % (ref, c.create_uid.name, c.member_id.code)
                if abs(c.amount)>EPS and c.collection_type in ['insurance','others']:
                    if key not in res:
                        res[key] = {
                            'ref': ref,
                            'code': c.member_id.code or "",
                            'name': c.member_id.name or "",
                            'collector': c.create_uid.name,
                            #'schedule': schedule,
                        }
                    res[key]['other'] = res[key].get('other',0.0) + c.amount

        #move lines
        jv_journal_id, cr_journal_id, cd_journal_id = self.env['wc.posting'].get_journals()
        moves = self.env['account.move'].search([
            ('journal_id','=',cr_journal_id.id),
            ('date','=',data['form'].get('date')),
            ('state','=','posted'),
            ('posting_id','=',False),
        ])
        for m in moves:
            ref = m.ref
            key = "%s-%s" % (ref, m.partner_id.name)
            if abs(m.amount)>EPS:
                if key not in res:
                    member_id = self.env['wc.member'].search([
                        ('partner_id','=',m.partner_id.id)
                    ])
                    if member_id:
                        member_code = member_id[0].code
                        member_name = member_id[0].name
                    else:
                        member_code = ""
                        member_name = m.partner_id and m.partner_id.name or ""
                        #still no name
                        #search move lines for partner_id
                        if member_name == "":
                            for ln in m.line_ids:
                                if "CASH" in ln.account_id.name.upper():
                                    member_name = ln.partner_id and ln.partner_id.name or ""
                                    break

                    res[key] = {
                        'ref': ref,
                        'code': member_code,
                        'name': member_name,
                        'collector': member_name,
                    }
                res[key]['other'] = res[key].get('other',0.0) + m.amount


        #compute totals
        res2 = []
        gtotal = {}
        hkeys = ['sa','cbu','td','loan','other']
        for k in sorted(res.keys()):
            ln = res[k]
            is_add = False
            total = 0.0
            for k2 in hkeys:
                amt = ln.get(k2, 0.0)
                #_logger.debug("ln %s: %s", k2, amt)
                if amt:
                    is_add = True
                    total += amt
                    gtotal[k2] = gtotal.get(k2,0.0) + amt

            if is_add:
                ln['total'] = total
                res2.append(ln)

        for k2 in hkeys:
            gtotal['total'] =  gtotal.get('total',0.0) + gtotal.get(k2, 0.0)

        #_logger.debug("res: %s", res)
        return res2, gtotal

    @api.model
    def render_html(self, docids, data=None):
         report_obj = self.env['report']
         report = report_obj._get_report_from_name('wc_collection_report.report_per_or')
         lines, total = self.get_lines(data)
         date_as_of = fields.Date.from_string(data['form'].get('date'))

         docargs = {
             'time': time,
             'form': data['form'],
             'date_as_of': date_as_of.strftime("%B %d, %Y"),
             'lines': lines,
             'gtotal': total,
             'fmt': fmt,
         }
         _logger.debug("report_per_or docargs: %s", docargs)
         return report_obj.render('wc_collection_report.report_per_or', docargs)


#
