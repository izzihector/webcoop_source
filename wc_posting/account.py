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

_logger = logging.getLogger(__name__)
DF = "%Y-%m-%d"

VALID_DATES = {
    'quarterly': {
        #end      #start
        "03-31" : "01-01",
        "06-30" : "04-01",
        "09-30" : "07-01",
        "12-31" : "10-01",
    },
    'semi-annual': {
        #end      #start
        "06-30": "01-01",
        "12-31": "07-01",
    },
    'annual': {
        #end      #start
        "12-31": "01-01",
    },
}

class AccountChartTemplate(models.Model):
    _inherit = "account.chart.template"

    #rename Vendor Bills Journal to Payable Journal
    @api.multi
    def _prepare_all_journals(self, acc_template_ref, company, journals_dict=None):
        res = super(AccountChartTemplate, self)._prepare_all_journals(
            acc_template_ref, company, journals_dict=journals_dict)

        for j in res:
            if j['name'] == _('Vendor Bills'):
                j['name'] = "Payables"
                j['code'] = "PAY"

        return res


class Account(models.Model):
    _inherit = "wc.account"

    @api.model
    def get_balance(self, account_id, date1, date2):
        filter = [
            ('account_id','=',account_id),
            ('state','in',['confirmed','posted']),
        ]
        if date1:
            filter.append( ('date','>=', date1) )
        if date2:
            filter.append( ('date','<=', date2) )
        trans = self.env['wc.account.transaction'].search(filter)
        balance = sum([ rec.deposit - rec.withdrawal for rec in trans ])
        return balance

    @api.model
    def check_savings_interest(self, date, acct):
        ok_to_post_interest = False
        date_start = False
        date_end = False
        sdate = VALID_DATES.get(acct.account_type_id.posting_schedule, {}).get(date[5:])
        _logger.debug("valid_dates: acct=%s date=%s sdate=%s", acct.name, date, sdate)
        if sdate:
            date_end = fields.Date.from_string(date) # - relativedelta(days=1)
            date_start = fields.Date.from_string("%s-%s" % (date[:4], sdate))
            _logger.debug("TAM-AN COMPUTE INTEREST sa: %s date:%s to %s",
                acct.name,
                date_start.strftime(DF),
                date_end.strftime(DF),
            )
            ok_to_post_interest = True
        return ok_to_post_interest, fields.Date.to_string(date_start), fields.Date.to_string(date_end)

    @api.model
    def compute_interest_amount(self, acct, date_start, date_end):

        def get_interest(dt, d1, bal, interest_treshold):
            days = (dt-d1).days
            if bal<=interest_treshold:
                _logger.debug("interest %s: bal=%s below maintaining %s",
                    fields.Date.to_string(dt), bal, interest_treshold)
                interest = 0.0
            else:
                interest = bal * days * int_rate
                _logger.debug("interest %s: bal=%s days=%s int=%s",
                     fields.Date.to_string(dt), bal, days, interest)
            return interest

        _logger.debug("interest: acct=%s d1=%s d2=%s", acct.name, date_start, date_end)
        trans = self.env['wc.account.transaction'].sudo().search([
            ('account_id','=',acct.id),
            ('state','in',['confirmed','posted']),
            ('date','<=', date_start),
        ])
        bal = sum([ rec.deposit - rec.withdrawal for rec in trans ])
        _logger.debug("interest %s: bal=%s", date_start, bal)

        trans = self.env['wc.account.transaction'].sudo().search([
            ('account_id','=',acct.id),
            ('state','in',['confirmed','posted']),
            ('date','>', date_start),
            ('date','<', date_end),
        ], order='date')

        d1 = fields.Date.from_string(date_start)
        d2 = fields.Date.from_string(date_end)
        int_rate = (acct.account_type_id.interest_rate or 0.0)/36500.0
        int_amt = 0.0

        interest_treshold = acct.account_type_id.interest_level

        for tr in trans:
            dt = fields.Date.from_string(tr.date)
            interest = get_interest(dt, d1, bal, interest_treshold)
            int_amt += interest
            bal += tr.deposit - tr.withdrawal
            d1 = dt

        #cut-off
        dt = fields.Date.from_string(date_end)
        interest = get_interest(dt, d1, bal, interest_treshold)
        int_amt += interest
        _logger.debug("interest %s: bal=%s total-interest=%s ***", date_end, bal, int_amt)
        return int_amt

    @api.multi
    def compute_deposit_interest(self, date, interest_id, posting=False):
        #pdate = fields.Date.from_string(date)
        _logger.debug("COMPUTE INTEREST start: date=%s", date)
        context = {'ir_sequence_date': date}

        data = []
        account_with_int_ids = []
        to_delete = self.env['wc.account.transaction'].browse([])

        for acct in self:

            ok_to_post_interest = False
            change_td_start_date = False

            if acct.account_type=='sa':
                ok_to_post_interest, date_start, date_end = self.check_savings_interest(date, acct)

            elif acct.account_type=='td' and date==acct.date_maturity:
                _logger.debug("COMPUTE INTEREST td: %s date=%s",
                    acct.name,
                    date,
                )
                #date_start = fields.Datetime.from_string(acct.date_start)
                #date_end = pdate - relativedelta(days=1)
                date_start = acct.date_start
                date_end = date
                ok_to_post_interest = True
                change_td_start_date = True

            if ok_to_post_interest:
                #delete old interest posting, in case of re-opening of posting date (not from draft)
                if posting and (posting.state!='draft'):
                    interest_records = self.env['wc.account.transaction'].sudo().search([
                        ('account_id','=',acct.id),
                        ('state','=','confirmed',),
                        ('date','=', date),
                        ('is_printed','=', False),
                        ('reference','=','Interest posting')
                    ])
                    _logger.debug("get old interest postings count=%s.", len(interest_records))
                    to_delete += interest_records
                    #interest_records.unlink()

                interest = self.compute_interest_amount(acct, date_start, date_end)
                v = [
                    acct.id,                    #account_id
                    acct.company_id.id,         #company_id, fix bug creep on #131
                    self.env['ir.sequence'].with_context(**context).next_by_code('wc.account.transaction'), #name
                    date,                       #date
                    'Interest posting',         #reference
                    "%0.2f" % interest,         #deposit
                    interest_id.id,             #trcode_id
                    'confirmed',                #state
                    self._uid,                  #teller_id
                    self._uid,                  #create_uid
                    self._uid,                  #write_uid
                ]
                q = self.env.cr.mogrify(
                    "(nextval('wc_account_transaction_id_seq'),"
                    + "%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,"
                    + "(now() at time zone 'UTC'),(now() at time zone 'UTC'))",
                    tuple(v)
                )
                data.append(q)

                account_with_int_ids.append(acct.id)
                if change_td_start_date and acct.account_type_id.is_autorollover:
                    _logger.debug("auto-rollver: acct=%s date=%s", acct.name, date)
                    acct.date_start = date

        if to_delete:
            _logger.debug("Deleting old interest postings count=%s.", len(to_delete))
            to_delete.unlink()
            _logger.debug("Done deleting old interest postings.")

        if data:
            start = time.time()
            #TODO: use sql_prepare later.
            #fix bug creep on #131, add company_id
            sql = """
                INSERT INTO wc_account_transaction (
                    id,
                    account_id,
                    company_id,
                    name,
                    date,
                    reference,
                    deposit,
                    trcode_id,
                    state,
                    teller_id,
                    create_uid,
                    write_uid,
                    create_date,
                    write_date
                ) VALUES \n"""

            idata = ",\n".join([d for d in data])
            sql = sql + idata

            #add records
            _logger.debug("INT multi-create trans: start records=%s sql=%s", len(data), sql)
            self.env.cr.execute(sql)
            _logger.debug("INT multi-create trans: stop1 time=%s", time.time() - start)
            self.env['wc.account.transaction'].invalidate_cache()
            _logger.debug("INT multi-create trans: stop2 time=%s", time.time() - start)

            #recompute total
            _logger.debug("Recomputing account totals.")
            accounts = self.env['wc.account'].sudo().browse(account_with_int_ids)
            accounts.compute_total()
            _logger.debug("Done recomputing account totals.")

    @api.multi
    def check_if_dormant(self, date, trcode_id):

        #trcode_id = self.env['wc.tr.code'].search([
        #    ('code','=','A->D')
        #], limit=1)
        #if not trcode_id:
        #    raise Warning(_("No transaction type defined for active to dormant (A->D)."))

        for acct in self:
            months = acct.account_type_id.dormant_months
            if months>0:
                #20191213 b603 start check if there is at least one transaction
                trans = self.env['wc.account.transaction'].sudo().search([
                    ('account_id','=',acct.id),
                    ('state','!=','draft'),
                ],limit=1)
                if not trans:
                    continue
                #20191213 b603 end

                mdate = fields.Datetime.from_string(date) - relativedelta(months=months)
                #get last transaction:
                trans = self.env['wc.account.transaction'].sudo().search([
                    ('account_id','=',acct.id),
                    ('state','!=','draft'),
                    ('date','>=',mdate.strftime(DF)),
                    ('trcode','not in',['A->D','INT','CM00','WTAX','XPLT']),
                ],limit=1)
                _logger.debug("*Dormant check %s: %s > %s", acct.name, mdate.strftime(DF), trans.date)
                if not trans:
                    _logger.debug("*Dormant: %s", acct)
                    context = {'ir_sequence_date': date}
                    name = self.env['ir.sequence'].with_context(**context).next_by_code('wc.account.transaction')
                    vals = {
                        'account_id': acct.id,
                        'trcode_id': trcode_id,
                        'date': date,
                        'name': name,
                        'state': 'confirmed',
                    }
                    ctx = {'tracking_disable': True}
                    self.env['wc.account.transaction'].with_context(**ctx).create(vals)
                    #acct.transaction_ids.create(vals)
                    acct.state = 'dormant'





#
