(() => {
    function paintStars(container, rating) {
        const stars = container.querySelectorAll('.star-btn');
        stars.forEach((star) => {
            const value = Number(star.dataset.value);
            star.classList.toggle('text-warning', value <= rating);
            star.classList.toggle('text-secondary', value > rating);
        });
    }

    document.querySelectorAll('.rating-stars').forEach((container) => {
        const reviewPanel = container.closest('.mt-3');
        const form = reviewPanel ? reviewPanel.querySelector('.review-form') : null;
        if (!form) {
            return;
        }

        const ratingInput = form.querySelector('.rating-input');
        const initialRating = Number(container.dataset.currentRating || 0);
        paintStars(container, initialRating);
        ratingInput.value = initialRating;

        container.querySelectorAll('.star-btn').forEach((star) => {
            star.addEventListener('click', () => {
                const chosen = Number(star.dataset.value);
                ratingInput.value = chosen;
                paintStars(container, chosen);
            });
        });

        form.addEventListener('submit', async (event) => {
            event.preventDefault();
            const payload = new FormData(form);
            const csrfToken = form.querySelector('input[name="csrfmiddlewaretoken"]')?.value || '';

            try {
                const response = await fetch(form.action, {
                    method: 'POST',
                    headers: {
                        'X-Requested-With': 'XMLHttpRequest',
                        'X-CSRFToken': csrfToken,
                    },
                    body: payload,
                });
                const data = await response.json();

                if (!response.ok || !data.ok) {
                    window.alert(data.message || 'Could not save review.');
                    return;
                }

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
