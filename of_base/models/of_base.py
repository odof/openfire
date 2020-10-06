# -*- coding: utf-8 -*-

from odoo import models, api, tools, fields, SUPERUSER_ID, _
from odoo.exceptions import AccessError
from odoo.tools import OrderedSet


class IrModelFields(models.Model):
    _inherit = 'ir.model.fields'

    of_custom_groupby = fields.Boolean(string=u"Autorisation forcée pour le regroupement")


class OfReadGroup(models.AbstractModel):
    """
    Cette classe permet d'effectuer un read_group sur un champ qui ne serait normalement pas accepté par Odoo.
    Normalement, un read_group ne peut être effectué que sur un champ ayant le paramètre store=True.
    Une classe héritant de of.readgroup peut en plus autoriser cette fonction sur les champs ayant le paramètre
    of_custom_groupby.
    Il faut ensuite surcharger _read_group_process_groupby afin de modifier la query et de retourner les
    éléments nécessaire à son interprétation.
    """
    _name = 'of.readgroup'

    @api.model
    def _read_group_raw(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        self.check_access_rights('read')
        query = self._where_calc(domain)
        fields = fields or [f.name for f in self._fields.itervalues() if f.store]

        groupby = [groupby] if isinstance(groupby, basestring) else list(OrderedSet(groupby))
        groupby_list = groupby[:1] if lazy else groupby
        annotated_groupbys = [self._read_group_process_groupby(gb, query) for gb in groupby_list]
        groupby_fields = [g['field'] for g in annotated_groupbys]
        order = orderby or ','.join([g for g in groupby_list])
        groupby_dict = {gb['groupby']: gb for gb in annotated_groupbys}

        self._apply_ir_rules(query, 'read')
        for gb in groupby_fields:
            assert gb in fields, "Fields in 'groupby' must appear in the list of fields to read (perhaps it's missing in the list view?)"
            assert gb in self._fields, "Unknown field %r in 'groupby'" % gb
            gb_field = self._fields[gb].base_field
            # Modification OpenFire : Un champ custom peut ne pas être présent en base de données
            if not getattr(gb_field, 'of_custom_groupby', False):
                assert gb_field.store and gb_field.column_type, "Fields in 'groupby' must be regular database-persisted fields (no function or related fields), or function fields with store=True"

        aggregated_fields = [
            f for f in fields
            if f != 'sequence'
            if f not in groupby_fields
            for field in [self._fields.get(f)]
            if field
            if field.group_operator
            if field.base_field.store and field.base_field.column_type
        ]

        field_formatter = lambda f: (
            self._fields[f].group_operator,
            self._inherits_join_calc(self._table, f, query),
            f,
        )
        select_terms = ['%s(%s) AS "%s" ' % field_formatter(f) for f in aggregated_fields]

        for gb in annotated_groupbys:
            select_terms.append('%s as "%s" ' % (gb['qualified_field'], gb['groupby']))

        groupby_terms, orderby_terms = self._read_group_prepare(order, aggregated_fields, annotated_groupbys, query)
        from_clause, where_clause, where_clause_params = query.get_sql()
        if lazy and (len(groupby_fields) >= 2 or not self._context.get('group_by_no_leaf')):
            count_field = groupby_fields[0] if len(groupby_fields) >= 1 else '_'
        else:
            count_field = '_'
        count_field += '_count'

        prefix_terms = lambda prefix, terms: (prefix + " " + ",".join(terms)) if terms else ''
        prefix_term = lambda prefix, term: ('%s %s' % (prefix, term)) if term else ''

        query = """
            SELECT min(%(table)s.id) AS id, count(%(table)s.id) AS %(count_field)s %(extra_fields)s
            FROM %(from)s
            %(where)s
            %(groupby)s
            %(orderby)s
            %(limit)s
            %(offset)s
        """ % {
            'table': self._table,
            'count_field': count_field,
            'extra_fields': prefix_terms(',', select_terms),
            'from': from_clause,
            'where': prefix_term('WHERE', where_clause),
            'groupby': prefix_terms('GROUP BY', groupby_terms),
            'orderby': prefix_terms('ORDER BY', orderby_terms),
            'limit': prefix_term('LIMIT', int(limit) if limit else None),
            'offset': prefix_term('OFFSET', int(offset) if limit else None),
        }
        self._cr.execute(query, where_clause_params)
        fetched_data = self._cr.dictfetchall()

        if not groupby_fields:
            return fetched_data

        # Modif OpenFire : Recherche directe du nom par name_get sur l'objet ciblé
        #  (la méthode standart Odoo procédait par lecture du champ sur l'objet courant,
        #   ce qui est impossible dans le cadre d'un champ one2many)
        for gb in annotated_groupbys:
            if gb['type'] == 'many2one':
                gb_field = gb['field']
                rel = self._fields[gb_field].base_field.comodel_name
                gb_obj = self.env[rel]
                gb_ids = [r[gb_field] for r in fetched_data if r[gb_field]]
                gb_dict = {d[0]: d for d in gb_obj.browse(gb_ids).name_get()}
                for d in fetched_data:
                    d[gb_field] = gb_dict.get(d[gb_field], False)

        data = map(lambda r: {k: self._read_group_prepare_data(k, v, groupby_dict) for k, v in r.iteritems()}, fetched_data)
        result = [self._read_group_format_result(d, annotated_groupbys, groupby, domain) for d in data]
        if lazy:
            # Right now, read_group only fill results in lazy mode (by default).
            # If you need to have the empty groups in 'eager' mode, then the
            # method _read_group_fill_results need to be completely reimplemented
            # in a sane way
            result = self._read_group_fill_results(
                domain, groupby_fields[0], groupby[len(annotated_groupbys):],
                aggregated_fields, count_field, result, read_group_order=order,
            )
        return result

    @api.model_cr_context
    def _field_create(self):
        """
        Ajoute la mise à jour de of_custom_groupby dans la table ir_model_fields
        """
        super(OfReadGroup, self)._field_create()
        cr = self._cr
        for field in self._fields.itervalues():
            query = "UPDATE ir_model_fields SET of_custom_groupby=%s WHERE model=%s AND name=%s"
            cr.execute(query, (getattr(field, 'of_custom_groupby', False), self._name, field.name))

    @api.model
    def _generate_order_by_inner(self, alias, order_spec, query, reverse_direction=False, seen=None):
        """
        Fonction identique à la fonction définie dans models.py, à l'exception de la zone spécifiée.
        Permet d'ordonner les résultats d'une requête en fonction de champs avec of_custom_groupby=True.
        Nécessite que la fonction of_custom_groupby_generate_order soit surchargée pour chacun de ces champs.
        """
        if seen is None:
            seen = set()
        self._check_qorder(order_spec)

        order_by_elements = []
        for order_part in order_spec.split(','):
            order_split = order_part.strip().split(' ')
            order_field = order_split[0].strip()
            order_direction = order_split[1].strip().upper() if len(order_split) == 2 else ''
            if reverse_direction:
                order_direction = 'ASC' if order_direction == 'DESC' else 'DESC'
            do_reverse = order_direction == 'DESC'

            field = self._fields.get(order_field)
            if not field:
                raise ValueError(_("Sorting field %s not found on model %s") % (order_field, self._name))

            if order_field == 'id':
                order_by_elements.append('"%s"."%s" %s' % (alias, order_field, order_direction))
            else:
                if field.inherited:
                    field = field.base_field
                if field.store and field.type == 'many2one':
                    key = (field.model_name, field.comodel_name, order_field)
                    if key not in seen:
                        seen.add(key)
                        order_by_elements += self._generate_m2o_order_by(alias, order_field, query, do_reverse, seen)
                elif field.store and field.column_type:
                    qualifield_name = self._inherits_join_calc(alias, order_field, query, implicit=False, outer=True)
                    if field.type == 'boolean':
                        qualifield_name = "COALESCE(%s, false)" % qualifield_name
                    order_by_elements.append("%s %s" % (qualifield_name, order_direction))
                # OF Modification OpenFire
                elif getattr(field, 'of_custom_groupby', False):
                    key = (field.model_name, field.comodel_name, order_field)
                    if key not in seen:
                        seen.add(key)
                        order_by_elements += self.of_custom_groupby_generate_order(
                            alias, order_field, query, do_reverse, seen)
                # Fin modification OpenFire
                else:
                    continue  # ignore non-readable or "non-joinable" fields

        return order_by_elements

    @api.model
    def of_custom_groupby_generate_order(self, alias, order_field, query, do_reverse, seen):
        """
        Fonction à surcharger pour ajouter des jointures dans query et retourner un ordre de tri.
        Le format de retour est le même que celui de _generate_order_by_inner()
        """
        return []


class ResUsers(models.Model):
    _inherit = "res.users"

    @api.model
    @tools.ormcache('self._uid')
    def context_get(self):
        # Pour désactiver l'envoi des notifications par courriel des changements d'affectation des commandes et factures.
        # On met par défaut dans le contexte des utilisateurs la valeur mail_auto_subscribe_no_notify qui inhibe l'envoi des notifications dans la fonction _message_auto_subscribe_notify() de /addons/mail/models.mail_thread.py.
        result = super(ResUsers, self).context_get()
        result['mail_auto_subscribe_no_notify'] = 1
        return result

    @api.multi
    def write(self, values):
        if SUPERUSER_ID in self._ids and self._uid != SUPERUSER_ID:
            raise AccessError(u'Seul le compte administrateur peut modifier les informations du compte administrateur.')
        return super(ResUsers, self).write(values)


class Module(models.Model):
    _inherit = 'ir.module.module'

    @api.multi
    def button_immediate_upgrade(self):
        super(Module, self).button_immediate_upgrade()
        # Dans le cadre d'une mise à jour de module, on souhaite rester sur la page courante.
        # On retourne donc une action de rechargement de la page sans spéficier de menu.
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }


class MailComposer(models.TransientModel):
    _inherit = 'mail.compose.message'

    # Store True pour éviter le recalcul lors de l'appui sur n'importe quel bouton.
    of_computed_body = fields.Html(string=u'Contenu calculé', compute='_compute_of_computed_body', sanitize_style=True, strip_classes=True, store=True)

    # Calcul des champs dans mail, mail_compose_message.py : render_message()
    @api.depends()
    def _compute_of_computed_body(self):
        for composer in self:
            composer.of_computed_body = composer.render_message([composer.res_id])[composer.res_id]['body']

    @api.multi
    def button_reload_computed_body(self):
        self._compute_of_computed_body()
        return {"type": "ir.actions.do_nothing"}

    # Permet à l'auteur du mail de le recevoir en copie si le paramètre du modèle est vrai.
    @api.multi
    def send_mail_action(self):
        res = super(MailComposer, self.with_context(mail_notify_author=self.template_id and self.template_id.of_copie_expediteur)).send_mail_action()
        return res


class MailTemplate(models.Model):
    _inherit = 'mail.template'

    of_copie_expediteur = fields.Boolean(string=u"Copie du mail à l'expéditeur")


class ResCompany(models.Model):
    _inherit = "res.company"

    of_juridique = fields.Char(string="Forme juridique")
    of_capital = fields.Char(string="Capital social")
    of_assu_dec = fields.Char(string=u"Assurance décennale")


class BaseConfigSettings(models.TransientModel):

    _inherit = 'base.config.settings'

    @api.model_cr_context
    def _auto_init(self):
        super(BaseConfigSettings, self)._auto_init()
        if not self.env['ir.values'].search([('name', '=', 'of_affichage_ville'), ('model', '=', 'base.config.settings')]):
            self.env['ir.values'].sudo().set_default('base.config.settings', 'of_affichage_ville', True)

    of_affichage_ville = fields.Boolean(
        string="(OF) Afficher ville",
        help=u"Affiche la ville entre parenthèses après le nom du partenaire lors de la recherche de partenaire")

    @api.multi
    def set_of_affichage_ville_defaults(self):
        return self.env['ir.values'].sudo().set_default('base.config.settings', 'of_affichage_ville', self.of_affichage_ville)

    @api.model
    def get_default_company_share_partner(self, fields):
        return {
            'company_share_partner': not self.env.ref('of_base.of_base_res_partner_rule').active
        }

    @api.multi
    def set_default_company_share_partner(self):
        partner_rule = self.env.ref('of_base.of_base_res_partner_rule')
        for config in self:
            partner_rule.write({'active': not config.company_share_partner})
