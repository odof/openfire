odoo.define('of_web_widgets.of_form_common', function (require) {
"use strict";

var form_common = require('web.form_common');
var utils = require('web.utils');
var core = require('web.core');
var _t = core._t;

form_common.CompletionFieldMixin.init = function(){
	this.limit = 7;
	this.orderer = new utils.DropMisordered();
	this.can_create = this.node.attrs.can_write == "false" ? false : true;
	this.can_write = this.node.attrs.can_write == "false" ? false : true;
	this.options.no_quick_create = true;
	//console.log(" test : ", this.options);
};

var FieldMany2One = core.form_widget_registry.get('many2one');

/**
    This widget is intended to display a warning near a label of a 'res.partner' many2one field
    indicating if the partner is not geolocalized.
    This widget depends on a field given with the param 'geo_lat_field', which contains
    the time difference between UTC time and local time, in minutes.
*/
var Localizable = FieldMany2One.extend({
    initialize_content: function() {
        this._super.apply(this, arguments);
        this.geo_lat_field = (this.options && this.options.geo_lat_field) || this.geo_lat_field || 'geo_lat';
        this.set({"geo_lat": this.field_manager.get_field_value(this.geo_lat_field)});
        this.on("change:geo_lat", this, this.render_value);
    },
    start: function() {
        this._super.apply(this, arguments);
        // trigger a render_value when geo_lat field change
        this.field_manager.on("field_changed:" + this.geo_lat_field, this, function() {
            this.set({"geo_lat": this.field_manager.get_field_value(this.geo_lat_field)});
        });
    },
    check_localized: function() {
        var partner_lat = this.get('geo_lat');
        if (!partner_lat) {
            return false;
        }
        return true;
    },
    render_value: function() {
        this._super.apply(this, arguments);
        this.$label.next('.o_tz_warning').remove();
        if(!this.check_localized()){
            var options = _.extend({
                delay: { show: 501, hide: 0 },
                title: _t("This partner is not geolocalized"),
            });
            $('<span/>').addClass('fa fa-exclamation-triangle o_tz_warning').insertAfter(this.$label).tooltip(options);
        }
    }
});

core.form_widget_registry.add('localizable', Localizable)

});
