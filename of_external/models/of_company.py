# -*- coding: utf-8 -*-

from odoo import fields, models, api

class ResCompany(models.Model):
    _inherit = "res.company"
    use_of_custom_footer = fields.Boolean(
        string=u'Utiliser le pied de page personnalisé pour cette société.',
        help=u"Cochez si vous voulez utiliser ce pied de page personnalisé pour les rapports PDF")
    of_custom_footer_line_1 = fields.Char(string='Ligne 1')
    of_custom_footer_line_2 = fields.Char(string='Ligne 2')
    of_custom_footer_line_3 = fields.Char(string='Ligne 3')
    of_custom_footer_line_1_size = fields.Selection([('medium', 'Moyen'), ('small', 'Petit'), ('smaller', 'Plus petit'), ('x-small', u'Très petit')], string='Taille', default='small', required=True)
    of_custom_footer_line_2_size = fields.Selection([('medium', 'Moyen'), ('small', 'Petit'), ('smaller', 'Plus petit'), ('x-small', u'Très petit')], string='Taille', default='small', required=True)
    of_custom_footer_line_3_size = fields.Selection([('medium', 'Moyen'), ('small', 'Petit'), ('smaller', 'Plus petit'), ('x-small', u'Très petit')], string='Taille', default='smaller', required=True)

    of_custom_header_line_1 = fields.Char(string='Ligne 1')
    of_custom_header_line_2 = fields.Char(string='Ligne 2')
    of_custom_header_line_3 = fields.Char(string='Ligne 3')
    of_custom_header_line_4 = fields.Char(string='Ligne 4')
    of_custom_header_line_1_size = fields.Selection([('medium', 'Moyen'), ('small', 'Petit'), ('smaller', 'Plus petit'), ('x-small', u'Très petit')], string='Taille', default='medium', required=True)
    of_custom_header_line_2_size = fields.Selection([('medium', 'Moyen'), ('small', 'Petit'), ('smaller', 'Plus petit'), ('x-small', u'Très petit')], string='Taille', default='medium', required=True)
    of_custom_header_line_3_size = fields.Selection([('medium', 'Moyen'), ('small', 'Petit'), ('smaller', 'Plus petit'), ('x-small', u'Très petit')], string='Taille', default='medium', required=True)
    of_custom_header_line_4_size = fields.Selection([('medium', 'Moyen'), ('small', 'Petit'), ('smaller', 'Plus petit'), ('x-small', u'Très petit')], string='Taille', default='medium', required=True)

    of_max_height_bandeau = fields.Integer(string=u'Hauteur max bandeau (px)', default=130, required=True)

    of_position_header_lines = fields.Selection(
        [
            ('logo_under', u"Logo société et adresse configurable dessous"),
            ('logo_right', u"Logo société et adresse configurable à droite"),
            ('bandeau_pastille', u"Bandeau image + pastille"),
            ('bandeau_totalite', u"Bandeau image totalité page "),
        ], string="Type d'en-tête société", default="logo_right",
        help=u"Position des lignes d'en-tête relativement au logo de société\n"
             u"Sous le logo : les lignes d'en-tête seront placées sous le logo de société.\n"
             u"À droite du logo : les lignes d'en-tête seront placées à droite du logo.")

    @api.multi
    def get_line_content(self, header_or_footer="header", number=1):
        """Analyse des variables mako"""
        self.ensure_one()
        field_to_render = self.of_custom_header_line_1
        if header_or_footer == "header":
            if number == 2:
                field_to_render = self.of_custom_header_line_2
            elif number == 3:
                field_to_render = self.of_custom_header_line_3
            elif number == 4:
                field_to_render = self.of_custom_header_line_4
        else:
            if number == 1:
                field_to_render = self.of_custom_footer_line_1
            elif number == 2:
                field_to_render = self.of_custom_footer_line_2
            else:
                field_to_render = self.of_custom_footer_line_3
        content = self.env['mail.template'].render_template(field_to_render, 'res.company', self.id, post_process=False)
        return content

class View(models.Model):
    _inherit = 'ir.ui.view'

    @api.multi
    def render(self, values=None, engine='ir.qweb'):
        # Ajout de la possibilité d'appeler hasattr depuis une vue qweb
        return super(View, self).render(dict(values or {}, hasattr=hasattr), engine)
