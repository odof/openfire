odoo.define('of_web_widgets.of_data', function (require) {
"use strict";

var core = require('web.core');
var data = require("web.data");
var _t = core._t;
var _lt = core._lt;

function starts_with (str, sub) {
    return ((typeof str === 'string' || str instanceof String) && (str.indexOf(sub) == 0));
};

function compute_domain (expr, fields) {
    if (! (expr instanceof Array))
        return !! expr;
    var stack = [];
    for (var i = expr.length - 1; i >= 0; i--) {
        var ex = expr[i];
        if (ex.length == 1) {
            var top = stack.pop();
            switch (ex) {
                case '|':
                    stack.push(stack.pop() || top);
                    continue;
                case '&':
                    stack.push(stack.pop() && top);
                    continue;
                case '!':
                    stack.push(!top);
                    continue;
                default:
                    throw new Error(_.str.sprintf(
                        _t("Unknown operator %s in domain %s"),
                        ex, JSON.stringify(expr)));
            }
        }

        var field = fields[ex[0]];
        if (!field) {
            throw new Error(_.str.sprintf(
                _t("Unknown field %s in domain %s"),
                ex[0], JSON.stringify(expr)));
        }
        var field_value = field.get_value ? field.get_value() : field.value;
        var op = ex[1];
        var val = ex[2];

        ////////////////////////////////////////////////////////////////////////////////////////// cette partie change
        if (starts_with(val, "_field_")) {
            val = val.substr(7);  // "_field_x" -> "x"
            var field_2 = fields[val];
            val = field_2.get_value ? field_2.get_value() : field_2.value;
        }
        //////////////////////////////////////////////////////////////////////////////////////////

        switch (op.toLowerCase()) {
            case '=':
            case '==':
                stack.push(_.isEqual(field_value, val));
                break;
            case '!=':
            case '<>':
                stack.push(!_.isEqual(field_value, val));
                break;
            case '<':
                stack.push(field_value < val);
                break;
            case '>':
                stack.push(field_value > val);
                break;
            case '<=':
                stack.push(field_value <= val);
                break;
            case '>=':
                stack.push(field_value >= val);
                break;
            case 'in':
                if (!_.isArray(val)) val = [val];
                stack.push(_(val).contains(field_value));
                break;
            case 'not in':
                if (!_.isArray(val)) val = [val];
                stack.push(!_(val).contains(field_value));
                break;
            default:
                console.warn(
                    _t("Unsupported operator %s in domain %s"),
                    op, JSON.stringify(expr));
        }
    }
    return _.all(stack, _.identity);
}

data.compute_domain = compute_domain;

});
