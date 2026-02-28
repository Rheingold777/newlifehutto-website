// New Life Hutto - Main JavaScript

// Mobile Navigation Toggle
document.addEventListener('DOMContentLoaded', function() {
    const navToggle = document.querySelector('.nav-toggle');
    const navMenu = document.querySelector('.nav-menu');
    
    if (navToggle && navMenu) {
        navToggle.addEventListener('click', function() {
            navMenu.classList.toggle('active');
            navToggle.classList.toggle('active');
        });
        
        // Close menu when clicking a link
        navMenu.querySelectorAll('a').forEach(link => {
            link.addEventListener('click', () => {
                navMenu.classList.remove('active');
                navToggle.classList.remove('active');
            });
        });
    }
    
    // Navbar background on scroll
    const navbar = document.querySelector('.navbar');
    if (navbar) {
        window.addEventListener('scroll', function() {
            if (window.scrollY > 50) {
                navbar.style.backgroundColor = 'rgba(26, 26, 46, 0.98)';
            } else {
                navbar.style.backgroundColor = 'rgba(26, 26, 46, 0.95)';
            }
        });
    }
});

// Smooth scroll for anchor links
document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function(e) {
        e.preventDefault();
        const target = document.querySelector(this.getAttribute('href'));
        if (target) {
            target.scrollIntoView({
                behavior: 'smooth',
                block: 'start'
            });
        }
    });
});

// Floating Action Button
const fabButton = document.getElementById('fabButton');
const fabMenu = document.getElementById('fabMenu');

if (fabButton && fabMenu) {
    fabButton.addEventListener('click', function() {
        fabMenu.classList.toggle('active');
        // Rotate the plus icon
        if (fabMenu.classList.contains('active')) {
            fabButton.style.transform = 'rotate(45deg)';
        } else {
            fabButton.style.transform = 'rotate(0deg)';
        }
    });
    
    // Close menu when clicking outside
    document.addEventListener('click', function(e) {
        if (!fabButton.contains(e.target) && !fabMenu.contains(e.target)) {
            fabMenu.classList.remove('active');
            fabButton.style.transform = 'rotate(0deg)';
        }
    });
}
