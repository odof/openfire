# -*- coding: utf-8 -*-


from odoo import api, fields, models

import odoo.addons.decimal_precision as dp

# Les classes sale.quote.template et sale.quote.line proviennent du module Odoo 11 website_quote/models/sale_quote.py
# La classe sale.order provient du module Odoo 11 website_quote/models/sale_order.py.
# Tout les champs qui ne commencent pas par of_ sont les champs déjà existants dans Odoo 11


class SaleQuoteTemplate(models.Model):
    _name = "sale.quote.template"
    _description = u"Modèle de devis"

    name = fields.Char(u'Nom du modèle', required=True)
    quote_line = fields.One2many('sale.quote.line', 'quote_id', u'Lignes du modèle', copy=True, help=u"Une ligne rouge signifie que l'article utilisé ne peut pas être vendu ou qu'il est désactivé.")
    note = fields.Text('Notes')
    active = fields.Boolean(default=True, help=u"Si archivé, ne sera pas visible dans les listes de modèles de devis sauf avec l'utilisation d'un filtre (permet de ne pas supprimer le modèle)")
    of_mail_template_ids = fields.Many2many('of.mail.template', string="Documents joints")
    of_comment_template1_id = fields.Many2one("base.comment.template", string=u"Utiliser un modèle")
    of_comment_template2_id = fields.Many2one("base.comment.template", string=u"Utiliser un modèle")
    of_note1 = fields.Html('Commentaire du haut')
    of_note2 = fields.Html('Commentaire du bas')
    of_fiscal_position_id = fields.Many2one('account.fiscal.position', string="Position fiscale")
    of_payment_term_id = fields.Many2one('account.payment.term', string="Conditions de règlement")

    @api.onchange('of_comment_template1_id')
    def _set_note1(self):
        """ Ajout du template de note 1 à la fin de la note (ne supprime pas la note existante)
        """
        comment = self.of_comment_template1_id
        if comment:
            self.of_note1 = (self.of_note1 or '') + comment.get_value()
            self.of_comment_template1_id = False

    @api.onchange('of_comment_template2_id')
    def _set_note2(self):
        """ Ajout du template de note 2 à la fin de la note (ne supprime pas la note existante)
        """
        comment = self.of_comment_template2_id
        if comment:
            self.of_note2 = (self.of_note2 or '') + comment.get_value()
            self.of_comment_template2_id = False


class SaleQuoteLine(models.Model):
    _name = "sale.quote.line"
    _description = u"Lignes de modèle de devis"
    _order = 'sequence, id'

    sequence = fields.Integer('Sequence', help=u"Permet de donner un ordre à l'affiche des lignes du devis du modèle.", default=10)
    quote_id = fields.Many2one('sale.quote.template', u'Modèle de devis', required=True, ondelete='cascade', index=True)
    name = fields.Text('Description', required=True, translate=True)
    product_id = fields.Many2one('product.product', 'Produit', domain=[('sale_ok', '=', True)], required=True)
    layout_category_id = fields.Many2one('sale.layout_category', string='Section')
    price_unit = fields.Float('Prix unitaire', required=True, digits=dp.get_precision('Product Price'))
    discount = fields.Float('Remise (%)', digits=dp.get_precision('Discount'), default=0.0)
    product_uom_qty = fields.Float(u'Quantitée', required=True, digits=dp.get_precision('Product UoS'), default=1)
    product_uom_id = fields.Many2one('product.uom', u'Unité de mesure', required=True)
    of_active = fields.Boolean('Article actif', compute="_compute_active")

    @api.depends('product_id')
    def _compute_active(self):
        """ Permet de déterminer quelles lignes sont utilisables dans un devis
        (Ajout openfire)
        """
        for line in self:
            line.of_active = line.product_id.active and line.product_id.sale_ok

    @api.onchange('product_id')
    def _onchange_product_id(self):
        """ Récupération de informations du produit
        (code Odoo v11)
        """
        self.ensure_one()
        domain = {'product_uom_id': [('category_id', 'ilike', '')]}
        if self.product_id:
            name = self.product_id.name_get()[0][1]
            if self.product_id.description_sale:
                name += '\n' + self.product_id.description_sale
            self.name = name
            self.price_unit = self.product_id.lst_price
            self.product_uom_id = self.product_id.uom_id.id
            domain = {'product_uom_id': [('category_id', '=', self.product_id.uom_id.category_id.id)]}
        return {'domain': domain}

    @api.onchange('product_uom_id')
    def _onchange_product_uom(self):
        """ Modification du prix en fonction de l'udm
        (code Odoo v11)
        """
        if self.product_id and self.product_uom_id:
            self.price_unit = self.product_id.uom_id._compute_price(self.product_id.lst_price, self.product_uom_id)


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    of_template_id = fields.Many2one('sale.quote.template', string=u'Modèle de devis', readonly=True,
        states={'draft': [('readonly', False)], 'sent': [('readonly', False)]})

    of_note_insertion = fields.Text(string=u"Note d'insertion", help=u"Cette note disparaitra lorsque le devis sera sauvegardé.",)

    @api.model
    def create(self, vals):
        """ Permet de cacher la note lors de la sauvegarde du devis/bon de commande
        """
        vals['of_note_insertion'] = ''
        return super(SaleOrder, self).create(vals)

    @api.multi
    def write(self, vals):
        """ Permet de cacher la note lors de la sauvegarde du devis/bon de commande
        """
        vals['of_note_insertion'] = ''
        return super(SaleOrder, self).write(vals)

    def _get_data_from_template(self, line, price, discount):
        """ Permet de renvoyer les informations nécessaires à la création de ligne du bon de commande
        (à surcharger pour ajouter des informations)
        """
        data = {
            'name': line.name,
            'price_unit': price,
            'discount': 100 - ((100 - discount) * (100 - line.discount)/100),
            'product_uom_qty': line.product_uom_qty,
            'product_id': line.product_id.id,
            'layout_category_id': line.layout_category_id,
            'product_uom': line.product_uom_id.id,
        }
        return data

    def _compute_prices_from_template(self):
        """ Permet le recalcul des prix des lignes
        """
        self.order_line._compute_tax_id()

    @api.onchange('of_template_id')
    def onchange_template_id(self):
        """ Ajout des informations du modèle de devis dans le devis
        """
        if not self.of_template_id:
            return
        template = self.of_template_id.with_context(lang=self.partner_id.lang)
        order_line_obj = self.env['sale.order.line']

        regime = self.env['ir.values'].get_default('sale.config.settings', 'of_quote_template')
        if regime == 'add':
            order_lines = self.order_line
        else:
            order_lines = order_line_obj
        inactif = False  # Permet de savoir si il y a un article inactif
        for line in template.quote_line:
            discount = 0
            if not line.of_active:
                inactif = True
            else:
                if self.pricelist_id:
                    price = self.pricelist_id.with_context(uom=line.product_uom_id.id).get_product_price(line.product_id, 1, False)
                    if self.pricelist_id.discount_policy == 'without_discount' and line.price_unit:
                        discount = (line.price_unit - price) / line.price_unit * 100
                        price = line.price_unit
                else:
                    price = line.price_unit

                data = self._get_data_from_template(line, price, discount)
                if self.pricelist_id:
                    data.update(self.env['sale.order.line']._get_purchase_price(self.pricelist_id, line.product_id, line.product_uom_id, fields.Date.context_today(self)))
                order_lines += order_line_obj.new(data)

        self.order_line = order_lines
        self._compute_prices_from_template()

        if template.note:
            self.note = template.note
        if template.of_note1:
            self.note1 = template.of_note1
        if template.of_note2:
            self.note2 = template.of_note2
        if template.of_fiscal_position_id and not self.fiscal_position_id:
            self.fiscal_position_id = template.of_fiscal_position_id.id
        if template.of_payment_term_id and not self.payment_term_id:
            self.payment_term_id = template.of_payment_term_id.id

        docs = [(5, 0, 0)]
        for doc in template.of_mail_template_ids:
            docs.append((4, doc.id))
        self.of_mail_template_ids = docs
        if inactif:  #  @TODO : voir si peut être fait avec une fenêtre en javascript.
            self.of_note_insertion = u"Un ou plusieurs articles du modèle ne sont plus utilisés ou ne peuvent être vendus et n'ont donc pas été importés."

class OFSaleConfiguration(models.TransientModel):
    _inherit = 'sale.config.settings'

    of_quote_template = fields.Selection([('add', u'Ajoute les lignes de commande du modèle au devis'), ('replace', u'Remplace les lignes de commande du devis par celles du modèle')],
        string=u"(OF) Modèle de devis", required=True, default='replace',
        help=u"Ceci ne modifie que le fonctionnement des lignes de commandes du modèle."
             u"Les autres informations (ex: position fiscale) ne sont pas impactées par ce paramètre et seront toujours remplacer par ceux du dernier modèle choisi")

    @api.multi
    def set_of_quote_template_defaults(self):
        return self.env['ir.values'].sudo().set_default('sale.config.settings', 'of_quote_template', self.of_quote_template)
