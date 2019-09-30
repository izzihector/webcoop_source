
from odoo import api, fields, models
from odoo import tools, _
from odoo.exceptions import ValidationError, Warning
from dateutil.relativedelta import relativedelta
import logging

_logger = logging.getLogger(__name__)
DF = "%Y-%m-%d"

class ResPartner(models.Model):
    _inherit = "wc.member"
    other_type_collection_lines = fields.One2many('wc.collection.line','member_id',
                        domain=[('collection_type','=','others'),('state','=','confirmed')])




