$(function(){
	$('.weui-tabbar__item').on('click', function () {
		$(this).addClass('weui-bar__item_on').siblings('.weui-bar__item_on').removeClass('weui-bar__item_on');
	});

	$('.comingSoon').on('click', function () {
	    $.toast('敬请期待', 'cancel');
	});

});

$( document ).ready(function() {
    var heights = $(".card-title").map(function() {
        return $(this).height();
    }).get(),

    maxHeight = Math.max.apply(null, heights);

    $(".card-title").height(maxHeight);
});
