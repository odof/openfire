# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging

from odoo import api

_logger = logging.getLogger(__name__)


class DS_CACHE:
    """
    Classe de gestion du cache ds_cache

    C'est le même cache utilisé par Odoo, il reste juste persistant jusqu'à la prochaine mise à jour de module
    `of_datastore` ou au démarrage d'odoo.
    """

    cache = {}
    columns = {}
    prefetchs = {}

    @classmethod
    def clear_cache(cls, dbname):
        _logger.info("Nettoyage du ds_cache...")
        cls.cache[dbname] = api.Cache()
        cls.columns[dbname] = {}
        cls.prefetchs[dbname] = {}

    @classmethod
    def get_cache(cls, dbname):
        return cls.cache[dbname]

    # Les méthodes suivantes permettent de stocker dans le ds_cache les champs disponibles sur un objet distant pour
    # ne pas redemander à la base distante à chaque besoin.

    @classmethod
    def get_column(cls, dbname, model):
        if columns := cls.columns[dbname].get(model, False):
            return columns
        cls.columns[dbname][model] = []
        return []

    @classmethod
    def set_column(cls, dbname, model, fields):
        cls.columns[dbname][model] = fields

    # Les méthodes suivantes permettent de savoir si un recordset est déjà prefetch dans le ds_cache, pour éviter des
    # nouveaux appels à la base distante.

    @classmethod
    def set_prefetch(cls, dbname, model, res_id):
        if cls.prefetchs[dbname].get(model, False):
            cls.prefetchs[dbname][model][res_id] = True
        else:
            cls.prefetchs[dbname][model] = {res_id: True}

    @classmethod
    def is_prefetch(cls, dbname, model, res_id):
        if pf_model := cls.prefetchs[dbname].get(model, False):
            return pf_model.get(res_id, False)
        else:
            return False
