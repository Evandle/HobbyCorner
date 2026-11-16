// Register feature. An enhancement only: the form works without it.
document.addEventListener("DOMContentLoaded", function () {
    // After a valid submit, lock the button so a double-tap can't post twice.
    document.querySelectorAll("form[method='post']").forEach(function (form) {
        form.addEventListener("submit", function () {
            if (form.checkValidity()) {
                form.querySelectorAll("button[type='submit']").forEach(function (b) { b.disabled = true; });
            }
        });
    });
    // Back-button restores the page with the button still locked; undo that.
    window.addEventListener("pageshow", function (event) {
        if (event.persisted) {
            document.querySelectorAll("button[type='submit']:disabled").forEach(function (b) { b.disabled = false; });
        }
    });
});
