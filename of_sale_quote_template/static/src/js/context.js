odoo.define('of_sale_quote_template.context', function (require) {
"use strict";

var pyeval = require('web.pyeval')

function isNullOrUndef(value) {
    return _.isUndefined(value) || _.isNull(value);
}

function get_m2m_ids (m2m) {
    var ids = []
    if (m2m instanceof Array && !isNullOrUndef(m2m[0]._store) && !isNullOrUndef(m2m[0]._store._store)) {
        m2m = m2m[0]._store._store
        for (var i = 0; i < m2m.length;i++) {
            ids.push(m2m[i][1])
        }
    }
    return ids
}

var old_ensure_evaluated = pyeval.ensure_evaluated

pyeval.ensure_evaluated = function (args, kwargs) {
    if (!isNullOrUndef(kwargs["context"]) && !isNullOrUndef(kwargs["context"].__contexts) &&
    kwargs["context"].__contexts instanceof Array && typeof kwargs["context"].__contexts[0] === 'object') {
        kwargs["context"].__contexts[0]["get_m2m_ids"] = get_m2m_ids
    }
    return old_ensure_evaluated(args, kwargs);
}

});
