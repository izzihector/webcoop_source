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

class ResPartner(models.Model):
    _inherit = "res.partner"

    street = fields.Char(track_visibility='onchange')
    street2 = fields.Char(track_visibility='onchange')
    city = fields.Char(track_visibility='onchange')
    state_id = fields.Many2one(string='Province', track_visibility='onchange')
    zip = fields.Char(track_visibility='onchange')
    country_id = fields.Many2one(track_visibility='onchange')

    mobile = fields.Char(track_visibility='onchange')
    phone = fields.Char(track_visibility='onchange')
    fax = fields.Char(track_visibility='onchange')
    email = fields.Char(track_visibility='onchange')

    @api.model
    def create(self, vals):
        new_name = vals.get('name', 'New')
        vals.update({ 'name': new_name })
        return super(ResPartner, self).create(vals)

    @api.model
    def get_member_code(self):
        self.ensure_one()
        res = self.env['wc.member'].search([('partner_id','=',self.id)], limit=1)
        return res and res[0].code or ""

class Member(models.Model):
    _name = "wc.member"
    _inherit = "mail.thread"
    _inherits = {'res.partner': 'partner_id'}
    _description = "Member Masterfile"
    _order = "lastname, firstname, middlename"

    @api.model
    def default_image(self):
        image_path = get_module_resource('wc_member', 'static/src/img', 'default_image.png')
        return tools.image_resize_image_big(open(image_path, 'rb').read().encode('base64'))

    code = fields.Char('Member ID', required=False, readonly=True, index=True)
    name = fields.Char("Name", related='partner_id.name', store=True)
    name2 = fields.Char(compute="compute_name")

    lastname = fields.Char('Last Name', required=True, track_visibility='onchange')
    firstname = fields.Char('First Name', required=True, track_visibility='onchange')
    middlename = fields.Char('Middle Name', track_visibility='onchange')

    partner_id = fields.Many2one('res.partner', required=True, ondelete='restrict', auto_join=True,
        string='Related Partner', help='Partner-related data of the user')

    member_type = fields.Selection([
        ('regular', 'Regular Member'),
        ('associate', 'Associate Member'),
        ('affiliate', 'Affiliate Member'),
        ('other', 'Others')
    ], string = 'Membership Type', track_visibility='onchange', default='regular')

    gender = fields.Selection([
        ('male', 'Male'),
        ('female', 'Female'),
    ], 'Gender', track_visibility='onchange')

    civil_status = fields.Selection([
        ('single', 'Single'),
        ('married', 'Married'),
        ('widower', 'Widower'),
        ('divorced', 'Divorced')
    ], string='Civil Status', track_visibility='onchange')

    company_id = fields.Many2one('res.company', string='Branch', readonly=True,
        default=lambda self: self.env['res.company']._company_default_get('wc.member'))

    center_id = fields.Many2one("wc.center", string="Center", required=False,
        track_visibility='onchange', ondelete="restrict")
    barangay_id = fields.Many2one("wc.barangay", string="Barangay", required=False,
        track_visibility='onchange', ondelete="restrict")
    municipal_id = fields.Many2one("wc.municipal", string="Municipality/City", required=False,
        track_visibility='onchange', ondelete="restrict")
    province_id = fields.Many2one("wc.province", string="Province", required=False,
        track_visibility='onchange', ondelete="restrict")

    spouse = fields.Char(track_visibility='onchange')
    birthplace = fields.Char(track_visibility='onchange')
    birthday = fields.Date(track_visibility='onchange')
    age = fields.Float(compute="_get_age", digits=(12,2))
    nationality = fields.Char(
        #default="Filipino",
        track_visibility='onchange')
    profession = fields.Char('Job/Profession', track_visibility='onchange')

    company = fields.Char('Company Name', track_visibility='onchange')
    company_address = fields.Char('Work Address', track_visibility='onchange')
    company_contact = fields.Char('Work Contact No.', track_visibility='onchange')

    account_officer_id = fields.Many2one('res.users', string="Account Officer",
        track_visibility='onchange', ondelete="restrict")

    is_approved = fields.Boolean(default=False, track_visibility='onchange')
    approver_id = fields.Many2one('res.users', string="Approved By",
        track_visibility='onchange', ondelete="restrict")
    approval_date = fields.Date('Date Approved', track_visibility='onchange')

    membership_date = fields.Date("Membership Date",
        track_visibility='onchange', default=fields.Date.context_today)
    membership_end_date = fields.Date("End Date", track_visibility='onchange')

    emergency_contact = fields.Char('Emergency Contact Name', help="Contact in case of emergency",
        track_visibility='onchange')

    sss_no = fields.Char('SSS No.', track_visibility='onchange')
    gsis_no = fields.Char('GSIS No.', track_visibility='onchange')
    phic_no = fields.Char('PhilHealth No.', track_visibility='onchange')
    tin = fields.Char('Tax ID No.', track_visibility='onchange')

    children = fields.Char('No. of Children', track_visibility='onchange')

    @api.model
    def create(self, vals):
        res = super(Member, self).create(vals)
        res.partner_id.sudo().write({
            'company_id': res.company_id.id,
            'name': res.name2,
            'customer': True,
            'supplier': True,
        })
        return res

    @api.multi
    def Xwrite(self, vals):
        res = super(Member, self).write(vals)
        name = vals.get('name')
        #if name and name!=self.partner_id.name:
        if name:
            self.partner_id.write({ 'name': name })
        return res

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        args = args or []
        records = self.browse()
        if name:
            records = self.search([('code', 'ilike', name)] + args, limit=limit)
        if not records:
            records = self.search([('name', operator, name)] + args, limit=limit)
        return records.name_get()

    @api.multi
    def approve_member(self):
        for rec in self:
            rec.approver_id = self._uid
            rec.approval_date = fields.Date.context_today(self)
            rec.is_approved = True
            if not rec.code:
                #prefix = self.env.user.company_id.branch_code
                if rec.company_id.branch_code:
                    prefix = "%s-" % rec.company_id.branch_code
                else:
                    prefix = ""
                rec.code = "%s%s" % (prefix, self.env['ir.sequence'].next_by_code('wc.member'))

    @api.multi
    def toggle_approved(self):
        self.ensure_one()
        if self.is_approved:
            self.approver_id = False
            self.approval_date = False
            self.is_approved = False
        else:
            self.approve_member()

    @api.multi
    def set_default_image(self):
        #_logger.info("Set default image: %s", self.ids)
        self.write({
            'image': self.default_image()
        })

    @api.onchange('center_id')
    def oc_center_id(self):
        for r in self:
            if r.center_id:
                #r.write({
                #    'barangay_id': r.center_id.barangay_id.id,
                #    'municipal_id': r.center_id.barangay_id.municipal_id.id,
                #    'province_id': r.center_id.barangay_id.municipal_id.province_id.id,
                #})
                r.barangay_id = r.center_id.barangay_id
                r.municipal_id = r.barangay_id.municipal_id
                r.province_id = r.municipal_id.province_id

    @api.onchange('barangay_id')
    def oc_barangay_id(self):
        if self.barangay_id:
            domain = {}
            if self.center_id.barangay_id != self.barangay_id:
                self.center_id = False
            self.municipal_id = self.barangay_id.municipal_id
            self.province_id = self.municipal_id.province_id
            center_domain = [('municipal_id','=',self.municipal_id.id)]
            domain = {
                'center_id': center_domain
            }
        else:
            domain = {
                'center_id': []
            }
        return {'domain': domain }

    @api.onchange('municipal_id')
    def oc_municipal_id(self):
        if self.municipal_id:
            domain = {}
            if self.barangay_id.municipal_id != self.municipal_id:
                self.barangay_id = False
            if self.center_id.barangay_id != self.barangay_id:
                self.center_id = False
            self.province_id = self.municipal_id.province_id
            barangay_domain = [('municipal_id','=',self.municipal_id.id)]
            barangay_ids = self.barangay_id.search(barangay_domain).ids[:]
            center_domain = [('barangay_id','in',barangay_ids)]
            domain = {
                'center_id': center_domain,
                'barangay_id': barangay_domain,
            }
        else:
            domain = {
                'center_id': [],
                'barangay_id': [],
            }
        return {'domain': domain }

    @api.onchange('province_id')
    def oc_province_id(self):
        if self.province_id:
            if self.municipal_id.province_id != self.province_id:
                self.municipal_id = False
            if self.barangay_id.municipal_id != self.municipal_id:
                self.barangay_id = False
            if self.center_id.barangay_id != self.barangay_id:
                self.center_id = False
            municipal_domain = [('province_id','=',self.province_id.id)]
            municipal_ids = self.municipal_id.search(municipal_domain).ids[:]
            barangay_domain = [('municipal_id','in',municipal_ids)]
            barangay_ids = self.barangay_id.search(barangay_domain).ids[:]
            center_domain = [('barangay_id','in',barangay_ids)]
            domain = {
                'center_id': center_domain,
                'barangay_id': barangay_domain,
                'municipal_id': municipal_domain,
            }
        else:
            domain = {
                'center_id': [],
                'barangay_id': [],
                'municipal_id': [],
            }
        return {'domain': domain }

    @api.depends('birthday')
    def _get_age(self):
        today = fields.Date.from_string(fields.Date.context_today(self))
        days_in_year = 365.2425
        for r in self:
            if r.birthday:
                r.age = (today - fields.Date.from_string(r.birthday)).days / days_in_year

    def format_name(self, r):
        title = r.title.shortcut and ("%s " % (r.title.shortcut.strip())) or ""
        fname = r.firstname and ("%s " % r.firstname) or ""
        mi = r.middlename and ("%s. " % r.middlename[0]) or ""
        lname = r.lastname and ("%s " % r.lastname) or ""
        name = ("%s%s%s%s" % (title,fname,mi,lname)).strip()
        return name

    @api.multi
    @api.depends('title','lastname','firstname','middlename','code')
    def compute_name(self):
        for r in self:
            lname = (r.lastname or "").strip()
            fname = (r.firstname or "").strip()
            mname = (r.middlename or "").strip()
            mname = mname and "%s." % mname[0]
            name = ("%s, %s %s" % (lname, fname, mname)).strip()
            r.name2 = name
            r.name = name
            #if r.name != name:
            #    r.name = name
            if r.partner_id.name != name:
                r.partner_id.write({'name': name})

    @api.depends('address1','address2','address3','zip')
    def _get_address(self):
        for r in self:
            addr = []
            for a in [r.address1, r.address2, r.address3]:
                if a:
                    addr.append(a)
            if r.zip:
                r.address = "%s %s" % (", ".join(addr), r.zip)
            else:
                r.address = ", ".join(addr)


class MemberDependents(models.Model):
    _name = "wc.member.dependent"
    _description = "Member Dependents"
    _order = "name"

    member_id = fields.Many2one('wc.member', 'Member', readonly=True, ondelete='restrict')
    name = fields.Char(required=True)
    relationship = fields.Char()
    birthday = fields.Date(track_visibility='onchange')
    age = fields.Float(compute="_get_age", digits=(12,2))
    contact = fields.Char('Contact No.')
    address = fields.Char('Address')
    note = fields.Text('Notes')

    @api.depends('birthday')
    def _get_age(self):
        today = fields.Date.from_string(fields.Date.context_today(self))
        days_in_year = 365.2425
        for r in self:
            if r.birthday:
                r.age = (today - fields.Date.from_string(r.birthday)).days / days_in_year


class Center(models.Model):
    _name = "wc.center"
    _description = "Center"
    _order = "name"

    name = fields.Char(required=True)
    barangay_id = fields.Many2one("wc.barangay", string="Barangay", required=True, ondelete="restrict")
    municipal_id = fields.Many2one("wc.municipal", related="barangay_id.municipal_id",
        string="Municipality/City", readonly=True, store=True)
    province_id = fields.Many2one("wc.province", related="municipal_id.province_id",
        string="Province", readonly=True, store=True)
    note = fields.Text('Notes')

    @api.multi
    @api.depends('name', 'barangay_id')
    def name_get(self):
        res = []
        for r in self:
            barangay = ""
            municipal = ""
            province = ""
            if r.barangay_id:
                barangay = r.barangay_id.name + "/"
                if r.municipal_id:
                    municipal = r.municipal_id.name + "/"
                    if r.province_id:
                        province = r.province_id.name + "/"
            loc = "%s%s%s" % (barangay, municipal, province)
            name = "%s (%s)" % (r.name, loc[:-1])
            res.append((r.id, name))
        return res


class Barangay(models.Model):
    _name = "wc.barangay"
    _description = "Barangay"
    _order = "name"

    name = fields.Char(required=True)
    municipal_id = fields.Many2one("wc.municipal", string="Municipality/City",
        required=True, ondelete="restrict")
    province_id = fields.Many2one("wc.province", related="municipal_id.province_id",
        string="Province", readonly=True, store=True)
    note = fields.Text('Notes')

    @api.multi
    @api.depends('name', 'province_id', 'municipal_id')
    def name_get(self):
        return [(r.id, "%s (%s/%s)" % (r.name, r.municipal_id.name, r.province_id.name)) for r in self]


class Municipal(models.Model):
    _name = "wc.municipal"
    _description = "Municipal"
    _order = "name"

    name = fields.Char(required=True)
    province_id = fields.Many2one("wc.province", string="Province", required=True, ondelete="restrict")
    note = fields.Text('Notes')

    @api.multi
    @api.depends('name', 'province_id')
    def name_get(self):
        return [(r.id, "%s (%s)" % (r.name, r.province_id.name)) for r in self]


class Province(models.Model):
    _name = "wc.province"
    _description = "Province"
    _order = "name"

    name = fields.Char(required=True)
    note = fields.Text('Notes')






#
