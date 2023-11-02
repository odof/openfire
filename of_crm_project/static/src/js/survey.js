odoo.define('of_crm_project.of_survey_form', function (require) {
'use strict';

    var OFSurveyFormWidget = require('of_survey.form');

    function sleep (time) {
      return new Promise((resolve) => setTimeout(resolve, time));
    }

    OFSurveyFormWidget.include({
        start: function () {
            var self = this;
            return this._super.apply(this, arguments).then(function () {
                var show_start = $('.show_start').attr('data-show');

                if (show_start=='no'){
                    self._submitForm({});
                }

            });
        },
        _onNextScreenDone: function (options) {
            // A chaque changement d'écran, on vérifie si nous sommes ou pas sur la dernière pas
            this._super.apply(this, arguments);
            var show_end = $('.show_end').attr('data-show');
            var crm_lead_id = $('.show_end').attr('crm-lead-id');
            var action_id = $('.show_end').attr('action-id');
            if (show_end=='no'){
                window.location = "/web/#id="+crm_lead_id+"&model=crm.lead&view_type=form&action="+action_id;
            }

        },

    });

    return OFSurveyFormWidget;

});
