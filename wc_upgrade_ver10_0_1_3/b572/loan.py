
from odoo import models, fields, api, _
from odoo.exceptions import Warning, ValidationError ,UserError
import odoo.addons.decimal_precision as dp
from datetime import datetime
from dateutil.relativedelta import relativedelta
import math
import logging
#from util import *

_logger = logging.getLogger(__name__)
DF = "%Y-%m-%d"
EPS = 0.00001

#IMPLEMENTATION = True

class Loan(models.Model):
    _inherit = "wc.loan"
    
    @api.depends('code', 'member_id', 'member_id.name', 'comaker_ids', 'comaker_ids.name')
    def compute_name(self):
        for r in self:
            #fix b572
            if not r.member_id:
                continue
            
            member_name = r.member_id.name
            if r.comaker_ids:
                member_name += " et al."

            r.name = "%s - %s" % (r.code, member_name)
            r.member_name = member_name
       