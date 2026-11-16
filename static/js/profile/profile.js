// Profile feature. Everything here is an enhancement: the form works without it.
document.addEventListener("DOMContentLoaded", function () {
    // 1. Clicking a suggested interest adds it to the Interests box.
    const box = document.querySelector("#id_interest_names");
    document.querySelectorAll(".interest-suggestion").forEach(function (button) {
        button.addEventListener("click", function () {
            if (!box) { return; }
            const wanted = button.dataset.interest;
            const current = box.value.split(",").map(function (s) { return s.trim(); }).filter(Boolean);
            const already = current.some(function (s) { return s.toLowerCase() === wanted.toLowerCase(); });
            if (!already) {
                current.push(wanted);
                box.value = current.join(", ");
            }
            box.focus();
        });
    });

    // 2. The bio grows with what you type.
    const bio = document.querySelector("#id_bio");
    if (bio) {
        bio.addEventListener("input", function () {
            this.style.height = "auto";
            this.style.height = this.scrollHeight + "px";
        });
    }

    // 3. After a valid submit, lock the buttons so a double-tap can't post twice.
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
