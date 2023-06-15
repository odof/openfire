# -*- coding: utf-8 -*-

from itertools import groupby
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
    of_sale_quote_tmpl_activity_ids = fields.One2many(
        comodel_name='of.sale.quote.tmpl.activity', inverse_name='template_id', string='Activities')

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
                layout_category.sequence_name = str(index + 1)

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

    @api.multi
    def reload_description_on_template_lines(self):
        for record in self:
            for line in record.quote_line:
                if line.product_id:
                    line.write({'name': line.product_id.quote_template_sale_description()})


class SaleQuoteLine(models.Model):
    _name = "sale.quote.line"
    _description = u"Lignes de modèle de devis"
    _order = 'layout_category_id, sequence, id'

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
        result = {}
        domain = {'product_uom_id': [('category_id', 'ilike', '')]}
        if self.product_id:
            warning = {}
            if self.product_id.sale_line_warn != 'no-message':
                title = _("Warning for %s") % self.product_id.name
                message = self.product_id.sale_line_warn_msg
                warning['title'] = title
                warning['message'] = message
                result = {'warning': warning}
                if self.product_id.sale_line_warn == 'block':
                    # rollback
                    self.product_id = self._origin and self._origin.product_id or False
                    return result

            name = self.product_id.quote_template_sale_description()
            self.name = name
            self.price_unit = self.product_id.lst_price
            self.product_uom_id = self.product_id.uom_id.id
            if self.env.user.has_group('sale.group_sale_layout'):
                if self.product_id.of_layout_category_id:
                    self.layout_category_id = self.product_id.of_layout_category_id
                elif self.product_id.categ_id.of_layout_id:
                    self.layout_category_id = self.product_id.categ_id.of_layout_id
            domain = {'product_uom_id': [('category_id', '=', self.product_id.uom_id.category_id.id)]}
        result['domain'] = domain
        return result

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
    depth = fields.Integer(string=u"Profondeur", compute='_compute_depth')
    quote_id = fields.Many2one('sale.quote.template', u'Modèle de devis', ondelete='cascade', index=True)
    parent_id = fields.Many2one('of.sale.quote.template.layout.category', string=u"Parent")
    quote_line_ids = fields.One2many(
        comodel_name='sale.quote.line', inverse_name='of_layout_category_id', string=u"Lignes de commande")
    quote_line_count = fields.Integer(string=u"Lignes de commande", compute='_compute_quote_line_count')

    @api.multi
    def name_get(self):
        res = []
        for category in self:
            if category.parent_id:
                name = " %s / %s" % (category.parent_id.name_get_recursive(), category.name)
            else:
                name = category.name
            res.append((category.id, name))

        return res

    def name_get_recursive(self):
        if self.parent_id:
            name = " %s / %s" % (self.parent_id.name_get_recursive(), self.name)
        else:
            name = self.name
        return name

    @api.depends('parent_id')
    def _compute_depth(self):
        for category in self.sorted('sequence'):
            if category.parent_id:
                category.depth = 1 + category.parent_id.depth
            else:
                category.depth = 0

    @api.depends('quote_id')
    def _compute_quote_line_count(self):
        quote_line_obj = self.env['sale.quote.line']
        for line in self:
            quote_line = quote_line_obj.search(
                [('quote_id', '=', line.quote_id.id), ('of_layout_category_id', 'child_of', line.id)])
            line.quote_line_count = len(quote_line.ids)

    @api.depends('sequence', 'parent_id')
    def _compute_sequence_name(self):
        quote_layout_category_obj = self.env['of.sale.quote.template.layout.category']

        sequence = 1

        lines = self.search([('id', 'in', self.ids), ('parent_id', '=', False)]).sorted('sequence')

        for index, line in enumerate(lines):
            line.sequence = sequence
            line.sequence_name = str(index + 1)

            # On calcule les séquences des sections enfants
            line.compute_childs_sequence_name()

            # La prochaine section sur ce niveau aura une séquence
            # plus grande que les enfants de la section courante
            number_of_child = len(quote_layout_category_obj.search(
                [('quote_id', '=', line.quote_id.id), ('id', 'child_of', line.id)]))

            sequence = sequence + number_of_child

    @api.multi
    def write(self, vals):
        res = super(OfSaleQuoteTemplateLayoutCategory, self).write(vals)
        # Si on modifie un parent sans passer par le wizard de déplacement, on met à jour les séquences
        if vals.get('parent_id'):
            self.mapped('quote_id').compute_of_section_line_ids()
        return res

    @api.multi
    def action_wizard_products(self):
        wizard_form = self.env.ref('of_sale_quote_template.view_of_sale_quote_template_layout_category_form')

        ctx = dict(
            default_quote_id=self.quote_id.id,
            default_of_layout_category_id=self.id,
        )
        return {
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'res_model': 'of.sale.quote.template.layout.category',
            'res_id': self.id,
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
            layout_category.sequence_name = u"%s.%s" % (self.sequence_name, str(index + 1))

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
        return [('id', 'in', order.of_layout_category_ids.ids)]

    sequence = fields.Integer(required=True, default=10)
    sequence_name = fields.Char(string=u"Séquence")
    name = fields.Char(string=u"Libellé", required=True)
    depth = fields.Integer(string=u"Profondeur", compute='_compute_depth')
    parent_id = fields.Many2one(
        comodel_name='of.sale.order.layout.category',
        string=u"Parent", domain=lambda self: self._get_domain_parent_id(), ondelete='cascade')
    quote_section_line_id = fields.Many2one(
        comodel_name='of.sale.quote.template.layout.category', string=u"Ligne d'origine")
    order_id = fields.Many2one(comodel_name='sale.order', string=u"Bon de commande", ondelete='cascade')
    state = fields.Selection(
        relation=[('draft', u"Estimation"),
                  ('sent', u"Devis"),
                  ('sale', u"Bon de commande"),
                  ('done', u"Vérrouillé"),
                  ('cancel', u"Annulé")], string=u"Etat", related='order_id.state')
    currency_id = fields.Many2one('res.currency', related='order_id.currency_id', store=True, readonly=True)
    cout = fields.Float(
        string=u"Coût", digits=dp.get_precision('Product Price'), compute='_compute_order_line_ids')
    prix_vente = fields.Float(
        string=u"Prix de vente", digits=dp.get_precision('Product Price'),
        compute='_compute_order_line_ids')
    pc_prix_vente = fields.Float(
        string=u"% Prix de vente", digits=dp.get_precision('Product Price'),
        compute='_compute_order_line_ids')
    # product_ids = fields.Many2many(comodel_name='product.product', string=u"Articles", compute='_compute_product_ids')

    # Lignes de commande qui comptent également les lignes de commande des sections enfants
    order_line_count = fields.Integer(string=u"Lignes de commande", compute='_compute_order_line_ids')
    order_line_ids = fields.Many2many(
        comodel_name='sale.order.line', string=u"Lignes de commande", compute='_compute_order_line_ids')
    invoice_status = fields.Selection(
        selection=[('no', u"Rien à facturer"),
                   ('to invoice', u"À facturer"),
                   ('partially invoiced', u"Partiellement facturé"),
                   ('invoiced', u"Entièrement facturé")],
        compute='_compute_invoice_status', string=u"État de facturation", readonly=True, default='no')

    # Lignes de commande qui ne comptent que les lignes de commande de la section
    order_line_without_child_count = fields.Integer(
        string=u"Lignes de commande", compute='_compute_order_line_without_child_ids')
    order_line_without_child_ids = fields.One2many(
        comodel_name='sale.order.line', inverse_name='of_layout_category_id', string=u"Lignes de commande")
    invoice_status_without_child = fields.Selection(
        selection=[('no', u"Rien à facturer"),
                   ('to invoice', u"À facturer"),
                   ('partially invoiced', u"Partiellement facturé"),
                   ('invoiced', u"Entièrement facturé")],
        compute='_compute_invoice_status_without_child', string=u"État de facturation", readonly=True, default='no')

    @api.multi
    def name_get(self):
        res = []
        for category in self:
            if category.parent_id:
                name = " %s - %s / %s" % (
                    category.sequence_name, category.parent_id.name_get_recursive(), category.name)
            else:
                name = " %s - %s" % (category.sequence_name, category.name)
            res.append((category.id, name))

        return res

    def name_get_recursive(self):
        if self.parent_id:
            name = " %s / %s" % (self.parent_id.name_get_recursive(), self.name)
        else:
            name = self.name
        return name

    @api.depends('parent_id')
    def _compute_depth(self):
        for category in self.sorted('sequence'):
            if category.parent_id:
                category.depth = 1 + category.parent_id.depth
            else:
                category.depth = 0

    @api.depends('order_id')
    def _compute_order_line_ids(self):
        order_line_obj = self.env['sale.order.line']
        for line in self:
            # On prend toutes les lignes enfants, notamment pour le calcul du cout, de prix_vente, pc_prix_vente
            order_lines = order_line_obj.search(
                [('order_id', '=', line.order_id.id), ('of_layout_category_id', 'child_of', line.id)])
            line.order_line_ids = order_lines.ids
            line.order_line_count = len(order_lines)
            line.prix_vente = sum(order_lines.mapped('price_subtotal'))
            if line.order_id.amount_untaxed:
                line.pc_prix_vente = (line.prix_vente / line.order_id.amount_untaxed) * 100
            line.cout = sum(order_lines.mapped(lambda l: l.purchase_price * l.product_uom_qty))

    @api.depends('order_line_ids.invoice_status', 'order_id.state')
    def _compute_invoice_status(self):
        for category in self:
            line_invoice_status = category.order_line_ids.mapped('invoice_status')

            if category.order_id.state not in ('sale', 'done'):
                category.invoice_status = 'no'
            elif not line_invoice_status:
                category.invoice_status = 'invoiced'
            elif all(invoice_status == 'to invoice' for invoice_status in line_invoice_status):
                category.invoice_status = 'to invoice'
            elif all(invoice_status == 'invoiced' for invoice_status in line_invoice_status):
                category.invoice_status = 'invoiced'
            elif any(invoice_status == 'invoiced' for invoice_status in line_invoice_status):
                category.invoice_status = 'partially invoiced'
            else:
                category.invoice_status = 'no'

    @api.depends('order_line_without_child_ids')
    def _compute_order_line_without_child_ids(self):
        for category in self:
            category.order_line_without_child_count = len(category.order_line_without_child_ids)

    @api.depends('order_line_without_child_ids.invoice_status', 'order_id.state')
    def _compute_invoice_status_without_child(self):
        for category in self:
            line_invoice_status = category.order_line_without_child_ids.mapped('invoice_status')

            if category.order_id.state not in ('sale', 'done'):
                category.invoice_status_without_child = 'no'
            elif not line_invoice_status:
                category.invoice_status_without_child = 'invoiced'
            elif all(invoice_status == 'to invoice' for invoice_status in line_invoice_status):
                category.invoice_status_without_child = 'to invoice'
            elif all(invoice_status == 'invoiced' for invoice_status in line_invoice_status):
                category.invoice_status_without_child = 'invoiced'
            elif any(invoice_status == 'invoiced' for invoice_status in line_invoice_status):
                category.invoice_status_without_child = 'partially invoiced'
            else:
                category.invoice_status_without_child = 'no'

    @api.multi
    def write(self, vals):
        res = super(OfSaleOrderLayoutCategory, self).write(vals)
        # Si on modifie un parent sans passer par le wizard de déplacement, on met à jour les séquences
        if vals.get('parent_id'):
            self.mapped('order_id').compute_of_layout_category_ids()
        return res

    @api.multi
    def action_wizard_order_lines(self):
        wizard_form = self.env.ref('of_sale_quote_template.view_of_sale_order_layout_category_form')

        ctx = dict(
            default_order_id=self.order_id.id,
            default_order_layout_category_id=self.id,
        )
        return {
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'res_model': 'of.sale.order.layout.category',
            'res_id': self.id,
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
            default_type='order',
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
            layout_category.sequence_name = u"%s.%s" % (self.sequence_name, str(index + 1))

            # On calcule les séquences des sections enfants
            layout_category.compute_childs_sequence_name()

            # La prochaine section sur ce niveau aura une séquence plus grande que les enfants de la section courante
            number_of_child = self.search_count(
                [('order_id', '=', self.order_id.id), ('id', 'child_of', layout_category.id)])
            sequence = sequence + number_of_child

    def get_color(self, model):
        """Prend la couleur dans la configuration et l'éclaircit en fonction de la profondeur d'une section"""
        model_obj = self.env[model]
        hex_color = model_obj.get_color_section()
        rgb_hex = [hex_color[x:x + 2] for x in [1, 3, 5]]
        new_rgb_int = [int(hex_value, 16) + ((self.depth - 2) * 35) for hex_value in rgb_hex]
        new_rgb_int = [min([255, max([0, i])]) for i in new_rgb_int]  # make sure new values are between 0 and 255
        # hex() produces "0x88", we want just "88"
        return "#" + "".join([hex(i)[2:] for i in new_rgb_int])


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    of_template_id = fields.Many2one(
        'sale.quote.template', string=u'Modèle de devis', readonly=True,
        states={'draft': [('readonly', False)], 'sent': [('readonly', False)]})
    of_note_insertion = fields.Text(
        string=u"Note d'insertion", help=u"Cette note disparaitra lorsque le devis sera sauvegardé.",)
    of_layout_category_ids = fields.One2many(
        'of.sale.order.layout.category', 'order_id', string=u"Liste de section", copy=True)
    of_layout_category_invoice_status = fields.Selection(
        selection=[('no', u"Rien à facturer"),
                   ('to invoice', u"À facturer"),
                   ('partially invoiced', u"Partiellement facturé"),
                   ('invoiced', u"Entièrement facturé")],
        compute='_compute_of_layout_category_invoice_status', string=u"État de facturation des lignes de section",
        readonly=True)
    of_price_printing = fields.Selection(selection_add=[
        ('layout_category', "Prix par sections"),
        ('layout_category_with_products', "Prix par sections avec articles"),
        ('summary', u"Récapitulatif des prix par sections"),
    ])

    # Onchange nécessaire, car lors de la suppression d'une ligne de section, les lignes de commande associées ne sont
    # pas supprimé. Du coup, Odoo bloque sur la sauvegarde.
    # Le ondelete = cascade ne fonctionne pas sur un même formulaire.
    @api.onchange('of_layout_category_ids')
    def onchange_of_layout_category_ids(self):
        order_lines = []
        order = self.env['sale.order'].browse(self._origin.id)
        order_line_to_delete = order.of_layout_category_ids.filtered(
            lambda lc: lc.id not in self.of_layout_category_ids.ids).mapped('order_line_ids')
        for ol in order.order_line.filtered(lambda ol: ol.id not in order_line_to_delete.ids):
            if isinstance(ol.id, int):
                order_lines.append((4, ol.id))
        self.order_line = order_lines

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
        if not self.partner_id and self.of_template_id.quote_line:
            self.of_template_id = False
            warning = {
                'title': (_("Warning!")),
                'message': (_("You must fill in the Customer field to go further."))
            }
            return {'warning': warning}
        template = self.of_template_id.with_context(lang=self.partner_id.lang)
        order_line_obj = self.env['sale.order.line']
        of_crm_activity_obj = self.env['of.crm.activity']

        regime = self.env['ir.values'].get_default('sale.config.settings', 'of_quote_template')
        order_lines = self.order_line if regime == 'add' else order_line_obj
        inactif = False  # Permet de savoir si il y a un article inactif
        product_obj = self.env['product.product']
        product_warn_ids = product_obj
        product_block_ids = product_obj

        new_lines = self.order_line.filtered(lambda l: not l.sequence)
        for line in new_lines:
            if line.layout_category_id:
                layout_new_line = line.layout_category_id
                max_sequence = max(self.order_line.filtered(
                    lambda l: l.layout_category_id.id == layout_new_line.id).mapped('sequence'))
            else:
                max_sequence = max(self.order_line.filtered(
                    lambda l: not l.layout_category_id).mapped('sequence'))
            line.sequence = max_sequence + 1

        for line in template.quote_line:
            discount = 0
            if not line.of_active:
                inactif = True
            else:
                if self.pricelist_id:
                    price = self.pricelist_id.with_context(uom=line.product_uom_id.id).get_product_price(
                        line.product_id, 1, False)
                    if self.pricelist_id.discount_policy == 'without_discount' and line.price_unit:
                        discount = (line.price_unit - price) / line.price_unit * 100
                        price = line.price_unit
                else:
                    price = line.price_unit

                if line.product_id.sale_line_warn == 'block':
                    product_block_ids |= line.product_id
                else:
                    if line.product_id.sale_line_warn == 'warning':
                        product_warn_ids |= line.product_id
                    data = self._get_data_from_template(line, price, discount)
                    if self.pricelist_id:
                        data.update(order_line_obj._get_purchase_price(
                            self.pricelist_id, line.product_id, line.product_uom_id, fields.Date.context_today(self)))
                        data.update(order_line_obj._get_of_seller_price(
                            self.pricelist_id, line.product_id, line.product_uom_id, fields.Date.context_today(self)))
                    new_line = order_line_obj._new_line_for_template(data)
                    if self.env.user.has_group('sale.group_sale_layout'):
                        if not new_line.layout_category_id and new_line.product_id.categ_id.of_layout_id:
                            new_line.layout_category_id = new_line.product_id.categ_id.of_layout_id

                    if self.order_line.filtered(lambda l: l.layout_category_id.id == line.layout_category_id.id):
                        new_line.sequence = max(self.order_line.filtered(
                            lambda l: l.layout_category_id.id == line.layout_category_id.id).mapped('sequence')) + 1
                    else:
                        new_line.sequence = 0

                    order_lines += new_line

        self.order_line = order_lines
        self._compute_prices_from_template()

        # add activities from the template
        if template.of_sale_quote_tmpl_activity_ids:
            crm_activities = of_crm_activity_obj
            for activity in template.of_sale_quote_tmpl_activity_ids:
                crm_activity = of_crm_activity_obj.new(activity._get_sale_activity_values(self))
                crm_activities |= crm_activity
            self.of_crm_activity_ids = crm_activities

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
            self.of_note_insertion = u"Un ou plusieurs articles du modèle ne sont plus utilisés ou ne peuvent " \
                u"être vendus et n'ont donc pas été importés."
        title = u""
        warning = {}
        if product_warn_ids and product_block_ids:
            title = u"Avertissement(s) et message(s) bloquant(s)"
        elif product_warn_ids:
            title = u"Avertissement(s)"
        elif product_block_ids:
            title = u"Message(s) bloquant(s)"
        if title:
            warning['title'] = title
            message = u""
            if product_warn_ids:
                message += u"Article(s) ayant un avertissement:\n"
                for product_warn in product_warn_ids:
                    message += u" - %s : %s\n" % (product_warn.name, product_warn.sale_line_warn_msg)
            if product_block_ids:
                message += u"Article(s) ayant un message bloquant (non ajoutés au devis):"
                for product_block in product_block_ids:
                    message += u"\n - %s : %s" % (product_block.name, product_block.sale_line_warn_msg)
            warning['message'] = message
            return {'warning': warning}
        return

    def compute_of_layout_category_ids(self):
        order_layout_category_obj = self.env['of.sale.order.layout.category']
        sequence = 1

        for order in self:

            # On récupère les sections de premier niveau
            of_layout_category_ids = order_layout_category_obj.search(
                [('order_id', '=', order.id), ('parent_id', '=', False)]).sorted('sequence')
            for index, layout_category in enumerate(of_layout_category_ids):
                layout_category.sequence = sequence
                layout_category.sequence_name = str(index + 1)

                # On calcul les séquences des sections enfants
                layout_category.compute_childs_sequence_name()

                # La prochaine section sur ce niveau aura une séquence
                # plus grande que les enfants de la section courante
                number_of_child = len(order_layout_category_obj.search(
                    [('order_id', '=', order.id), ('id', 'child_of', layout_category.id)]))
                sequence = sequence + number_of_child

    @api.depends('of_layout_category_ids.invoice_status', 'state')
    def _compute_of_layout_category_invoice_status(self):
        for order in self:
            category_invoice_status = order.of_layout_category_ids.mapped('invoice_status_without_child')

            if order.state not in ('sale', 'done'):
                order.of_layout_category_invoice_status = 'no'
            elif not category_invoice_status:
                order.of_layout_category_invoice_status = 'invoiced'
            elif all(invoice_status == 'to invoice' for invoice_status in category_invoice_status):
                order.of_layout_category_invoice_status = 'to invoice'
            elif all(invoice_status == 'invoiced' for invoice_status in category_invoice_status):
                order.of_layout_category_invoice_status = 'invoiced'
            elif any(invoice_status == 'invoiced' for invoice_status in category_invoice_status):
                order.of_layout_category_invoice_status = 'partially invoiced'
            else:
                order.of_layout_category_invoice_status = 'no'

    def load_sections(self):
        template = self.of_template_id.with_context(lang=self.partner_id.lang)
        order_line_obj = self.env['sale.order.line']
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
    def action_layout_category_invoicing(self):
        wizard_form = self.env.ref('of_sale_quote_template.of_layout_category_invoicing_wizard_view_form')
        of_layout_category_ids = self.of_layout_category_ids.filtered(
            lambda c: c.invoice_status_without_child in ['to invoice', 'partially invoiced'])

        ctx = dict(
            default_order_id=self.id,
            default_layout_category_ids=of_layout_category_ids.ids,
            layout_category_ids_domain=of_layout_category_ids.ids,
        )
        return {
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'of.layout.category.invoicing.wizard',
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
        section_color = self.get_color_section()

        # Si les sections avancées sont configurées
        if self.user_has_groups('of_sale_quote_template.group_of_advanced_sale_layout_category') \
                and self.of_layout_category_ids:
            new_dict = {}
            of_layout_category_ids_sorted = self.of_layout_category_ids.sorted('sequence')

            # On crée une liste de lignes de commande pour chaque section avancée, y compris celles vides
            for index, layout_category in enumerate(of_layout_category_ids_sorted):
                domain = [('of_layout_category_id', '=', layout_category.id)]

                lines = self.order_line.search(domain)
                new_dict[index] = {
                    'layout_category': layout_category,
                    'order_lines': lines,
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
                    'name': category and "%s%s - %s" % (
                        '&#160;' * 3 * category.depth, category.sequence_name, category.name) or _('Uncategorized'),
                    'subtotal': category and category.prix_vente if len(list(lines)) else 0.0,
                    'pagebreak': False,
                    'lines': list(lines),
                    'color': category and category.get_color('sale.order') or section_color
                })

        # Si les sections avancées ne sont pas configurées, on appelle le super()
        else:
            report_pages = super(SaleOrder, self).order_lines_layouted()
            for page in report_pages:
                for group in page:
                    group['color'] = section_color

        return report_pages

    @api.multi
    def _prepare_invoice(self):
        """
        Prepare the dict of values to create the new invoice for a sales order. This method may be
        overridden to implement custom invoice generation (making sure to call super() to establish
        a clean extension chain).
        """
        invoice_vals = super(SaleOrder, self)._prepare_invoice()
        if self.of_layout_category_ids:
            invoice_vals['of_layout_category_ids'] = [(6, 0, self.of_layout_category_ids.ids)]
        return invoice_vals

    @api.multi
    def button_gestion_prix(self):
        res = super(SaleOrder, self).button_gestion_prix()

        remise = self.env['of.sale.order.gestion.prix'].browse(res['res_id'])

        categ_prec_id = -1
        forbidden_discount_prec = -1
        layout_category_vals = []
        # On trie les lignes de gestion de prix par section puis par le critère de remise interdite
        remise_lines_sorted = remise.line_ids.sorted(
                key=lambda l: (not l.order_line_id.of_layout_category_id,
                               l.order_line_id.of_layout_category_id.sequence,
                               l.order_line_id.of_layout_category_id.id,
                               l.order_line_id.of_product_forbidden_discount))
        for remise_line in remise_lines_sorted:
            # Ici, on s'attaque à une nouvelle section, donc on rajoute une ligne
            if remise_line.order_line_id.of_layout_category_id.id != categ_prec_id:
                category = remise_line.order_line_id.of_layout_category_id
                forbidden_discount_prec = remise_line.order_line_id.of_product_forbidden_discount
                categ_prec_id = category.id
                layout_category_vals.append({
                    'layout_category_id': category.id,
                    'product_forbidden_discount': forbidden_discount_prec,
                    'line_ids': [(6, 0, [remise_line.id])],
                    'state': 'included' if
                    not forbidden_discount_prec
                    else 'excluded',
                    'simulated_price_subtotal': remise_line.order_line_id.price_subtotal,
                    'simulated_price_total': remise_line.order_line_id.price_total,
                })
            # Ici, on passe à un changement de remise interdite au sein d'une section, donc on rajoute une ligne
            elif remise_line.order_line_id.of_product_forbidden_discount != forbidden_discount_prec:
                forbidden_discount_prec = remise_line.order_line_id.of_product_forbidden_discount
                layout_category_vals.append({
                    'layout_category_id': category.id,
                    'product_forbidden_discount': forbidden_discount_prec,
                    'line_ids': [(6, 0, [remise_line.id])],
                    'state': 'included' if
                    not forbidden_discount_prec
                    else 'excluded',
                    'simulated_price_subtotal': remise_line.order_line_id.price_subtotal,
                    'simulated_price_total': remise_line.order_line_id.price_total,
                })
            # Si on ne change ni de section ni de remise interdite,
            # alors on additionne la ligne courante à la dernière ligne traitée.
            else:
                vals = layout_category_vals[-1]
                vals['line_ids'][0][2].append(remise_line.id)
                vals['simulated_price_subtotal'] += remise_line.order_line_id.price_subtotal
                vals['simulated_price_total'] += remise_line.order_line_id.price_total
        if self.amount_untaxed:
            for vals in layout_category_vals:
                vals['pc_sale_price'] = 100.0 * vals['simulated_price_subtotal'] / self.amount_untaxed
        # on ajoute les catégories vide si on veut mettre les remises sur d'autres catégories
        for layout_category in self.of_layout_category_ids.filtered(lambda r: not r.order_line_ids):
            layout_category_vals.append({
                'layout_category_id': layout_category.id,
                'pc_sale_price': 0.0,
                'product_forbidden_discount': False,
                'simulated_price_subtotal': 0.0,
                'simulated_price_total': 0.0,
                'state': 'excluded',
            })
        remise.write({
            'layout_category_ids': [(0, 0, vals) for vals in layout_category_vals],
        })

        return res

    def _get_sale_quote_template_values(self):
        return {
            'name': self.name,
            'property_of_fiscal_position_id': self.fiscal_position_id or False,
            'of_payment_term_id': self.payment_term_id or False,
            'of_note1': self.note1 or False,
            'of_note2': self.note2 or False}

    @api.multi
    def make_sale_quote_template(self):
        self.ensure_one()
        sale_quote_template = self.env['sale.quote.template']
        sale_quote_template_new = sale_quote_template.new(self._get_sale_quote_template_values())
        quote_template_values = sale_quote_template_new._convert_to_write(sale_quote_template_new._cache)

        lines_to_create = []
        for line in self.order_line:
            line_vals = line.prepare_sqt_line_vals()
            lines_to_create.append((0, 0, line_vals))

        activities_to_create = []
        for line in self.of_crm_activity_ids:
            activity_vals = line.prepare_sqt_activity_vals()
            activities_to_create.append((0, 0, activity_vals))

        quote_template_values.update({
            'quote_line': lines_to_create,
            'of_sale_quote_tmpl_activity_ids': activities_to_create,
        })
        sale_quote_template = self.env['sale.quote.template'].create(quote_template_values)
        return {
            'name': u"Modèle de devis",
            'view_mode': 'form',
            'res_model': 'sale.quote.template',
            'type': 'ir.actions.act_window',
            'target': 'current',
            'res_id': sale_quote_template.id,
        }


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

    @api.multi
    def _prepare_invoice_line(self, qty):
        """
        Prepare the dict of values to create the new invoice line for a sales order line.

        :param qty: float quantity to invoice
        """
        res = super(SaleOrderLine, self)._prepare_invoice_line(qty)
        res['of_layout_category_id'] = self.of_layout_category_id and self.of_layout_category_id.id or False
        return res

    @api.multi
    def prepare_sqt_line_vals(self):
        self.ensure_one()
        sale_quote_line_obj = self.env['sale.quote.line']
        quote_line_new = sale_quote_line_obj.new({
            'product_id': self.product_id.id,
            'product_uom_id': self.product_uom.id,
            'product_uom_qty': self.product_uom_qty,
            'price_unit': self.price_unit,
            'name': self.product_id.name,
        })
        return quote_line_new._convert_to_write(quote_line_new._cache)


class AccountInvoice(models.Model):
    _inherit = 'account.invoice'

    of_layout_category_ids = fields.Many2many('of.sale.order.layout.category', string=u"Liste de section", copy=True)
    of_price_printing = fields.Selection(selection_add=[
        ('layout_category', "Prix par sections"),
        ('layout_category_with_products', "Prix par sections avec articles"),
        ('summary', u"Récapitulatif des prix par sections"),
    ])

    @api.multi
    def order_lines_layouted(self):
        """ Surcharge de la fonction de mise en page des lignes de facture groupées par section"""
        self.ensure_one()
        report_pages = [[]]
        section_color = self.get_color_section()

        # Si les sections avancées sont configurées
        if self.user_has_groups('of_sale_quote_template.group_of_advanced_sale_layout_category') \
                and self.of_layout_category_ids:
            new_dict = {}
            of_layout_category_ids_sorted = self.of_layout_category_ids.sorted('sequence')

            # On crée une liste de lignes de facture pour chaque section avancée, y compris celles vides
            for index, layout_category in enumerate(of_layout_category_ids_sorted):
                domain = [('of_layout_category_id', '=', layout_category.id)]

                lines = self.invoice_line_ids.search(domain)
                new_dict[index] = {
                    'layout_category': layout_category,
                    'invoice_line_ids': lines,
                }

            # On récupère les lignes de facture qui n'ont pas de lignes de section associées
            lines_without_layout_category = self.invoice_line_ids.filtered(
                lambda line: line.of_layout_category_id.id is False)
            if lines_without_layout_category:
                new_dict[-1] = {
                    'layout_category': False,
                    'invoice_line_ids': lines_without_layout_category,
                }

            # On remplit la liste de liste qui sera passée au rapport
            for key, values in new_dict.items():
                category = values['layout_category']
                lines = values['invoice_line_ids']

                # If last added category induced a pagebreak, this one will be on a new page
                if report_pages[-1] and report_pages[-1][-1]['pagebreak']:
                    report_pages.append([])
                # Append category to current report page
                report_pages[-1].append({
                    'name': category and "%s%s - %s" % (
                        '&#160;' * 3 * category.depth, category.sequence_name, category.name) or _('Uncategorized'),
                    'subtotal': category and category.prix_vente if len(list(lines)) else 0.0,
                    'pagebreak': False,
                    'lines': list(lines),
                    'color': category and category.get_color('account.invoice') or section_color
                })

        # Si les sections avancées ne sont pas configurées,
        # on reprend le comportement standard (odoo/addons/sale/models/account_invoice.py). Il est répété ici
        # pour éviter de surcharger la fonction de mise en page des lignes de facture.
        # Nous ajoutons juste la traduction de la section quand il n'y a pas de section : _("Uncategorized").
        else:
            for category, lines in groupby(self.invoice_line_ids, lambda l: l.layout_category_id):
                # If last added category induced a pagebreak, this one will be on a new page
                if report_pages[-1] and report_pages[-1][-1]['pagebreak']:
                    report_pages.append([])
                # Append category to current report page
                report_pages[-1].append({
                    'name': category and category.name or _("Uncategorized"),
                    'subtotal': category and category.subtotal,
                    'pagebreak': category and category.pagebreak,
                    'lines': list(lines)
                })
            for page in report_pages:
                for group in page:
                    group['color'] = section_color
        return report_pages

    @api.multi
    def of_get_printable_data(self):
        """
            On surcharge cette fonction pour les sections avancées, car sur les factures,
            les sections vides ne sont pas affichées.
        """
        result = super(AccountInvoice, self).of_get_printable_data()

        # Si les sections avancées sont configurées
        if self.user_has_groups('of_sale_quote_template.group_of_advanced_sale_layout_category') \
                and self.of_layout_category_ids:
            report_pages_full = self.order_lines_layouted()
            report_lines = result['lines']
            report_pages = []
            for page_full in report_pages_full:
                page = []
                for group in page_full:
                    lines = [line for line in group['lines'] if line in report_lines]
                    group['lines'] = lines
                    page.append(group)
                if page:
                    report_pages.append(page)
            result['lines_layouted'] = report_pages

        return result


class AccountInvoiceLine(models.Model):
    _inherit = 'account.invoice.line'

    of_layout_category_id = fields.Many2one('of.sale.order.layout.category', string=u"Ligne de section")

    @api.multi
    def get_merge_columns(self):
        data = super(AccountInvoiceLine, self).get_merge_columns()
        if 'of_layout_category_id' in data:
            del data['of_layout_category_id']
        return data


class OFCRMActivity(models.Model):
    _inherit = 'of.crm.activity'

    @api.multi
    def prepare_sqt_activity_vals(self):
        self.ensure_one()
        sale_quote_template_obj = self.env['of.sale.quote.tmpl.activity']
        activity_line_new = sale_quote_template_obj.new({
            'activity_id': self.type_id.id,
            'compute_date': self.type_id.of_compute_date,
            'days': self.type_id.days,
            'description': self.description,
        })
        return activity_line_new._convert_to_write(activity_line_new._cache)
