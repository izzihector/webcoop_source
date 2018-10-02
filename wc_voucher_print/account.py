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

class AccountMove(models.Model):
    _inherit = "account.move"

    cash_amount = fields.Monetary(compute='cash_amount_compute', store=True)

    @api.multi
    @api.depends('line_ids.debit', 'line_ids.credit', 'line_ids.account_id')
    def cash_amount_compute(self):
        for move in self:
            total = 0.0
            for line in move.line_ids:
                if line.account_id.user_type_id.name=='Bank and Cash':
                    total += line.debit - line.credit
            move.cash_amount = -total

    @api.model
    def num2amt(self, pnum, join=True):
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
