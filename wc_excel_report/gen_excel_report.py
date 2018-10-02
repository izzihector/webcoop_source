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
from odoo.tools.safe_eval import safe_eval
import logging
from openpyxl import load_workbook
import base64
from copy import copy
try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO

_logger = logging.getLogger(__name__)
DF = "%Y-%m-%d"

def set_cell_format(new_cell, ref_cell):
    new_cell.font = copy(ref_cell.font)
    new_cell.border = copy(ref_cell.border)
    new_cell.fill = copy(ref_cell.fill)
    new_cell.number_format = copy(ref_cell.number_format)
    new_cell.alignment = copy(ref_cell.alignment)

def set_cell(ws_out, ws_ref, ccol, row, value):
    cname = ccol + ("%d" % row)
    cref = '%s15' % ccol
    new_cell = ws_out[cname]
    ref_cell = ws_ref[cref]
    new_cell.value = value
    set_cell_format(new_cell, ref_cell)


class ExcelReportWizard(models.TransientModel):
    _inherit = 'wc.excel.report.wizard'
