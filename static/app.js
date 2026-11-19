/* ==================================================================
   LOTLINE — small dependency-free interaction layer.
   No network calls, no storage of tokens, no client-side decisions.

   The behaviours live in /static/js/*.js, each of which registers one
   initialiser. This file owns the shared helpers and runs the queue in
   file order, which is the order the page expects.
   ================================================================== */
(function () {
  "use strict";

  var $ = function (selector, root) { return (root || document).querySelector(selector); };
  var $$ = function (selector, root) { return Array.prototype.slice.call((root || document).querySelectorAll(selector)); };
  var api = { $: $, $$: $$ };

  (window.LotlineBoot || []).forEach(function (boot) {
    try {
      boot(api);
    } catch (error) {
      /* one page behaviour failing must not take the rest of the page down */
      if (window.console) window.console.error("[lotline]", error);
    }
  });

  if (api.toast) window.LotlineUI = { toast: api.toast, openDialog: api.openDialog };
})();
