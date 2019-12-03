# -*- coding: utf-8 -*-

from odoo import models, fields, api

class BetterZip(models.Model):
    _inherit = 'res.better.zip'

    geo_lat = fields.Float(string='Latitude', digits=(16, 5))
    geo_lng = fields.Float(string='Longitude', digits=(16, 5))

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        # Fonction inspirée de celle de product_product
        if not args:
            args = []
        if name and operator == 'ilike':
            tab = name.strip().split(' ')
            zips = self.search([('name', '=like', tab[0]+'%')])
            if zips:
                name = ' '.join(tab[1:])
            elif len(tab) > 1:
                zips = self.search([('name', '=like', tab[-1]+'%')])
                if zips:
                    name = ' '.join(tab[:-1])

            if zips:
                zips = self.search([('id', 'in', zips._ids), ('city', 'ilike', name)] + args)
                return zips.name_get()
        return super(BetterZip, self).name_search(name=name, args=args, operator=operator, limit=limit)

    @api.one
    def _get_display_name(self):
        if self.country_id and self.country_id.code == 'FR':
            if self.name:
                name = [self.name, self.city]
            else:
                name = [self.city]
            self.display_name = ", ".join(name)
        else:
            super(BetterZip, self)._get_display_name()

class ResPartner(models.Model):
    _inherit = 'res.partner'

    of_secteur_com_id = fields.Many2one('of.secteur', string="Secteur commercial", oldname="secteur_com_id")
    of_secteur_tech_id = fields.Many2one('of.secteur', string="Secteur technique")

    @api.onchange('of_secteur_com_id')
    def _onchange_of_secteur_com_id(self):
        self.ensure_one()
        if self.of_secteur_com_id and self.of_secteur_com_id.type == 'tech_com':
            self.of_secteur_tech_id = self.of_secteur_com_id.id


class OfSecteur(models.Model):
    _name = "of.secteur"

    name = fields.Char(string="Libellé", required=True)
    code = fields.Char(string="Code")
    type = fields.Selection(
        [('tech', 'Technique'),
         ('com', 'Commercial'),
         ('tech_com', 'Technique et commercial'),
        ], string="type de secteur", required=True, default='tech_com')
    zip_range_ids = fields.One2many('of.secteur.zip.range', 'secteur_id', string=u'Codes postaux')
    active = fields.Boolean(string='Actif', default=True)

    _sql_constraints = [
        ('name_uniq', 'unique(name)', 'Oups ! On dirait que ce secteur existe déjà...'),
    ]

    @api.multi
    def get_secteurs_interieurs(self, type='tech'):
        zip_range_obj = self.env['of.secteur.zip.range']
        types = ('tech', 'tech_com') if type == 'tech' else ('com', 'tech_com')
        if len(self) == 1:
            zip_range_ids = self.env['of.secteur.zip.range']
            for zip_range in self.zip_range_ids:
                under_zip_range_ids = zip_range_obj.search([('cp_min', '<=', zip_range.cp_max), ('cp_max', '>=', zip_range.cp_min)])
                for under_zip_range_id in under_zip_range_ids:
                    if under_zip_range_id.secteur_id.type in types:
                        zip_range_ids |= under_zip_range_id
            return zip_range_ids.mapped('secteur_id').filtered(lambda s: s.id != self.id)
        elif len(self) > 1:
            res = {}
            for secteur in self:
                zip_range_ids = self.env['of.secteur.zip.range']
                for zip_range in secteur.zip_range_ids:
                    under_zip_range_ids = zip_range_obj.search([('cp_min', '<=', zip_range.cp_max), ('cp_max', '>=', zip_range.cp_min)])
                    for under_zip_range_id in under_zip_range_ids:
                        if under_zip_range_id.secteur_id.type in types:
                            zip_range_ids |= under_zip_range_id
                res[secteur.id] = zip_range_ids.mapped('secteur_id').filtered(lambda s: s.id != secteur.id)
            return res

    @api.model
    def get_secteur_from_cp(self, cp):
        return self.env['of.secteur.zip.range'].search(
            [('cp_min', '<=', cp), ('cp_max', '>=', cp)],
            order="cp_min DESC, cp_max", limit=1
        ).secteur_id

    @api.multi
    def get_partners(self):
        partner_obj = self.env['res.partner']
        zip_range_obj = self.env['of.secteur.zip.range']

        domain = ['|'] * (len(self) - 1)

        for zip_range in self.mapped("zip_range_ids"):
            cp_min = zip_range.cp_min
            cp_max = zip_range.cp_max
            zip_ranges_intra = zip_range_obj.search(
                [('cp_min', '>=', cp_min), ('cp_min', '<=', cp_max), ('id', '!=', zip_range.id)],
                order='cp_min, cp_max DESC')

            domain_secteur = ['&'] * (len(zip_ranges_intra) + 1)
            domain_secteur += [('zip', '>=', cp_min), ('zip', '<=', cp_max)]
            for zip_range_intra in zip_ranges_intra:
                if zip_range_intra.cp_max >= cp_min:
                    domain_secteur += ['|', ('zip', '<', zip_range_intra.cp_min), ('zip', '>', zip_range_intra.cp_max)]
                    cp_min = zip_range_intra.cp_max
            domain += domain_secteur

        return partner_obj.search(domain)

class OfSecteurZipRange(models.Model):
    _name = "of.secteur.zip.range"
    _order = 'cp_min, cp_max'

    name = fields.Char(string=u"Nom affiché", compute="_compute_name", store=True)
    cp_min = fields.Char(u'Code postal début', required=True)
    cp_max = fields.Char(u'Code postal fin', required=True)
    secteur_id = fields.Many2one('of.secteur', string='Secteur', required=True, ondelete='cascade')

    @api.depends('cp_min', 'cp_max')
    @api.multi
    def _compute_name(self):
        for zip_range in self:
            if zip_range.cp_min == zip_range.cp_max:
                zip_range.name = zip_range.cp_min
            else:
                zip_range.name = zip_range.cp_min + u' - ' + zip_range.cp_max

    @api.onchange('cp_min')
    def _onchange_cp_min(self):
        self.ensure_one()
        self.cp_max = self.cp_min
