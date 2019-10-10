odoo.define('of_geolocalize.of_form_relational_widgets', function (require) {
"use strict";

//var form_common = require('web.form_common');
//var utils = require('web.utils');
var Model = require('web.DataModel');
var core = require('web.core');
var _t = core._t;

var FieldMany2One = core.form_widget_registry.get('many2one');

function isNullOrUndef(value) {
    return _.isUndefined(value) || _.isNull(value);
}

/**
    This widget is intended to display a warning near a label of a 'res.partner' many2one field
    indicating if the partner is not geolocalized.
    This widget depends on a field given with the param 'geo_lat_field', which contains
    the time difference between UTC time and local time, in minutes.
*/
FieldMany2One.include({
    init: function(field_manager, node) {
        this._super(field_manager, node);
        this.dfd_geo_lat = $.Deferred()
    },
    initialize_content: function() {
        var self = this;
        this._super.apply(this, arguments);

        if (this.field.relation == 'res.partner') {
            this.geo_lat_field = (this.options && this.options.geo_lat_field) || this.geo_lat_field || 'geo_lat';
            if (!isNullOrUndef(this.field_manager.fields[this.geo_lat_field])) {
                this.set({"geo_lat": this.field_manager.get_field_value(this.geo_lat_field)});
            }else{
                this.set_geo_lat();
            }
        }
    },
    set_geo_lat: function () {
        var self = this;

        var partner_id = this.field_manager.get_field_value(this.name)
        if (!partner_id) {
            self.set({"geo_lat": undefined});
            self.dfd_geo_lat.resolve();
        }else{
            var ResPartner = new Model("res.partner");
            ResPartner.query(['id', 'geo_lat', 'name']) // retrieve geo_lat from db
                .filter([['id','=',partner_id]]) // id
                .all()
                .then(function (partners){
                    self.set({"geo_lat": partners[0]["geo_lat"]});
                    // on peut vérifier la géo_loc maintenant
                    self.dfd_geo_lat.resolve();
                    return partners[0]["geo_lat"]
                })
        }

    },
    check_localized: function() {
        var partner_lat = this.get('geo_lat');
        if (partner_lat === 0) {
            return false;
        }
        return true;
    },
    render_value: function() {
        var self = this;
        this._super.apply(this, arguments);
        if (this.field.relation == 'res.partner') {
            this.dfd_geo_lat = $.Deferred()
            this.set_geo_lat();
            // on attend d'avoir set la valeur de geo_lat avant de la verifier :D
            $.when(this.dfd_geo_lat).then(function(){
                self.$label.next('.o_tz_warning').remove();
                if(!self.check_localized()){
                    // n'est pas géolocalisé
                    var options = _.extend({
                        delay: { show: 501, hide: 0 },
                        title: _t((self.current_display || self.field_manager.datarecord[self.name][1] || "Ce partenaire ") + " n'est pas géolocalisé"),
                    });
                    $('<span/>').addClass('fa fa-exclamation-triangle o_tz_warning').insertAfter(self.$label).tooltip(options);
                }
            });
        }
    }
});


});
