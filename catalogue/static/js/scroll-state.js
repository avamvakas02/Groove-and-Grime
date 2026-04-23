// cart.js — Handles adding items to the cart, updating quantities,
// and keeping the cart badge in sync without reloading the page

document.addEventListener('DOMContentLoaded', () => {

    // I include the URL path in the key so each page stores its own scroll position
    const SCROLL_STATE_KEY = `scroll-state:${window.location.pathname}${window.location.search}`;

    const saveScrollPosition = () => {
        sessionStorage.setItem(SCROLL_STATE_KEY, String(window.scrollY || window.pageYOffset || 0));
    };

    const restoreScrollPosition = () => {
        const saved = sessionStorage.getItem(SCROLL_STATE_KEY);
        if (saved === null) return;

        const y = Number.parseInt(saved, 10);
        sessionStorage.removeItem(SCROLL_STATE_KEY);
        if (Number.isNaN(y)) return;

        // I scroll twice because lazy-loaded images can shift the layout after the first attempt
        window.requestAnimationFrame(() => window.scrollTo(0, y));
        window.setTimeout(() => window.scrollTo(0, y), 60);
    };

    // I turn off the browser's built-in scroll restoration so it doesn't conflict with mine
    if ('scrollRestoration' in window.history) {
        window.history.scrollRestoration = 'manual';
    }
    restoreScrollPosition();

    const cartAddLinks = document.querySelectorAll('a[href*="/cart/add/"]');
    const cartForms = document.querySelectorAll('form[data-cart-form]');
    const cartLink = document.querySelector('a[aria-label="Open crate"]');
    const preserveScrollLinks = document.querySelectorAll('a[data-preserve-scroll]');
    const preserveScrollForms = document.querySelectorAll('form[data-preserve-scroll], .wishlist-form, .review-form, form[data-cart-form]');

    preserveScrollLinks.forEach((link) => link.addEventListener('click', saveScrollPosition));
    preserveScrollForms.forEach((form) => form.addEventListener('submit', saveScrollPosition));

    // I create or update the badge on the cart icon depending on the item count
    const upsertCartBadge = (itemCount) => {
        if (!cartLink) return;
        const existingBadge = cartLink.querySelector('.badge');

        if (itemCount > 0) {
            if (existingBadge) {
                existingBadge.textContent = itemCount;
                return;
            }
            const badge = document.createElement('span');
            badge.className = 'position-absolute top-0 start-100 translate-middle badge rounded-pill bg-warning text-dark';
            badge.style.fontSize = '0.6rem';
            badge.textContent = itemCount;
            cartLink.appendChild(badge);
        } else if (existingBadge) {
            existingBadge.remove();
        }
    };

    cartAddLinks.forEach((link) => {
        link.addEventListener('click', async (event) => {
            event.preventDefault();

            // I use a loading flag to prevent the same item being added twice on double-click
            if (link.dataset.loading === 'true') return;

            saveScrollPosition();
            link.dataset.loading = 'true';
            const originalText = link.textContent;

            // I fix the button width so it doesn't jump when the text changes to "ADDED"
            link.style.minWidth = `${link.getBoundingClientRect().width}px`;
            link.classList.add('disabled');

            try {
                const response = await fetch(link.href, {
                    headers: { 'X-Requested-With': 'XMLHttpRequest' }
                });
                const payload = await response.json();

                if (!response.ok || payload.ok === false) {
                    if (payload.redirect_url) {
                        window.location.href = payload.redirect_url;
                        return;
                    }
                    throw new Error('Cart add request failed');
                }

                upsertCartBadge(payload.item_count);
                link.textContent = 'ADDED';
                setTimeout(() => { link.textContent = originalText; }, 800);

            } catch (error) {
                // If something goes wrong I fall back to normal navigation
                window.location.href = link.href;
            } finally {
                link.dataset.loading = 'false';
                link.classList.remove('disabled');
            }
        });
    });

    const cartCount = document.querySelector('[data-cart-count]');
    if (cartForms.length && cartCount) {

        const cartCountSuffix = document.querySelector('[data-cart-count-suffix]');
        const cartSubtotal = document.querySelector('[data-cart-subtotal]');
        const cartDiscount = document.querySelector('[data-cart-discount]');
        const cartDiscountRow = document.querySelector('[data-cart-discount-row]');
        const cartTotal = document.querySelector('[data-cart-total]');

        const updateCartSummary = (payload) => {
            cartCount.textContent = payload.item_count;
            if (cartCountSuffix) {
                // Handles "item" vs "items" depending on the count
                cartCountSuffix.textContent = payload.item_count === 1 ? '' : 's';
            }
            if (cartSubtotal) cartSubtotal.textContent = payload.subtotal;
            if (cartTotal) cartTotal.textContent = payload.total_after_discount;

            if (cartDiscount && cartDiscountRow) {
                if (payload.discount_percent > 0) {
                    cartDiscount.textContent = payload.discount_amount;
                    cartDiscountRow.classList.remove('d-none');
                } else {
                    cartDiscountRow.classList.add('d-none');
                }
            }
            upsertCartBadge(payload.item_count);
        };

        cartForms.forEach((form) => {
            form.addEventListener('submit', async (event) => {
                event.preventDefault();
                const submitButton = form.querySelector('button[type="submit"]');
                if (submitButton) submitButton.disabled = true;

                try {
                    const response = await fetch(form.action, {
                        method: 'POST',
                        headers: { 'X-Requested-With': 'XMLHttpRequest' },
                        body: new FormData(form)
                    });

                    if (!response.ok) throw new Error('Cart request failed');

                    const payload = await response.json();
                    updateCartSummary(payload);

                    const row = form.closest('[data-cart-row]');
                    if (row) {
                        if (payload.quantity <= 0) {
                            row.remove();
                        } else {
                            row.querySelectorAll('[data-cart-quantity]').forEach((el) => {
                                el.textContent = payload.quantity;
                            });
                            const lineTotal = row.querySelector('[data-cart-line-total]');
                            if (lineTotal) lineTotal.textContent = payload.line_total;
                        }
                    }
                } catch (error) {
                    form.submit(); // fall back to a normal submit if the AJAX call fails
                } finally {
                    if (submitButton) submitButton.disabled = false;
                }
            });
        });
    }
});