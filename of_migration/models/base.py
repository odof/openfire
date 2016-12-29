# -*- coding: utf-8 -*-

from openerp import models, api
from main import MAGIC_COLUMNS_VALUES, MAGIC_COLUMNS_TABLES

class import_base(models.AbstractModel):
    _inherit = "of.migration"

    @api.model
    def import_res_country(self):
        self._cr.execute("UPDATE res_country_61 AS c61 SET id_90 = c90.id\n"
                         "FROM res_country AS c90\n"
                         "WHERE c90.code = c61.code")

    @api.model
    def import_res_country_state(self):
        self._cr.execute("UPDATE res_country_state_61 AS s61 SET id_90 = s90.id\n"
                         "FROM res_country_state AS s90\n"
                         "LEFT JOIN res_country_61 AS c61 ON c61.id_90 = s90.country_id\n"
                         "WHERE s90.code = s61.code AND s61.country_id = c61.id")

    @api.model
    def import_res_company(self):
        """
        Normalement les sociétés sont créées à la main.
        On fait uniquement un matching
        """
        cr = self._cr
        # Matching des societes par nom
        cr.execute("UPDATE res_company_61 AS c61\n"
                   "SET id_90 = c90.id\n"
                   "FROM res_company AS c90\n"
                   "WHERE c90.name = c61.name")
        cr.execute("SELECT name FROM res_company_61 WHERE id_90 IS NULL")
        rows = cr.fetchall()
        if not rows:
            return "Import res_company ok"

        # Si plusieurs societes n'ont pas matché, on retourne une erreur
        if len(rows) > 1:
            raise ValueError(u"Pas de correspondance trouvée pour la société %s" % rows[0][0])
        cr.execute("SELECT id,name FROM res_company WHERE id NOT IN (SELECT id_90 FROM res_company_61)")
        rows2 = cr.fetchall()
        # Si une seule société n'a pas matché, mais que plusieurs sociétés 9.0 sont candidates, on retourne une erreur
        if len(rows2) != 1:
            raise ValueError(u"Pas de correspondance trouvée pour la société %s" % rows[0][0])
        # Si une seule societe n'a pas matché et une seule societe 9.0 est candidate, on les associe
        cr.execute("UPDATE res_company_61 SET id_90=%s WHERE id_90 IS NULL" % rows2[0][0])
        return 'Import res_company avec association forcée "%s" avec "%s"' % (rows[0][0], rows2[0][1])

    def import_sale_shop(self):
        # @todo: Effectuer la migration
        cr = self._cr
        # Matching des societes par nom
        cr.execute("UPDATE sale_shop_61 AS shop\n"
                   "SET id_90 = c90.id\n"
                   "FROM res_company AS c90\n"
                   "WHERE c90.name = shop.name")
        cr.execute("SELECT name FROM sale_shop_61 WHERE id_90 IS NULL LIMIT 1")
        rows = cr.fetchall()
        if rows:
            raise ValueError(u"Pas de correspondance trouvée pour le magasin %s" % rows[0][0])

    @api.model
    def import_res_users(self):
        """
        Import des utilisateurs
        Correspondances de droits à réaliser ensuite
        Dans un premier temps, pour la base OpenFire, un simple matching suffira
        """
        cr = self._cr
        cr.execute("UPDATE res_users_61 AS u61 "
                   "SET id_90 = u90.id "
                   "FROM res_users AS u90 "
                   "WHERE u90.login = u61.login")
        # @todo: Creation des utilisateurs manquants
        cr.execute("SELECT login FROM res_users_61 WHERE id_90 IS NULL")
        rows = cr.fetchall()
        if rows:
            raise ValueError(u"Un utilisateur n'a pas été préalablement créé : login '%s'" % rows[0][0])

    @api.model
    def import_res_partner(self):
        # @todo: Effectuer la migration
        cr = self._cr
        # Suppression ligne d'export ir_model_data du main partner
        cr.execute("DELETE FROM ir_model_data_61 "
                   "WHERE model='res.partner' "
                   "  AND name != 'main_partner' "
                   "  AND res_id IN (SELECT res_id FROM ir_model_data_61 "
                   "                 WHERE model='res.partner' "
                   "                 AND name='main_partner');")

        self.model_data_mapping('res_partner_61', 'res.partner')

        # Pour les partenaires restants, on fait un matching au niveau du nom
        cr.execute("UPDATE res_partner_61 AS p61 "
                   "SET id_90 = p90.id "
                   "FROM res_partner AS p90 "
                   "WHERE p61.id_90 IS NULL "
                   "  AND p90.name ILIKE p61.name "
                   "  AND p90.parent_id IS NULL")

        cr.execute("SELECT id, name FROM res_partner_61 WHERE id_90 IS NULL")
        rows = cr.fetchall()
        if rows:
            if len(rows) == 1:
                raise ValueError(u"Un partenaire n'a pas pu être associé : %s" % (tuple(rows[0]),))
            else:
                raise ValueError(u"%s partenaires n'ont pas pu être associés : %s" % (len(rows), tuple(rows)))

    @api.model
    def import_res_partner_address(self):
        # @todo: Effectuer la migration
        cr = self._cr
        self.model_data_mapping('res_partner_address_61', 'res.partner.address', 'res.partner')

        # Pour les adresses restantes, on recupere le matching du partenaire lié
        cr.execute("UPDATE res_partner_address_61 AS a61 "
                   "SET id_90 = p61.id_90 "
                   "FROM res_partner_61 AS p61 "
                   "WHERE p61.id = a61.partner_id "
                   "  AND a61.id_90 IS NULL")

        cr.execute("SELECT id, name FROM res_partner_address_61 WHERE id_90 IS NULL")
        rows = cr.fetchall()
        if rows:
            print rows
            print len(rows)
            raise ValueError(u"Une adresse de partenaire n'a pas pu être associée : %s" % (tuple(rows[0]),))

    @api.model
    def import_res_bank(self):
        # @todo: Effectuer la migration
        self.model_data_mapping('res_bank_61', 'res.bank')

        cr = self._cr

        # Association des res_bank_61 aux res_bank 9.0
        cr.execute("UPDATE res_bank_61 SET id_90 = nextval('res_bank_id_seq') WHERE id_90 IS NULL")

        fields_90 = ['city', 'fax', 'name', 'zip', 'country', 'street2', 'bic', 'phone', 'state', 'street', 'active', 'email']

        values = {field: "tab."+field for field in fields_90}
        values.update({
            'id'        : 'tab.id_90',
            'country'   : 'country.id_90',
            'state'     : 'state.id_90',
        })
        values.update(MAGIC_COLUMNS_VALUES)

        tables = [
            ('tab', 'res_bank_61', False, False, False),
            ('country', 'res_country_61', 'id', 'tab', 'country'),
            ('state', 'res_country_state_61', 'id', 'tab', 'state'),
        ] + MAGIC_COLUMNS_TABLES

        where_clause = "tab.id_90 NOT IN (SELECT DISTINCT id FROM res_bank)"

        self.insert_values('res.bank', values, tables, where_clause=where_clause)

    @api.model
    def import_res_partner_bank(self):
        # Note : en 9.0 le compte bancaire devient unique (sanitized_acc_number)
        # Il faut donc fusionner les doublons
        cr = self._cr

        # Ajout et calcul de sanitized_acc_number dans la table 6.1
        cr.execute('ALTER TABLE "res_partner_bank_61" ADD COLUMN "sanitized_acc_number" character varying')
        cr.execute("UPDATE res_partner_bank_61 SET sanitized_acc_number = upper(regexp_replace(acc_number, '\W+', '', 'g'))") # Flag 'g' pour remplacer toutes les occurences

        # Association des res_partner_bank_61 aux res_partner_bank 9.0 déjà créés
        cr.execute("UPDATE res_partner_bank_61 AS b SET id_90 = b90.id\n"
                   "FROM res_partner_bank AS b90\n"
                   "WHERE b.sanitized_acc_number = b90.sanitized_acc_number")

        # Association des res_partner_bank_61 aux res_partner_bank 9.0 à créer
        # id_90 n'est renseigné que pour une occurence des sanitized_acc_number. les doublons sont gérés en fin de fonction
        cr.execute("UPDATE res_partner_bank_61 SET id_90 = nextval('res_partner_bank_id_seq')\n"
                   "WHERE id IN (SELECT min(id) FROM res_partner_bank_61 GROUP BY sanitized_acc_number)\n"
                   "  AND sanitized_acc_number NOT IN (SELECT sanitized_acc_number FROM res_partner_bank_61 WHERE id_90 IS NOT NULL)")

        fields_90 = ['sequence', 'company_id', 'sanitized_acc_number', 'acc_number', 'partner_id', 'bank_id']

        values = {field: "tab."+field for field in fields_90}
        values.update({
            'id'                  : 'tab.id_90',
            'company_id'          : 'comp.id_90',
            'partner_id'          : 'partner.id_90',
            'bank_id'             : 'bank.id_90',
        })
        values.update(MAGIC_COLUMNS_VALUES)

        tables = [
            ('tab', 'res_partner_bank_61', False, False, False),
            ('comp', 'res_company_61', 'id', 'tab', 'company_id'),
            ('partner', 'res_partner_61', 'id', 'tab', 'partner_id'),
            ('bank', 'res_bank_61', 'id', 'tab', 'bank'),
        ] + MAGIC_COLUMNS_TABLES

        where_clause = ("tab.id_90 IS NOT NULL\n"
                        "  AND tab.id_90 NOT IN (SELECT id FROM res_partner_bank)")

        self.insert_values('res.partner.bank', values, tables, where_clause=where_clause)

        # Definition du id_90 des doublons
        cr.execute("UPDATE res_partner_bank_61 AS b SET id_90 = b2.id_90\n"
                   "FROM res_partner_bank_61 AS b2\n"
                   "WHERE b.id_90 IS NULL AND b2.id_90 IS NOT NULL AND b.sanitized_acc_number = b2.sanitized_acc_number") 

    @api.model
    def import_res_currency(self):
        cr = self._cr
        cr.execute("UPDATE res_currency_61 AS c61 "
                   "SET id_90 = c90.id "
                   "FROM res_currency AS c90 "
                   "WHERE c90.name = c61.name")

    def import_ir_sequence(self):
        cr = self._cr
        self.model_data_mapping('ir_sequence_61', 'ir.sequence')

        # En 6.1 account_sequence n'est référencé que par account_journal.sequence_id
        # Récupération des séquences utilisées
        cr.execute("SELECT DISTINCT sequence_id FROM account_journal_61 WHERE sequence_id IS NOT NULL")
        sequence_ids = [row[0] for row in cr.fetchall()]

        # On récupère aussi toutes les séquences créées "manuellement" (ou du moins pas en xml)
        cr.execute("SELECT DISTINCT s.id, implementation FROM ir_sequence_61 AS s "
                   "LEFT JOIN ir_model_data_61 AS d "
                   "  ON d.model='ir.sequence' "
                   "  AND d.res_id = s.id "
                   "WHERE s.id_90 IS NULL "
                   "  AND (d.id IS NULL OR s.id in %s)", (tuple(sequence_ids),))

        fields_90 = ["company_id", "code", "name", "number_next", "implementation", "padding", "number_increment", "prefix", "active", "suffix"]

        values = {field: "tab."+field for field in fields_90}
        values.update({
            'id'        : 'tab.id_90',
            'company_id': 'comp.id_90',
        })
        values.update(MAGIC_COLUMNS_VALUES)

        where_clause = "tab.id = %s"

        tables = [
            ('tab', 'ir_sequence_61', False, False, False),
            ('comp', 'res_company_61', 'id', 'tab', 'company_id'),
        ] + MAGIC_COLUMNS_TABLES

        for sequence_id_61, impl in cr.fetchall():
            cr.execute("SELECT nextval('ir_sequence_id_seq')")
            sequence_id = cr.fetchone()[0]

            # Lien avec la séquence 6.1
            cr.execute("UPDATE ir_sequence_61 SET id_90=%s WHERE id=%s" % (sequence_id, sequence_id_61))

            self.insert_values('ir.sequence', values, tables, where_clause=where_clause % sequence_id_61)

            # Création de la table de séquence
            if impl == 'standard':
                cr.execute("SELECT last_value, is_called, increment_by FROM ir_sequence_%03d_61" % sequence_id_61)
                last_value, is_called, increment = cr.fetchone()

                cr.execute("CREATE SEQUENCE ir_sequence_%03d INCREMENT BY %s START WITH %s" % (sequence_id, increment, last_value+is_called))

    def import_ir_model_fields(self):
        cr = self._cr
        # Matching par nom de champ
        cr.execute("UPDATE ir_model_fields_61 AS f61\n"
                   "SET id_90 = f90.id\n"
                   "FROM ir_model_fields AS f90\n"
                   "WHERE f90.model = f61.model\n"
                   "  AND f90.name = f61.name")

        # Ajout des champs dont le prefixe _id a été ajouté en v9.0
        cr.execute("UPDATE ir_model_fields_61 AS f61\n"
                   "SET id_90 = f90.id\n"
                   "FROM ir_model_fields AS f90\n"
                   "WHERE f61.id_90 IS NULL\n"
                   "  AND f90.model = f61.model\n"
                   "  AND f90.name = TEXTCAT(f61.name, '_id')")


    @api.model
    def import_module_base(self):
        return (
            'res_country',
            'res_country_state',
            'res_company',
            'sale_shop',
            'res_users',
            'res_partner',
            'res_partner_address',
            'res_bank',
            'res_partner_bank',
            'res_currency',
            'ir_sequence',
            'ir_model_fields',
        )
