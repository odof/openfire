======================
OF datastore connector
======================

Module OpenFire de connexion à une base Odoo.
----------------------------------------------

C'est un module socle apportant une classe abstraite permettant de se connecter à une autre base odoo.

Il est nécessaire de créer un module/objet qui en hérite pour créer un connecteur et accéder aux différentes fonctions.

Exemple :

.. code-block:: python

    class MyConnectorObject(models.Model):
        _name = 'my.connector.object'
        _inherit = 'of.datastore.connector'
        _description = "My connector object"
        _rec_name = 'db_name'
        _order = 'db_name'


        def test_get_partners_names(self):
            """ Get partners names from the other database """
            for record in self:
                client = record.of_datastore_connect()
                if isinstance(client, str):
                    raise UserError("Connection error : %s" % client)

            ds_partner_obj = record.of_datastore_get_model(client, 'res.partner')

            partners = record.of_datastore_search_read(ds_partner_obj,  [], ['name'])
            return partners
