# -*- coding: utf-8 -*-

from odoo import api, models, fields, _
from odoo.exceptions import UserError
from datetime import timedelta
from odoo.addons.of_utils.models.of_utils import se_chevauchent, format_date


class OFHoraireSaveModeleWizard(models.TransientModel):
    _name = 'of.horaire.save.modele.wizard'

    name = fields.Char(string=u"Libellé", required=True)
    creneau_ids = fields.Many2many("of.horaire.creneau", string=u"Créneaux")
    horaires_recap = fields.Html(compute='_compute_horaires_recap', string=u"Récapitulatif des horaires")
    fait = fields.Boolean(string="fait!")
    wizard_id = fields.Many2one('of.horaire.segment.wizard', string="wizard")
    mode = fields.Selection([
        ('create', u"Créer"),
        ('edit', u"Éditer"),
        ('unlink', u"Supprimer"),
    ])

    @api.multi
    @api.depends('creneau_ids')
    def _compute_horaires_recap(self):
        for wizard in self:
            if not self.creneau_ids:
                self.horaires_recap = u""
            else:
                recap = u'<div colspan="2" style="text-align: left;">'
                recap += u'<br/>\n&nbsp;&nbsp;&nbsp;'.join(self.creneau_ids.format_str_list()) + u'</div>\n'
                wizard.horaires_recap = recap

    @api.multi
    def action_confirm(self):
        if not self.name:
            raise UserError(_(u"Échec de la sauvegarde : nom manquant."))
        if not self.creneau_ids:
            raise UserError(_(u"Échec de la sauvegarde : horaires non trouvés."))
        self.env['of.horaire.modele'].create({
            'name': self.name,
            'creneau_ids': [(6, 0, self.creneau_ids.ids)],
        })
        self.fait = True
        return {'type': 'ir.actions.do_nothing'}

    @api.multi
    def action_retour(self):
        if not self.wizard_id:
            return {'type': 'ir.actions.do_nothing'}
        action = self.env.ref('of_calendar.action_of_horaire_segment_' + self.mode + '_form_view').read()[0]
        action['res_id'] = self.wizard_id.id
        return action


class OFHoraireSegmentWizard(models.TransientModel):
    _name = 'of.horaire.segment.wizard'

    def _default_jours_ids(self):
        # Lundi à vendredi comme valeurs par défaut
        jours = self.env['of.jours'].search([('numero', 'in', (1, 2, 3, 4, 5))], order="numero")
        res = [jour.id for jour in jours]
        return res

    @api.model
    def _default_premier_seg(self):
        employee_id = self._context.get("default_employee_id", False)
        if not employee_id:
            return False
        employee = self.env['hr.employee'].browse(employee_id)
        return not employee.of_segment_ids or not employee.of_segment_ids.filtered(lambda s: s.permanent)

    @api.model
    def _get_segment_id_domain(self):
        active_id = self._context.get('active_id')
        if not active_id:
            return []
        wizard = self.env['of.horaire.segment.wizard'].browse(active_id)
        return [
            ('employee_id', '=', wizard.employee_id.id),
            ('permanent', '=', wizard.permanent),
            '|',
            ('date_fin', '>=', fields.Date.today()),
            ('date_fin', '=', False),
        ]

    @api.multi
    @api.constrains('creneau_ids')
    def check_no_overlapping(self):
        for wizard in self:
            for creneaux in (wizard.creneau_ids):
                creneaux_len = len(creneaux)
                for j in xrange(creneaux_len - 1):
                    if creneaux[j].jour_id != creneaux[j+1].jour_id:
                        continue
                    d1 = creneaux[j].heure_debut
                    f1 = creneaux[j].heure_fin
                    d2 = creneaux[j+1].heure_debut
                    f2 = creneaux[j+1].heure_fin
                    if se_chevauchent(d1, f1, d2, f2):
                        raise UserError(u"Oups! Des créneaux se chevauchent")

    mode = fields.Selection([
        ('create', u"Créer"),
        ('edit', u"Éditer"),
        ('unlink', u"Supprimer"),
    ])
    type = fields.Selection(
        selection=[('regular', u"Normaux")], string=u"Type d'horaires", required=True, default='regular')
    employee_id = fields.Many2one('hr.employee', string=u"Employé", required=True, ondelete='cascade')
    date_deb = fields.Date(string=u"Date de début", default=lambda self: fields.Date.today())
    date_fin = fields.Date(string="Date de fin", default=lambda self: fields.Date.today())
    permanent = fields.Boolean(
        string="Horaire permanent",
        help=u"Horaires valables sur une durée indéterminée.",
        default=lambda self: self._default_premier_seg()
    )
    premier_seg = fields.Boolean(string=u"premier segment permanent?", default=lambda self: self._default_premier_seg())
    motif = fields.Char(string="Motif du changement")
    modele_id = fields.Many2one('of.horaire.modele', string=u"Charger un modèle")
    mode_horaires = fields.Selection([
        ("easy", "Facile"),
        ("advanced", u"Avancé")], string=u"Mode de Sélection des horaires", required=True, default="easy")
    creneau_ids = fields.Many2many("of.horaire.creneau", string=u"Créneaux")
    hor_md = fields.Float(string=u'Matin début', digits=(12, 5), default=9)
    hor_mf = fields.Float(string=u'Matin fin', digits=(12, 5), default=12)
    hor_ad = fields.Float(string=u'Après-midi début', digits=(12, 5), default=14)
    hor_af = fields.Float(string=u'Après-midi fin', digits=(12, 5), default=18)
    jour_ids = fields.Many2many('of.jours', string=u'Jours travaillés', default=lambda self: self._default_jours_ids())

    # Champs en cas de chevauchement
    remplacement = fields.Boolean(string="besoin confirmation")
    seg_1_horaires_recap = fields.Html(compute='_compute_horaires_recap', string="Horaires de travail")
    seg_exist_ids = fields.Many2many('of.horaire.segment', string="Segment existants", order="date_deb")
    seg_exist_recap = fields.Html(compute='_compute_horaires_recap', string="Horaires de travail")
    result_recap = fields.Html(compute='_compute_horaires_recap', string="Horaires de travail")

    # Pour la modification et la suppression
    segment_id = fields.Many2one('of.horaire.segment', string=u"Période concernée")#, domain=_get_segment_id_domain)

    # @api.depends

    @api.multi
    @api.depends('creneau_ids', 'seg_exist_ids', 'date_deb', 'date_fin', 'permanent')
    def _compute_horaires_recap(self):
        lang = self.env['res.lang']._lang_get(self.env.lang or 'fr_FR')

        def format_date(date):
            return fields.Date.from_string(date).strftime(lang.date_format)

        def formate_creneaux(creneaux):
            return u'<p>\n&nbsp;&nbsp;&nbsp;' + u'<br/>\n&nbsp;&nbsp;&nbsp;'.join(
                creneaux.format_str_list()) + u'</p>\n'

        for wizard in self:
            if not self.seg_exist_ids or not self.date_deb or not self.date_fin or self.permanent:
                self.seg_1_horaires_recap = False
                self.seg_exist_recap = False
                self.result_recap = False
            else:
                seg_exist_pluriel = len(self.seg_exist_ids) > 1
                recap_1 = u'<div><i>Vous avez entré la période horaire suivante :</i></div>'
                recap_1 += u'<div colspan="2" style="text-align: left;">'
                recap_1 += u'<p><b style="color: deepskyblue;">Du ' + format_date(
                    self.date_deb) + u' au ' + format_date(self.date_fin) + u'</b></p>'
                recap_1 += u'<br/>\n&nbsp;&nbsp;&nbsp;'.join(self.creneau_ids.format_str_list()) + u'</div>\n'
                wizard.seg_1_horaires_recap = recap_1
                if seg_exist_pluriel:
                    recap_2 = u'<div><i>Elle entre en conflit avec les périodes existantes suivantes :</i></div>'
                else:
                    recap_2 = u'<div><i>Elle entre en conflit avec la période existante suivante :</i></div>'
                recap_2 += u'<table colspan="2" style="width: 100%; text-align: left;">'
                for segment in self.seg_exist_ids:
                    # recap_2 += '<tr><td style="min-widht: ' + str(pourcent) + '%; border:1px solid black;">'
                    recap_2 += u'<tr><td>'
                    recap_2 += u'<p><b style="color: blue">Du ' + format_date(segment.date_deb) + u' au ' + format_date(
                        segment.date_fin) + u'</b></p>'
                    recap_2 += formate_creneaux(segment.creneau_ids) + u'</td></tr>'
                recap_2 += u'</table>'
                wizard.seg_exist_recap = recap_2

                un_jour = timedelta(days=1)
                premier_fin_da = fields.Date.from_string(self.date_deb) - un_jour
                premier_fin_str = fields.Date.to_string(premier_fin_da)
                premier_seg = self.seg_exist_ids[0]
                dernier_deb_da = fields.Date.from_string(self.date_fin) + un_jour
                dernier_deb_str = fields.Date.to_string(dernier_deb_da)
                dernier_seg = self.seg_exist_ids[-1]

                if seg_exist_pluriel:
                    recap_3 = u'<div><i>Si vous remplacez les périodes existantes, Le résultat sera le suivant : </i></div>'
                else:
                    recap_3 = u'<div><i>Si vous remplacez la période existante, Le résultat sera le suivant : </i></div>'
                recap_3 += u'<table colspan="2" style="width: 100%; text-align: left">'

                if premier_seg.date_deb <= premier_fin_str:
                    recap_3 += u'</tr><td>'
                    recap_3 += u'<p><b style="color: blue">Du ' + format_date(
                        premier_seg.date_deb) + u' au <span style="color:red">' + \
                               format_date(premier_fin_str) + u'</span></b></p>'
                    recap_3 += formate_creneaux(premier_seg.creneau_ids) + u'</td></tr>'
                recap_3 += u'<tr><td>'
                recap_3 += u'<p><b style="color: deepskyblue">Du ' + format_date(self.date_deb) + u' au ' + format_date(
                    self.date_fin) + u'</b></p>'
                recap_3 += formate_creneaux(self.creneau_ids) + u'</td></tr>'
                if dernier_deb_str <= dernier_seg.date_fin:
                    recap_3 += u'<tr><td>'
                    recap_3 += u'<p><b style="color: blue">Du <span style="color:red">' + format_date(
                        dernier_deb_str) + u'</span> au ' + \
                               format_date(dernier_seg.date_fin) + u'</b></p>'
                    recap_3 += formate_creneaux(dernier_seg.creneau_ids) + u'</td></tr>'
                recap_3 += u'</table>'
                wizard.result_recap = recap_3

    # @api.onchange

    @api.multi
    @api.onchange('date_deb')
    def onchange_date_deb(self):
        self.ensure_one()
        self.remplacement = False
        if self.date_deb and not self.permanent:
            self.date_fin = self.date_deb

    @api.multi
    @api.depends('permanent')
    def onchange_permanent(self):
        for wizard in self:
            if wizard.permanent and wizard.employee_id.of_segment_ids:
                seg_exist = wizard.employee_id.of_segment_ids.filtered(lambda s: s.permanent)
                wizard.premier_seg = not seg_exist
            elif wizard.permanent:
                wizard.premier_seg = True

    @api.onchange('modele_id')
    def onchange_modele_id(self):
        self.ensure_one()
        if self.modele_id:
            self.creneau_ids = False  # car on ne peut pas utiliser de code 5 dans create() qui est appelé par clique sur bouton
            self.creneau_ids = self.modele_id.creneau_ids.ids
            self.mode_horaires = 'advanced'
            self.modele_id = False

    @api.multi
    @api.onchange('hor_md', 'hor_mf', 'hor_ad', 'hor_af', 'mode_horaires')
    def onchange_hor_ma_df(self):
        self.ensure_one()
        if self.mode_horaires == 'easy' and not (0 <= self.hor_md <= self.hor_mf <= self.hor_ad <= self.hor_af < 24):
            raise UserError(u"Il y a une incohérence au niveau des horaires.")

    @api.multi
    @api.onchange('segment_id')
    def onchange_segment_id(self):
        self.ensure_one()
        if self.segment_id:
            self.date_deb = self.segment_id.date_deb
            self.date_fin = self.segment_id.date_fin
            self.mode_horaires = 'advanced'
            self.motif = self.segment_id.motif
            self.creneau_ids = self.segment_id.creneau_ids
            if not self.segment_id.date_deb:
                self.premier_seg = True
        if self.mode != 'create' and (self.segment_id and self.segment_id.date_deb or not self.segment_id):
            self.premier_seg = False

    # Actions

    @api.multi
    def button_save_modele(self):
        self.ensure_one()
        self.onchange_hor_ma_df()
        creneau_obj = self.env['of.horaire.creneau']
        segment_obj = self.env['of.horaire.segment']
        if self.mode_horaires == 'easy':
            create_exist_ids = creneau_obj.create_if_necessary(
                self.hor_md, self.hor_mf, self.hor_ad, self.hor_af, self.jour_ids.ids)
            creneau_ids = create_exist_ids['create_ids'] + create_exist_ids['exist_ids']
        else:
            creneau_ids = self.creneau_ids.ids

        action = self.env.ref('of_calendar.action_of_horaire_save_modele_form_view').read()[0]
        action['context'] = {

            'default_creneau_ids': creneau_ids,
            'default_wizard_id': self.id,
            'default_mode': self.mode,
        }
        return action

    @api.multi
    def button_create_edit(self):
        self.ensure_one()
        if self.mode == "edit" and not self.segment_id:
            raise UserError(u"Veuillez Sélectionner une période à modifier")
        if not self.permanent and self.date_fin and self.date_fin < self.date_deb:
            raise UserError(u"la date de fin doit être postérieure ou égale à la date de début")
        self.onchange_hor_ma_df()
        creneau_obj = self.env['of.horaire.creneau']
        segment_obj = self.env['of.horaire.segment']
        if self.mode_horaires == 'easy':
            create_exist_ids = creneau_obj.create_if_necessary(
                self.hor_md, self.hor_mf, self.hor_ad, self.hor_af, self.jour_ids.ids)
            creneau_ids = create_exist_ids['create_ids'] + create_exist_ids['exist_ids']
        else:
            creneau_ids = self.creneau_ids.ids

        chevauche_seg_ids = segment_obj.search([
            ('employee_id', '=', self.employee_id.id),
            ('date_deb', '<=', self.date_fin),
            ('date_fin', '>=', self.date_deb),
            ('permanent', '=', False),
            ('id', '!=', self.segment_id and self.segment_id.id or False),
            ('type', '=', self.type),
        ], order="date_deb")
        if chevauche_seg_ids and not self.permanent:
            self.creneau_ids = [(6, 0, creneau_ids)]
            self.seg_exist_ids = [(6, 0, chevauche_seg_ids.ids)]
            self.remplacement = True
            return {'type': 'ir.actions.do_nothing'}
        self.remplacement = False
        self.employee_id.mode_horaires = self.mode_horaires  # conserver le mode horaires pour les futures utilisations du wizard
        vals = {
            'employee_id': self.employee_id.id,
            'creneau_ids': [(6, 0, creneau_ids)],
            'motif': self.motif,
        }
        if not self.premier_seg:
            vals['date_deb'] = self.date_deb
        else:
            vals['date_deb'] = "1970-01-01"
        if self.permanent:
            segment_meme_deb = segment_obj.search([
                ('employee_id', '=', self.employee_id.id),
                ('date_deb', '=', self.date_deb),
                ('permanent', '=', True),
                ('id', '!=', self.segment_id and self.segment_id.id or False),
                ('type', '=', self.type),
            ])
            if segment_meme_deb:
                raise UserError(u"Des horaires permanents qui commencent à cette date existent déjà")
            vals['permanent'] = True
        else:
            vals['date_fin'] = self.date_fin
        if self.mode == 'create':
            vals['type'] = self.type
            segment_obj.create(vals)
        else:
            self.segment_id.write(vals)
        if self.permanent:
            segment_obj.recompute_permanent_date_fin(self.employee_id.id, seg_type=self.type)
        #

        return {'type': 'ir.actions.act_window_close'}

    @api.multi
    def button_unlink(self):
        self.ensure_one()
        if not self.segment_id:
            raise UserError(u"Veuillez Sélectionner une période à supprimer")
        self.segment_id.unlink()
        if self.permanent:
            self.env['of.horaire.segment'].recompute_permanent_date_fin(self.employee_id.id, seg_type=self.type)
        return {'type': 'ir.actions.act_window_close'}

    @api.multi
    def button_remplacer(self):
        self.ensure_one()
        segment_obj = self.env['of.horaire.segment']

        un_jour = timedelta(days=1)
        premier_fin_da = fields.Date.from_string(self.date_deb) - un_jour
        premier_fin_str = fields.Date.to_string(premier_fin_da)
        premier_seg = self.seg_exist_ids[0]
        dernier_deb_da = fields.Date.from_string(self.date_fin) + un_jour
        dernier_deb_str = fields.Date.to_string(dernier_deb_da)
        dernier_seg = self.seg_exist_ids[-1]
        seg_nb = len(self.seg_exist_ids)
        # conserver la date de fin initial en cas de segment unique
        dernier_fin_str = dernier_seg.date_fin

        if premier_seg.date_deb <= premier_fin_str:  # maj premier segment qui chevauche
            premier_seg.date_fin = premier_fin_str
        elif premier_seg.date_fin <= self.date_fin:  # 1er segment entièrement recouvert
            premier_seg.active = False
        if dernier_deb_str <= dernier_fin_str:  # maj dernier segment qui chevauche
            # il y a plus d'un segment
            # ou l'unique segment n'a pas été modifié => il déborde seulement à droite
            if seg_nb > 1 or premier_seg.date_fin != premier_fin_str:
                dernier_seg.date_deb = dernier_deb_str
            else:  # il n'y a qu'un segment qui déborde à droite et à gauche
                vals = {
                    'employee_id': self.employee_id.id,
                    'date_deb': dernier_deb_str,
                    'date_fin': dernier_fin_str,
                    'permanent': False,
                    'creneau_ids': [(6, 0, premier_seg.creneau_ids.ids)],
                    'motif': premier_seg.motif,
                    'type': self.type,
                }
                segment_obj.create(vals)
        # dernier segment entièrement recouvert.
        # Si il y a un seul segment entièrement recouvert il a déjà été passé inactif plus haut
        elif seg_nb > 1:
            dernier_seg.active = False
        for i in range(1, len(self.seg_exist_ids) -1):  # maj tous les segments existants sauf le premier et le dernier
            self.seg_exist_ids[i].active = False
        vals = {
            'date_deb': self.date_deb,
            'date_fin': self.date_fin,
            'creneau_ids': [(6, 0, self.creneau_ids.ids)],
            'motif': self.motif,
        }
        if self.mode == 'create':
            vals['employee_id'] = self.employee_id.id
            vals['permanent'] = False
            vals['type'] = self.type
            segment_obj.create(vals)
        elif self.segment_id:
            self.segment_id.write(vals)

        return {"type": "ir.actions.act_window_close"}
