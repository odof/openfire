 var formHasChanged = false;
 var submitted = false;

// On regarde si un des input du formulaire a été modifié
$(document).on('change', 'form#bank_detail_form input, form#bank_detail_form select, form#bank_detail_form textarea', function (e) {
    formHasChanged = true;
});

$(document).ready(function() {
    window.onbeforeunload = function (e) {
        // Si les champs ont été modifié et qu'on ne vient pas du bouton de validation, alors on affiche le message de prévention
        if (formHasChanged && !submitted) {
            var message = "You have not saved your changes.", e = e || window.event;
            if (e) {
                e.returnValue = message;
            }
            return message;
        }
    }
    // On regarde si on vient du bouton de validation du formulaire
    $("form#bank_detail_form").submit(function() {
        submitted = true;
    });

});
