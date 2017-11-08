odoo.define('web.of_form_widgets', function (require) {
"use strict";
// copiés de web.form_widgets.js
var ajax = require('web.ajax');
var core = require('web.core');
var crash_manager = require('web.crash_manager');
var data = require('web.data');
var datepicker = require('web.datepicker');
var dom_utils = require('web.dom_utils');
var Priority = require('web.Priority');
var ProgressBar = require('web.ProgressBar');
var Dialog = require('web.Dialog');
var common = require('web.form_common');
var formats = require('web.formats');
var framework = require('web.framework');
var Model = require('web.DataModel');
var pyeval = require('web.pyeval');
var session = require('web.session');
var utils = require('web.utils');

var _t = core._t;
var QWeb = core.qweb;

// nouveau
var form_widgets = require('web.form_widgets');
var FieldFloat = form_widgets.FieldFloat;

var OFFieldColorIndex = FieldFloat.extend({
	template: 'OFFieldColorIndex', // template qweb pour le widget -> les templates sont définis dans static/src/xml
	events: {
		// définir les events ici exple: 'click el': 'nom_fonction_handle_click_el'

	},

	init: function() {
        this._super.apply(this, arguments);
        // ajouter des action appliquées à l'initialisation du widget
    },

    // ajouter des fonctions ici. voir widget many2many_tags définis dans /web/static/src/js/views/form_relational_widgets.js
    // dans l'idée: une fonction de clique sur le widget, une fonction update_color
});


core.form_widget_registry
    .add('color_index', OFFieldColorIndex)

return {
    OFFieldColorIndex: OFFieldColorIndex,
};

});
