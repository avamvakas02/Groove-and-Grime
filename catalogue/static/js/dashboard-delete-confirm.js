document.addEventListener("DOMContentLoaded", () => {

    // I use a single page-level listener so it works for dynamically loaded elements too
    document.addEventListener("click", (event) => {

        const deleteLink = event.target.closest("[data-confirm-delete]");

        // If the click wasn't on a delete element, exit early
        if (!deleteLink) return;

        const message = deleteLink.getAttribute("data-confirm-delete") || "Are you sure?";

        // If the user hits cancel, I block the delete from going through
        if (!window.confirm(message)) {
            event.preventDefault();
        }
    });
});