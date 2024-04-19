import logging

import graphene

from odoo.exceptions import AccessError

logger = logging.getLogger(__name__)


def lazy_create(env, model, input):
    value_object = {}
    if type(input) is dict:
        for field in input.keys():
            if field in input:
                value_object[field] = input[field]
    else:
        for field in input.__dict__:
            if field in input:
                value_object[field] = input[field]
    object = env[model].create(value_object)
    return object


def lazy_update(env, model, id, input):
    value_object = {}
    if type(input) is dict:
        for field in input.keys():
            if field in input:
                value_object[field] = input[field]
    else:
        for field in input.__dict__:
            if field in input:
                value_object[field] = input[field]

    object = env[model].search([('id', '=', id)], limit=1)
    if not object:
        raise AccessError(f"Unable to find object ({model}) with id: {id}")

    object.write(value_object)
    return object


def lazy_delete(env, model, id):
    object = env[model].search([('id', '=', id)])
    if object:
        object.unlink()
        return object

    return env[model]


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
    def group_class(cls, classes):
        # ici on regroupe les classes ayant le même _name pour retourner une seule classe par _name
        res = {}
        for cl in classes:
            if cl._name in res:
                res[cl._name].append(cl)
            else:
                res[cl._name] = [cl]
        classes_list = list(res.values())
        pool_classes = []

        for cl in classes_list:
            if len(cl) > 1:
                cl.reverse()
                cl = type(cl[0]._name, tuple(cl), {})
            else:
                cl = cl[0]
            pool_classes.append(cl)
        return pool_classes

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
            # on peut avoir des variables dans les classes query qui sont identiques
            # il faut donc alors regrouper ces classes en gérant le bon ordre de surcharge
            class_queries = cls.group_class(cls.pool[dbname]["query"])
            class_query = type("Query", tuple(class_queries), {})

        if len(cls.pool[dbname]['mutation']) > 0:
            # on peut avoir des variables dans les classes mutations qui sont identiques
            # il faut donc alors regrouper ces classes en gérant le bon ordre de surcharge
            class_mutations = cls.group_class(cls.pool[dbname]["mutation"])
            class_mutation = type("Mutation", tuple(class_mutations), {})

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
