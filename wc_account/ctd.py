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

_logger = logging.getLogger(__name__)
DF = "%Y-%m-%d"

def num2amt(pnum, join=True):
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


class Account(models.Model):
    _inherit = "wc.account"

    ctd_data_front = fields.Binary('CTD Front', compute='get_ctd_front')
    ctd_data_back = fields.Binary('CTD Back', compute='get_ctd_front')

    @api.multi
    @api.depends(
        'member_id',
        'account_type_id',
        'balance',
        'date_start',
        'date_maturity',
    )
    def get_ctd_front(self):
        with_eject = False
        for acct in self:
            date_start = fields.Date.from_string(acct.date_start)
            date_maturity = fields.Date.from_string(acct.date_maturity)
            days = (date_maturity-date_start).days
            amt = num2amt(acct.balance).upper()
            balance = "{:,.2f}".format(acct.balance)
            sp0 = 85-len(amt)
            if sp0<0:
                sp0 = 1
            cdate_start = date_start.strftime("%B %d, %Y").ljust(22)[:22]
            cdate_maturity = date_maturity.strftime("%B %d, %Y")

            outputStream = StringIO()
            outputStream.write("\r\n" * 10)
            outputStream.write("                    %s" % cdate_start)
            outputStream.write("                                                                ")
            outputStream.write("%s\r\n" % cdate_maturity)
            outputStream.write("                                            ")
            outputStream.write("%s\r\n" % (acct.clean_name or "").upper())
            outputStream.write("            ")
            outputStream.write("%s%s%s\r\n" % (amt, " "*sp0, balance))
            outputStream.write("\r\n")
            outputStream.write("                                 %d DAYS\r\n" % days)
            outputStream.write("                                                                          ")
            outputStream.write("%5.2f                               PER ANNUM\r\n" % acct.account_type_id.interest_rate)
            outputStream.write("\r\n" * 2)
            outputStream.write("               %s" % balance)
            sp1 = 51 - len(balance)
            outputStream.write(" " * sp1)

            manager = (acct.account_type_id.ctd_signatory or "").center(30, " ")
            teller = ("%s" % self.env.user.name).center(30, " ")
            outputStream.write("%s     %s\r\n" % (manager, teller))

            if with_eject:
                outputStream.write("\f")
            acct.ctd_data_front = base64.encodestring(outputStream.getvalue())
            outputStream.close()

            #back
            outputStream = StringIO()
            outputStream.write("\r\n" * 8)
            outputStream.write(" " * 78)
            outputStream.write("%5.2f\r\n" % acct.account_type_id.interest_rate)
            outputStream.write("\r\n" * 6)
            outputStream.write(" " * 66)
            outputStream.write("%s\r\n" % (acct.clean_name or "").upper())

            if with_eject:
                outputStream.write("\f")
            acct.ctd_data_back = base64.encodestring(outputStream.getvalue())
            outputStream.close()


    @api.multi
    def print_ctd_front(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.report.xml',
            'report_type': 'controller',
            'report_file': '/web/content/wc.account/%s/ctd_data_front/output.prx?download=true' % self.id,
        }

    @api.multi
    def print_ctd_back(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.report.xml',
            'report_type': 'controller',
            'report_file': '/web/content/wc.account/%s/ctd_data_back/output.prx?download=true' % self.id,
        }


#
