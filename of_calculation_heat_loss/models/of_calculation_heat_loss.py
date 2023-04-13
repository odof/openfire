# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import re
import base64

from odoo import models, fields, api


class OFCalculationHeatLoss(models.Model):
    _name = 'of.calculation.heat.loss'
    _description = u"Calcul de déperdition de chaleur"

    name = fields.Char(string=u"Nom", compute='_compute_name', store=True)
    number = fields.Char(string=u"Numéro", readonly=True)
    sequence = fields.Integer(string=u"Séquence")
    partner_id = fields.Many2one(comodel_name='res.partner', string=u"Contact")
    lead_id = fields.Many2one(comodel_name='crm.lead', string=u"Opportunité")
    order_id = fields.Many2one(comodel_name='sale.order', string=u"Devis / Bon de commande")
    parc_installe_id = fields.Many2one(comodel_name='of.parc.installe', string=u"Parc installé")
    partner_name = fields.Char(string=u"Nom du contact", related='partner_id.name', required=True)
    partner_zip = fields.Char(string=u"Code postal du contact", related='partner_id.zip', required=True)
    partner_city = fields.Char(string=u"Ville du contact", related='partner_id.city')
    partner_street = fields.Char(string=u"Rue du contact", related='partner_id.street')
    partner_street2 = fields.Char(string=u"Rue du contact", related='partner_id.street2')
    partner_state_id = fields.Many2one(comodel_name='res.country.state', related='partner_id.state_id', string=u"État")
    partner_country_id = fields.Many2one(comodel_name='res.country', related='partner_id.country_id', string=u"Pays")
    surface = fields.Float(string=u"Surface à chauffer (en m²)", help=u"Surface de la ou des pièces à chauffer")
    height = fields.Float(string=u"Hauteur de plafond (en m)")
    construction_date_id = fields.Many2one(
        comodel_name='of.calculation.construction.date', string=u"Date de construction")
    department_id = fields.Many2one(
        comodel_name='of.calculation.department', string=u"Département", compute='_compute_department_id')
    available_altitude_ids = fields.Many2many(
        comodel_name='of.calculation.altitude', relation='of_calculation_heat_loss_altitude_rel',
        column1='calculation_id', column2='altitude_id', string="Altitudes disponibles",
        compute='_compute_department_id')
    altitude_id = fields.Many2one(
        comodel_name='of.calculation.altitude', string=u"Altitude")
    base_temperature_line_id = fields.Many2one(
        comodel_name='of.calculation.base.temperature.line', string=u"Ligne de température",
        compute='_compute_base_temperature_line_id')
    temperature = fields.Float(string=u"Température de confort désirée", default=19.0)
    estimated_power = fields.Float(string=u"Puissance estimée de l’appareil (nombre)")
    estimated_power_text = fields.Char(string=u"Puissance estimée de l’appareil (texte)")
    product_ids = fields.Many2many(
        comodel_name='product.template', relation='of_calculation_heat_loss_product_template_rel',
        column1='calculation_id', column2='product_id', string="Articles compatibles", compute='_compute_product_ids')

    @api.depends('number', 'create_date')
    def _compute_name(self):
        for rec in self:
            date = fields.Date.from_string(rec.create_date).strftime('%d/%m/%Y')
            rec.name = u"%s - %s" % (rec.number, date)

    @api.multi
    @api.depends('partner_zip')
    def _compute_department_id(self):
        department_obj = self.env['of.calculation.department']
        for rec in self:
            if rec.partner_zip:
                department = department_obj.search([('code', '=', rec.partner_zip[0:2])], limit=1)
                if department:
                    altitudes = department.base_temperature_id.line_ids.mapped('altitude_id')
                    rec.department_id = department.id
                    rec.available_altitude_ids = [(6, 0, altitudes.ids)]

    @api.multi
    @api.depends('department_id', 'altitude_id')
    def _compute_base_temperature_line_id(self):
        for rec in self:
            if rec.department_id and rec.altitude_id:
                rec.base_temperature_line_id = rec.department_id.base_temperature_id.line_ids.filtered(
                    lambda l: l.altitude_id == rec.altitude_id).id

    @api.multi
    @api.depends('estimated_power')
    def _compute_product_ids(self):
        product_obj = self.env['product.template']
        for rec in self:
            if rec.estimated_power:
                products = product_obj.search([('of_puissance_nom_flo', '>=', rec.estimated_power/1000)])
                rec.product_ids = [(6, 0, products.ids)]

    @api.multi
    @api.onchange('department_id')
    def _onchange_department_id(self):
        self.altitude_id = False

    @api.model
    def create(self, vals):
        if not vals.get('partner_id'):
            vals, partner_vals = self._of_extract_partner_values(vals)  # split vals
            partner_vals.update({
                'name': vals.get('partner_name'),
                'type': False,
                'customer': True,
            })

            partner = self.env['res.partner'].create(partner_vals)
            vals['partner_id'] = partner.id
            vals['of_check_duplications'] = True

        vals['number'] = self.env['ir.sequence'].next_by_code('of.calculation.heat.loss')
        return super(OFCalculationHeatLoss, self).create(vals)

    @api.multi
    def write(self, vals):
        partner_vals = False
        if len(self._ids) == 1 and vals.get('partner_id', self.partner_id):
            vals, partner_vals = self._of_extract_partner_values(vals)
        res = super(OFCalculationHeatLoss, self).write(vals)
        if partner_vals:
            self.partner_id.write(partner_vals)
        return res

    @api.multi
    def button_compute_estimated_power(self):
        for rec in self:
            reference_temperature = rec.base_temperature_line_id.temperature
            estimated_power = rec.surface * rec.height * rec.construction_date_id.coefficient * (
                    rec.temperature - reference_temperature)
            rec.write({
                'estimated_power': estimated_power,
                'estimated_power_text': "%s %s" % (estimated_power/1000, "kWatt/h"),
            })

    @api.multi
    def button_quick_send(self):
        self.ensure_one()
        self.send_calculation()
        return {'type': 'ir.actions.do_nothing'}

    @api.model
    def _of_extract_partner_values(self, vals):
        new_vals = vals.copy()
        partner_vals = {}
        for field_name, val in vals.iteritems():
            if field_name not in self._fields:  # don't take vals that are not fields into account
                continue
            field = self._fields[field_name]
            # field is not related or is partner_name-> let it be
            if not getattr(field, 'related') or field.name == 'partner_name':
                continue
            related = field.related
            if related and related[0] == 'partner_id':  # field related to partner_id
                partner_vals['.'.join(related[1:])] = val  # add value to partner_vals
                del new_vals[field_name]  # take value out of new vals
        return new_vals, partner_vals

    @api.multi
    def send_calculation(self):
        template_id = self.env.ref('of_calculation_heat_loss.email_template_calcul_deperdition')
        email_values = {}
        today_str = fields.Date.today()
        # création du pdf et ajout dans les values, il sera automatiquement joint à l'email envoyé
        planning_pdf = self.env['report'].get_pdf(
            self.ids, 'of_calculation_heat_loss.of_calculation_heat_loss_report')
        attachment = self.env['ir.attachment'].create({
            'name': u"Déperdition de chaleur pour %s le %s" % (self.create_uid.name, today_str),
            'datas_fname': u"deperdition_%s_%s.pdf" % (self.create_uid.name, today_str),
            'type': 'binary',
            'datas': base64.encodestring(planning_pdf),
            'res_model': 'of.calculation.heat.loss',
            'res_id': self.id,
            'mimetype': 'application/x-pdf'
        })
        email_values['attachment_ids'] = attachment.ids
        # envoi immédiat de l'email
        template_id.send_mail(self.id, force_send=True, email_values=email_values)

        return True


class OFCalculationConstructionDate(models.Model):
    _name = 'of.calculation.construction.date'
    _description = u"Date de construction"
    _order = 'sequence'

    name = fields.Char(string=u"Nom", required=True)
    sequence = fields.Integer(string=u"Séquence")
    coefficient = fields.Float(string=u"Coefficient G", required=True)


class OFCalculationDepartment(models.Model):
    _name = 'of.calculation.department'
    _description = u"Département"
    _order = 'code'

    name = fields.Char(string=u"Nom", required=True)
    code = fields.Integer(string=u"Code", required=True)
    base_temperature_id = fields.Many2one(
        comodel_name='of.calculation.base.temperature', string=u"Température extérieure de base",
        required=True, help=u"Température extérieure de base ramenée au niveau de la mer")


class OFCalculationBaseTemperature(models.Model):
    _name = 'of.calculation.base.temperature'
    _description = u"Température extérieure de base au niveau de la mer"
    _order = 'name'

    name = fields.Char(string=u"Nom", compute='_compute_name')
    sequence = fields.Integer(string=u"Séquence")
    temperature = fields.Float(
        string=u"Température extérieure de base", required=True,
        help=u"Température extérieure de base ramenée au niveau de la mer")
    line_ids = fields.One2many(
        comodel_name='of.calculation.base.temperature.line', inverse_name='base_temperature_id',
        string=u"Lignes de température", help=u"Température extérieure de base en fonction de l'altitude")

    @api.multi
    @api.depends('temperature')
    def _compute_name(self):
        for rec in self:
            rec.name = u"%s°C" % rec.temperature


class OFCalculationAltitude(models.Model):
    _name = 'of.calculation.altitude'
    _description = u"Altitude du site"
    _order = 'sequence'

    name = fields.Char(string=u"Nom", required=True)
    sequence = fields.Integer(string=u"Sequence")


class OFCalculationBaseTemperatureLine(models.Model):
    _name = 'of.calculation.base.temperature.line'
    _description = u"Température en fonction de l'altitude pour un site"
    _order = 'sequence'

    sequence = fields.Integer(string=u"Sequence", related='altitude_id.sequence')
    name = fields.Char(string=u"Nom", compute='_compute_name')
    temperature = fields.Float(string=u"Température", required=True)
    altitude_id = fields.Many2one(comodel_name='of.calculation.altitude', string=u"Altitude", required=True)
    base_temperature_id = fields.Many2one(
        comodel_name='of.calculation.base.temperature', string=u"Site", required=True, ondelete='cascade')

    @api.multi
    @api.depends('altitude_id', 'temperature')
    def _compute_name(self):
        for rec in self:
            rec.name = u"%s°C de %sm" % (rec.temperature, rec.altitude_id.name)


class CRMLead(models.Model):
    _inherit = 'crm.lead'

    @api.multi
    def name_get(self):
        """Permet dans un Calcul de déperdition de chaleur de proposer les opportunités d'autres contacts
            entre parenthèses
        """
        partner_id = self._context.get('partner_prio_id')
        if partner_id:
            result = []
            for rec in self:
                is_partner = rec.partner_id.id == partner_id
                result.append((rec.id, "%s%s%s" % ('' if is_partner else '(', rec.name, '' if is_partner else ')')))
            return result
        return super(CRMLead, self).name_get()

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        """Permet dans un calcul de déperdition de chaleur de proposer en priorité les opportunités du contact"""
        if self._context.get('partner_prio_id'):
            partner_id = self._context['partner_prio_id']
            args = args or []
            res = super(CRMLead, self).name_search(
                name,
                args + [['partner_id', '=', partner_id]],
                operator,
                limit) or []
            limit = limit - len(res)
            res += super(CRMLead, self).name_search(
                name,
                args + [['partner_id', '!=', partner_id]],
                operator,
                limit) or []
            return res
        return super(CRMLead, self).name_search(name, args, operator, limit)


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    @api.multi
    def name_get(self):
        """Permet dans un Calcul de déperdition de chaleur de proposer les devis d'autres contacts entre parenthèses"""
        partner_id = self._context.get('partner_prio_id')
        if partner_id:
            result = []
            for rec in self:
                is_partner = rec.partner_id.id == partner_id
                result.append((rec.id, "%s%s%s" % ('' if is_partner else '(', rec.name, '' if is_partner else ')')))
            return result
        return super(SaleOrder, self).name_get()

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        """Permet dans un calcul de déperdition de chaleur de proposer en priorité les devis du contact"""
        if self._context.get('partner_prio_id'):
            partner_id = self._context['partner_prio_id']
            args = args or []
            res = super(SaleOrder, self).name_search(
                name,
                args + [['partner_id', '=', partner_id]],
                operator,
                limit) or []
            limit = limit - len(res)
            res += super(SaleOrder, self).name_search(
                name,
                args + [['partner_id', '!=', partner_id]],
                operator,
                limit) or []
            return res
        return super(SaleOrder, self).name_search(name, args, operator, limit)


class OFParcInstalle(models.Model):
    _inherit = 'of.parc.installe'

    @api.multi
    def name_get(self):
        """Permet dans un Calcul de déperdition de chaleur de proposer les appareils d'autres contacts
            entre parenthèses
        """
        partner_id = self._context.get('partner_prio_id')
        if partner_id:
            result = []
            for rec in self:
                is_partner = rec.client_id.id == partner_id
                result.append((rec.id, "%s%s%s" % ('' if is_partner else '(', rec.name, '' if is_partner else ')')))
            return result
        return super(OFParcInstalle, self).name_get()

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        """Permet dans un calcul de déperdition de chaleur de proposer en priorité les appareils du contact"""
        if self._context.get('partner_prio_id'):
            partner_id = self._context['partner_prio_id']
            args = args or []
            res = super(OFParcInstalle, self).name_search(
                name,
                args + [['client_id', '=', partner_id]],
                operator,
                limit) or []
            limit = limit - len(res)
            res += super(OFParcInstalle, self).name_search(
                name,
                args + [['client_id', '!=', partner_id]],
                operator,
                limit) or []
            return res
        return super(OFParcInstalle, self).name_search(name, args, operator, limit)


class OFProductTemplate(models.Model):
    _inherit = 'product.template'

    of_puissance_nom_flo = fields.Float(
        string=u"Puissance nominale (nombre flottant)", compute='_compute_of_puissance_nom_flo', store=True)

    @api.depends('of_puissance_nom')
    def _compute_of_puissance_nom_flo(self):
        for record in self:
            if record.of_puissance_nom:
                # Regular expression for extracting float value
                pattern = r"\d+[.,]?\d*"

                # extract float value
                match = re.search(pattern, record.of_puissance_nom)

                if match:
                    record.of_puissance_nom_flo = float(match.group().replace(",", "."))
