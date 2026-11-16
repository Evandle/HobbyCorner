// Login feature — only affects the login screen.
document.addEventListener("DOMContentLoaded", function () {
    const usernameField = document.querySelector("#id_username");
    if (usernameField) {
        usernameField.focus();
    }
});
