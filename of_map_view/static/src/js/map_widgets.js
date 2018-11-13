odoo.define('of_map_view.map_widgets', function (require) {
"use strict";

var core = require('web.core');
var formats = require('web.formats');
var Priority = require('web.Priority');
var ProgressBar = require('web.ProgressBar');
var pyeval = require('web.pyeval');
var Registry = require('web.Registry');
var session = require('web.session');
var Widget = require('web.Widget');
var QWeb = core.qweb;
var _t = core._t;

/*
 * Future map widgets to be added :D
 */

var fields_registry = new Registry();

return {
    registry: fields_registry,
};

});