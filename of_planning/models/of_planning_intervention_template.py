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
    _name = 'of.planning.intervention.template'

    @api.model
    def _get_default_template_values(self):
        return self._get_default_template_values_fi()

    @api.model
    def _get_default_template_values_fi(self):
        default_template = self.env.ref('of_planning.of_planning_default_intervention_template', raise_if_not_found=False)
        values = {}
        if default_template:
            copy = default_template.copy_data()[0] or {}
            for key, value in copy.iteritems():
                # copier les valeurs du rapport d'intervention
                if isinstance(key, basestring) and key.startswith("fi_") and key != 'fi_default':
                    values[key] = value
        return values

    @api.model
    def default_get(self, fields_list):
        res = super(OfPlanningInterventionTemplate, self).default_get(fields_list)
        default_template_values = self._get_default_template_values()
        if default_template_values:
            if isinstance(res, dict):
                res.update(default_template_values)
            else:
                res = default_template_values
        return res

    name = fields.Char(string=u"Nom du modèle", required=True)
    active = fields.Boolean(string="Active", default=True)
    code = fields.Char(string="Code", compute="_compute_code", inverse="_inverse_code", store=True, required=True)
    sequence_id = fields.Many2one('ir.sequence', string=u"Séquence", readonly=True)
    tache_id = fields.Many2one('of.planning.tache', string=u"Tâche")
    fiscal_position_id = fields.Many2one('account.fiscal.position', string="Position fiscale", company_dependent=True)
    line_ids = fields.One2many('of.planning.intervention.template.line', 'template_id', string="Lignes de facturation")
    product_ids = fields.Many2many('product.product')

    is_default_template = fields.Boolean(compute="_compute_is_default_template")
    # FICHE D'INTERVENTION
    fi_default = fields.Boolean(string=u"Rapport par défaut", default=True)
    fi_title = fields.Char(string="Titre du rapport", default="Rapport d'intervention")
    # -- FI - Commande
    fi_order = fields.Boolean(string="COMMANDE")
    fi_order_client = fields.Boolean(string="Client")
    fi_order_name = fields.Boolean(string=u"Commande associée")  # doublons ?
    fi_order_confirmation_date = fields.Boolean(string="Date de confirmation")
    fi_order_interv_label = fields.Boolean(string=u"Libellé")  # doublons ?
    fi_order_company = fields.Boolean(string="Magasin")
    fi_order_seller = fields.Boolean(string="Vendeur")
    # -- FI - Articles
    fi_products = fields.Boolean(string="ARTICLES")
    fi_products_order = fields.Boolean(string="Lignes de commande")
    fi_products_picking = fields.Boolean(string="Lignes de BL")
    # -- FI - Rdv d'intervention
    fi_rdv = fields.Boolean(string="INTERVENTION")
    fi_rdv_date_start = fields.Boolean(string=u"Date de début")
    fi_rdv_date_end = fields.Boolean(string="Date de fin")
    fi_rdv_task = fields.Boolean(string=u"Tâche")
    fi_rdv_task_description = fields.Boolean(string=u"Description tâche")
    fi_rdv_duration = fields.Boolean(string=u"Durée")
    fi_rdv_tech = fields.Boolean(string="Technicien(s)")
    fi_rdv_address = fields.Boolean(string="Adresse d'intervention")
    fi_rdv_mail = fields.Boolean(string="E-mail")
    fi_rdv_phone = fields.Boolean(string=u"Téléphone")
    # -- FI - Descriptions
    fi_description = fields.Boolean(sring="DESCRIPTION(S)")
    fi_description_ext = fields.Boolean(sring="Description externe")
    # -- FI - Facturation
    fi_invoicing = fields.Boolean(string="FACTURATION")
    fi_invoicing_ht = fields.Boolean(string="Total HT")
    fi_invoicing_taxes = fields.Boolean(string="Taxes")
    fi_invoicing_ttc = fields.Boolean(string="Total TTC")

    @api.depends()
    def _compute_is_default_template(self):
        default_template = self.env.ref('of_planning.of_planning_default_intervention_template', raise_if_not_found=False)
        if default_template:
            default_template.is_default_template = True

    @api.depends('sequence_id')
    def _compute_code(self):
        for template in self:
            template.code = template.sequence_id.prefix

    def _inverse_code(self):
        sequence_obj = self.env['ir.sequence']
        for template in self:
            if not template.code:
                continue
            sequence_name = u"Modèle d'intervention " + template.code
            sequence_code = self._name
            # Si une séquence existe déjà avec ce code, on la reprend
            sequence = sequence_obj.search([('code', '=', sequence_code), ('prefix', '=', self.code)])
            if sequence:
                template.sequence_id = sequence
                continue

            if template.sequence_id:
                # Si la séquence n'est pas utilisée par un autre modèle, on la modifie directement,
                # sinon il faudra en re-créer une.
                if not self.search([('sequence_id', '=', template.sequence_id.id), ('id', '!=', template.id)]):
                    template.sequence_id.sudo().write({'prefix': template.code, 'name': sequence_name})
                    continue

            # Création d'une séquence pour le modèle
            sequence_data = {
                'name': sequence_name,
                'code': sequence_code,
                'implementation': 'no_gap',
                'prefix': template.code,
                'padding': 4,
                }
            template.sequence_id = self.env['ir.sequence'].sudo().create(sequence_data)

    @api.onchange('fi_default')
    def _onchange_ri_default(self):
        if self.fi_default:
            self.update(self._get_default_template_values_fi())

    @api.model
    def create(self, vals):
        if vals.get('fi_default', False):
            vals.update(self._get_default_template_values_fi())
        return super(OfPlanningInterventionTemplate, self).create(vals)

    @api.multi
    def write(self, vals):
        if vals.get('fi_default', False):
            vals.update(self._get_default_template_values_fi())
        res = super(OfPlanningInterventionTemplate, self).write(vals)
        default_template = self.env.ref('of_planning.of_planning_default_intervention_template', raise_if_not_found=False)
        if default_template and default_template in self:
            others = self.search([('id', '!=', default_template.id), ('fi_default', '=', True)])
            others.write(self._get_default_template_values_fi())
        return res

    @api.multi
    def unlink(self):
        default_template = self.env.ref('of_planning.of_planning_default_intervention_template', raise_if_not_found=False)
        if default_template and default_template in self:
            raise UserError(u"Impossible de supprimer le modèle d'intervention par défaut")
        res = super(OfPlanningInterventionTemplate, self).unlink()
        return res


class OfPlanningInterventionTemplateLine(models.Model):
    _name = 'of.planning.intervention.template.line'

    template_id = fields.Many2one('of.planning.intervention.template', string=u"Modèle", required=True)
    product_id = fields.Many2one('product.product', string='Article')
    price_unit = fields.Float(string='Prix unitaire', digits=dp.get_precision('Product Price'), default=0.0)
    qty = fields.Float(string=u'Qté', digits=dp.get_precision('Product Unit of Measure'))
    name = fields.Text(string='Description')

    @api.onchange('product_id')
    def _onchange_product(self):
        product = self.product_id
        self.qty = 1
        self.price_unit = product.lst_price
        if product:
            name = product.name_get()[0][1]
            if product.description_sale:
                name += '\n' + product.description_sale
            self.name = name
        else:
            self.name = ''

    @api.multi
    def get_intervention_line_values(self):
        self.ensure_one()
        return {
            'product_id': self.product_id,
            'price_unit': self.price_unit,
            'qty': self.qty,
            'name': self.name,
            }


class IrModelData(models.Model):
    _inherit = 'ir.model.data'

    # Surcharge pour permettre la progagation des informations du modèle d'intervention par défaut
    # vers les autres modèles existants
    @api.model
    def _update(self, model, module, values, xml_id=False, store=True, noupdate=False, mode='init', res_id=False):
        res = super(IrModelData, self)._update(
                model=model, module=module, values=values, xml_id=xml_id, store=store, noupdate=noupdate, mode=mode,
                res_id=res_id)
        if xml_id == 'of_planning_default_intervention_template':
            template_obj = self.env['of.planning.intervention.template']
            default_template = self.env.ref(
                    'of_planning.of_planning_default_intervention_template', raise_if_not_found=False)
            if default_template:
                others = template_obj.search([('id', '!=', default_template.id), ('fi_default', '=', True)])
                others.write(template_obj._get_default_template_values_fi())
        return res
