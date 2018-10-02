# -*- coding: utf-8 -*-
###############################################
# EzTech Software & Consultancy Inc. (c) 2017
###############################################
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
import datetime
import logging

_logger = logging.getLogger(__name__)

class Holidays(models.Model):
    _name = "ez.holiday"
    _description = "Holidays"
    _order = "year desc, date desc"

    name = fields.Char('Name', required=True)
    year = fields.Char(required=True)
    date = fields.Date("Date")
    type = fields.Selection([
        ('lh', 'Regular Holiday'),
        ('sh', 'Special Holiday'),
        ], 'Type', required=True, default=lambda self: "sh")
    note = fields.Text('Notes')


class CreateHolidays(models.TransientModel):
    _name = "ez.create.holiday.wizard"
    _description = "Create Holidays Wizard"

    year = fields.Char('Year', required=True,
        default=lambda self: datetime.datetime.now().year)

    @api.model
    def get_holidays(self):
        return [
            ["New Year's Day", '01-01', 'lh'],
            ["Maundy Thursday", None, 'lh'],
            ["Good Friday", None, 'lh'],
            ["Araw ng Kagitingan", '04-09', 'lh'],
            ["Labor Day", '05-01', 'lh'],
            ["Independence Day", '06-12','lh'],
            ["National Heroes Day", None, 'lh'],
            ["Bonifacio Day", '11-30', 'lh'],
            ["Christmas Day", '12-25', 'lh'],
            ["Rizal Day", '12-30', 'lh'],
            ['Chinese New Year', None, 'sh'],
            ['Black Saturday', None, 'sh'],
            ['Ninoy Aquino Day', '08-21', 'sh'],
            ['All Saints Day', '11-01', 'sh'],
            ['Last Day of the Year', '12-31' ,'sh'],
        ]

    @api.multi
    def create_holidays(self):
        years = []
        holiday = self.env['ez.holiday']

        for rec in self:

            years.append(rec.year)

            for h in self.get_holidays():
                hname = h[0]
                if h[1]:
                    dt = "%s-%s" % (rec.year, h[1])
                else:
                    dt = None
                htype = h[2]

                res = holiday.search([
                    ('name','=',hname),
                    ('year','=',rec.year),
                ])

                try:
                    y = int(rec.year)
                except:
                    y = 0

                if y>2000 and not res:
                    if not dt:
                        if hname == "National Heroes Day":
                            #last monday of august
                            d = datetime.date(year=int(rec.year), month=8, day=20)
                            while d.month==8:
                                if d.weekday() == 0:
                                    dt = d.strftime("%Y-%m-%d")
                                d = d + datetime.timedelta(days=1)

                    holiday.create({
                        'name': hname,
                        'type': htype,
                        'date': dt,
                        'year': rec.year,
                    })

        return {
            'name': _("Holidays"),
            'view_type': 'form',
            'view_mode': 'tree',
            'res_model': 'ez.holiday',
            'view_id': False,
            'type': 'ir.actions.act_window',
            'domain': [('year', 'in', years)]
        }
