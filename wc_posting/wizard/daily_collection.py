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
EPS = 0.00001

class DailyCollectionWizard(models.TransientModel):
    _name = "daily.collection.wizard"
    _description = 'Daily Collection Wizard'

    def get_first_open_date(self):
        company_id = self.env.user.company_id.id
        return self.env['wc.posting'].get_first_open_date(company_id)

    def get_default_collector(self):
        return self.env.user.id

    collector_id = fields.Many2one('res.users', string='Account Officer')
    date = fields.Date(default=get_first_open_date)
    due_filter = fields.Selection([
        ('Due this date only', 'Due this date only'),
        ('With missed payments', 'With missed payments'),
        ('All collectibles', 'All collectibles'),
    ], 'Filter', default='Due this date only', required=True)

    @api.multi
    def print_report(self):
        self.ensure_one()
        data = {}
        data['doc_ids'] = self.id
        data['form'] = self.read(['collector_id', 'date', 'due_filter'])[0]
        return self.env['report'].with_context(landscape=True).get_action(self, 'wc_posting.report_daily_collection', data=data)

class DailyCollectionReport(models.AbstractModel):
    _name = 'report.wc_posting.report_daily_collection'

    @api.model
    def get_loans(self, data):
        mfilter = [('state','in',['approved','past-due'])]
        due_filter =  data['form']['due_filter']
        #only_due_this_date = data['form']['only_due']
        #only_past_due = data['form']['only_past_due']

        collector_id = data['form']['collector_id'] and data['form']['collector_id'][0]
        if collector_id:
            mfilter.append(('account_officer_id','=',collector_id))
        if due_filter=='Due this date only':
            mfilter.append(('ldate_soa','<=',data['form']['date']))
        #if due_filter=='past-due':
        #    mfilter.append(('ldate_soa','<=',data['form']['date']))

        loans = self.env['wc.loan'].search(mfilter)

        if due_filter=='With missed payments':
            remove = self.env['wc.loan'].browse([])
            for loan in loans:
                for det in loan.details:
                    if det.state=='due' and det.total_due>EPS:
                        remove += loan
                        break
            loans -= remove

        return sorted(loans, key=lambda r: "%s - %s - %s - %s - %s" % (
            r.loan_type_id.name,
            r.member_id.center_id.name,
            r.member_id.lastname,
            r.member_id.firstname,
            r.member_id.middlename,
        ))

    @api.model
    def get_other_headers(self, loans):
        deductions = {}
        for loan in loans:
            for ded in loan.deduction_ids:
                if ded.recurring:
                    deductions[ded.code] = ded.sequence
        s = [ [deductions[k],k] for k in deductions ]
        res = [a[1] for a in sorted(s)]
        return res

    @api.model
    def render_html(self, docids, data=None):
        report_obj = self.env['report']
        report = report_obj._get_report_from_name('wc_posting.report_daily_collection')
        docs = self.get_loans(data)
        headers = self.get_other_headers(docs)
        docargs = {
            'time': time,
            'form': data['form'],
            'docs': docs,
            'headers': headers,
            'collector': data['form']['collector_id'] and data['form']['collector_id'][1] or "ALL"
        }
        return report_obj.render('wc_posting.report_daily_collection', docargs)



#
