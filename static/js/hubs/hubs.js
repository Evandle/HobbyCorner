// Hubs feature.
// 1. Forms marked data-confirm ask first, using the native <dialog>.
// 2. After a submit, the buttons are disabled so a double-tap can't post twice.
// Both are progressive: without JS the forms still submit normally and the
// server does the real work.
document.addEventListener("DOMContentLoaded", function () {
    const dialog = document.getElementById("confirm-dialog");
    const message = document.getElementById("confirm-dialog-message");
    let pendingForm = null;

    function lockButtons(form) {
        form.querySelectorAll("button").forEach(function (button) {
            button.disabled = true;
        });
    }

    document.querySelectorAll("form[method='post']").forEach(function (form) {
        form.addEventListener("submit", function (event) {
            const needsConfirm = form.dataset.confirm && dialog
                && typeof dialog.showModal === "function";
            if (needsConfirm) {
                event.preventDefault();
                pendingForm = form;
                message.textContent = form.dataset.confirm;
                dialog.returnValue = "";   // a stale "confirm" must never survive an Esc
                dialog.showModal();
                return;
            }
            lockButtons(form);
        });
    });

    if (dialog) {
        dialog.addEventListener("close", function () {
            if (dialog.returnValue === "confirm" && pendingForm) {
                lockButtons(pendingForm);
                pendingForm.submit();
            }
            pendingForm = null;
        });
    }

    // Coming back with the Back button restores the page from cache with the
    // buttons still disabled; undo that.
    window.addEventListener("pageshow", function (event) {
        if (event.persisted) {
            document.querySelectorAll("form button:disabled").forEach(function (button) {
                button.disabled = false;
            });
        }
    });
});
