// Local design work only: a local server started with DEV_RELOAD=1 tells this tab which frontend files changed.
// Directly linked stylesheets are swapped in place (scroll position and the open tab stay put), anything else
// reloads the page. On girloffs.com and the Pages previews this does nothing.
(function() {
    if (/(^|\.)girloffs\.com$|\.pages\.dev$/.test(location.hostname)) return;

    var events = new EventSource('/dev/reload');
    events.onmessage = function(e) {
        var changed = JSON.parse(e.data);
        var links = Array.from(document.querySelectorAll('link[rel="stylesheet"]'));
        var linked = links.map(function(link) { return new URL(link.href).pathname.slice(1); });
        var cssOnly = changed.every(function(file) { return linked.indexOf(file) !== -1; });
        if (!cssOnly) return location.reload();

        links.forEach(function(link, i) {
            if (changed.indexOf(linked[i]) === -1) return;
            var fresh = link.cloneNode();
            var url = new URL(link.href);
            url.searchParams.set('v', Date.now());
            fresh.href = url.href;
            fresh.onload = function() {
                link.remove();
                window.dispatchEvent(new Event('resize'));  // layout may have moved: redraw bracket lines
            };
            link.after(fresh);
        });
    };
})();
