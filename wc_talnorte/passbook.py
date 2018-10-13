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

MARGIN_TOP = 6
MARGIN_LEFT = 0
SKIP_MIDDLE = 12
SKIP_MIDDLE_LINES = 2
MAXLINES = 29
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

class AccountTransaction(models.Model):
    _inherit = "wc.account.transaction"

    @api.model
    def get_validation_data(self):
        r = self
        with_eject = False

        if r.deposit:
            tmargin = 13
            lmargin = 3
        else:
            tmargin = 3
            lmargin = 18

        amt = abs(r.deposit - r.withdrawal)
        ts = fields.Datetime.from_string(r.confirm_date)
        try:
            cdate = fields.Datetime.context_timestamp(self, ts)
        except:
            cdate = "INVALID"

        sdate = ("%s" % r.date)[:19]

        outputStream = StringIO()
        outputStream.write("\r\n" * tmargin)
        outputStream.write("%s%s %s\r\n" % (
            " " * lmargin,
            ("%s" % cdate)[:19],
            #cdate,
            r.teller_id.name
         ))
        outputStream.write("%sP%s %s\r\n" % (
            " " * lmargin,
            "{:,.2f}".format(amt),
             r.account_id.code
        ))
        if with_eject:
            outputStream.write("\f")
        res = base64.encodestring(outputStream.getvalue())
        outputStream.close()
        return res


class PassbookWizard(models.TransientModel):
    _inherit = 'wc.account.passbook.wizard'

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
            outputStream.write("\r\n" * 6)
            outputStream.write("%s%s\r\n" % (" " * 22, r.account_id.clean_name.strip()))
            outputStream.write("\r\n")
            outputStream.write("%s%s\n" % (" " * 12, ascii_clean(address)))
            outputStream.write("\r\n")
            outputStream.write("%s%s\r\n" % (" " * 22, r.account_id.code))
            #outputStream.write("%s%s\r\n" % (" " * 22, r.account_id.member_id.code))

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

        def fmt_balance(balance):
            sbal =  "P{0:,.2f}".format(balance)
            len_bal =  len(sbal)
            if len(sbal) < 14:
                sbal = ("*"*(14-len_bal)) + sbal
            return sbal


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
                        outputStream.write("\r\n" * SKIP_MIDDLE_LINES)

                    if is_new_page:
                        if WITH_LINE_NUMBER:
                            left_margin = "%s%2d " % (" " * MARGIN_LEFT, i)
                        else:
                            left_margin = "%s   " % (" " * MARGIN_LEFT)

                        outputStream.write("%s%s%s\r\n" % (
                            left_margin,
                            (" " * 43) + "Balance Forward ",
                            fmt_balance(balance)
                        ))
                        i += 1

                    for tr in trans:
                        dt = fields.Date.from_string(tr.date)
                        #code = "%s %s" % (tr.trcode_id.code or "", tr.reference or "")
                        balance += tr.deposit - tr.withdrawal

                        if WITH_LINE_NUMBER:
                            left_margin = "%s%2d " % (" " * MARGIN_LEFT, i)
                        else:
                            left_margin = "%s   " % (" " * MARGIN_LEFT)

                        cwithdraw = " " * 15
                        if tr.withdrawal:
                            cwithdraw = "{0:>15,.2f}".format(tr.withdrawal)

                        cdeposit = " " * 17
                        if tr.deposit:
                            cdeposit = "{0:>17,.2f}".format(tr.deposit)

                        scode = ((tr.trcode_id.code or "")[:4] + (tr.name or "")).ljust(15)[:15]

                        #                   line number
                        #                    |
                        #                    | date
                        #                    | |
                        #                    | | withdrawal
                        #                    | | |
                        #                    | | | deposit
                        #                    | | | |
                        #                    | | | |    sequence code
                        #                    | | | |    |
                        #                    | | | |    | balance
                        #                    | | | |    | |
                        outputStream.write("%s%s%s%s   %s %s\r\n" % (
                            left_margin,
                            dt.strftime("%m/%d/%y"),
                            cwithdraw,
                            cdeposit,
                            scode,
                            fmt_balance(balance)
                        ))

                        if i==SKIP_MIDDLE:
                            outputStream.write("\r\n" * SKIP_MIDDLE_LINES)
                        i += 1

                    #eject page
                    if with_eject:
                        outputStream.write("\f")

                    r.print_data = base64.encodestring(outputStream.getvalue())
                    outputStream.close()






#
