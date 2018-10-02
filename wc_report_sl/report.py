# -*- coding: utf-8 -*-
###############################################
# EzTech Software & Consultancy Inc. (c) 2017
###############################################

from odoo import api, fields, models
from odoo import tools, _
from odoo.exceptions import ValidationError, Warning, UserError
from odoo.modules.module import get_module_resource
from datetime import datetime
from dateutil.relativedelta import relativedelta
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT
import logging
import time

_logger = logging.getLogger(__name__)
DF = "%Y-%m-%d"

class ObjStruct(object):
    def __init__(self, d):
        for a, b in d.items():
            if isinstance(b, (list, tuple)):
               setattr(self, a, [obj(x) if isinstance(x, dict) else x for x in b])
            else:
               setattr(self, a, obj(b) if isinstance(b, dict) else b)

def nfmt(a):
    if type(a) in (float, int):
        return "{0:,.2f}".format(a)
    else:
        return ""

class AccountSL(models.TransientModel):
    #_inherit = "account.common.partner.report"
    _name = "account.report.sl"
    _description = "Account Subsidiary Ledger"

    def get_month_start(self):
        dt = fields.Date.context_today(self)
        return dt[0:8]+"01"

    def get_month_end(self):
        dt = fields.Date.from_string(self.get_month_start())
        dt2 = (dt + relativedelta(months=1)) - relativedelta(days=1)
        return dt2.strftime(DF)

    company_id = fields.Many2one('res.company', string='Company', readonly=True, default=lambda self: self.env.user.company_id)
    date_from = fields.Date(string='Start Date', default=get_month_start)
    date_to = fields.Date(string='End Date', default=get_month_end)
    partner_ids = fields.Many2many('res.partner', string='Partners / SL')

    def print_report(self):
        data = {}
        data['form'] = self.read(['date_from', 'date_to', 'partner_ids'])[0]
        _logger.debug("*sl_report: form=%s", data['form'])
        return self.env['report'].get_action(self, 'account.report_sl', data=data)

class ReportSL(models.AbstractModel):
    _name = 'report.account.report_sl'

    @api.model
    def get_lines(self, data):
        query_where = []
        query_params = []

        query_where.append("m.state=%s")
        query_params.append('posted')

        query_where.append("account_move_line.company_id=%s")
        query_params.append(self.env.user.company_id.id)

        if data['form']['date_from']:
            query_where.append("(account_move_line.date>=%s)")
            query_params.append(data['form']['date_from'])

        if data['form']['date_to']:
            query_where.append("(account_move_line.date<=%s)")
            query_params.append(data['form']['date_to'])

        if data['form']['partner_ids']:
            query_where.append("(account_move_line.partner_id IN %s)")
            query_params.append(tuple(data['form']['partner_ids']))

        where_str = ("\n                AND ".join(query_where))

        query = """
            SELECT
                account_move_line.partner_id,
                account_move_line.account_id,
                account_move_line.date,
                j.code,
                account_move_line.ref,
                m.name as move_name,
                account_move_line.name,
                account_move_line.debit,
                account_move_line.credit
            FROM account_move_line
            INNER JOIN account_journal AS j
                ON j.id = account_move_line.journal_id
            INNER JOIN account_move AS m
                ON m.id = account_move_line.move_id
            WHERE """ + where_str + """
            ORDER BY 1,2,3"""

        _logger.debug("get_lines: sql=%s", self.env.cr.mogrify(query, tuple(query_params)))
        self.env.cr.execute(query, tuple(query_params))
        res = self.env.cr.dictfetchall()
        _logger.debug("*sl_report: get_lines=%s", len(res))

        lang_code = self.env.context.get('lang') or 'en_US'
        lang = self.env['res.lang']
        lang_id = lang._lang_get(lang_code)
        date_format = lang_id.date_format

        lines = {}
        for r in res:
            partner_id = r['partner_id']
            account_id = r['account_id']
            if partner_id not in lines:
                lines[partner_id] = {}
            if account_id not in lines[partner_id]:
                lines[partner_id][account_id] = []
            r['date'] = datetime.strptime(r['date'], DEFAULT_SERVER_DATE_FORMAT).strftime(date_format)
            r['displayed_name'] = '-'.join(
                r[field_name] for field_name in ('move_name', 'ref', 'name')
                if r[field_name] not in (None, '', '/')
            )
            r['particulars'] = '-'.join(
                r[field_name] for field_name in ('ref', 'name')
                if r[field_name] not in (None, '', '/')
            )
            lines[partner_id][account_id].append(r)

        return lines

    @api.model
    def get_accounts(self, partner_id, partner_accounts):
        res = partner_accounts.get(partner_id, [])
        #_logger.debug("get_accounts: partner_id=%s", partner_id)
        #_logger.debug("get_accounts: res=%s", res)
        return res

    @api.model
    def get_account_lines(self, partner_id, account_id, account_lines):
        res = account_lines.get(partner_id, {}).get(account_id, [])
        #_logger.debug("get_account_lines: partner_id=%s account_id=%s ", partner_id, account_id)
        #_logger.debug("get_account_lines: lines=%s", res)
        return res

    @api.model
    def render_html(self, docids, data=None):

        query_where = []
        query_params = []

        if data['form']['date_from']:
            query_params.append(data['form']['date_from'])
            query_params.append(data['form']['date_from'])
        else:
            query_params.append('1900-01-01')
            query_params.append('1900-01-01')

        query_where.append("m.state=%s")
        query_params.append('posted')

        query_where.append("account_move_line.company_id=%s")
        query_params.append(self.env.user.company_id.id)

        if data['form']['date_to']:
            query_where.append("(account_move_line.date<=%s)")
            query_params.append(data['form']['date_to'])

        if data['form']['partner_ids']:
            query_where.append("(account_move_line.partner_id IN %s)")
            query_params.append(tuple(data['form']['partner_ids']))

        where_str = ("\n                AND ".join(query_where))

        query = """
            SELECT
                account_move_line.partner_id,
                acc.code AS a_code,
                acc.name AS a_name,
                account_move_line.account_id,
                SUM(CASE WHEN account_move_line.date<%s THEN account_move_line.debit END) AS tdebit,
                SUM(CASE WHEN account_move_line.date<%s THEN account_move_line.credit END) AS tcredit
            FROM account_move_line
            INNER JOIN account_account AS acc
                ON acc.id=account_move_line.account_id
            INNER JOIN account_move AS m
                ON m.id=account_move_line.move_id
            WHERE (NOT acc.deprecated)
                AND """ + where_str + """
            GROUP BY 1,2,3,4
            ORDER BY 1,2,3,4"""

        _logger.debug("sl_report: sql=%s", self.env.cr.mogrify(query, tuple(query_params)))
        self.env.cr.execute(query, tuple(query_params))

        partner_accounts = {}
        for r in self.env.cr.dictfetchall():
            partner_id = r['partner_id']
            if partner_id not in partner_accounts:
                partner_accounts[partner_id] = []
            partner_accounts[partner_id].append({
                'account_id': r['account_id'],
                'code': r['a_code'],
                'name': r['a_name'],
                'tdebit': r['tdebit'],
                'tcredit': r['tcredit'],
            })

        partner_ids = partner_accounts.keys()
        partners = self.env['res.partner'].browse(partner_ids)
        partners = sorted(partners, key=lambda x: (x and x.name or "").upper())
        #_logger.debug("*sl_report: partner=%s accounts=%s", partners, partner_accounts)

        lines = self.get_lines(data)
        _logger.debug("*sl_report: lines=%s", len(lines))
        #_logger.debug("*sl_report: lines=%s", lines)

        docargs = {
            'doc_ids': partner_ids,
            'doc_model': self.env['res.partner'],
            'data': data,
            'time': time,
            'docs': partners,
            'partner_accounts': partner_accounts,
            'account_lines': lines,
            'nfmt': nfmt,
            'get_accounts': self.get_accounts,
            'get_account_lines': self.get_account_lines,
        }
        return self.env['report'].render('account.report_sl', docargs)
