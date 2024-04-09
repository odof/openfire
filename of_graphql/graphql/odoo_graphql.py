import graphene

from odoo.exceptions import AccessError


def lazy_create(env, model, input):
    value_object = {}
    for field in input.__dict__:
        if field in input:
            value_object[field] = input[field]

    object = env[model].create(value_object)
    return object


def lazy_update(env, model, id, input):
    value_object = {}
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
