// The tree starts centered under the header logo, wherever the header layout puts it.
export function initCredits() {
    var logo = document.querySelector('.logo');
    var container = document.querySelector('.credits-container');
    function align() {
        var r = logo.getBoundingClientRect();
        var s = getComputedStyle(logo);
        var center = r.left + (r.width + parseFloat(s.paddingLeft) - parseFloat(s.paddingRight)) / 2;
        container.style.setProperty('--logo-center', center + 'px');
    }
    align();
    logo.addEventListener('load', align);
    window.addEventListener('resize', align);
}
