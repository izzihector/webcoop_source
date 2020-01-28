# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo import tools, _
# from odoo.exceptions import ValidationError, Warning
# from odoo.modules.module import get_module_resource
# from datetime import datetime
# from dateutil.relativedelta import relativedelta
import logging
# import time
# from util import *

_logger = logging.getLogger(__name__)
DF = "%Y-%m-%d"
EPS = 0.00001

class Posting(models.Model):
    _inherit = "wc.posting"

    #20191217 delete saving interest calculation from daily posting
    def open_date_sub_interest_computation_sa(self):
        return


