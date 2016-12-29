# -*- coding: utf-8 -*-

u"""
Lancement du processus de migration
Ce fichier doit être importé en dernier
"""

from openerp import models, api#, sql_db

MAGIC_COLUMNS_FIELDS = ['user1.id_90', 'tab.create_date', 'user2.id_90', 'tab.write_date']
MAGIC_COLUMNS_FROM = ("LEFT JOIN res_users_61 AS user1 ON user1.id=tab.create_uid\n"
                      "LEFT JOIN res_users_61 AS user2 ON user2.id=tab.write_uid\n")
MAGIC_COLUMNS_VALUES = {
    'create_uid' : 'user1.id_90',
    'create_date': 'tab.create_date',
    'write_uid'  : 'user2.id_90',
    'write_date' : 'tab.write_date',
}

MAGIC_COLUMNS_TABLES = [
    ('user1', 'res_users_61', 'id', 'tab', 'create_uid'),
    ('user2', 'res_users_61', 'id', 'tab', 'write_uid'),
]

class Main(models.AbstractModel):
    _name = 'of.migration'

    @api.model
    def add_match_column(self, table_name):
        self._cr.execute("SELECT COUNT(*) FROM information_schema.columns "
                         "WHERE table_name=%s AND column_name='id_90';",
                         (table_name,))
        if self._cr.fetchone()[0]==1:
            return False
        self._cr.execute('ALTER TABLE "%s" ADD COLUMN "id_90" integer'% (table_name,))
        return True

    @api.model
    def model_data_mapping(self, table_name, model, model_90=False):
        u""" Remplit la colonne id_90 de table_name en matchant les xml_ids (noms dans ir_model_data)
        """
        self._cr.execute("UPDATE %s AS t61\n"
                         "SET id_90 = d90.res_id\n"
                         "FROM ir_model_data_61 AS d61\n"
                         "INNER JOIN ir_model_data AS d90\n"
                         "  ON d61.model = '%s'\n"
                         "  AND d90.model = '%s'\n"
                         "  AND d61.module = d90.module\n"
                         "  AND d61.name = d90.name\n"
                         "WHERE d61.res_id = t61.id" % (table_name, model, model_90 or model)
                         )

    @api.model
    def map_relation_table(self, table_name, field1, table_rel1, field2, table_rel2):
        self._cr.execute("INSERT INTO %s(%s, %s)\n"
                         "SELECT rel1.id_90, rel2.id_90\n"
                         "FROM %s_61 AS tab\n"
                         "INNER JOIN %s_61 AS rel1 ON rel1.id = tab.%s\n"
                         "INNER JOIN %s_61 AS rel2 ON rel2.id = tab.%s\n"
                         "WHERE rel1.id_90 IS NOT NULL\n"
                         "  AND rel2.id_90 IS NOT NULL" %
                         (table_name, field1, field2, table_name, table_rel1, field1, table_rel2, field2))

    @api.model
    def map_relation_field(self, model, field):
        obj = self.env[model]
        column = obj._columns[field]
        obj2 = self.env[column._obj]
        self.map_relation_table(column._rel, column._id1, obj._table, column._id2, obj2._table)

    def insert_values(self, object_name, values, tables_data, where_clause=""):
        u""" Fonction générique de migration de table
        
        @param object_name: Nom de l'objet à migrer
        @param values: Dictionnaire de valeurs {champ: valeur dans la requête SQL}
        @param tables_data: Liste des tables et jointures à utiliser : 
                            [(shortcut, table_name, clef de jointure, table de jointure, champ de la table de jointure)]
                            Les 3 derniers paramètres valent False pour une table non obtenue par jointure
                            Pour une jointure exotique, utiliser le modèle suivant :
                            [(shortcut, table_name, False, table de jointure, condition de jointure)]
        @param where_clause: Filtre where pour la requête SQL
        """
        obj = self.env[object_name]
        tables = set()
        fields = []
        # Filtre des champs absents de la db (module non installé)
        for field, value in values.iteritems():
            if field in obj._columns and obj._columns[field]._classic_write:
                fields.append(field)
                if value[0].isalpha():
                    # Recupération des tables utilisées, par des formules contenant 'table.champ'
                    for s in value.split():
                        tab = s.split('.')
                        if len(tab) == 2:
                            tables.add(tab[0])
        if not fields:
            return

        query = ("INSERT INTO %s(\"%s\")\n"
                 "SELECT %s\n"
                 "FROM %s\n"
                 "%s")

        # Préparation de la valeur FROM
        sep = ""
        from_clause = ""
        for tab, table, key, tab2, key2 in reversed(tables_data):
            if tab not in tables:
                continue
            if tab2:
                tables.add(tab2)
                if key:
                    from_clause = "LEFT JOIN %s AS %s ON %s.%s = %s.%s" % (table, tab, tab, key, tab2, key2) + sep + from_clause
                else:
                    from_clause = "LEFT JOIN %s AS %s ON %s" % (table, tab, key2) + sep + from_clause
                sep = "\n"
            else:
                from_clause = "%s AS %s" % (table, tab) + sep + from_clause
                sep = ",\n"

        self._cr.execute(query % (obj._table, '","'.join(fields), ",".join([values[field] for field in fields]), from_clause, where_clause and "WHERE "+where_clause))

    def show_property_fields(self):
        print "Liste des fields.property"
        for model in self.env:
            obj = self.env[model]
            for field_name, field in obj._columns.iteritems():
                try:
                    company_dependent = field.to_field_args().get('company_dependent', False)
                except:
                    continue
                if company_dependent:
                    print "%s.%s (%s, %s)" % (model, field_name, field._type, getattr(field, '_obj', '?'))

    @api.model
    def process(self):
#         # Connection a la base 6.1
#         db_name = "%s_61" % self._cr.dbname
#         cr_61 = sql_db.db_connect(db_name)

        self.show_property_fields()
#         return True

        # Nettoyage de ir_model_data_61
        self._cr.execute("DELETE FROM ir_model_data_61 "
                         "WHERE module='__export__' "
                         "AND name LIKE TEXTCAT(translate(model,'.','_'), '\_%\_%')")
        self._cr.commit()

        modules = (
            'base',
            'product',
            'account',
            'sale',

            'mail',
            'post_process',   # Migration des fields.property, workflow, ir.attachment
        )

        for module in modules:
            tables = eval('self.import_module_%s()' % module)
            for table in tables:
                if self.add_match_column(table+'_61'):
                    print "-- %s --" % table
                    message = eval('self.import_%s()' % table)
                    # Ajouter dans les logs : 
                    # message
                    print message
                    self._cr.commit()
                else:
                    pass
                    # Ajouter dans les logs : 
                    # u"Migration déjà effectuée"

        # Migration des fields.property

        return True
