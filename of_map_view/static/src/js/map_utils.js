odoo.define('of_map_view.map_utils', function (require) {
"use strict";

var core = require('web.core');
var map_widgets = require('of_map_view.map_widgets');
var fields_registry = map_widgets.registry;
var qweb = core.qweb;

function qweb_add_if(node, condition) {
    if (node.attrs[qweb.prefix + '-if']) {
        condition = _.str.sprintf("(%s) and (%s)", node.attrs[qweb.prefix + '-if'], condition);
    }
    node.attrs[qweb.prefix + '-if'] = condition;
}

function transform_qweb_template (node, fvg, many2manys, options) {
    // Process modifiers
    if (node.tag && node.attrs.modifiers) {
        var modifiers = JSON.parse(node.attrs.modifiers || '{}');
        if (modifiers.invisible) {
            qweb_add_if(node, _.str.sprintf("!map_record_compute_domain(%s)", JSON.stringify(modifiers.invisible)));
        }
    }
    switch (node.tag) {
        case 'field':
            var ftype = fvg.fields[node.attrs.name].type;
            ftype = node.attrs.widget ? node.attrs.widget : ftype;
            if (ftype === 'many2many') {
                if (_.indexOf(many2manys, node.attrs.name) < 0) {
                    many2manys.push(node.attrs.name);
                }
                if (node.attrs["of_options"]) {
                    var of_options = {};
                    of_options = JSON.parse(node.attrs["of_options"]);  // /!\ JSON.parse requires property names with double-quotes {"prop": "val"}
                    if (of_options["exclude_vals"]) {  //
                        var exclude_vals = {};
                        exclude_vals[node.attrs.name] = of_options["exclude_vals"]
                        var vals = exclude_vals[node.attrs.name]
                        for (var i=0; i<vals.length; i++){
                            vals[i] = vals[i].toLowerCase();
                        }
                        of_options["exclude_vals"] = exclude_vals;
                    }
                    options = _.extend(options,of_options);
                }
                node.tag = 'div';
                node.attrs['class'] = (node.attrs['class'] || '') + ' of_map_record_field of_map_record_field_many2manytags of_map_record_tags'; // TODO: verif
            } else if (fields_registry.contains(ftype)) {
                // do nothing, the map record will handle it
            } else {
                node.tag = qweb.prefix;
                node.attrs[qweb.prefix + '-esc'] = 'record.' + node.attrs.name + '.value';
            }
            break;
        case 'button':
        case 'a':
            var type = node.attrs.type || '';
            if (_.indexOf('action,object,edit,open,delete,url,set_cover'.split(','), type) !== -1) {
                _.each(node.attrs, function(v, k) {
                    if (_.indexOf('icon,type,name,args,string,context,states,kanban_states'.split(','), k) != -1) {
                        node.attrs['data-' + k] = v;
                        delete(node.attrs[k]);
                    }
                });
                if (node.attrs['data-string']) {
                    node.attrs.title = node.attrs['data-string'];
                }
                if (node.tag == 'a' && node.attrs['data-type'] != "url") {
                    node.attrs.href = '#';
                } else {
                    node.attrs.type = 'button';
                }

                var action_classes = " of_map_record_action of_map_record_action_" + node.tag;
                if (node.attrs['t-attf-class']) {
                    node.attrs['t-attf-class'] += action_classes;
                } else if (node.attrs['t-att-class']) {
                    node.attrs['t-att-class'] += " + '" + action_classes + "'";
                } else {
                    node.attrs['class'] = (node.attrs['class'] || '') + action_classes;
                }
            }
            break;
    }
    if (node.children) {
        for (var i = 0, ii = node.children.length; i < ii; i++) {
            transform_qweb_template(node.children[i], fvg, many2manys, options);
        }
    }
}
return {transform_qweb_template: transform_qweb_template};
});