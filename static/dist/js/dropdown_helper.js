$(document).ready(function () {
    $(".dropdown-menu li button").click(function () {
        var selText = $(this).text();
        var selValue = $(this).attr('value');
        $(this).parents('.btn-group').find('.dropdown-toggle').html(selText);
        $(this).parents('.btn-group').find('.input-group').attr('value', selValue);
    });
});