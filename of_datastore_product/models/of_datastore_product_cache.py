# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, fields, api, registry
from odoo.tools.safe_eval import safe_eval
from odoo.addons.of_utils.models.of_utils import BigInteger

from contextlib import contextmanager
from threading import Lock


class OfDatastoreCache(models.TransientModel):
    # Odoo V10 a un code javascript très sale (quasi totalement réécrit en V11)
    # Lors de la saisie d'un kit, pour une seule ligne de composant saisie,
    # il appelle 3 fois name_get() et 3 fois onchange() !
    # Cela est ensuite multiplié par le nombre de lignes saisies (raffraichissement de la vue liste)
    # Le temps d'affichage est alors énorme...
    # Faute de retravailler le javascript, nous allons mettre les données recueillies dans un cache, ce qui limitera les
    #   appels aux bases centrales
    _name = 'of.datastore.cache'
    _datastore_cache_locks = {'main': Lock()}

    model = fields.Char(string='Model', required=True)
    res_id = BigInteger(string='Resource id', required=True)
    company_id = fields.Many2one('res.company', string=u"Société", required=True)
    vals = fields.Char(string='Values', help="Dictionnary of values for this object", required=True)

    @contextmanager
    def _get_cache_token(self, key, blocking=True):
        """
        Fonction de jeton permettant d'éviter à différents threads d'accéder simultanément à la même clef.
        Ainsi, si plusieurs threads veulent récupérer les mêmes données sur une base centrale,
          seul le premier sera autorisé à le faire pendant que les autres attendront le résultat.
        @param key: clef permettant d'identifier un jeton
                    (dans la pratique il s'agit de l'id du connecteur à la base centrale)
        @param blocking: Si vrai, le processus attendra jusqu'à la libération du jeton,
                         si faux la fonction renverra faux si le jeton n'est pas disponible.
        @return: Le modèle 'of.datastore.cache' avec un nouveau cursor si le jeton a pu être obtenu, faux sinon
        """
        if key not in self._datastore_cache_locks:
            self._datastore_cache_locks['main'].acquire()
            if key not in self._datastore_cache_locks:
                self._datastore_cache_locks[key] = Lock()
            self._datastore_cache_locks['main'].release()

        acquired = self._datastore_cache_locks[key].acquire(blocking)
        try:
            if acquired:
                cr = registry(self._cr.dbname).cursor()
                result = self.env(cr=cr)['of.datastore.cache']
            yield result
            cr.commit()
        finally:
            if acquired:
                try:
                    cr.close()
                except Exception:
                    pass
                self._datastore_cache_locks[key].release()

    @api.model
    def store_values(self, model, vals):
        """ Fonction de mise à jour du cache.
        Cette fonction ne devrait jamais être appelée sans avoir au préalable acquis un token avec _get_cache_token
        """
        model_obj = self.env[model]
        res_ids = [v['id'] for v in vals]
        company = self.env.user.company_id
        if hasattr(company, 'accounting_company_id'):
            # Utilisation de la société comptable si le module of_base_multicompany est installé
            company = company.accounting_company_id
        stored = {
            ds_cache.res_id: ds_cache
            for ds_cache in self.search(
                [('model', '=', model), ('company_id', '=', company.id), ('res_id', 'in', res_ids)])
        }
        for v in vals:
            # Les champs calculés ne doivent pas être stockés
            v = {key: val for key, val in v.iteritems() if not model_obj._of_datastore_is_computed_field(key)}

            ds_cache = stored.get(v['id'])
            v = model_obj._convert_to_cache(v, update=True, validate=False)
            res_id = v.pop('id')
            if ds_cache:
                ds_cache_vals = safe_eval(ds_cache.vals)
                ds_cache_vals.update(v)
                # Appel explicite de write, une affectation avec '=' ne marcherait pas si on est dans un on_change
                ds_cache.write({'vals': str(ds_cache_vals)})
            else:
                self.create({
                    'model': model,
                    'res_id': res_id,
                    'company_id': company.id,
                    'vals': str(v),
                })

    @api.model
    def apply_values(self, record):
        record.ensure_one()

        # Nouveau curseur pour récupérer les données en DB indépendamment de ce processus.
        # Indispensable dans la mesure où store_values() s'applique sur un curseur séparé, généré par _get_cache_token()
        cr = registry(self._cr.dbname).cursor()

        # Société, utilisée dans la clef en raison des champs company-dependent
        company = record.env.user.company_id
        if hasattr(company, 'accounting_company_id'):
            # Utilisation de la société comptable si le module of_base_multicompany est installé
            company = company.accounting_company_id

        # Requête SQL pour gagner en performance
        cr.execute(
            "SELECT vals FROM of_datastore_cache WHERE model = %s AND company_id = %s AND res_id = %s",
            (record._name, company.id, record.id))
        vals = cr.fetchall()
        cr.close()
        if vals:
            vals = safe_eval(vals[0][0])
            record._cache.update(record._convert_to_cache(vals, validate=False))
