document.addEventListener('DOMContentLoaded', () => {

    // I grab every alert on the page and loop through them
    document.querySelectorAll('.alert').forEach((alert) => {

        // I give the user 3 seconds to read the message before I start removing it
        setTimeout(() => {

            // I fade it out first instead of just deleting it — looks cleaner
            alert.style.opacity = '0';

            // I wait another 500ms for the fade to finish, then remove the element completely
            setTimeout(() => alert.remove(), 500);

        }, 3000);
    });
});