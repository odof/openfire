# -*- coding: utf-8 -*-

from odoo import api, fields, models

class OfSaleOrderVerification(models.TransientModel):
    _name = 'of.sale.order.verification'

    message = fields.Text(string="Message")
    type = fields.Selection(selection=[
        ('margin', u'Contrôle de marge')
        ], string="Type")
    order_id = fields.Many2one(comodel_name='sale.order', string="Commande")

    @api.model
    def do_verification(self, order):
        """ À surcharger pour ajouter les différentes vérifications """
        # Vérification de la marge sur catégorie de l'article principal
        sale_responsible = self.env.user.has_group('sales_team.group_sale_manager')
        skipped_types = self._context.get('skipped_types', [])
        if 'margin' not in skipped_types and not self._context.get('no_verif_margin', False):
            article_principal = order.order_line.filtered('of_article_principal')
            if article_principal and article_principal[0].product_id.categ_id.of_taux_marge:
                if int(order.of_marge_pc) < article_principal[0].product_id.categ_id.of_taux_marge:
                    # les " et ' risque de faire planter le js, on les remplace par des espaces à la fin.
                    message = (u"Le montant de marge de la commande %s est de %.2f%% alors que la catégorie %s de "
                               u"l'article principal %s %s une marge minimum de %s%%" % (
                                  order.name,
                                  order.of_marge_pc,
                                  article_principal[0].product_id.categ_id.name,
                                  article_principal[0].product_id.display_name,
                                  sale_responsible and u"demande" or u"requiert",
                                  article_principal[0].product_id.categ_id.of_taux_marge)
                               ).replace('"', ' ').replace("'", " ")
                    skipped_types.append('margin')
                    context = {
                        'default_type': 'margin',
                        'default_message': message,
                        'default_order_id': order.id,
                        'skipped_types' : skipped_types,
                    }
                    return self.action_return(context, 'margin')
        return False, False

    @api.model
    def action_return(self, context, type, titre="Informations"):
        return {
            'type': 'ir.actions.act_window',
            'name': titre,
            'res_model': 'of.sale.order.verification',
            'view_type': 'form',
            'view_mode': 'form',
            'target': 'new',
            'context': str(context),
        }, type

    @api.multi
    def next_step(self):
        action, type = self.do_verification(self.order_id)
        return action

    @api.multi
    def skip_validation(self):
        action, type = self.do_verification(self.order_id)
        return action
