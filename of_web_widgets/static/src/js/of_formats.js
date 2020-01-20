odoo.define('of_web_widgets.of_formats', function (require) {
"use strict";

var translation = require('web.translation');
var time = require('web.time');
var utils = require('web.utils');

var _t = translation._t;

var formats = require("web.formats");

function starts_with (str, sub) {
    return ((typeof str === 'string' || str instanceof String) && (str.indexOf(sub) == 0));
};

/**
 * Formats a single atomic value based on a field descriptor
 *
 * @param {Object} value read from OpenERP
 * @param {Object} descriptor union of orm field and view field
 * @param {Object} [descriptor.widget] widget to use to display the value
 * @param {Object} descriptor.type fallback if no widget is provided, or if the provided widget is unknown
 * @param {Object} [descriptor.digits] used for the formatting of floats
 * @param {String} [value_if_empty=''] returned if the ``value`` argument is considered empty
 */
function format_value (value, descriptor, value_if_empty) {
    var l10n = _t.database.parameters;
    var date_format = time.strftime_to_moment_format(l10n.date_format);
    var time_format = time.strftime_to_moment_format(l10n.time_format);
    // If NaN value, display as with a `false` (empty cell)
    if (typeof value === 'number' && isNaN(value)) {
        value = false;
    }
    //noinspection FallthroughInSwitchStatementJS
    switch (value) {
        case '':
            if (descriptor.type === 'char' || descriptor.type === 'text') {
                return '';
            }
            console.warn('Field', descriptor, 'had an empty string as value, treating as false...');
            return value_if_empty === undefined ?  '' : value_if_empty;
        case false:
        case undefined:
        case Infinity:
        case -Infinity:
            return value_if_empty === undefined ?  '' : value_if_empty;
    }
    switch (descriptor.widget || descriptor.type || (descriptor.field && descriptor.field.type)) {
        case 'id':
            return value.toString();
        case 'integer':
            return utils.insert_thousand_seps(
                _.str.sprintf('%d', value));
        case 'monetary':
        case 'float':
        case 'field_float_scannable':
            var digits = descriptor.digits ? descriptor.digits : [69,2];
            digits = typeof digits === "string" ? py.eval(digits) : digits;
            var precision = digits[1];
            var formatted = _.str.sprintf('%.' + precision + 'f', value).split('.');
            formatted[0] = utils.insert_thousand_seps(formatted[0]);
            return formatted.join(l10n.decimal_point);
        case 'float_time':
            var pattern = '%02d:%02d';
            if (value < 0) {
                value = Math.abs(value);
                pattern = '-' + pattern;
            }
            var hour = Math.floor(value);
            var min = Math.round((value % 1) * 60);
            if (min == 60){
                min = 0;
                hour = hour + 1;
            }
            return _.str.sprintf(pattern, hour, min);
        case 'many2one':
            // name_get value format
            return value[1] ? value[1].split("\n")[0] : value[1];
        case 'one2many':
        case 'many2many':
            if (typeof value === 'string') {
                return value;
            }
            /////////////////////////////////////// DEBUT CODE OF
            else if (value.length == 0) {
                return "-"
            }
            ////////////////////////////////////// FIN CODE OF
            return _.str.sprintf(_t("(%d records)"), value.length);
        case 'datetime':
            if (typeof(value) == "string")
                value = moment(time.auto_str_to_date(value));
            else {
                value = moment(value);
            }
            return value.format(date_format + ' ' + time_format);
        case 'date':
            if (typeof(value) == "string")
                value = moment(time.auto_str_to_date(value));
            else {
                value = moment(value);
            }
            return value.format(date_format);
        case 'time':
            if (typeof(value) == "string")
                value = moment(time.auto_str_to_date(value));
            else {
                value = moment(value);
            }
            return value.format(time_format);
        case 'selection': case 'statusbar':
            // Each choice is [value, label]
            if(_.isArray(value)) {
                 return value[1];
            }
            var result = _(descriptor.selection).detect(function (choice) {
                return choice[0] === value;
            });
            if (result) { return result[1]; }
            return;
        default:
            return value;
    }
}

formats.format_value = format_value;

});
