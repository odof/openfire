# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import base64

from odoo import api, fields, models
from odoo.exceptions import UserError


class OFCalculationHeatLoss(models.Model):
    _name = 'of.calculation.heat.loss'
    _inherit = 'mail.thread'
    _description = u"Calcul de déperdition de chaleur"
    _order = "create_date DESC"

    name = fields.Char(string=u"Nom", compute='_compute_name', store=True)
    number = fields.Char(string=u"Numéro", readonly=True)
    sequence = fields.Integer(string=u"Séquence")
    partner_id = fields.Many2one(comodel_name='res.partner', string=u"Contact")
    lead_id = fields.Many2one(comodel_name='crm.lead', string=u"Opportunité")
    order_id = fields.Many2one(comodel_name='sale.order', string=u"Devis / Bon de commande")
    parc_installe_id = fields.Many2one(comodel_name='of.parc.installe', string=u"Parc installé")
    partner_name = fields.Char(string=u"Nom du contact", related='partner_id.name')
    partner_email = fields.Char(string=u"Email du contact", related='partner_id.email')
    partner_zip = fields.Char(string=u"Code postal du contact", related='partner_id.zip', required=True)
    partner_city = fields.Char(string=u"Ville du contact", related='partner_id.city')
    partner_street = fields.Char(string=u"Rue du contact", related='partner_id.street')
    partner_street2 = fields.Char(string=u"Rue du contact", related='partner_id.street2')
    zip_id = fields.Many2one(comodel_name='res.better.zip', string=u"City")
    partner_state_id = fields.Many2one(comodel_name='res.country.state', related='partner_id.state_id', string=u"État")
    partner_country_id = fields.Many2one(comodel_name='res.country', related='partner_id.country_id', string=u"Pays")
    surface = fields.Float(
        string=u"Surface à chauffer (en m²)", help=u"Surface de la ou des pièces à chauffer", required=True)
    height = fields.Float(string=u"Hauteur de plafond (en m)", required=True)
    volume = fields.Float(string=u"Volume (en m³)", compute='_compute_volume', store=True)
    construction_date_id = fields.Many2one(
        comodel_name='of.calculation.construction.date', string=u"Date de construction", required=True)
    construction_type_id = fields.Many2one(
        comodel_name='of.calculation.construction.type', string=u"Type de bâtiment", required=True)
    better_g = fields.Boolean(string=u"Meilleur calcul G", compute='_compute_better_g')
    message = fields.Text(string=u"Message", related='construction_date_id.message', readonly=True)
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
    temperature = fields.Float(string=u"Température de confort désirée", default=19.0, required=True)
    estimated_power = fields.Float(string=u"Puissance estimée de l’appareil (nombre)")
    estimated_power_text = fields.Char(string=u"Puissance estimée de l’appareil (texte)")
    line_ids = fields.One2many(
        comodel_name='of.calculation.heat.loss.line', inverse_name='calculation_heat_loss_id',
        string=u"Lignes de calcul")
    annual_consumption = fields.Float(string=u"Consommation estimée de l’appareil (nombre)")
    annual_consumption_text = fields.Char(string=u"Consommation estimée de l’appareil (texte)")
    fuel_consumption_ids = fields.One2many(
        comodel_name='of.calculation.fuel.consumption', inverse_name='calculation_id',
        string=u"Consommation par combustible")
    floor_number = fields.Integer(string=u"Nombre de niveaux", default=1)
    volume_type = fields.Selection(
        selection=[
            ('IP1', u"IP1 - Volume < 270 m³, 1 niveau "),
            ('IP2', u"IP2 - Volume < 270 m³, 2 niveaux"),
            ('IG1', u"IG1 - Volume >= 270 m³, 1 niveau"),
            ('IG2/3', u"IG2/IG3 - Volume >= 270 m³, 2/3 niveaux"),
        ], string=u"Type de coefficient", compute='_compute_type')
    wall_surface_id = fields.Many2one(
        comodel_name='of.calculation.surface', string=u"Murs", domain=[('surface_type', '=', 'wall')])
    roof_surface_id = fields.Many2one(
        comodel_name='of.calculation.surface', string=u"Toiture", domain=[('surface_type', '=', 'roof')])
    floor_surface_id = fields.Many2one(
        comodel_name='of.calculation.surface', string=u"Plancher bas", domain=[('surface_type', '=', 'floor')])
    coefficient = fields.Float(string=u"Coefficient G", compute='_compute_coefficient')
    fuel_coef_id = fields.Many2one(comodel_name='of.calculation.fuel.coef', string=u"Chauffage au bois")
    coef_wood = fields.Float(string=u"Coef (Chauffage au bois)", default=1.0)

    @api.constrains('floor_number')
    def _check_floor_number(self):
        if self.floor_number:
            if self.floor_number < 1:
                raise UserError(u"Le niveau minimum est 1.")
            if self.volume < 270.0 and self.floor_number > 2:
                raise UserError(u"Le calcul de déperdition de chaleur pour un volume inférieur à 270 m³ ne se fait que "
                                u"sur 2 niveaux maximum.")
            elif self.volume > 270.0 and self.floor_number > 3:
                raise UserError(u"Le calcul de déperdition de chaleur pour un volume supérieur ou égal à 270 m³ ne se "
                                u"fait que sur 3 niveaux maximum.")

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
    @api.depends('surface', 'height')
    def _compute_volume(self):
        for rec in self:
            volume = rec.surface * rec.height
            rec.volume = volume

    @api.multi
    @api.depends('construction_date_id')
    def _compute_better_g(self):
        ids = self.get_construction_date_for_better_g()
        for rec in self:
            rec.better_g = rec.construction_date_id.id in ids

    @api.multi
    @api.depends('floor_number', 'volume')
    def _compute_type(self):
        for rec in self:
            if rec.volume and rec.volume < 270.0 and rec.floor_number > 0 and rec.floor_number <= 2:
                rec.volume_type = 'IP%s' % rec.floor_number
            elif rec.volume and rec.volume >= 270.0 and rec.floor_number > 0 and rec.floor_number <= 3:
                rec.volume_type = 'IG%s' % (rec.floor_number > 1 and '2/3' or rec.floor_number)

    @api.multi
    @api.depends('wall_surface_id', 'roof_surface_id', 'floor_surface_id', 'better_g', 'volume_type')
    def _compute_coefficient(self):
        g_values = self.env['of.calculation.g'].search([])
        for rec in self:
            if rec.better_g:
                g_value = g_values.filtered(
                    lambda g: rec.volume_type == g.volume_type
                              and rec.wall_surface_id.k_value == g.k_wall
                              and rec.roof_surface_id.k_value == g.k_roof
                              and rec.floor_surface_id.k_value == g.k_floor)
                rec.coefficient = g_value and g_value[0].g_value or 0.0
            else:
                rec.coefficient = rec.construction_date_id.coefficient

    @api.multi
    @api.onchange('department_id')
    def _onchange_department_id(self):
        self.altitude_id = False

    @api.multi
    @api.onchange('order_id')
    def _onchange_order_id(self):
        if self.order_id:
            self.lead_id = self.order_id.opportunity_id
            self.parc_installe_id = self.order_id.of_parc_installe_ids and self.order_id.of_parc_installe_ids[0]

    @api.multi
    @api.onchange('fuel_coef_id')
    def _onchange_fuel_coef_id(self):
        if self.fuel_coef_id:
            self.coef_wood = self.fuel_coef_id.coef
        else:
            self.coef_wood = 1.0

    @api.onchange('zip_id')
    def onchange_zip_id(self):
        if self.zip_id:
            self.partner_zip = self.zip_id.name
            self.partner_city = self.zip_id.city
            self.partner_state_id = self.zip_id.state_id
            self.partner_country_id = self.zip_id.country_id

    @api.model
    def create(self, vals):
        if not vals.get('partner_id'):
            vals, partner_vals = self._of_extract_partner_values(vals)  # split vals
            partner_vals.update({
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
    def button_view_graph(self):
        self.ensure_one()
        return {
            'name': u"Consommation par combustible",
            'view_type': 'form',
            'view_mode': 'graph',
            'res_model': 'of.calculation.fuel.consumption',
            'type': 'ir.actions.act_window',
            'target': 'current',
            'domain': "[('calculation_id', '=', %s)]" % self.id,
        }

    @api.multi
    def button_compute_estimated_power(self):
        errors = []
        for rec in self:
            error = False
            if rec.surface <= 0.0:
                error = True
                errors.append(u"La surface à chauffer (en m²) doit être supérieur a 0 pour le calcul %s." % rec.name)
            if rec.height <= 0.0:
                error = True
                errors.append(u"La hauteur de plafond (en m) doit être supérieur a 0 pour le calcul %s ." % rec.name)
            if error:
                continue
            reference_temperature = rec.base_temperature_line_id.temperature
            estimated_power = rec.surface * rec.height * rec.get_coefficient_g() * max(
                rec.temperature - reference_temperature, 0)
            products = self.env['product.template'].search([('of_puissance_nom_flo', '>=', estimated_power / 1000)])

            annual_consumption = estimated_power * rec.department_id.unified_day_degree \
                                 * rec.construction_type_id.intermittency_coefficient / 1000
            rec.write(
                {
                    'estimated_power': estimated_power,
                    'estimated_power_text': "%s %s" % (estimated_power / 1000, "kWatt"),
                    'line_ids': [(5,)] + [(0, 0, {'product_id': p.id}) for p in products],
                    'annual_consumption': annual_consumption,
                    'annual_consumption_text': "%.2f %s" % (annual_consumption, "kWatt/an"),
                }
            )
            self.get_fuel_consumption_data()
        if errors:
            return self.env['of.popup.wizard'].popup_return(message=u"\n".join(errors), titre="Erreur(s)")

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
            # field is not related
            if not getattr(field, 'related'):
                continue
            related = field.related
            if related and related[0] == 'partner_id':  # field related to partner_id
                partner_vals['.'.join(related[1:])] = val  # add value to partner_vals
                del new_vals[field_name]  # take value out of new vals
        if 'partner_name' in vals and not partner_vals['name']:
            partner_vals['name'] = "Web"
        return new_vals, partner_vals

    @api.multi
    def send_calculation(self):
        template_id = self.env.ref('of_calculation_heat_loss.email_template_calcul_deperdition')
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
        email_values = {'attachment_ids': attachment.ids}
        # envoi immédiat de l'email
        template_id.send_mail(self.id, force_send=True, email_values=email_values)

        return True

    def get_fuel_consumption_data(self):
        fuels = self.env['of.calculation.fuel'].search([])
        res = []
        fuel_coef = self.coef_wood
        for fuel in fuels:
            annual_consumption = self.annual_consumption
            if fuel.use_coef:
                annual_consumption *= fuel_coef
            volume =  annual_consumption / fuel.calorific_value
            values = {
                'calculation_id': self.id,
                'fuel_id': fuel.id,
                'fuel_volume': volume,
                'fuel_cost': volume * fuel.price,
            }
            if not self.fuel_consumption_ids.filtered(lambda f: f.fuel_id == fuel):
                res += [(0, 0, values)]
            else:
                for fuel in self.fuel_consumption_ids.filtered(lambda f: f.fuel_id == fuel):
                    res += [(1, fuel.id, values)]
        self.write({'fuel_consumption_ids': res})

    @api.model
    def get_construction_date_for_better_g(self):
        construction_dates = [
            self.env.ref('of_calculation_heat_loss.construction_date_4', raise_if_not_found=False),
            self.env.ref('of_calculation_heat_loss.construction_date_5', raise_if_not_found=False),
            self.env.ref('of_calculation_heat_loss.construction_date_6', raise_if_not_found=False),
            self.env.ref('of_calculation_heat_loss.construction_date_7', raise_if_not_found=False),
            self.env.ref('of_calculation_heat_loss.construction_date_8', raise_if_not_found=False),
        ]
        return [date.id for date in construction_dates if date]

    @api.multi
    def get_coefficient_g(self):
        self.ensure_one()
        return self.coefficient or self.construction_date_id.coefficient


class OFCalculationConstructionDate(models.Model):
    _name = 'of.calculation.construction.date'
    _description = u"Date de construction"
    _order = 'sequence'

    name = fields.Char(string=u"Nom", required=True)
    sequence = fields.Integer(string=u"Séquence")
    coefficient = fields.Float(string=u"Coefficient G", required=True)
    message = fields.Text(string=u"Message")


class OFCalculationDepartment(models.Model):
    _name = 'of.calculation.department'
    _description = u"Département"
    _order = 'code'

    name = fields.Char(string=u"Nom", required=True)
    code = fields.Integer(string=u"Code", required=True)
    unified_day_degree = fields.Float(string=u"DJU", help=u"Degré jour unifié")
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
