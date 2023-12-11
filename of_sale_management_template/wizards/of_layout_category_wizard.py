# -*- coding: utf-8 -*-

from odoo import models, fields, api


class OfLayoutCategoryAddWizard(models.TransientModel):
    _name = 'of.layout.category.add.wizard'
    _description = u"Wizard d'ajout de ligne de section"

    type = fields.Selection([('quote', u"Modèle de devis"), ('order', "Devis/Commande")], string=u"Type", required=True)

    order_id = fields.Many2one('sale.order', string=u"Commande")
    order_layout_category_id = fields.Many2one(
        'of.sale.order.layout.category', string=u"Ligne de section", ondelete='cascade')

    quote_id = fields.Many2one('sale.quote.template', string=u"Modèle de devis")
    quote_layout_category_id = fields.Many2one(
        'of.sale.quote.template.layout.category', string=u"Ligne de section", ondelete='cascade')

    section_number = fields.Integer(string=u"Nombre de sections", required=True)
    min_section_number = fields.Integer(string=u"Nombre de sections minimum", required=True)
    display_button = fields.Boolean(string=u"Afficher bouton de validation")

    @api.onchange('section_number')
    def onchange_section_number(self):
        self.display_button = self.section_number >= self.min_section_number

    def action_done_order(self):
        order_layout_category_obj = self.env['of.sale.order.layout.category']

        number_of_new_section = self.section_number - self.min_section_number

        # On récupère les sous sections
        layout_category_ids = order_layout_category_obj.search(
            [('order_id', '=', self.order_id.id), ('parent_id', '=', self.order_layout_category_id.id or False)]
        ).sorted('sequence')

        # S'il existe déjà des sous sections, on prend la dernière
        if layout_category_ids:
            last_layout_category_id = layout_category_ids[-1]
        # Sinon on prend la section courante
        else:
            last_layout_category_id = self.order_layout_category_id

        # On crée autant de section que nécessaire
        for i in range(number_of_new_section):
            order_layout_category_obj.create({
                'name': u"Section %s" % (i + 1),
                'parent_id': self.order_layout_category_id.id or False,
                'order_id': self.order_id.id,
                'sequence': last_layout_category_id.sequence + (i + 1),
            })

        # On recalcule les séquences
        self.order_id.compute_of_layout_category_ids()

    def action_done_quote(self):
        quote_layout_category_obj = self.env['of.sale.quote.template.layout.category']

        number_of_new_section = self.section_number - self.min_section_number

        # On récupère les sous sections
        layout_category_ids = quote_layout_category_obj.search(
            [('quote_id', '=', self.quote_id.id), ('parent_id', '=', self.quote_layout_category_id.id or False)]
        ).sorted('sequence')

        # S'il existe déjà des sous sections, on prend la dernière
        if layout_category_ids:
            last_layout_category_id = layout_category_ids[-1]
        # Sinon on prend la section courante
        else:
            last_layout_category_id = self.quote_layout_category_id

        # On crée autant de section que nécessaire
        for i in range(number_of_new_section):
            quote_layout_category_obj.create({
                'name': u"Section %s" % (i + 1),
                'parent_id': self.quote_layout_category_id.id or False,
                'quote_id': self.quote_id.id,
                'sequence': last_layout_category_id.sequence + (i + 1),
            })

        # On recalcule les séquences
        self.quote_id.compute_of_section_line_ids()


class OfLayoutCategoryDuplicateWizard(models.TransientModel):
    _name = 'of.layout.category.duplicate.wizard'
    _description = u"Wizard de duplication de ligne de section"

    type = fields.Selection([('quote', u"Modèle de devis"), ('order', "Devis/Commande")], string=u'Type', required=True)

    order_id = fields.Many2one('sale.order', string=u"Commande")
    order_layout_category_id = fields.Many2one(
        'of.sale.order.layout.category', string=u"Ligne de section", ondelete='cascade')
    order_parent_id = fields.Many2one(
        'of.sale.order.layout.category', string=u"Parent")

    quote_id = fields.Many2one('sale.quote.template', string=u"Modèle de devis")
    quote_layout_category_id = fields.Many2one(
        'of.sale.quote.template.layout.category', string=u"Ligne de section", ondelete='cascade')
    quote_parent_id = fields.Many2one(
        'of.sale.quote.template.layout.category', string=u"Parent")

    name = fields.Char(string=u"Nom de la section", required=True)
    inclure_sous_sections = fields.Boolean(string=u"Inclure les sous-sections")

    def action_done_order(self):
        # On duplique la section
        sale_order_layout_category_parent = self.order_layout_category_id.copy({
            'name': self.name or '',
            'parent_id': self.order_parent_id.id or False,
        })

        for line in self.order_layout_category_id.order_line_without_child_ids:
            line.copy({
                'of_layout_category_id': sale_order_layout_category_parent.id,
            })

        sale_order_layout_category_parent.sequence = sale_order_layout_category_parent.sequence + 1

        #  On duplique les sections enfants si le paramètre est coché
        if self.inclure_sous_sections:
            self.order_layout_category_id.duplicate_childs(sale_order_layout_category_parent)

        # On recalcule les séquences
        self.order_id.compute_of_layout_category_ids()

    def action_done_quote(self):
        # On duplique la section
        quote_layout_category_parent = self.quote_layout_category_id.copy({
            'name': self.name or '',
            'parent_id': self.quote_parent_id.id or False,
        })

        for line in self.quote_layout_category_id.quote_line_ids:
            line.copy({
                'of_layout_category_id': quote_layout_category_parent.id,
            })

        quote_layout_category_parent.sequence = quote_layout_category_parent.sequence + 1

        #  On duplique les sections enfants si le paramètre est coché
        if self.inclure_sous_sections:
            self.quote_layout_category_id.duplicate_childs(quote_layout_category_parent)

        # On recalcule les séquences
        self.quote_id.compute_of_section_line_ids()


class OfLayoutCategoryMoveWizard(models.TransientModel):
    _name = 'of.layout.category.move.wizard'
    _description = u"Wizard de déplacement de ligne de section"

    type = fields.Selection([('quote', u"Modèle de devis"), ('order', "Devis/Commande")], string=u"Type", required=True)

    order_id = fields.Many2one('sale.order', string=u"Commande")
    order_layout_category_id = fields.Many2one(
        'of.sale.order.layout.category', string=u"Ligne de section", ondelete='cascade')
    order_parent_id = fields.Many2one(
        'of.sale.order.layout.category', string=u"Parent")

    quote_id = fields.Many2one('sale.quote.template', string=u'Modèle de devis')
    quote_layout_category_id = fields.Many2one(
        'of.sale.quote.template.layout.category', string=u"Ligne de section", ondelete='cascade')
    quote_parent_id = fields.Many2one(
        'of.sale.quote.template.layout.category', string=u"Parent")

    position = fields.Integer(string=u"Position de la ligne")
    previous_position = fields.Integer(string=u"Position précédente")
    inclure_sous_sections = fields.Boolean(string=u"Inclure les sous-sections", default=True)

    def action_done_order(self):
        order_layout_category_obj = self.env['of.sale.order.layout.category']

        # On stocke l'ancien parent pour le cas les sous sections ne sont pas inclus dans le déplacement
        old_parent = self.order_layout_category_id.parent_id or False

        # On stocke les anciens enfants et les nouveaux. Pour les nouveaux, on ne prend que les enfants directs
        old_child_layout_category_ids = order_layout_category_obj.search([
            ('order_id', '=', self.order_id.id),
            ('id', 'child_of', self.order_layout_category_id.id),
            ('id', '!=', self.order_layout_category_id.id)])
        new_child_order_layout_category_ids = order_layout_category_obj.search([
            ('order_id', '=', self.order_id.id),
            ('parent_id', '=', self.order_parent_id.id)
        ]).sorted('sequence')

        self.order_layout_category_id.parent_id = self.order_parent_id

        # Si le nouveau parent n'a pas d'enfant, on ne s'occupe pas de sa position
        if not new_child_order_layout_category_ids:
            sequence = self.order_parent_id.sequence
        # Sinon on le place à la bonne position
        else:
            position = min(max(self.position, 1), len(new_child_order_layout_category_ids))
            previous_layout_category_id = new_child_order_layout_category_ids[position - 1]
            sequence = previous_layout_category_id.sequence

            # Selon qu'on augmente ou baisse la position, on rajoute ou enlève 1 à la séquence
            if position < self.previous_position:
                sequence -= 1
            if position > self.previous_position:
                sequence += 1

        self.order_layout_category_id.sequence = sequence

        # On déplace les sous sections ou on leur assigne l'ancien parent
        for child in old_child_layout_category_ids:
            if self.inclure_sous_sections:
                child.sequence = self.order_parent_id.sequence
            else:
                child.parent_id = old_parent.id or False
                child.sequence = old_parent.sequence

        # On recalcule les séquences
        self.order_id.compute_of_layout_category_ids()

    def action_done_quote(self):
        quote_layout_category_obj = self.env['of.sale.quote.template.layout.category']

        # On stocke l'ancien parent pour le cas les sous sections ne sont pas inclus dans le déplacement
        old_parent = self.quote_layout_category_id.parent_id or False

        # On stocke les anciens enfants et les nouveaux. Pour les nouveaux, on ne prend que les enfants directs
        old_child_layout_category_ids = quote_layout_category_obj.search([
            ('quote_id', '=', self.quote_id.id),
            ('id', 'child_of', self.quote_layout_category_id.id),
            ('id', '!=', self.quote_layout_category_id.id)])
        new_child_quote_layout_category_ids = quote_layout_category_obj.search([
            ('quote_id', '=', self.quote_id.id),
            ('parent_id', '=', self.quote_parent_id.id)
        ]).sorted('sequence')

        self.quote_layout_category_id.parent_id = self.quote_parent_id

        # Si le nouveau parent n'a pas d'enfant, on ne s'occupe pas de sa position
        if not new_child_quote_layout_category_ids:
            sequence = self.quote_parent_id.sequence
        # Sinon on le place à la bonne position
        else:
            position = min(max(self.position, 1), len(new_child_quote_layout_category_ids))
            previous_layout_category_id = new_child_quote_layout_category_ids[position - 1]
            sequence = previous_layout_category_id.sequence

            # Selon qu'on augmente ou baisse la position, on rajoute ou enlève 1 à la séquence
            if position < self.previous_position:
                sequence -= 1
            if position > self.previous_position:
                sequence += 1

        self.quote_layout_category_id.sequence = sequence

        # On déplace les sous sections ou on leur assigne l'ancien parent
        for child in old_child_layout_category_ids:
            if self.inclure_sous_sections:
                child.sequence = self.quote_parent_id.sequence
            else:
                child.parent_id = old_parent.id or False
                child.sequence = old_parent.sequence

        # On recalcule les séquences
        self.quote_id.compute_of_section_line_ids()
