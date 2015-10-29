// header fix
$(window).scroll(function(){
    if ($(window).scrollTop() >= 13) {
       $('.navbar-top').addClass('navbar-fixed-top');
    }
    else {
       $('.navbar-top').removeClass('navbar-fixed-top');
    }
});

 
 

