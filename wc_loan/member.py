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

class Member(models.Model):
    _inherit = "wc.member"

    loan_ids = fields.One2many('wc.loan', 'member_id', string='Loans')
    comaker_loan_ids = fields.Many2many('wc.loan',
        string='Comaker Loans', readonly=True)
        
    cycle_add = fields.Integer("Cycle Add", help="Added cycle base.",
        default=0, track_visibility='onchange')

    loan_count = fields.Integer("Loans", compute="compute_loan")

    @api.multi
    @api.depends('loan_ids')
    def compute_loan(self):

        for r in self:
            loans = 0
            #loan_ids = self.env['wc.loan'].sudo().search([
            #    ('id','in',r.loan_ids)
            #])
            #comaker_loan_ids = self.env['wc.loan'].sudo().search([
            #    ('id','in',r.comaker_loan_ids)
            #])
            #for loan in loan_ids:
            for loan in r.loan_ids:
                if loan.state in ['approved','paid']:
                    loans += 1
            #for loan in comaker_loan_ids:
            for loan in r.comaker_loan_ids:
                if loan.member_id.id!=r.id and loan.state in ['approved','paid']:
                    loans += 1
            r.loan_count = loans

    @api.multi
    def show_loans(self):
        self.ensure_one()
        domain = [
            "|",
                ('member_id','=',self.id),
                ('comaker_ids','=',self.id),
        ]
        context = {
            'search_default_available': 1,
            'default_member_id': self.id,
        }
        #view_id = self.env.ref('wc_account.kanban_account')
        return {
            'name': 'Loans',
            'domain': domain,
            'res_model': 'wc.loan',
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'context': context,
            #'target': 'current',
            'target': 'self',
            #'target': 'new',
        }


#
