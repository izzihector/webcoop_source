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

    account_ids = fields.One2many('wc.account', 'member_id', string='Accounts')
    cbu_account_ids = fields.One2many('wc.account', 'member_id',
        domain=[('account_type','=','cbu')], string='CBU Accounts')

    joint_account_ids = fields.Many2many('wc.account',
        string='Joint Accounts', readonly=True)

    total_cbu = fields.Float("Total CBU", digits=(12,2), compute="compute_totals")
    total_sa = fields.Float("Total Savings", digits=(12,2), compute="compute_totals")
    account_count = fields.Integer("No. of Accounts", compute="compute_totals")

    @api.multi
    def show_accounts(self):
        self.ensure_one()
        domain = [
            "|",
                ('member_id','=',self.id),
                ('other_member_ids','=',self.id),
        ]
        #context = "{'default_account_id': %d}" % (self.id)
        context = {
            'search_default_open':1,
            'search_default_dormant':1,
            'default_member_id': self.id,
            'account_type_category':'sa',
        }
        return {
            'name': 'Accounts',
            'domain': domain,
            'res_model': 'wc.account',
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'context': context,
            'target': 'self',
            'view_mode': 'kanban,tree,form',
            #'view_ids': [
            #    (5, 0, 0),
            #    (0, 0, {'view_mode': 'kanban', 'view_id': self.env.ref('wc_account.kanban_cbu')}),
            #    (0, 0, {'view_mode': 'tree', 'view_id': self.env.ref('wc_account.tree_cbu')}),
            #    (0, 0, {'view_mode': 'form', 'view_id': self.env.ref('wc_account.form_account')}),
            #]
        }

    @api.multi
    @api.depends('account_ids','account_ids.balance', 'joint_account_ids')
    def compute_totals(self):
        for r in self:
            total_cbu = 0.0
            total_sa = 0.0
            n = 0
            account_ids = set()
            for acc in r.account_ids:
                if acc.state in ["open","dormant"]:
                    n += 1
                    account_ids.add(acc.id)
                    if acc.account_type=="cbu":
                        total_cbu += acc.balance
                    else:
                        total_sa += acc.balance

            for acc in r.joint_account_ids:
                if (acc.state in ["open","dormant"]) and (acc.id not in account_ids):
                    n += 1
                    if acc.account_type=="cbu":
                        total_cbu += acc.balance
                    else:
                        total_sa += acc.balance

            r.total_cbu = total_cbu
            r.total_sa = total_sa
            r.account_count = n

    @api.multi
    def approve_member(self):
        super(Member, self).approve_member()
        #cbu_type_id = self.env.ref('wc_account.acct_type_cbu')

        cbu_type_id = False
        for m in self:

            if m.member_type=='regular':
                
                if not cbu_type_id:
                    res_id = self.env['wc.account.type'].search([
                        ('category','=','cbu'),
                        ('company_id','=',m.company_id.id),
                    ], limit=1)
                    if not res_id:
                        raise Warning(_("Account type CBU is missing."))
                    cbu_type_id = res_id[0]

                if m.cbu_account_ids:
                    m.cbu_account_ids.approve_account()
                else:
                    acct = self.env['wc.account'].create({
                        'member_id': m.id,
                        'account_type_id': cbu_type_id.id,
                    })
                    acct.approve_account()
                    _logger.debug("**Approve member and create account %s", acct)









#
