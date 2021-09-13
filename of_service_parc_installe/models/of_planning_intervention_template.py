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
                    "WHERE table_name = %s AND column_name = 'fi_pi'", (self._table,))
            init = not bool(cr.fetchall())
        res = super(OfPlanningInterventionTemplate, self)._auto_init()
        if init:
            default = self.env.ref('of_planning.of_planning_default_intervention_template', raise_if_not_found=False)
            if default:
                cr.execute(
                    "SELECT * FROM information_schema.columns "
                    "WHERE table_name = %s AND column_name = 'ri_pi'", (self._table,))
                init2 = not bool(cr.fetchall())
                cr.execute(
                        "UPDATE of_planning_intervention_template "
                        "SET fi_pi = 't', "
                        "fi_pi_serial = 't', "
                        "fi_pi_product = 't', "
                        "fi_pi_brand = 't', "
                        "fi_pi_model = 't', "
                        "fi_pi_installation_date = 't', "
                        "fi_pi_state = 't', "
                        "fi_pi_notes = 't' "
                        "WHERE id = %s", (default.id,))
                if init2:
                    cr.execute(
                        "UPDATE of_planning_intervention_template "
                        "SET ri_pi = 't', "
                        "ri_pi_serial = 't', "
                        "ri_pi_product = 't', "
                        "ri_pi_brand = 't', "
                        "ri_pi_model = 't', "
                        "ri_pi_installation_date = 't', "
                        "ri_pi_state = 't', "
                        "ri_pi_notes = 't' "
                        "WHERE id = %s", (default.id,))
        return res

    # -- FI - Parc installé
    fi_pi = fields.Boolean(string=u"PARC INSTALLÉ")
    fi_pi_serial = fields.Boolean(string=u"N° série")
    fi_pi_product = fields.Boolean(string=u"Produit installé")
    fi_pi_brand = fields.Boolean(string="Marque")
    fi_pi_model = fields.Boolean(string=u"Modèle")
    fi_pi_installation_date = fields.Boolean(string="Date d'installation")
    fi_pi_state = fields.Boolean(string=u"État")
    fi_pi_notes = fields.Boolean(string="Notes")

    # -- RI - Parc installé
    ri_pi = fields.Boolean(string=u"PARC INSTALLÉ")
    ri_pi_product = fields.Boolean(string=u"Produit installé")
    ri_pi_serial = fields.Boolean(string=u"N° série")
    ri_pi_brand = fields.Boolean(string="Marque")
    ri_pi_model = fields.Boolean(string=u"Modèle")
    ri_pi_installation_date = fields.Boolean(string="Date d'installation")
    ri_pi_state = fields.Boolean(string=u"État")
    ri_pi_notes = fields.Boolean(string="Notes")