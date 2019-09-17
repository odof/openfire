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

    secteur_com_id = fields.Many2one('of.secteur', string="Secteur Commercial")
    secteur_tech_id = fields.Many2one('of.secteur', string="Secteur Technique")

    @api.onchange('secteur_com_id')
    def _onchange_secteur_com_id(self):
        self.ensure_one()
        if self.secteur_com_id and self.secteur_com_id.type == 'tech_com':
            self.secteur_tech_id = self.secteur_com_id.id

class OfSecteur(models.Model):
    _name = "of.secteur"

    name = fields.Char(string="Libellé", required=True)
    code = fields.Char(string="Code")
    type = fields.Selection(
        [('tech', 'Technique'),
         ('com', 'Commercial'),
         ('tech_com', 'Technique et commercial'),
        ], string="type de secteur", required=True, default='tech_com')
    regle_ids = fields.One2many('of.secteur.regle', 'secteur_com_id', string=u'Codes postaux')
    active = fields.Boolean(string='Actif', default=True)

    _sql_constraints = [
        ('name_uniq', 'unique(name)', 'Oups ! On dirait que ce secteur existe déjà...'),
    ]

    @api.multi
    @api.depends('type', 'zip_com_ids', 'zip_tech_ids')
    def _compute_zip_utile_ids(self):
        for secteur in self:
            if secteur.type == 'tech':
                secteur.zip_utile_ids = [(5, )] + [(4, zip_id, 0) for zip_id in self.zip_tech_ids._ids]
            else:
                secteur.zip_utile_ids = [(5, )] + [(4, zip_id, 0) for zip_id in self.zip_com_ids._ids]

    @api.multi
    def write(self, vals):
        if vals.get('type') == 'tech_com':  # Est transformé en secteur technique et commercial
            vals['zip_tech_ids'] = [(5, )] + vals['zip_com_ids']
        return super(OfSecteur, self).write(vals)

    @api.model
    def create(self, vals):
        if vals.get('type') == 'tech_com':
            vals['zip_tech_ids'] = [(5, )] + vals['zip_com_ids']
        return super(OfSecteur, self).create(vals)

    @api.model
    def get_secteur_from_cp(self, cp):
        return self.env['of.secteur.regle'].search(
            [('cp_min', '<=', cp), ('cp_max', '>=', cp)],
            order="cp_min DESC, cp_max", limit=1
        ).secteur_id

    @api.multi
    def get_partners(self):
        partner_obj = self.env['res.partner']
        regle_obj = self.env['of.secteur.regle']

        domain = ['|'] * (len(self) - 1)

        for regle in self.mapped(regle_ids):
            cp_min = regle.cp_min
            cp_max = regle.cp_max
            regles_intra = regle_obj.search(
                [('cp_min', '>=', cp_min), ('cp_min', '<=', cp_max), ('id', '!=', regle.id)],
                order='cp_min, cp_max DESC')

            domain_secteur = ['&'] * (len(regles_intra) + 1)
            domain_secteur += [('zip', '>=', cp_min), ('zip', '<=', cp_max)]
            for regle_intra in regles_intra:
                if regle_intra.cp_max >= cp_min:
                    domain_secteur += ['|', ('zip', '<', regle_intra.cp_min), ('zip', '>', regle_intra.cp_max)]
                    cp_min = regle_intra.cp_max
            domain += domain_secteur

        return partner_obj.search(domain)

class OfSecteurRegle(models.Model):
    _name = "of.secteur.regle"
    _order = 'cp_min, cp_max'

    cp_min = fields.Char(u'Code postal début', required=True)
    cp_max = fields.Char(u'Code postal fin', required=True)
    secteur_id = fields.Many2one('of.secteur', string='Secteur', required=True, ondelete='cascade')

    @api.onchange('cp_min')
    def _onchange_cp_min(self):
        self.ensure_one()
        self.cp_max = self.cp_min
