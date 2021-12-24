# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
import odoo.addons.decimal_precision as dp

# Les classes sale.quote.template et sale.quote.line proviennent du module Odoo 11 website_quote/models/sale_quote.py
# La classe sale.order provient du module Odoo 11 website_quote/models/sale_order.py.
# Tout les champs qui ne commencent pas par of_ sont les champs déjà existants dans Odoo 11


class SaleQuoteTemplate(models.Model):
    _name = "sale.quote.template"
    _description = u"Modèle de devis"

    name = fields.Char(u'Nom du modèle', required=True)
    quote_line = fields.One2many(
        'sale.quote.line', 'quote_id', u'Lignes du modèle', copy=True,
        help=u"Une ligne rouge signifie que l'article utilisé ne peut pas être vendu ou qu'il est désactivé.")
    note = fields.Text('Notes')
    active = fields.Boolean(
        default=True,
        help=u"Si archivé, ne sera pas visible dans les listes de modèles de devis sauf "
             u"avec l'utilisation d'un filtre (permet de ne pas supprimer le modèle)")
    of_section_line_ids = fields.One2many(
        'of.sale.quote.template.layout.category', 'quote_id', u'Sections du modèle', copy=True)
    of_mail_template_ids = fields.Many2many('of.mail.template', string="Documents joints")
    of_comment_template1_id = fields.Many2one("base.comment.template", string=u"Utiliser un modèle")
    of_comment_template2_id = fields.Many2one("base.comment.template", string=u"Utiliser un modèle")
    of_note1 = fields.Html('Commentaire du haut')
    of_note2 = fields.Html('Commentaire du bas')
    property_of_fiscal_position_id = fields.Many2one(
        'account.fiscal.position', string="Position fiscale", company_dependent=True)
    of_payment_term_id = fields.Many2one('account.payment.term', string="Conditions de règlement")

    @api.multi
    def copy(self, default=None):
        """ Les lignes de sections et les lignes de commande sont bien dupliquées,
            mais leur champ parent_id et of_layout_category_id continuent de pointer vers
            ceux du modèle original
        """
        res = super(SaleQuoteTemplate, self).copy(default)

        # On modifie le nom du modèle de devis
        res.name += ' (copie)'

        # Pour chaque ligne de section nouvellement créée
        for res_index, res_section in enumerate(res.of_section_line_ids):

            # On récupère son équivalent original
            old_section = self.of_section_line_ids[res_index]

            # On cherche l'index du parent de son équivalent original
            for self_index, self_section in enumerate(self.of_section_line_ids):
                if self_section == old_section.parent_id:

                    # On met à jour avec le parent nouvellement crée
                    new_parent_id = res.of_section_line_ids[self_index]
                    res_section.parent_id = new_parent_id
                    break

        # Pour chaque ligne de commande nouvellement créé ayant une section
        for res_quote_line in res.quote_line.filtered(lambda line: line.of_layout_category_id.id is not False):

            # On récupère la ligne de section pas à jour
            old_section = res_quote_line.of_layout_category_id

            # On cherche son équivalent nouvellement crée
            for self_index, self_section in enumerate(self.of_section_line_ids):
                if self_section == old_section:
                    new_section = res.of_section_line_ids[self_index]

                    # On la met à jour
                    res_quote_line.of_layout_category_id = new_section
                    break
        return res

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

    @api.depends('of_section_line_ids')
    def compute_of_section_line_ids(self):
        quote_layout_category_obj = self.env['of.sale.quote.template.layout.category']
        sequence = 1

        for quote in self:

            # On récupère les sections de premier niveau
            of_layout_category_ids = quote_layout_category_obj.search(
                [('quote_id', '=', quote.id), ('parent_id', '=', False)]).sorted('sequence')
            for index, layout_category in enumerate(of_layout_category_ids):
                layout_category.sequence = sequence
                layout_category.sequence_name = str(index+1)

                # On calcul les séquences des sections enfants
                layout_category.compute_childs_sequence_name()

                # La prochaine section sur ce niveau aura une séquence
                # plus grande que les enfants de la section courante
                number_of_child = len(quote_layout_category_obj.search(
                    [('quote_id', '=', quote.id), ('id', 'child_of', layout_category.id)]))
                sequence = sequence + number_of_child



    @api.multi
    def action_add(self):
        wizard_form = self.env.ref('of_sale_quote_template.of_layout_category_add_wizard_form_view')
        quote_layout_category_obj = self.env['of.sale.quote.template.layout.category']
        quote_layout_category_ids = quote_layout_category_obj.search(
            [('quote_id', '=', self.id), ('parent_id', '=', False)])

        ctx = dict(
            default_type='quote',
            default_order_layout_category_id=False,
            default_quote_id=self.id,
            default_section_number=len(quote_layout_category_ids),
            default_min_section_number=len(quote_layout_category_ids),
        )
        return {
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'of.layout.category.add.wizard',
            'views': [(wizard_form.id, 'form')],
            'view_id': wizard_form.id,
            'target': 'new',
            'context': ctx,
        }


class SaleQuoteLine(models.Model):
    _name = "sale.quote.line"
    _description = u"Lignes de modèle de devis"
    _order = 'sequence, id'

    sequence = fields.Integer(
        u'Sequence', help=u"Permet de donner un ordre à l'affiche des lignes du devis du modèle.", default=10)
    quote_id = fields.Many2one('sale.quote.template', u'Modèle de devis', required=True, ondelete='cascade', index=True)
    name = fields.Text(u'Description', required=True, translate=True)
    product_id = fields.Many2one('product.product', u'Produit', domain=[('sale_ok', '=', True)], required=True)
    layout_category_id = fields.Many2one('sale.layout_category', string='Section')
    of_layout_category_id = fields.Many2one('of.sale.quote.template.layout.category', string='Section')
    price_unit = fields.Float(u'Prix unitaire', required=True, digits=dp.get_precision('Product Price'))
    discount = fields.Float(u'Remise (%)', digits=dp.get_precision('Discount'), default=0.0)
    product_uom_qty = fields.Float(u'Quantité', required=True, digits=dp.get_precision('Product UoS'), default=1)
    product_uom_id = fields.Many2one('product.uom', u'Unité de mesure', required=True)
    of_active = fields.Boolean(u'Article actif', compute="_compute_active")
    of_article_principal = fields.Boolean(
        u"Article principal", help="Cet article est l'article principal de la commande")

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
            if self.env.user.has_group('sale.group_sale_layout'):
                if self.product_id.categ_id.of_layout_id:
                    self.layout_category_id = self.product_id.categ_id.of_layout_id
            domain = {'product_uom_id': [('category_id', '=', self.product_id.uom_id.category_id.id)]}
        return {'domain': domain}

    @api.onchange('product_uom_id')
    def _onchange_product_uom(self):
        """ Modification du prix en fonction de l'udm
        (code Odoo v11)
        """
        if self.product_id and self.product_uom_id:
            self.price_unit = self.product_id.uom_id._compute_price(self.product_id.lst_price, self.product_uom_id)


class OfSaleQuoteTemplateLayoutCategory(models.Model):
    _name = 'of.sale.quote.template.layout.category'
    _description = u"Ligne de sections"
    _order = 'sequence'

    sequence = fields.Integer(required=True, default=10)
    sequence_name = fields.Char(string="Séquence", compute='_compute_sequence_name')
    name = fields.Char(string="Libellé", required=True)
    quote_id = fields.Many2one('sale.quote.template', u'Modèle de devis', ondelete='cascade', index=True)
    parent_id = fields.Many2one('of.sale.quote.template.layout.category', string=u"Parent")
    quote_line_ids = fields.Many2many('sale.quote.line', string=u"Lignes de commande", compute='_compute_product_ids')
    quote_line_count = fields.Integer(string=u"Lignes de commande", compute='_compute_product_ids')
    product_ids = fields.Many2many('product.product', string=u"Composants", compute='_compute_product_ids')

    @api.depends('quote_id')
    def _compute_product_ids(self):
        quote_line_obj = self.env['sale.quote.line']
        for line in self:
            quote_line_ids = quote_line_obj.search(
                [('quote_id', '=', line.quote_id.id), ('of_layout_category_id', '=', line.id)])
            product_ids = quote_line_ids.mapped('product_id')
            line.quote_line_ids = [(6, 0, quote_line_ids.ids)]
            line.quote_line_count = len(quote_line_ids.ids)
            line.product_ids = [(6, 0, product_ids.ids)]

    @api.depends('sequence', 'parent_id')
    def _compute_sequence_name(self):
        quote_layout_category_obj = self.env['of.sale.quote.template.layout.category']

        sequence = 1

        lines = self.search([('id', 'in', self.ids), ('parent_id', '=', False)]).sorted('sequence')

        for index, line in enumerate(lines):
            line.sequence = sequence
            line.sequence_name = str(index+1)

            # On calcule les séquences des sections enfants
            line.compute_childs_sequence_name()

            # La prochaine section sur ce niveau aura une séquence
            # plus grande que les enfants de la section courante
            number_of_child = len(quote_layout_category_obj.search(
                [('quote_id', '=', line.quote_id.id), ('id', 'child_of', line.id)]))

            sequence = sequence + number_of_child

    @api.multi
    def action_wizard_products(self):
        wizard_form = self.env.ref('of_sale_quote_template.of_select_product_wizard_from_view')

        ctx = dict(
            default_quote_id=self.quote_id.id,
            default_quote_template_layout_category_id=self.id,
            default_product_ids=self.product_ids.ids,
        )
        return {
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'of.select.product.wizard',
            'views': [(wizard_form.id, 'form')],
            'view_id': wizard_form.id,
            'target': 'new',
            'context': ctx,
        }

    @api.multi
    def create_sale_order_layout_category(self, order_id, quote_id, parent_id):
        sale_order_layout_category_obj = self.env['of.sale.order.layout.category']
        sale_quote_template_layout_category_obj = self.env['of.sale.quote.template.layout.category']

        for section in self:
            child_sections = sale_quote_template_layout_category_obj.search(
                [('id', 'in', quote_id.of_section_line_ids.ids), ('parent_id', '=', section.id)])
            new_section = sale_order_layout_category_obj.create({
                'name': section.name,
                'parent_id': parent_id.id,
                'order_id': order_id.id,
                'sequence_name': section.sequence_name,
                'quote_section_line_id': section.id,
            })
            child_sections.create_sale_order_layout_category(order_id, quote_id, new_section)

    def compute_childs_sequence_name(self):
        """Fonction récursive de calcul de séquence des sections enfants"""
        sequence = self.sequence + 1

        # On récupère les sections enfants directes
        of_layout_category_ids = self.search(
            [('quote_id', '=', self.quote_id.id), ('parent_id', '=', self.id)]).sorted('sequence')

        for index, layout_category in enumerate(of_layout_category_ids):
            layout_category.sequence = sequence
            layout_category.sequence_name = u"%s.%s" % (self.sequence_name, str(index+1))

            # On calcule les séquences des sections enfants
            layout_category.compute_childs_sequence_name()

            # La prochaine section sur ce niveau aura une séquence plus grande que les enfants de la section courante
            number_of_child = self.search_count(
                [('quote_id', '=', self.quote_id.id), ('id', 'child_of', layout_category.id)])
            sequence = sequence + number_of_child

    @api.multi
    def action_add(self):
        wizard_form = self.env.ref('of_sale_quote_template.of_layout_category_add_wizard_form_view')
        quote_layout_category_obj = self.env['of.sale.quote.template.layout.category']
        quote_layout_category_ids = quote_layout_category_obj.search(
            [('quote_id', '=', self.quote_id.id), ('parent_id', '=', self.id)])

        ctx = dict(
            default_type='quote',
            default_quote_layout_category_id=self.id,
            default_quote_id=self.quote_id.id,
            default_section_number=len(quote_layout_category_ids),
            default_min_section_number=len(quote_layout_category_ids),
        )
        return {
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'of.layout.category.add.wizard',
            'views': [(wizard_form.id, 'form')],
            'view_id': wizard_form.id,
            'target': 'new',
            'context': ctx,
        }

    @api.multi
    def action_duplicate(self):
        wizard_form = self.env.ref('of_sale_quote_template.of_layout_category_duplicate_wizard_form_view')

        ctx = dict(
            default_type='quote',
            default_quote_layout_category_id=self.id,
            default_quote_parent_id=self.parent_id.id or False,
            default_quote_id=self.quote_id.id,
        )
        return {
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'of.layout.category.duplicate.wizard',
            'views': [(wizard_form.id, 'form')],
            'view_id': wizard_form.id,
            'target': 'new',
            'context': ctx,
        }

    @api.multi
    def action_move(self):
        position = 1
        quote_layout_category_obj = self.env['of.sale.quote.template.layout.category']
        quote_layout_category_ids = quote_layout_category_obj.search(
            [('quote_id', '=', self.quote_id.id), ('parent_id', '=', self.parent_id.id or False)]).sorted('sequence')

        for index, layout_category in enumerate(quote_layout_category_ids):
            if self == layout_category:
                position = index + 1

        wizard_form = self.env.ref('of_sale_quote_template.of_layout_category_move_wizard_form_view')
        ctx = dict(
            default_type='quote',
            default_quote_layout_category_id=self.id,
            default_quote_id=self.quote_id.id,
            default_quote_parent_id=self.parent_id.id,
            default_position=position,
            default_previous_position=position,
        )
        return {
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'of.layout.category.move.wizard',
            'views': [(wizard_form.id, 'form')],
            'view_id': wizard_form.id,
            'target': 'new',
            'context': ctx,
        }

    def duplicate_childs(self, parent_id):
        """Fonction récursive de duplication des sections enfants"""

        # On récupère les enfants directs
        quote_layout_category_ids = self.search([('parent_id', '=', self.id)])

        # Pour chaque enfant
        for layout_category_id in quote_layout_category_ids:
            # On le duplique
            new_layout_category_id = layout_category_id.copy({
                'parent_id': parent_id.id
            })

            # On duplique les lignes de commandes associées
            for line in layout_category_id.quote_line_ids:
                line.copy({
                    'of_layout_category_id': new_layout_category_id.id,
                })

            # On traite les enfants
            layout_category_id.duplicate_childs(new_layout_category_id)


class OfSaleOrderLayoutCategory(models.Model):
    _name = 'of.sale.order.layout.category'
    _description = u"Ligne de sections"
    _order = 'sequence'

    @api.model
    def _get_domain_parent_id(self):
        order = self.env['sale.order'].browse(self._context.get('default_order_id'))
        res = [('id', 'in', order.of_layout_category_ids.ids)]
        return res

    sequence = fields.Integer(required=True, default=10)
    sequence_name = fields.Char(string=u"Séquence")
    name = fields.Char(string=u"Libellé", required=True)
    parent_id = fields.Many2one(
        'of.sale.order.layout.category', string=u"Parent", domain=lambda self: self._get_domain_parent_id())
    quote_section_line_id = fields.Many2one('of.sale.quote.template.layout.category', string=u"Ligne d'origine")
    order_id = fields.Many2one('sale.order', string=u"Bon de commande", ondelete='cascade')
    cout = fields.Float(string=u"Coût", digits=dp.get_precision('Product Price'), compute='_compute_product_ids')
    prix_vente = fields.Float(
        string=u"Prix de vente", digits=dp.get_precision('Product Price'), compute='_compute_product_ids')
    pc_prix_vente = fields.Float(
        string=u"% Prix de vente", digits=dp.get_precision('Product Price'), compute='_compute_product_ids')
    order_line_ids = fields.Many2many('sale.order.line', string=u"Lignes de commande", compute='_compute_product_ids')
    order_line_count = fields.Integer(string=u"Lignes de commande", compute='_compute_product_ids')
    product_ids = fields.Many2many('product.product', string=u"Articles", compute='_compute_product_ids')

    @api.depends('order_id')
    def _compute_product_ids(self):
        order_line_obj = self.env['sale.order.line']
        for line in self:
            order_lines = order_line_obj.search(
                [('order_id', '=', line.order_id.id), ('of_layout_category_id', '=', line.id)])
            product_ids = order_lines.mapped('product_id')
            line.order_line_ids = [(6, 0, order_lines.ids)]
            line.order_line_count = len(order_lines.ids)
            line.product_ids = [(6, 0, product_ids.ids)]
            line.cout = sum(order_lines.mapped('purchase_price'))
            line.prix_vente = sum(order_lines.mapped('price_unit'))
            if line.order_id.amount_untaxed:
                line.pc_prix_vente = (line.prix_vente / line.order_id.amount_untaxed) * 100

    @api.multi
    def action_wizard_products(self):
        wizard_form = self.env.ref('of_sale_quote_template.of_select_order_product_wizard_from_view')

        ctx = dict(
            default_type='order',
            default_order_id=self.order_id.id,
            default_order_layout_category_id=self.id,
            default_product_ids=self.product_ids.ids,
        )
        return {
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'of.select.order.product.wizard',
            'views': [(wizard_form.id, 'form')],
            'view_id': wizard_form.id,
            'target': 'new',
            'context': ctx,
        }

    @api.multi
    def action_add(self):
        wizard_form = self.env.ref('of_sale_quote_template.of_layout_category_add_wizard_form_view')
        order_layout_category_obj = self.env['of.sale.order.layout.category']
        order_layout_category_ids = order_layout_category_obj.search(
            [('order_id', '=', self.order_id.id), ('parent_id', '=', self.id)])

        ctx = dict(
            default_type='order',
            default_order_layout_category_id=self.id,
            default_order_id=self.order_id.id,
            default_section_number=len(order_layout_category_ids),
            default_min_section_number=len(order_layout_category_ids),
        )
        return {
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'of.layout.category.add.wizard',
            'views': [(wizard_form.id, 'form')],
            'view_id': wizard_form.id,
            'target': 'new',
            'context': ctx,
        }

    @api.multi
    def action_duplicate(self):
        wizard_form = self.env.ref('of_sale_quote_template.of_layout_category_duplicate_wizard_form_view')

        ctx = dict(
            default_type='order',
            default_order_layout_category_id=self.id,
            default_order_parent_id=self.parent_id.id or False,
            default_order_id=self.order_id.id,
        )
        return {
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'of.layout.category.duplicate.wizard',
            'views': [(wizard_form.id, 'form')],
            'view_id': wizard_form.id,
            'target': 'new',
            'context': ctx,
        }

    @api.multi
    def action_move(self):
        position = 1
        order_layout_category_obj = self.env['of.sale.order.layout.category']
        order_layout_category_ids = order_layout_category_obj.search(
            [('order_id', '=', self.order_id.id), ('parent_id', '=', self.parent_id.id or False)]).sorted('sequence')

        for index, layout_category in enumerate(order_layout_category_ids):
            if self == layout_category:
                position = index + 1

        wizard_form = self.env.ref('of_sale_quote_template.of_layout_category_move_wizard_form_view')
        ctx = dict(
            default_order_layout_category_id=self.id,
            default_order_id=self.order_id.id,
            default_order_parent_id=self.parent_id.id,
            default_position=position,
            default_previous_position=position,
        )
        return {
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'of.layout.category.move.wizard',
            'views': [(wizard_form.id, 'form')],
            'view_id': wizard_form.id,
            'target': 'new',
            'context': ctx,
        }

    def duplicate_childs(self, parent_id):
        """Fonction récursive de duplication des sections enfants"""

        # On récupère les enfants directs
        sale_order_layout_category_ids = self.search([('parent_id', '=', self.id)])

        # Pour chaque enfant
        for layout_category_id in sale_order_layout_category_ids:
            # On le duplique
            new_layout_category_id = layout_category_id.copy({
                'parent_id': parent_id.id
            })

            # On duplique les lignes de commandes associées
            for line in layout_category_id.order_line_ids:
                line.copy({
                    'of_layout_category_id': new_layout_category_id.id,
                })

            # On traite les enfants
            layout_category_id.duplicate_childs(new_layout_category_id)

    def compute_childs_sequence_name(self):
        """Fonction récursive de calcul de séquence des sections enfants"""
        sequence = self.sequence + 1

        # On récupère les sections enfants directes
        of_layout_category_ids = self.search(
            [('order_id', '=', self.order_id.id), ('parent_id', '=', self.id)]).sorted('sequence')

        for index, layout_category in enumerate(of_layout_category_ids):
            layout_category.sequence = sequence
            layout_category.sequence_name = u"%s.%s" % (self.sequence_name, str(index+1))

            # On calcule les séquences des sections enfants
            layout_category.compute_childs_sequence_name()

            # La prochaine section sur ce niveau aura une séquence plus grande que les enfants de la section courante
            number_of_child = self.search_count(
                [('order_id', '=', self.order_id.id), ('id', 'child_of', layout_category.id)])
            sequence = sequence + number_of_child


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    of_template_id = fields.Many2one(
        'sale.quote.template', string=u'Modèle de devis', readonly=True,
        states={'draft': [('readonly', False)], 'sent': [('readonly', False)]})
    of_note_insertion = fields.Text(
        string=u"Note d'insertion", help=u"Cette note disparaitra lorsque le devis sera sauvegardé.",)
    of_layout_category_template_id = fields.Many2one(
        'of.sale.layout.category.template', string=u"Modèle de liste de section")
    of_layout_category_ids = fields.One2many('of.sale.order.layout.category', 'order_id', string=u"Liste de section", copy=True)

    # Onchange nécessaire, car lors de la suppression d'une ligne de section, cette ligne de section est toujours
    # renseignée dans les lignes de commande. Du coup, Odoo bloque sur la sauvegarde.
    # Le ondelete = set null ne fonctionne pas sur un même formulaire.
    @api.onchange('of_layout_category_ids')
    def onchange_of_layout_category_ids(self):
        order_id = self._origin.id
        order_lines = self.env['sale.order.line'].search(
            [('order_id', '=', order_id),
             ('of_layout_category_id', '!=', False),
             ('of_layout_category_id', 'not in', self.of_layout_category_ids.ids)])
        order_lines.update({
            'of_layout_category_id': False,
        })

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

    @api.multi
    def copy(self, default=None):
        """ Les lignes de sections et les lignes de commande sont bien dupliquées,
            mais leur champ parent_id et of_layout_category_id continuent de pointer vers
            ceux du modèle original
        """
        res = super(SaleOrder, self).copy(default)

        # Pour chaque ligne de section nouvellement créée
        for res_index, res_section in enumerate(res.of_layout_category_ids):

            # On récupère son équivalent original
            old_section = self.of_layout_category_ids[res_index]

            # On cherche l'index du parent de son équivalent original
            for self_index, self_section in enumerate(self.of_layout_category_ids):
                if self_section == old_section.parent_id:

                    # On met à jour avec le parent nouvellement crée
                    new_parent_id = res.of_layout_category_ids[self_index]
                    res_section.parent_id = new_parent_id
                    break

        # Pour chaque ligne de commande nouvellement créé ayant une section
        for res_quote_line in res.order_line.filtered(lambda line: line.of_layout_category_id.id is not False):

            # On récupère la ligne de section pas à jour
            old_section = res_quote_line.of_layout_category_id

            # On cherche son équivalent nouvellement crée
            for self_index, self_section in enumerate(self.of_layout_category_ids):
                if self_section == old_section:
                    new_section = res.of_layout_category_ids[self_index]

                    # On la met à jour
                    res_quote_line.of_layout_category_id = new_section
                    break
        return res

    def _get_data_from_template(self, line, price, discount):
        """ Permet de renvoyer les informations nécessaires à la création de ligne du bon de commande
        (à surcharger pour ajouter des informations)
        """
        data = {
            'name': line.name,
            'price_unit': price,
            'discount': 100 - ((100 - discount) * (100 - line.discount) / 100),
            'product_uom_qty': line.product_uom_qty,
            'product_id': line.product_id.id,
            'product_uom': line.product_uom_id.id,
            'of_article_principal': line.of_article_principal,
            'of_product_forbidden_discount': line.product_id.of_forbidden_discount,
            'of_quote_line_id': line,
            'layout_category_id': line.layout_category_id,
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
                new_line = order_line_obj._new_line_for_template(data)

                new_line.product_id_change()

                if self.env.user.has_group('sale.group_sale_layout'):
                    if not new_line.layout_category_id and new_line.product_id.categ_id.of_layout_id:
                        new_line.layout_category_id = new_line.product_id.categ_id.of_layout_id
                order_lines += new_line

        self.order_line = order_lines
        self._compute_prices_from_template()

        if template.note:
            self.note = template.note
        if template.of_note1:
            self.note1 = template.of_note1
        if template.of_note2:
            self.note2 = template.of_note2
        if template.property_of_fiscal_position_id and not self.fiscal_position_id:
            self.fiscal_position_id = template.property_of_fiscal_position_id.id
        if template.of_payment_term_id and not self.payment_term_id:
            self.payment_term_id = template.of_payment_term_id.id

        docs = [(5, 0, 0)]
        for doc in template.of_mail_template_ids:
            docs.append((4, doc.id))
        self.of_mail_template_ids = docs
        if inactif:  # @TODO : voir si peut être fait avec une fenêtre en javascript.
            self.of_note_insertion = u"Un ou plusieurs articles du modèle ne sont plus utilisés ou ne peuvent être vendus et n'ont donc pas été importés."

    def compute_of_layout_category_ids(self):
        order_layout_category_obj = self.env['of.sale.order.layout.category']
        sequence = 1

        for order in self:

            # On récupère les sections de premier niveau
            of_layout_category_ids = order_layout_category_obj.search(
                [('order_id', '=', order.id), ('parent_id', '=', False)]).sorted('sequence')
            for index, layout_category in enumerate(of_layout_category_ids):
                layout_category.sequence = sequence
                layout_category.sequence_name = str(index+1)

                # On calcul les séquences des sections enfants
                layout_category.compute_childs_sequence_name()

                # La prochaine section sur ce niveau aura une séquence
                # plus grande que les enfants de la section courante
                number_of_child = len(order_layout_category_obj.search(
                    [('order_id', '=', order.id), ('id', 'child_of', layout_category.id)]))
                sequence = sequence + number_of_child

    def load_sections(self):
        template = self.of_template_id.with_context(lang=self.partner_id.lang)
        order_line_obj = self.env['sale.order.line']
        quote_line_obj = self.env['sale.quote.line']
        order_layout_category_obj = self.env['of.sale.order.layout.category']
        template_layout_category_obj = self.env['of.sale.quote.template.layout.category']

        # On parcourt les sections de 1er niveau du modèle
        for section in template_layout_category_obj.search(
                [('id', 'in', template.of_section_line_ids.ids), ('parent_id', '=', False)]):

            # On récupère les enfants directs
            child_sections = template_layout_category_obj.search(
                [('id', 'in', template.of_section_line_ids.ids), ('parent_id', '=', section.id)])

            # On crée les sections parentes
            new_section = order_layout_category_obj.create({
                'name': section.name,
                'order_id': self.id,
                'sequence_name': section.sequence_name,
                'quote_section_line_id': section.id,
            })
            # On crée récursivement les sections enfants
            child_sections.create_sale_order_layout_category(self, template, new_section)

        # On récupère les nouvelles sections
        new_sections = order_layout_category_obj.search([('order_id', '=', self.id)])

        # On crée les liens de parenté
        for section in new_sections:
            quote_line_ids = section.quote_section_line_id and section.quote_section_line_id.quote_line_ids
            if quote_line_ids:
                order_lines = order_line_obj.search(
                    [('order_id', '=', section.order_id.id), ('of_quote_line_id', 'in', quote_line_ids.ids)])
                order_lines.write({
                    'of_layout_category_id': section.id,
                })

        # On compute les noms de séquence
        self.compute_of_layout_category_ids()

    @api.multi
    def action_add(self):
        wizard_form = self.env.ref('of_sale_quote_template.of_layout_category_add_wizard_form_view')
        order_layout_category_obj = self.env['of.sale.order.layout.category']
        order_layout_category_ids = order_layout_category_obj.search(
            [('order_id', '=', self.id), ('parent_id', '=', False)])

        ctx = dict(
            default_type='order',
            default_order_layout_category_id=False,
            default_order_id=self.id,
            default_section_number=len(order_layout_category_ids),
            default_min_section_number=len(order_layout_category_ids),
        )
        return {
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'of.layout.category.add.wizard',
            'views': [(wizard_form.id, 'form')],
            'view_id': wizard_form.id,
            'target': 'new',
            'context': ctx,
        }

    @api.multi
    def order_lines_layouted(self):
        """ Surcharge de la fonction de mise en page des lignes de commande groupées par section"""
        self.ensure_one()
        report_pages = [[]]

        # Si les sections avancées sont configurées
        if self.user_has_groups('of_sale_quote_template.group_of_advanced_sale_layout_category') \
                and self.of_layout_category_ids:
            new_dict = {}
            of_layout_category_ids_sorted = self.of_layout_category_ids.sorted(key=lambda x: x.sequence)

            # On créé une liste de lignes de commande pour chaque section avancée, y compris celles vides
            for index, layout_category in enumerate(of_layout_category_ids_sorted):
                new_dict[index] = {
                    'layout_category': layout_category,
                    'order_lines': self.order_line.filtered(
                        lambda line: line.of_layout_category_id.id == layout_category.id),
                }

            # On récupère les lignes de commande qui n'ont pas de lignes de section associées
            lines_without_layout_category = self.order_line.filtered(
                lambda line: line.of_layout_category_id.id is False)
            if lines_without_layout_category:
                new_dict[-1] = {
                    'layout_category': False,
                    'order_lines': lines_without_layout_category,
                }

            # On remplit la liste de liste qui sera passée au rapport
            for key, values in new_dict.items():
                category = values['layout_category']
                lines = values['order_lines']

                # If last added category induced a pagebreak, this one will be on a new page
                if report_pages[-1] and report_pages[-1][-1]['pagebreak']:
                    report_pages.append([])
                # Append category to current report page
                report_pages[-1].append({
                    'name': category and category.name or _('Uncategorized'),
                    'subtotal': category and category.prix_vente,
                    'pagebreak': False,
                    'lines': list(lines)
                })

        # Si les sections avancées ne sont pas configurées, on appelle le super()
        else:
            report_pages = super(SaleOrder, self).order_lines_layouted()

        return report_pages


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    of_layout_category_id = fields.Many2one('of.sale.order.layout.category', string=u"Ligne de section")
    of_quote_line_id = fields.Many2one('sale.quote.line', string=u"Ligne de modèle de devis")

    @api.model
    def _new_line_for_template(self, data):
        """
        Fonction à surcharger pour faire appel à des fonctions avant d'ajouter la nouvelle ligne au bon de commande
        :param data: dictionnaire de valeurs
        :return: sale.order.line(<newId>)
        """
        return self.new(data)


class OFSaleConfiguration(models.TransientModel):
    _inherit = 'sale.config.settings'

    of_quote_template = fields.Selection(
        [('add', u'Ajoute les lignes de commande du modèle au devis'),
         ('replace', u'Remplace les lignes de commande du devis par celles du modèle')],
        string=u"(OF) Modèle de devis", required=True, default='replace',
        help=u"Ceci ne modifie que le fonctionnement des lignes de commandes du modèle."
             u"Les autres informations (ex: position fiscale) ne sont pas impactées par ce paramètre et seront "
             u"toujours remplacées par celles du dernier modèle choisi")

    @api.multi
    def set_of_quote_template_defaults(self):
        return self.env['ir.values'].sudo().set_default(
            'sale.config.settings', 'of_quote_template', self.of_quote_template)
