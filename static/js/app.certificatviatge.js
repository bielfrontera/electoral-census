jQuery(document).ready(function($){

    var $result = $("#result");
    var $errors = $("#errors");
    var $nif = $("#nif");
    var $birthdate = $("#birthdate");
    $("#certificatviatge").submit(function(evt){
        $result.hide();
        $errors.hide();
        $("#submit").prop('disabled', true);
        var nif = $nif.val();
        var birthdate = $birthdate.val();

        evt.preventDefault();
        $.ajax('/certificat-viatge/check', {
            data: {'nif': nif, 'birthdate': birthdate},
            success: function(data, status, jqXHR) {
                $result.html("El certificat es descarregarà en breus instants. En cas contrari, clica <a href='" + data.url_certificat + "'>aquí</a>");
                $result.show();
                $("#submit").prop('disabled', false);
                window.location.href = data.url_certificat;
            },
            error: function(jqXHR, textStatus, errorThrown) {
                $("#submit").prop('disabled', false);
                try{
                    var error = $.parseJSON(jqXHR.responseText);
                    $("#error").html(error.error_desc);
                } catch(err) {
                    $("#error").html("S'ha produit un error a l'aplicació. Torni-ho a provar en uns moments o telefoni a l\'Ajuntament d\'Inca.");
                }
                $errors.show();
            },

        });

    });

});