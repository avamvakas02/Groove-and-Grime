(() => {
    // I use this helper to visually update the stars based on a given rating
    // It highlights stars up to the rating value in yellow, the rest in grey
    function paintStars(container, rating) {
        const stars = container.querySelectorAll('.star-btn');
        stars.forEach((star) => {
            const value = Number(star.dataset.value);
            star.classList.toggle('text-warning', value <= rating);
            star.classList.toggle('text-secondary', value > rating);
        });
    }

    document.querySelectorAll('.rating-stars').forEach((container) => {
        // I look for the review form that belongs to this specific star container
        const reviewPanel = container.closest('.mt-3');
        const form = reviewPanel ? reviewPanel.querySelector('.review-form') : null;
        if (!form) return;

        const ratingInput = form.querySelector('.rating-input');

        // I read the existing rating from the element and paint the stars on page load
        const initialRating = Number(container.dataset.currentRating || 0);
        paintStars(container, initialRating);
        ratingInput.value = initialRating;

        // When a star is clicked I update the hidden input and repaint the stars
        container.querySelectorAll('.star-btn').forEach((star) => {
            star.addEventListener('click', () => {
                const chosen = Number(star.dataset.value);
                ratingInput.value = chosen;
                paintStars(container, chosen);
            });
        });

        // I submit the review via AJAX so the page doesn't reload
        form.addEventListener('submit', async (event) => {
            event.preventDefault();
            const payload = new FormData(form);
            const csrfToken = form.querySelector('input[name="csrfmiddlewaretoken"]')?.value || '';

            try {
                const response = await fetch(form.action, {
                    method: 'POST',
                    headers: {
                        'X-Requested-With': 'XMLHttpRequest',
                        'X-CSRFToken': csrfToken, // Django requires this token on every POST request
                    },
                    body: payload,
                });
                const data = await response.json();

                if (!response.ok || !data.ok) {
                    window.alert(data.message || 'Could not save review.');
                    return;
                }

                // I update the rating summary text and repaint the stars with the new saved value
                const summary = document.getElementById(`rating-summary-${data.record_id}`);
                if (summary) {
                    summary.textContent = `${Number(data.average_rating).toFixed(1)} (${data.review_count} reviews)`;
                }
                paintStars(container, Number(data.user_rating));
                ratingInput.value = Number(data.user_rating);

            } catch (_error) {
                window.alert('Network issue while saving review. Please try again.');
            }
        });
    });
})();