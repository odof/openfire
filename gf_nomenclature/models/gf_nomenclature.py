# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.addons import decimal_precision as dp
from odoo.exceptions import UserError, ValidationError

class GFNomenclature(models.Model):
    _name = "gf.nomenclature"

    @api.model
    def _get_euro(self):
        return self.env['res.currency.rate'].search([('rate', '=', 1)], limit=1).currency_id

    @api.model
    def _get_user_currency(self):
        currency_id = self.env['res.users'].browse(self._uid).company_id.currency_id
        return currency_id or self._get_euro()

    @api.model
    def _get_company(self):
        return self.env.user.company_id

    name = fields.Char(string="Nom", required=True)
    default_code = fields.Char(string="Réf interne")
    company_ids = fields.Many2many('res.company', 'res_company_users_rel', 'user_id', 'cid',
        string='Companies', default=_get_company)
    nom_line_ids = fields.One2many('gf.nomenclature.line', 'nomenclature_id', string='Products')
    currency_id = fields.Many2one('res.currency', string='Currency', required=True, default=lambda self: self._get_user_currency())
    price_comps = fields.Monetary('Compo Price/Kit', digits=dp.get_precision('Product Price'), compute='_compute_compo_price_n_cost',
                                  help="Sum of the prices of all components necessary for 1 unit of this nom")
    cost_comps = fields.Monetary('Compo Cost/Kit', digits=dp.get_precision('Product Price'), compute='_compute_compo_price_n_cost',
                                  help="Sum of the costs of all components necessary for 1 unit of this nom")
    active = fields.Boolean(string="Active", default=True)
    product_count = fields.Integer('# Products', compute='_compute_product_count')
    sequence = fields.Integer(string=u'Sequence', default=10)

    saleorder_count = fields.Integer(string="# Sale orders", compute="_compute_docs_count")
    saleorder_ids = fields.One2many("sale.order", "nomenclature_id", string="Sale orders")
    invoice_count = fields.Integer(string="# Invoices", compute="_compute_docs_count")
    invoice_ids = fields.One2many("account.invoice", "nomenclature_id", string="Invoices")

    @api.multi
    @api.depends("saleorder_ids")
    def _compute_docs_count(self):
        for nomenclature in self:
            nomenclature.saleorder_count = len(nomenclature.saleorder_ids)
            nomenclature.invoice_count = len(nomenclature.invoice_ids)

    @api.multi
    @api.depends('nom_line_ids')
    def _compute_compo_price_n_cost(self):
        for nomenclature in self:
            price_n_cost = nomenclature.get_compo_price_n_cost()
            nomenclature.price_comps = price_n_cost['price']
            nomenclature.cost_comps = price_n_cost['cost']

    @api.multi
    @api.depends('nom_line_ids')
    def _compute_product_count(self):
        for nomenclature in self:
            nomenclature.product_count = len(nomenclature.nom_line_ids)

    def get_compo_price_n_cost(self):
        """
        returns the sum of the prices and costs of all components in this kit.
        """
        self.ensure_one()
        res = {'price': 0.0, 'cost': 0.0}
        for line in self.nom_line_ids:
            #if line.product_id.of_is_kit:
            #    res['price'] += line.product_id.of_price_used * line.product_qty
            #    res['cost'] += line.product_id.cost_comps * line.product_qty
            #else:
            res['price'] += line.product_id.list_price * line.product_qty
            res['cost'] += line.product_id.standard_price * line.product_qty
        return res

    @api.multi
    def _prepare_saleorder_vals(self):
        self.ensure_one()
        vals= {}
        saleorder_lines = [(5,)]
        for line in self.nom_line_ids:
            line_vals = line._prepare_saleorder_line_vals()
            saleorder_lines.append((0, 0, line_vals))
        vals["order_line"] = saleorder_lines
        return vals

    @api.multi
    def _prepare_invoice_vals(self):
        self.ensure_one()
        vals= {}
        invoice_lines = [(5,)]
        for line in self.nom_line_ids:
            line_vals = line._prepare_saleorder_line_vals()
            invoice_lines.append((0, 0, line_vals))
        vals["invoice_line_ids"] = invoice_lines
        return vals

    @api.multi
    def action_make_saleorder(self):
        # action déclenchée depuis le bouton "créer devis"
        self.ensure_one()
        action = {
            "type": "ir_actions.act_window",
            "name": "nomenclature_make_so_action",
            "res_model": "sale.order",
            "view_type": "form",
            "view_mode": "form",
            "target": "same",
        }
        # pré-remplir les lignes de commande
        action["context"] = {
            "default_order_line": self._prepare_saleorder_vals()["order_line"]
        }
        return action

    @api.multi
    def action_make_invoice(self):
        # action déclenchée depuis le bouton "créer facture"
        self.ensure_one()
        action = {
            "type": "ir_actions.act_window",
            "name": "nomenclature_make_fac_action",
            "res_model": "account.invoice",
            "view_type": "form",
            "view_mode": "form",
            "target": "same",
        }
        # pré-remplir les lignes de commande
        action["context"] = {
            "default_invoice_line_ids": self._prepare_invoice_vals()["invoice_line_ids"]
        }
        return action

class GFNomenclatureLine(models.Model):
    _name = "gf.nomenclature.line"
    _order = 'nomenclature_id, sequence'

    def _get_default_product_uom_id(self):
        return self.env['product.uom'].search([], limit=1, order='id').id

    #name = fields.Char(string="Name", required=True)
    nomenclature_id = fields.Many2one("gf.nomenclature", string="Nomenclature", required=True,
                             help="Nomenclature", ondelete="cascade")
    product_id = fields.Many2one("product.product", string="Product", required=True,
                                 help="Product this line references")
    product_qty = fields.Float(string='Qty / Kit', digits=dp.get_precision('Product Unit of Measure'), required=True, default=1.0,
                               help="Quantity per kit unit.")
    product_uom_id = fields.Many2one('product.uom', string='UoM', default=_get_default_product_uom_id, required=True, oldname="product_uom")
    sequence = fields.Integer(string=u'Sequence', default=10)
    product_price = fields.Float(related='product_id.list_price', readonly=True)
    product_cost = fields.Float(related='product_id.standard_price', readonly=True)
    currency_id = fields.Many2one(related="nomenclature_id.currency_id", readonly=True)
    #kit_line_ids = fields.One2many(related="product_id.product_tmpl_id.kit_line_ids", readonly=True)  #probleme de onchange O2M dans O2M malgré readonly?

    def _prepare_saleorder_line_vals(self):
        self.ensure_one()
        vals = {
            'product_id': self.product_id.id,
            'product_uom_qty': self.product_qty,
            'product_uom': self.product_uom_id.id,
        }
        return vals

    def _prepare_invoice_line_vals(self):
        self.ensure_one()
        vals = {
            'product_id': self.product_id.id,
            'quantity': self.product_qty,
            'uom_id': self.product_uom_id.id,
        }
        return vals

    def _prepare_vals_for_insert(self):
        self.ensure_one()
        vals = {
            'product_id': self.product_id.id,
            'product_qty': self.product_qty,
            'product_uom_id': self.product_uom_id.id,
            'sequence': self.sequence,
        }
        return vals

    @api.multi
    @api.onchange("product_id")
    def _onchange_product_id(self):
        # changer l'udm
        return True

    @api.multi
    @api.onchange("product_uom_id")
    def _onchange_product_uom_id(self):
        # recalculer quelquechose?
        return True

    @api.model
    def create(self, vals):
        line = super(GFNomenclatureLine, self).create(vals)
        return line

    @api.multi
    def write(self, vals):
        super(GFNomenclatureLine, self).write(vals)
        return True

    @api.multi
    def unlink(self):
        super(GFNomenclatureLine, self).unlink()


class GFProductTemplate(models.Model):
    _inherit = "product.template"

    nom_count = fields.Integer('# Nomenclatures', compute='_compute_nom_count')

    @api.multi
    @api.depends('product_variant_ids', 'product_variant_ids.nom_count')
    def _compute_nomenclature_count(self):
        for product_tmpl in self:
            nom_count = 0
            for variant in product_tmpl.product_variant_ids:
                nom_count += variant.nom_count
            product_tmpl.nom_count = nom_count

    @api.multi
    def action_view_noms(self):
        action = self.env.ref('gf_nomenclature.gf_template_open_nom').read()[0]
        action['domain'] = [('nom_line_ids.product_id.product_tmpl_id', 'in', [self.ids])]
        return action


class GFProductProduct(models.Model):
    _inherit = "product.product"

    nom_count = fields.Integer('# Nomenclatures', compute='_compute_nom_count')

    def _compute_nom_count(self):
        read_group_res = self.env['gf.nomenclature.line'].read_group([('product_id', 'in', self.ids)], ['product_id'], ['product_id'])
        mapped_data = dict([(data['product_id'][0], data['product_id_count']) for data in read_group_res])
        for product in self:
            nom_count = mapped_data.get(product.id, 0)
            product.nom_count = nom_count


class GFSaleOrder(models.Model):
    _inherit = "sale.order"

    nomenclature_id = fields.Many2one("gf.nomenclature", string="Nomenclature")



class GFAccountInvoice(models.Model):
    _inherit = "account.invoice"

    nomenclature_id = fields.Many2one("gf.nomenclature", string="Nomenclature")

