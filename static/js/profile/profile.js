// Profile feature — only affects the profile screen.
document.addEventListener("DOMContentLoaded", function () {
    const bioField = document.querySelector("#id_bio");
    if (bioField) {
        bioField.addEventListener("input", function () {
            this.style.height = "auto";
            this.style.height = this.scrollHeight + "px";
        });
    }
});
