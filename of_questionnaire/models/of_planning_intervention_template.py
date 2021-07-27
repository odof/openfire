# -*- coding: utf-8 -*-

from dateutil.relativedelta import relativedelta
import pytz
import re
import requests
import urllib

from odoo import api, models, fields, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools import config, DEFAULT_SERVER_DATETIME_FORMAT
from odoo.tools.float_utils import float_compare
from odoo.tools.safe_eval import safe_eval

import odoo.addons.decimal_precision as dp
from odoo.addons.of_utils.models.of_utils import se_chevauchent, float_2_heures_minutes, heures_minutes_2_float, \
    compare_date


class OfPlanningInterventionTemplate(models.Model):
    _inherit = 'of.planning.intervention.template'

    @api.model_cr_context
    def _auto_init(self):
        cr = self._cr
        init = False
        if self._auto:
            cr.execute(
                    "SELECT * FROM information_schema.columns "
                    "WHERE table_name = %s AND column_name = 'fi_surveys'", (self._table,))
            init = not bool(cr.fetchall())
        res = super(OfPlanningInterventionTemplate, self)._auto_init()
        if init:
            default = self.env.ref('of_planning.of_planning_default_intervention_template', raise_if_not_found=False)
            if default:
                cr.execute(
                    "SELECT * FROM information_schema.columns "
                    "WHERE table_name = %s AND column_name = 'ri_surveys'", (self._table,))
                init2 = not bool(cr.fetchall())
                cr.execute(
                        "UPDATE of_planning_intervention_template "
                        "SET fi_surveys = 't', "
                        "fi_surveys_rdv = 't' "
                        "WHERE id = %s", (default.id, ))
                if init2:
                    cr.execute(
                        "UPDATE of_planning_intervention_template "
                        "SET ri_surveys = 't', "
                        "ri_surveys_rdv = 't' "
                        "WHERE id = %s", (default.id, ))
        return res

    # -- FI - Questionnaires
    fi_surveys = fields.Boolean(string="QUESTIONNAIRE(S)")
    fi_surveys_rdv = fields.Boolean(string="Intervention")

    # -- RI - Questionnaire
    ri_surveys = fields.Boolean(string="QUESTIONNAIRE(S)")
    ri_surveys_rdv = fields.Boolean(string="Intervention")
