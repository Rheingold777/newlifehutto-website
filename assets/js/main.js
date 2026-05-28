// New Life Hutto - Main JavaScript v2

document.addEventListener('DOMContentLoaded', function() {

    // ========================================
    // Mobile Navigation Toggle
    // ========================================
    const navToggle = document.querySelector('.nav-toggle');
    const navMenu = document.querySelector('.nav-menu');

    if (navToggle && navMenu) {
        navToggle.addEventListener('click', function() {
            navMenu.classList.toggle('active');
            navToggle.classList.toggle('active');
        });

        // Close menu when clicking a link
        navMenu.querySelectorAll('a').forEach(function(link) {
            link.addEventListener('click', function() {
                navMenu.classList.remove('active');
                navToggle.classList.remove('active');
            });
        });
    }

    // ========================================
    // Navbar: transparent → solid on scroll
    // ========================================
    var navbar = document.getElementById('mainNav');
    if (navbar) {
        var isTransparent = navbar.classList.contains('navbar--transparent');

        function handleNavScroll() {
            if (window.scrollY > 80) {
                navbar.classList.add('navbar--scrolled');
            } else {
                navbar.classList.remove('navbar--scrolled');
            }
        }

        if (isTransparent) {
            window.addEventListener('scroll', handleNavScroll, { passive: true });
            handleNavScroll(); // run once on load
        }
    }

    // ========================================
    // Scroll-triggered fade-in animations
    // ========================================
    var fadeElements = document.querySelectorAll('.fade-in');
    if (fadeElements.length > 0 && 'IntersectionObserver' in window) {
        var fadeObserver = new IntersectionObserver(function(entries) {
            entries.forEach(function(entry) {
                if (entry.isIntersecting) {
                    entry.target.classList.add('visible');
                    fadeObserver.unobserve(entry.target);
                }
            });
        }, {
            threshold: 0.15,
            rootMargin: '0px 0px -50px 0px'
        });

        fadeElements.forEach(function(el) {
            fadeObserver.observe(el);
        });
    } else {
        // Fallback: show all immediately
        fadeElements.forEach(function(el) {
            el.classList.add('visible');
        });
    }

});

// ========================================
// Smooth scroll for anchor links
// ========================================
document.querySelectorAll('a[href^="#"]').forEach(function(anchor) {
    anchor.addEventListener('click', function(e) {
        e.preventDefault();
        var target = document.querySelector(this.getAttribute('href'));
        if (target) {
            target.scrollIntoView({
                behavior: 'smooth',
                block: 'start'
            });
        }
    });
});
