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

import base64
try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO

MARGIN_TOP = 4
MARGIN_LEFT = 2
SKIP_MIDDLE = 18
MAXLINES = 38
WITH_LINE_NUMBER = True

_logger = logging.getLogger(__name__)
DF = "%Y-%m-%d"

def ascii_clean(a):
    if not a:
        return ""
    enye_caps = u"\u00D1"
    enye = u"\u00F1"
    res = a.replace(enye_caps, "N").replace(enye,"n").encode('ascii','replace')
    return res

class Account(models.Model):
    _inherit = "wc.account"
    passbook_line = fields.Integer("Passbook Line", readonly=True, default=0)

    @api.multi
    def print_passbook(self):
        res0 = super(Account, self).print_passbook()
        self.ensure_one()
        ctx = self.env.context.copy()
        ctx.update({
            'pp_loan_id':  self.id,
            'pp_passbook_line': self.passbook_line,
        })

        res = {
            'name': 'Passbook Printing',
            'context': ctx,
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'wc.account.passbook.wizard',
            #'res_id': self.id,
            'view_id': False,
            'type': 'ir.actions.act_window',
            'target': 'new',
        }
        _logger.debug("print_passbook: inh base=%s res=%s", res0, res)
        return res



class AccountTransaction(models.Model):
    _inherit = "wc.account.transaction"

    validation_data = fields.Binary(compute='compute_validation_data')

    @api.multi
    def print_validation(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.report.xml',
            'report_type': 'controller',
            'report_file': '/web/content/wc.account.transaction/%s/validation_data/output.prx?download=true' % self.id,
        }

    @api.model
    def get_validation_data(self):
        r = self
        with_eject = False
        tmargin = 15 #16
        lmargin = 39
        amt = abs(r.deposit - r.withdrawal)
        ts = fields.Datetime.from_string(r.confirm_date)
        try:
            cdate = fields.Datetime.context_timestamp(self, ts)
        except:
            cdate = "INVALID"

        outputStream = StringIO()
        outputStream.write("\r\n" * tmargin)
        outputStream.write("%s%s\r\n" % (" " * lmargin, r.account_id.name))
        outputStream.write("%s%s %s %s %s\r\n" % (
            " " * lmargin,
            r.name,
            r.date,
            r.trcode,
            "{:,.2f}".format(amt)))
        outputStream.write("%sTeller: %s\r\n" % (" " * lmargin, r.teller_id.name))
        outputStream.write("%sTransacted: %s\r\n" % (" " * lmargin, cdate))
        if with_eject:
            outputStream.write("\f")
        res = base64.encodestring(outputStream.getvalue())
        outputStream.close()
        return res

    @api.multi
    @api.depends(
        'state',
        'name',
        'teller_id',
        'confirm_date',
        'deposit',
        'withdrawal',
    )
    def compute_validation_data(self):
        for r in self:
            r.validation_data = r.get_validation_data()



class PassbookWizard(models.TransientModel):
    _name = 'wc.account.passbook.wizard'
    _description = 'Wizard for Passbook'

    account_id = fields.Many2one('wc.account',
        string='Deposit Account',
        readonly=True)
    passbook_line = fields.Integer("Passbook Line")
    print_data = fields.Binary('Print Data', compute='get_print_data')
    print_header = fields.Binary('Print Header', compute='get_print_header')
    front_cover_data = fields.Binary('Front Cover', compute='get_print_header')

    state = fields.Selection([
        ('draft', 'Draft'),
        #('to-confirm', 'To Confirm'),
        ('printed', 'Printed'),
    ], 'State', default="draft")

    @api.model
    def default_get(self, fields):
        rec = super(PassbookWizard, self).default_get(fields)
        context = dict(self._context or {})
        rec.update({
            'account_id': context.get('pp_loan_id'),
            'passbook_line': context.get('pp_passbook_line'),
        })
        return rec

    @api.model
    def get_first_not_printed(self):
        #find first record not printed
        trans0 = self.env['wc.account.transaction'].search([
            ('account_id','=',self.account_id.id),
            ('state','=','confirmed'),
            ('is_printed','=',False),
        ], order="date asc, name asc", limit=1)
        if trans0:
            return trans0[0].id
        else:
            return False

    @api.multi
    @api.depends(
        'account_id',
        'account_id.member_id',
        #'passbook_line',
    )
    def get_print_header(self):
        with_eject = False
        for r in self:
            address = ""
            if r.account_id.member_id.street:
                address += r.account_id.member_id.street + ", "
            if r.account_id.member_id.street2:
                address += r.account_id.member_id.street2 + ", "
            if r.account_id.member_id.city:
                address += r.account_id.member_id.city + " "
            if r.account_id.member_id.zip:
                address += r.account_id.member_id.zip + " "
            acct_no = "%s" % r.account_id.code
            outputStream = StringIO()
            outputStream.write("\r\n")
            #outputStream.write("                             %s\r\n" % r.account_id.code)
            outputStream.write("                             %s\r\n" % r.account_id.member_id.code)
            outputStream.write("      %s\r\n" % (r.account_id.clean_name))
            outputStream.write("              %s\r\n" % address)
            if with_eject:
                outputStream.write("\f")
            r.print_header = base64.encodestring(outputStream.getvalue())
            outputStream.close()

            outputStream = StringIO()
            bold_sequence = [0x12, 0x0e, 0x1B, 0x45, 0x1B, 0x47]
            outputStream.write("".join(chr(i) for i in bold_sequence))
            outputStream.write("\r\n" * 17)

            #outputStream.write("\r\n      %s" % r.account_id.code)
            outputStream.write("  %s\r\n" % r.account_id.member_id.code)
            bname = "%s%s\r\n" % (" " * 23, r.account_id.clean_name.strip())
            outputStream.write(bname[-53:])
            reset_sequence = [0x1B, 0x48, 0x1B, 0x46, 0x0F]
            outputStream.write("".join(chr(i) for i in reset_sequence))
            if with_eject:
                outputStream.write("\f")
            r.front_cover_data = base64.encodestring(outputStream.getvalue())
            outputStream.close()


    @api.multi
    @api.depends(
        'account_id',
        #'passbook_line',
    )
    def get_print_data(self):
        with_eject = False
        for r in self:
            #find first record not printed
            np_id = r.get_first_not_printed()

            if np_id:
                #get beginning balance
                btrans = self.env['wc.account.transaction'].search([
                    ('account_id','=',r.account_id.id),
                    ('state','=','confirmed'),
                    ('id','<',np_id),
                ])
                balance = 0.0 + sum(t.deposit-t.withdrawal for t in btrans)

                if self.passbook_line < 2:
                    is_new_page = 1
                    self.passbook_line = 1
                else:
                    is_new_page = 0

                limit = MAXLINES - self.passbook_line - is_new_page
                trans = self.env['wc.account.transaction'].search([
                    ('account_id','=',r.account_id.id),
                    ('state','=','confirmed'),
                    ('is_printed','=',False),
                    ('id','>=',np_id),
                ], order="date asc, name asc", limit=limit)

                if trans:
                    outputStream = StringIO()
                    outputStream.write("\r\n" * MARGIN_TOP)
                    outputStream.write("\r\n" * r.passbook_line)

                    i = r.passbook_line
                    if i>SKIP_MIDDLE:
                        outputStream.write("\r\n" * 3)

                    if WITH_LINE_NUMBER:
                        left_margin = "%s%02d" % (" " * MARGIN_LEFT, i)
                    else:
                        left_margin = "%s  " % (" " * MARGIN_LEFT)

                    if is_new_page:
                        if r.account_id.account_type=='sa':
                            outputStream.write(" %s%s%s\r\n" % (
                                left_margin[2:],
                                (" " * 12) + "Balance Forwarded" + (" " * 38),
                                "{0:*>13,.2f}".format(balance)
                            ))
                        elif r.account_id.account_type=='cbu':
                            outputStream.write("%s%s%s\r\n" % (
                                left_margin,
                                (" " * 10) + "Balance Forwarded" + (" " * 41),
                                "{0:*>12,.2f}".format(balance)
                            ))
                        i += 1

                    for tr in trans:
                        dt = fields.Date.from_string(tr.date)
                        code = "%s %s" % (tr.trcode_id.code or "", tr.reference or "")
                        balance += tr.deposit - tr.withdrawal

                        if WITH_LINE_NUMBER:
                            left_margin = "%s%02d" % (" " * MARGIN_LEFT, i)
                        else:
                            left_margin = "%s  " % (" " * MARGIN_LEFT)

                        if tr.reference == 'loan approval':
                            reference = 'Loan'
                        else:
                            reference = tr.reference or tr.trcode_id.code or ""

                        if r.account_id.account_type=='sa':
                            #ref = code.strip().ljust(13)[:13]
                            ref = reference.strip().ljust(13)[:13]
                            cdeposit = " " * 12
                            cwithdraw = " " * 12
                            cinterest = " " * 10
                            if tr.trcode_id.code == 'INT':
                                cinterest = "{0:>10,.2f}".format(tr.deposit)
                            else:
                                if tr.deposit:
                                    cdeposit = "{0:>12,.2f}".format(tr.deposit)
                                if tr.withdrawal:
                                    cwithdraw = "{0:>12,.2f}".format(tr.withdrawal)
                            #                    ln dt   r  d   w   i
                            outputStream.write(" %s %s   %s %s  %s  %s   %s\r\n" % (
                                left_margin[2:],
                                dt.strftime("%m/%d/%y"),
                                ref,
                                cdeposit,
                                cwithdraw,
                                cinterest,
                                "{0:*>13,.2f}".format(balance)
                            ))
                        elif r.account_id.account_type=='cbu':
                            #ref = code.strip().ljust(7)[:7]
                            #loan approval
                            ref = reference.strip().ljust(7)[:7]
                            cdeposit = " " * 12
                            cwithdraw = " " * 12
                            cdividend = " " * 10
                            cpatronage = " " * 10

                            if tr.trcode_id.code == 'DIV':
                                cdividend = "{0:>10,.2f}".format(tr.deposit)
                            elif tr.trcode_id.code == 'PAT':
                                cpatronage = "{0:>10,.2f}".format(tr.deposit)
                            else:
                                if tr.deposit:
                                    cdeposit = "{0:>12,.2f}".format(tr.deposit)
                                if tr.withdrawal:
                                    cwithdraw = "{0:>12,.2f}".format(tr.withdrawal)
                            #                   ln r  dt d   w  dv  p  b
                            outputStream.write("%s %s %s %s  %s %s  %s %s\r\n" % (
                                left_margin,
                                dt.strftime("%m/%d/%y"),
                                ref,
                                cdeposit,
                                cwithdraw,
                                cdividend,
                                cpatronage,
                                "{0:*>12,.2f}".format(balance)
                            ))

                        elif r.account_id.account_type=='td':
                            dtm = fields.Date.from_string(r.account_id.date_maturity)
                            #ref = code.strip().ljust(9)[:9]
                            ref = reference.strip().ljust(9)[:9]
                            cdeposit = " " * 12
                            cwithdraw = " " * 12
                            dt2 = " " * 8
                            cinterest = " " * 10

                            #ref = (tr.trcode_id.code or "").ljust(9)[:9]
                            if tr.trcode_id.code == 'INT':
                                cinterest = "{0:>10,.2f}".format(tr.deposit)
                            else:
                                if tr.deposit:
                                    cdeposit = "{0:>12,.2f}".format(tr.deposit)
                                if tr.withdrawal:
                                    cwithdraw = "{0:>12,.2f}".format(tr.withdrawal)
                                dt2 =dtm.strftime("%m/%d/%y")

                            #                   m  d  ref d  w   d2  i  b
                            outputStream.write("%s %s %s %s %s   %s  %s %s\r\n" % (
                                left_margin,
                                dt.strftime("%m/%d/%y"),
                                ref,
                                cdeposit,
                                cwithdraw,
                                dt2,
                                cinterest,
                                "{0:*>13,.2f}".format(balance)
                            ))

                        if i==SKIP_MIDDLE:
                            outputStream.write("\r\n" * 3)
                        i += 1

                    #eject page
                    if with_eject:
                        outputStream.write("\f")

                    r.print_data = base64.encodestring(outputStream.getvalue())
                    outputStream.close()

    @api.multi
    def send_to_printer(self):
        self.ensure_one()
        np_id = self.get_first_not_printed()
        if not np_id:
            raise Warning(_("No transactions to print"))

        self.state = 'printed'
        return {
            'type': 'ir.actions.report.xml',
            'report_type': 'controller',
            'report_file': '/web/content/wc.account.passbook.wizard/%s/print_data/output.prx?download=true' % self.id,
        }

    @api.multi
    def print_member_name(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.report.xml',
            'report_type': 'controller',
            'report_file': '/web/content/wc.account.passbook.wizard/%s/print_header/output.prx?download=true' % self.id,
        }

    @api.multi
    def print_front_cover(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.report.xml',
            'report_type': 'controller',
            'report_file': '/web/content/wc.account.passbook.wizard/%s/front_cover_data/output.prx?download=true' % self.id,
        }

    @api.multi
    def confirm_printed(self):
        self.ensure_one()
        np_id = self.get_first_not_printed()
        if np_id:
            if self.passbook_line == 0:
                is_new_page = 1
                self.passbook_line = 1
            else:
                is_new_page = 0
            limit = MAXLINES - self.passbook_line - is_new_page
            trans = self.env['wc.account.transaction'].search([
                ('account_id','=',self.account_id.id),
                ('state','=','confirmed'),
                ('id','>=',np_id),
            ], order="date asc, name asc", limit=limit)
            if trans:
                trans.write({'is_printed': True})

            new_pline = (self.passbook_line + len(trans) + is_new_page) % MAXLINES
            if new_pline != self.account_id.passbook_line:
                self.account_id.passbook_line = new_pline
                #self.passbook_line = new_pline






#
