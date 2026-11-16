// Register feature — only affects the register screen.
document.addEventListener("DOMContentLoaded", function () {
    const usernameField = document.querySelector("#id_username");
    if (usernameField) {
        usernameField.focus();
    }
});
