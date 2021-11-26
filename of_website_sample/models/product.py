# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class ProductTemplate(models.Model):
    _name = 'product.template'
    _inherit = ['product.template', 'of.form.readonly']

    sample_available = fields.Boolean("Sample available")
    is_sample = fields.Boolean("Is sample", readonly=True)
    sample_id = fields.Many2one("product.template", string="Sample")
    sample_default_code = fields.Char(related="sample_id.default_code", string="Sample ref.", readonly=True)
    sample_active = fields.Boolean(related="sample_id.active", string="Sample active", readonly=True)
    sample_parent_id = fields.Many2one("product.template", string="Sample parent")
    sample_parent_default_code = fields.Char(related="sample_parent_id.default_code",
                                             string="Parent ref.", readonly=True)
    sample_parent_active = fields.Boolean(related="sample_parent_id.active", string="Parent active", readonly=True)

    @api.model
    def create(self, args):
        res = super(ProductTemplate, self).create(args)
        # Si gestion des écantillons
        if res.sample_available:
            args_sample = res.get_sample_values()
            # On crée sample_id
            sample = res.create(args_sample)
            res.with_context(skip_sample=True).sample_id = sample.id
        return res

    @api.multi
    def write(self, args):
        website_published = args.get('website_published')
        templates = self.env['product.template']
        samples = self.env['product.template']
        if website_published:
            # Les échantillons ne doivent pas être publiés, on sépare les échantillons des autres articles pour le super
            for pt in self:
                if pt.is_sample:
                    samples += pt
                else:
                    templates += pt
            res1 = super(ProductTemplate, templates).write(args)
            args.pop('website_published')
            res2 = super(ProductTemplate, samples).write(args)
            res = res1 and res2
        else:
            res = super(ProductTemplate, self).write(args)

        if not self._context.get('skip_sample'):
            unaffected_fields = self.sample_unaffected_fields()
            any_field = any([field not in unaffected_fields for field in args.keys()])
            for pt in self:
                if pt.sample_available and not pt.sample_id:
                    args_sample = pt.get_sample_values()
                    # On crée sample_id
                    sample_id = pt.with_context(skip_sample=True).create(args_sample)
                    pt.with_context(skip_sample=True).sample_id = sample_id.id
                elif any_field:
                    args_sample = pt.get_sample_values()
                    if not pt.sample_available:
                        # si pt.active == False alors args_sample['active'] déjà à False donc pas besoin de vérifier
                        args_sample['active'] = False
                    # On met à jour sample_id et on le désarchive
                    pt.sample_id.with_context(skip_sample=True).write(args_sample)
        return res

    @api.multi
    def unlink(self):
        # Si gestion des échantillons, on supprime le sample associé
        if self.sample_id:
            self.sample_id.unlink()

        # Si échantillon, on désactive la gestion des échantillons sur le parent
        if self.is_sample:
            self.sample_parent_id.sample_available = False

        return super(ProductTemplate, self).unlink()

    @api.multi
    def get_sample_values(self, force=False):
        """ Renvoi un dictionnaire de valeur pour permettre la création/synchronisation d'un échantillon avec les
            valeurs de son parent. """
        self.ensure_one()
        sample_dict = self.copy_data()[0]
        if not self.sample_id or force:
            seller_ids = []
            for seller in self.seller_ids:
                seller_id_copy = seller.copy()
                seller_ids.append(seller_id_copy.id)
            args_sample = dict(sample_dict, **{
                "name": self.name + _(u" (sample)"),
                "default_code": (self.default_code or '')
                                + self.env['ir.sequence'].next_by_code('product.sample') or '_ECH',
                "is_sample": True,
                "website_published": False,
                "sample_parent_id": self.id,
                "seller_ids": [[6, 0, seller_ids]]
                })
        else:
            unaffected_fields = self.sample_unaffected_fields()

            args_sample = {key: val for key, val in sample_dict.iteritems() if key not in unaffected_fields}
        args_sample['sample_available'] = False
        args_sample['is_sample'] = True
        return args_sample

    @api.model
    def sample_unaffected_fields(self):
        return [
            'name', 'default_code', 'seller_ids', 'website_description',
            'description_sale', 'description_purchase', 'description_picking',
            'description_fabricant', 'list_price', 'standard_price', 'website_published'
            ]

    @api.multi
    def action_view_sample(self):
        self.ensure_one()
        return {
            'name': 'Sample',
            'view_mode': 'form',
            'res_model': 'product.template',
            'res_id': self.sample_id.id,
            'type': 'ir.actions.act_window',
            'context': {'form_readonly': '[("is_sample","=",True)]'},
        }

    @api.multi
    def action_view_sample_parent(self):
        self.ensure_one()
        return {
            'name': 'Sample',
            'view_mode': 'form',
            'res_model': 'product.template',
            'res_id': self.sample_parent_id.id,
            'type': 'ir.actions.act_window',
            'context': {'form_readonly': '[("is_sample","=",True)]'},
        }
