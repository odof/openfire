# -*- coding: utf-8 -*-

from odoo import models, fields, api


class ProductTemplate(models.Model):
    _inherit = 'product.template'


    @api.model
    def create(self, args):
        sample_available = args.get('sample_available', False)

        # Si gestion des échantillons
        if sample_available:
            # On créé le sample
            sample_id = self.create({
                "name": args.get('name') + u" (échantillon)",
                "type": args.get('type',False),
                "brand_id": args.get('brand_id',False),
                "default_code": args.get('default_code', '')
                                + self.env['ir.sequence'].next_by_code('product.sample') or '_ECH',
                "categ_id": args.get('categ_id',False),
                "public_categ_ids": args.get('public_categ_ids',False),
                "description_sale": args.get('description_sale',False),
                "description_purchase": args.get('description_purchase',False),
                "description_picking": args.get('description_picking',False),
                "description_fabricant": args.get('description_fabricant',False),
                "seller_ids": args.get('seller_ids',False),
                "is_sample": True,
                "active": True,
                "website_published": False,
            })

            args['sample_id'] = sample_id.id
        res = super(ProductTemplate, self).create(args)

        if sample_available:
            # On assigne le parent
            res.sample_id.write({
                "sample_parent_id": res.id,
            })

        return res


    sample_available = fields.Boolean("Sample available")
    is_sample = fields.Boolean("Is sample")
    sample_id = fields.Many2one("product.template", string="Sample")
    sample_default_code = fields.Char(related="sample_id.default_code", string="Sample ref.", readonly=True)
    sample_active = fields.Boolean(related="sample_id.active", string="Sample active", readonly=True)
    sample_parent_id = fields.Many2one("product.template", string="Sample parent")
    sample_parent_default_code = fields.Char(related="sample_parent_id.default_code", string="Parent ref.", readonly=True)
    sample_parent_active = fields.Boolean(related="sample_parent_id.active", string="Parent active", readonly=True)


    @api.multi
    def action_view_sample(self):
        if self.ensure_one():
            return {
                'name': 'Sample',
                'view_mode': 'form',
                'res_model': 'product.template',
                'res_id': self.sample_id.id,
                'type': 'ir.actions.act_window',
            }

    @api.multi
    def action_view_sample_parent(self):
        if self.ensure_one():
            return {
                'name': 'Sample',
                'view_mode': 'form',
                'res_model': 'product.template',
                'res_id': self.sample_parent_id.id,
                'type': 'ir.actions.act_window',
            }


    @api.multi
    def write(self, args):
        sample_available = args.get('sample_available')
        website_published = args.get('website_published')

        # Si on archive/désarchive le parent, on archive/désarchive l'enfant
        if 'active' in args:
            if self.sample_id:
                self.sample_id.active = args['active']

        # On ne veut pas qu'un sample apparaisse dans le shop
        if website_published == True:
            if self.is_sample:
                args.pop('website_published')

        # Si gestion des échantillons
        if sample_available:

            supplierinfo_obj = self.env['product.supplierinfo']

            if not self.sample_id:

                # On créé d'abord les fournisseurs
                seller_ids = []
                for seller in self.seller_ids:
                    seller_id = supplierinfo_obj.create({
                        "name": seller.name.id,
                    })
                    seller_ids.append(seller_id.id)


                # On créé sample_id
                sample_id = self.create({
                    "name": self.name + u" (échantillon)",
                    "type": self.type,
                    "brand_id": self.brand_id.id,
                    "default_code": self.default_code
                                    + self.env['ir.sequence'].next_by_code('product.sample') or '_ECH',
                    "categ_id": self.categ_id and self.categ_id.id,
                    "public_categ_ids": self.public_categ_ids and self.public_categ_ids.ids,
                    "description_sale": self.description_sale,
                    "description_purchase": self.description_purchase,
                    "description_picking": self.description_picking,
                    "description_fabricant": self.description_fabricant,
                    "seller_ids": [[6, 0, seller_ids]],
                    "is_sample": True,
                    "sample_parent_id": self.id,
                    "active": True,
                    "website_published": False,
                })

                args['sample_id'] = sample_id.id

            else:
                # On met à jour sample_id et on le désarchive
                self.sample_id.write({
                    "name": self.name + u" (échantillon)",
                    "type": self.type,
                    "brand_id": self.brand_id.id,
                    "categ_id": self.categ_id and self.categ_id.id,
                    "public_categ_ids": self.public_categ_ids and self.public_categ_ids.ids,
                    "description_sale": self.description_sale,
                    "description_purchase": self.description_purchase,
                    "description_picking": self.description_picking,
                    "description_fabricant": self.description_fabricant,
                    "is_sample": True,
                    "sample_parent_id": self.id,
                    "active": True,
                    "website_published": False,
                })

        # On teste sample_available == False au lieu de not sample_available
        # Car sample_available = args.get('sample_available') renvoie None si non présent dans le dict
        elif sample_available == False:
            # on désactive sample_available et on archive le sample")
            self.sample_id.write({
                    "active": False,
                })

        return super(ProductTemplate, self).write(args)

    @api.multi
    def unlink(self):
        # Si gestion des échantillons, on supprime le sample associé
        if self.sample_available:
            self.sample_id.unlink()

        # Si échantillon, on désactive la gestion des échantillons sur le parent
        if self.is_sample:
            self.sample_parent_id.sample_available = False

        return super(ProductTemplate, self).unlink()