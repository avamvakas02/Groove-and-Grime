// scroll_reveal.js — Triggers CSS animations when elements scroll into view

document.addEventListener('DOMContentLoaded', () => {
    const revealElements = document.querySelectorAll('.reveal');

    if (!revealElements.length) return;

    // I used IntersectionObserver here instead of listening to the scroll event
    // because it performs better and doesn't fire constantly while scrolling
    const observer = new IntersectionObserver((entries) => {
        entries.forEach((entry) => {
            if (entry.isIntersecting) {
                entry.target.classList.add('active'); // this is what kicks off the CSS animation
            }
        });
    }, { threshold: 0.1 }); // element needs to be 10% in view before it triggers

    revealElements.forEach((element) => observer.observe(element));
});