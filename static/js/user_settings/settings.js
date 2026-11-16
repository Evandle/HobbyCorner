// Settings feature — only affects the settings screen.
document.addEventListener("DOMContentLoaded", function () {
    const darkModeToggle = document.querySelector("#id_dark_mode");
    if (darkModeToggle) {
        darkModeToggle.addEventListener("change", function () {
            document.body.classList.toggle("bg-dark", this.checked);
        });
    }
});
