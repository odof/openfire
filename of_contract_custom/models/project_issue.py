# -*- coding: utf-8 -*-

from odoo import models, fields, api
from datetime import datetime, timedelta
import logging

_logger = logging.getLogger(__name__)


class ProjectIssue(models.Model):
    _inherit = 'project.issue'

    is_migrated = fields.Boolean(string=u"Est migré")

    @api.model
    def migrer_sav_di(self):
        u"""
        Migre les données des SAV dans les DI.
        Pour les SAV liés à au moins une DI -> rempli les champ de la 1ère DI avec ceux du SAV
        Pour les SAV sans DI -> créé une DI avec toutes les informations du SAV
        """
        if not self.env['ir.config_parameter'].sudo().get_param('of_migration_sav_di'):
            sav_obj = self.env['project.issue']
            service_obj = self.env['of.service']
            planning_tag_obj = self.env['of.planning.tag']
            sav_type = self.env.ref('of_contract_custom.of_contract_custom_type_sav')
            sav_tache  = self.env['of.planning.tache'].search([('name', 'ilike', 'SAV')], limit=1)
            if not sav_tache:
                _logger.error(u"OPENFIRE ERROR : impossible de migrer les SAV dans les DI, tâche 'SAV' inexistante")
                return
            dans_7_jours_str = fields.Date.to_string(fields.Date.from_string(fields.Date.today()) + timedelta(days=1))
            error_dict = {}

            def get_vals(sav, di):
                # concaténer diffŕenets champs dans la description
                note = di and di.note or sav.description or u""
                note += sav.of_intervention and u"\nNature de l'intervention: %s" % sav.of_intervention or u""
                note += sav.of_piece_commande and u"\nPièces à commander: %s" % sav.of_piece_commande or u""
                note += u"\nnº SAV ancienne version: %s" % sav.of_code
                if sav.product_name_id and not sav.of_produit_installe_id:
                    note += u"\nArticle associé ancienne version: %s" % sav.product_name_id.display_name
                # récupérer les étiquettes de la DI si existante, ajouter les étiquettes du SAV
                # les project.tags sont migrées dans les of.planning.tags dans l'auto_init et donc
                # avant l'exécution de cette fonction
                di_tags = di and di.tag_ids or planning_tag_obj
                sav_tags = planning_tag_obj.search([('name', 'in', sav.tag_ids.mapped('name'))])
                tag_ids = (di_tags | sav_tags).ids
                # prendre les RDV des SAV, les ajouter à la DI si besoin
                intervention_ids = sav.interventions_liees and sav.interventions_liees.ids or []
                # peupler le nouveau champ payer_mode
                payer_mode = False
                if sav.of_payant_client and sav.of_payant_fournisseur:
                    payer_mode = 'retailer'
                elif sav.of_payant_client and not sav.of_payant_fournisseur:
                    payer_mode = 'client'
                elif not sav.of_payant_client and sav.of_payant_fournisseur:
                    payer_mode = 'manufacturer'
                # s'assurer que la date de début et de fin de planif soient cohérentes
                date_next = di and di.date_next or sav.date or fields.Date.today()
                date_fin = di and di.date_fin or sav.date_deadline or dans_7_jours_str
                if date_fin < date_next:
                    date_fin = fields.Date.to_string(fields.Date.from_string(date_next) + timedelta(days=7))

                di_vals = {
                    #'titre': di and di.titre or sav.name,
                    #'active': di and di.active or sav_sans.active,
                    #'partner_id': di and di.partner_id.id or sav.partner_id.id,
                    #'address_id': di and di.address_id and di.address_id.id or sav.partner_id.id,
                    #'company_id': di and di.company_id and di.company_id.id or sav.company_id and sav.company_id.id,
                    #'note': note,
                    'tag_ids': [(6, 0, tag_ids)],
                    #'priority': di and di.priority or sav.priority,
                    #'user_id': di and di.user_id and di.user_id.id or sav.user_id and sav.user_id.id,
                    'date_next': date_next,
                    'date_fin': date_fin,
                    'intervention_ids': [(4, i_id, 0) for i_id in intervention_ids],
                    #'of_categorie_id': sav.of_categorie_id and sav.of_categorie_id.id,
                    #'of_canal_id': sav.of_canal_id and sav.of_canal_id.id,
                    #'parc_installe_id': di and di.parc_installe_id and di.parc_installe_id.id or
                    #                    sav.of_produit_installe_id and sav.of_produit_installe_id.id,
                    #'sav_id': sav.id,
                    #'payer_mode': payer_mode,
                    'type_id': sav_type.id,
                    'tache_id': sav_tache.id,
                }
                return di_vals
            # Ne pas toucher aux SAV déjà migrés
            # Mettre à jour les DI des SAV avec DI, créer des DI pour les autres
            sav_avec_di = service_obj.search([('sav_id', '!=', False)]).mapped('sav_id')\
                .filtered(lambda s: not s.is_migrated)
            sav_sans_di = sav_obj.search([('is_migrated', '=', False)]) - sav_avec_di

            for sav_avec in sav_avec_di:
                try:
                    di = service_obj.search([('sav_id', '=', sav_avec.id)], limit=1)
                    vals = get_vals(sav_avec, di)
                    di.write(vals)
                    sav_avec.is_migrated = True
                except Exception as e:
                    k = e.message or e.name
                    if not error_dict.get(k):
                        error_dict[k] = []
                    error_dict[k].append(sav_avec.id)
            for sav_sans in sav_sans_di:
                if not sav_sans.partner_id:
                    continue
                try:
                    vals = get_vals(sav_sans, False)
                    service_obj.create(vals)
                    sav_sans.is_migrated = True
                except Exception as e:
                    k = e.message or e.name
                    if not error_dict.get(k):
                        error_dict[k] = []
                    error_dict[k].append(sav_sans.id)

            if error_dict:
                _logger.error(u"OPENFIRE ERROR : migration des SAV dans les DI (T2356)")
                for kew in error_dict:
                    _logger.error(u"erreur pour les ids %s" % error_dict[kew])
                    _logger.error(u"%s" % kew)
            else:
                _logger.info(u"OPENFIRE SUCCÈS : migration des SAV dans les DI (T2356)")
                self.env['ir.config_parameter'].sudo().set_param('of_migration_sav_di', True)

    @api.multi
    def _compute_of_a_programmer_count(self):
        """Dû aux changement des services on n'utilise plus le système de récurrence inclus dans le service."""
        service_obj = self.env['of.service']
        for sav in self:
            sav.of_a_programmer_count = len(service_obj.search([('sav_id', '=', sav.id)]))

    @api.multi
    def action_view_a_programmer(self):
        self.ensure_one()
        action = self.env.ref('of_contract_custom.action_of_contract_service_form_planning').read()[0]
        action['domain'] = [('sav_id', '=', self.id)]
        action['context'] = {
            'default_partner_id': self.of_parc_installe_client_id.id,
            'default_address_id': self.of_parc_installe_lieu_id.id,
            'default_recurrence': False,
            'default_date_next': fields.Date.today(),
            'default_sav_id': self.id,
            'default_parc_installe_id': self.of_produit_installe_id.id,
            'default_origin': u"[SAV] " + self.name,
            'default_type_id': self.env.ref('of_contract_custom.of_contract_custom_type_sav').id,
        }
        return action

    @api.multi
    def action_prevoir_intervention(self):
        self.ensure_one()
        action = self.env.ref('of_contract_custom.action_of_contract_service_form_planning').read()[0]
        action['name'] = u"Prévoir une intervention"
        action['view_mode'] = "form"
        action['view_ids'] = False
        action['view_id'] = self.env['ir.model.data'].xmlid_to_res_id("of_contract_custom.view_of_contract_service_form")
        action['views'] = False
        action['target'] = "new"
        action['context'] = {
            'default_partner_id': self.of_parc_installe_client_id.id,
            'default_address_id': self.of_parc_installe_lieu_id.id,
            'default_recurrence': False,
            'default_date_next': fields.Date.today(),
            'default_sav_id': self.id,
            'default_parc_installe_id': self.of_produit_installe_id.id,
            'default_origin': u"[SAV] " + self.name,
            'default_type_id': self.env.ref('of_contract_custom.of_contract_custom_type_sav').id,
            }
        return action


class ProjectTags(models.Model):
    _inherit = "project.tags"

    @api.model_cr_context
    def _auto_init(self):
        u"""
        Fusion de project.tags dans of.planning.tag
        """
        cr = self._cr
        res = super(ProjectTags, self)._auto_init()
        # ce param de config est passé à True dans la fonction "migrer_sav_di"
        if not self.env['ir.config_parameter'].sudo().get_param('of_migration_sav_di'):
            # Créer les étiquettes de planning. Attention aux doublons!
            # Ne pas créer si il y a une étiquette planning du même nom
            cr.execute("INSERT INTO of_planning_tag "
                       "(name, color, create_uid, write_uid, create_date, write_date, active) "
                       "SELECT pt.name, pt.color, pt.create_uid, pt.write_uid, pt.create_date, pt.write_date, true "
                       "FROM project_tags AS pt "
                       "WHERE UPPER(pt.name) NOT IN (SELECT UPPER(name) FROM of_planning_tag);")
            # Connecter les étiquettes de planning aux services existants qui possèdent un SAV
            # en fonction des étiquettes de projet
            cr.execute(
                "INSERT INTO of_service_of_planning_tag_rel (service_id, tag_id) "
                "SELECT os.id, opt.id "
                "FROM of_service os "
                "JOIN project_issue_project_tags_rel pipt ON pipt.project_issue_id = os.sav_id "
                "JOIN project_tags pt ON pt.id = pipt.project_tags_id "
                "JOIN of_planning_tag opt ON UPPER(opt.name) = UPPER(pt.name) "
                "ON CONFLICT DO NOTHING;")
        return res
