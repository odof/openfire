import logging

import graphene

from odoo import Command
from odoo.exceptions import AccessError

logger = logging.getLogger(__name__)


def lazy_delete(env, model, id):
    object = env[model].search([('id', '=', id)])
    if object:
        object.unlink()
        return object

    return env[model]


def convertImage(datas):
    datas = datas.split(",")
    if len(datas) > 1:
        datas = datas[1]
    else:
        datas = datas[0]
    return datas


def many2one(self, model, input):
    # cette méthode retourne l'id du many2one crée ou mis à jour selon la présence ou non
    # d'un id dans input
    obj = self.env[model]
    obj_values = obj._prepare_mutation_values(**input)
    if input.id:
        record = obj.search([('id', '=', input.id)])
        if record:
            if len(obj_values.keys()) > 0:
                record.write(obj_values)
            return record.id
        else:
            raise AccessError(f"Unable to find object ({model}) with id: {input.id}")
    else:
        if len(obj_values.keys()) > 0:
            record = obj.create(obj_values)
            return record.id
        else:
            return False


def x2many(self, model, input, default=False, keep=False):
    # cette méthode retourne une liste de Command pour les one2many/many2many
    # parent_id est l'id de l'enregistrement parent
    # default est un dict qui contient les valeurs par défaut que l'on souhaite ajouter à chaque ligne
    # keep permet de préciser si les nouvelles lignes sont ajoutées aux lignes existantes du x2many
    # ou bien si on supprime les lignes existantes avant d'ajouter les nouvelles
    obj = self.env[model]
    res = []
    res_ids = []
    creates = []
    if type(default) is bool:
        default = {}

    if type(input) is not list:
        input = [input]

    if len(input) == 0:
        return [Command.clear()]

    logger.info(input)

    for record in input:
        record_value = default.copy()
        values = obj._prepare_mutation_values(**record)
        record_value.update(values)
        if record.id:
            if not obj.search([('id', '=', record.id)]):
                raise AccessError(f"Unable to find object ({model}) with id: {record.id}")
            record = obj.search([('id', '=', record.id)])
            if len(record_value.keys()) > 0:
                record.write(record_value)
            res_ids.append(record.id)

        else:
            creates += [record_value]
            # record = obj.create(record_value)
            # res_ids.append(record.id)

    if keep:
        for id in res_ids:
            res.append(Command.link(id))
    else:
        res = [Command.set(res_ids)]

    for create in creates:
        res.append(Command.create(create))

    return res


class OdooGraphql:
    """
    Le principe de cette classe c'est de 'stocker' par base le schéma Graphql selon les modules installés
    cette classe, contient une variable static 'pool' qui est un dictionnaire dont la clef est le nom de la base
    odoo et qui contient ces données là :

    query : C'est une liste de toutes les classes Query graphql des modules installés

    mutation : C'est une liste de toutes les classe Mutation graphql des modules installés

    types : c'est un dictionnaire avec pour clef le nom d'un objet qui sera accessible dans la Query graphql.
    Le champs _name de cette classe permet de regrouper ensemble les mêmes types pour gérer l'héritage
    à la Odoo des objets. Par exemple, si dans un module on a une classe type Partner avec différents champs,
    et un _name = 'Partner', un autre module qui voudra ajouter à cette même classe un nouveau champ aura juste à mettre
    _name = 'Partner'. On pourrait comparer cela avec le _inherit de odoo. Ici, on ne gère juste pas l'ordre d'héritage
    (peut-être est ce que cela sera utile plus tard ?), on regroupe tous les champs dans une même classe. Le _name doit
     avoir le même nom que la classe

    subscription : non implémenté encore

    """

    pool = {}

    @classmethod
    def clear_pool(cls, dbname):
        cls.pool[dbname] = {'query': [], 'mutation': [], 'types': {}, 'subscription': [], 'schema': False}

    @classmethod
    def get_pool(cls, dbname):
        return cls.pool[dbname]

    @classmethod
    def add(cls, dbname, objs):
        if dbname not in cls.pool:
            cls.pool[dbname] = {
                'query': [],
                'mutation': [],
                'types': {},
                'subscription': [],
                'schema': False,
            }

        if not isinstance(objs, list):
            objs = [objs]

        for obj in objs:
            if obj._type == 'types':
                if obj._name:
                    if obj._name in cls.pool[dbname]['types']:
                        cls.pool[dbname]['types'][obj._name].append(obj)
                    else:
                        cls.pool[dbname]['types'][obj._name] = [obj]
            else:
                OdooGraphql.pool[dbname][obj._type].append(obj)

    @classmethod
    def schema(cls, dbname):
        class_query = False
        if cls.pool[dbname]['schema']:
            return cls.pool[dbname]['schema']

        if len(cls.pool[dbname]['query']) > 0:
            class_query = type("Query", tuple(cls.pool[dbname]["query"]), {})

        if len(cls.pool[dbname]['mutation']) > 0:
            class_mutation = type("Mutation", tuple(cls.pool[dbname]["mutation"]), {})

        types = []

        if len(cls.pool[dbname]['types']) > 0:
            for t in cls.pool[dbname]['types']:
                class_type = type(t, tuple(cls.pool[dbname]['types'][t]), {})
                types.append(class_type)

        if len(types) == 0:
            if class_query:
                schema = graphene.Schema(query=class_query, mutation=class_mutation)
            else:
                schema = False
        else:
            if class_query:
                schema = graphene.Schema(query=class_query, mutation=class_mutation, types=types)
            else:
                schema = graphene.Schema(mutation=class_mutation, types=types)
        cls.pool[dbname]['schema'] = schema
        return schema

    @classmethod
    def debug(cls, dbname):
        # Cette fonction va afficher en détail le contenu du pool
        pool = cls.get_pool(dbname)
        for mutation in pool['mutation']:
            logger.info(f"mutation : {mutation._meta.class_type._name}")
            fields = mutation._meta.fields
            for field in fields.values():
                logger.info(f"--> {field._type._name}")
                for arg in field.args.values():
                    if hasattr(arg._type, '_meta'):
                        logger.info(f"---->{arg._type._meta.name}")
                    else:
                        if hasattr(arg._type._of_type, '_meta'):
                            logger.info(f"---->{arg._type._of_type._meta}")
                        else:
                            logger.info(f"---->{arg._type.__dict__}")
                            logger.info(f"---->{arg._type._of_type.__dict__}")
