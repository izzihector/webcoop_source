# -*- coding: utf-8 -*-
###############################################
# EzTech Software & Consultancy Inc. (c) 2017
###############################################

from openerp import models, fields, api, _
from openerp.exceptions import Warning, ValidationError
import openerp.addons.decimal_precision as dp
from datetime import datetime
from dateutil.relativedelta import relativedelta
import logging

_logger = logging.getLogger(__name__)
DF = "%Y-%m-%d"

class Collections(models.Model):
    _name = "wc.collection"
    _description = "Payment and Account Deposit Collection"
    _inherit = [ 'mail.thread' ]
    _order = "date desc, name"

    def is_teller(self):
        teller_group = self.env.ref('wc.group_teller')
        if teller_group.id in self.env.user.groups_id.ids:
            return True
        else:
            return False

    company_id = fields.Many2one('res.company', string='Branch', readonly=True,
        default=lambda self: self.env['res.company']._company_default_get('wc.collection'))

    name = fields.Char("Reference/OR#", required=True,
        track_visibility='onchange', readonly=True, states={'draft': [('readonly', False)]})
    code = fields.Char()
    check_number = fields.Char("Check No.",
        track_visibility='onchange', readonly=True, states={'draft': [('readonly', False)]})
    date = fields.Date("Date", required=True, default=fields.Date.context_today,
        track_visibility='onchange', readonly=True, states={'draft': [('readonly', False)]}, index=True)
    member_id = fields.Many2one('wc.member', string='Member', required=True,
        domain=[('is_approved','=',True)],
        track_visibility='onchange', readonly=True, states={'draft': [('readonly', False)]})
    member_code = fields.Char(related="member_id.code", readonly=True)
    #amount = fields.Float("Total Amount", digits=(12,2),
    #    track_visibility='onchange', readonly=True, states={'draft': [('readonly', False)]})
    amount = fields.Float("Total Amount", digits=(12,2), compute="get_amount")

    in_branch = fields.Boolean("In Branch", default=is_teller,
        readonly=False)
        #readonly=True, states={'draft': [('readonly', False)]})

    schedule = fields.Selection([
        ('am','AM - Morning'),
        ('pm','PM - Afternoon'),
    ], string='Schedule')

    note = fields.Text(string='Notes', track_visibility='onchange')
    state = fields.Selection([
        ('draft','Draft'),
        ('cancelled','Cancelled'),
        ('reversed','Reversed'),
        ('confirmed','Confirmed'),
    ], string='State', default=lambda self: 'draft',
        track_visibility='onchange', readonly=True)

    #line_filtered_ids = fields.One2many('wc.collection.line', 'collection_id', 'Collection Details',
    #    domain=[('is_deleted','=',False)], readonly=True, states={'draft': [('readonly', False)]})

    line_ids = fields.One2many('wc.collection.line', 'collection_id', 'Collection Details',
        #readonly=True, states={'draft': [('readonly', False)]},
        domain=[('is_deleted','=',False)])

    @api.model
    def get_lines(self, c):
        lines = []
        if c.member_id:
            seq = 2000
            for icoll in c.member_id.insurance_ids:
                tdue = icoll.amount - icoll.amount_paid
                if tdue > 0.0:
                    val = {
                        'collection_id' : c.id,
                        'sequence': seq,
                        'name': 'Payment %s' % (icoll.insurance_id.name),
                        'insurance_id': icoll.insurance_id.id,
                        'amount_due': tdue,
                        'insurance_collectible_id': icoll.id,
                        'collection_type': 'insurance',
                    }
                    lines.append( (0, False, val) )
                    seq += 1

        return lines

    @api.multi
    def gen_lines(self):
        for r in self:
            for ln in r.line_ids:
                if ln.collection_type != 'others':
                    ln.unlink()
            lines = r.get_lines(r)
            if lines:
                r.line_ids = lines

    @api.onchange('member_id')
    def oc_member_id(self):
        self.ensure_one()
        for line in self.line_ids:
            line.write({
                'is_deleted': True,
            })

    @api.multi
    def erase_unused(self):
        line_obj = self.env["wc.collection.line"]
        for rec in self:
            #delete lines that are not used
            lines = line_obj.search([
                ('collection_id','=',rec.id)
            ])
            for line in lines:
                if line.amount==0.0 or line.is_deleted:
                    _logger.debug("**erasing %s", line)
                    line.unlink()

    @api.multi
    def confirm(self):
        #return  #test only, delete this line on prod
        self.erase_unused()
        for rec in self:

            if rec.state!='draft':
                raise Warning(_("You can only confirm a draft collection."))
            if len(rec.line_ids)==0:
                raise Warning(_("No details entered."))
            if rec.amount<=0.0:
                raise Warning(_("Total Amount is less than or equal to 0.0."))

            if rec.name:
                #check OR# duplicates
                sql = """
                    SELECT id, date, member_id
                    FROM wc_collection
                    WHERE company_id=%s
                        AND id != %s
                        AND state != 'cancelled'
                        AND name = %s
                    LIMIT 1
                """
                self.env.cr.execute(sql, (rec.company_id.id, rec.id, rec.name))
                res = self.env.cr.dictfetchall()
                if res:
                    member_id = self.env['wc.member'].browse(res[0]['member_id'])
                    raise ValidationError(_("OR# already inputted or used.\nDate=[%s]\nMember=[%s]") \
                        % (res[0]['date'], member_id.name))

            rec.state = 'confirmed'
            for ln in rec.line_ids:
                #fix #132
                #check if insurance was CANCELLED
                if (ln.insurance_collectible_id
                    and ln.insurance_collectible_id
                    and ln.insurance_collectible_id.insurance_id
                    and ln.insurance_collectible_id.insurance_id.state=='cancelled'):
                    raise Warning(_("Cannot confirm  transaction.\nInsurance %s was cancelled.") % (
                        ln.insurance_collectible_id.insurance_id.name))

                ln.state = 'confirmed'




    @api.multi
    def cancel(self):
        self.erase_unused()
        for rec in self:
            if rec.state!='draft':
                raise Warning(_("You can only cancel a draft collection."))
            rec.state = 'cancelled'
            for ln in rec.line_ids:
                ln.state = 'cancelled'

    @api.multi
    def get_amount(self):
        for rec in self:
            tamt = 0.0
            for line in rec.line_ids:
                tamt += line.amount
            rec.amount = tamt


class CollectionDetail(models.Model):
    _name = "wc.collection.line"
    _description = "Collection Lines"
    _order = "sequence"

    collection_id = fields.Many2one('wc.collection', 'Reference', ondelete='restrict')
    member_id = fields.Many2one(related="collection_id.member_id", readonly=True, store=True)
    company_id = fields.Many2one(related="collection_id.company_id", readonly=True, store=True)
    member_code = fields.Char(related="collection_id.member_id.code", readonly=True)
    date = fields.Date(related="collection_id.date", readonly=True, store=True, index=True)
    sequence = fields.Integer("Seq", readonly=True)
    name = fields.Char(readonly=True)
    collection_type = fields.Char(readonly=True)
    amount_due = fields.Float("Amount Due", digits=(12,2), readonly=True)
    amount = fields.Float("Amount", digits=(12,2))

    insurance_id = fields.Many2one('wc.insurance', string='Insurance', readonly=True, ondelete="restrict")
    insurance_collectible_id = fields.Many2one('wc.insurance.collectible', string='Premium Line', readonly=True, ondelete="restrict")

    note = fields.Text(string='Notes')
    is_deleted = fields.Boolean()
    is_reversed = fields.Boolean()
    #state = fields.Selection(related="collection_id.state", readonly=True, store=True)
    state = fields.Selection([
        ('draft','Draft'),
        ('cancelled','Cancelled'),
        ('confirmed','Confirmed'),
    ], string='State', default=lambda self: 'draft', readonly=True)

    @api.one
    @api.constrains('amount','is_reversed')
    def _check_negative_values(self):
        #remove constraints so that collection entry can be used to reverse or return payments.
        if self.amount < 0.0 and (not self.is_reversed) and (not self.collection_type=="others"):
            raise ValidationError(_("Amount must be more than zero."))
