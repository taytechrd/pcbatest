/**
 * Global Dropdown Initialization for PCBA Test System
 * 
 * This file provides universal dropdown functionality across all pages.
 * It includes Bootstrap dropdown initialization and fallback handlers.
 */

(function() {
  'use strict';

  // Wait for DOM to be ready
  function initializeDropdowns() {
    console.log('Initializing global dropdown functionality...');

    // Debug: Check DOM state
    const profileDropdowns = document.querySelectorAll('.topbar-user .dropdown-toggle');
    console.log('Found profile dropdowns:', profileDropdowns.length);

    // Check if Bootstrap is loaded
    if (typeof bootstrap !== 'undefined') {
      console.log('Bootstrap loaded successfully, version:', bootstrap.Tooltip?.VERSION || 'Unknown');
      
      // Initialize all dropdowns
      var dropdownElementList = [].slice.call(document.querySelectorAll('[data-bs-toggle="dropdown"]'));
      console.log('Total dropdown elements found:', dropdownElementList.length);
      
      var dropdownList = dropdownElementList.map(function (dropdownToggleEl, index) {
        try {
          const dropdown = new bootstrap.Dropdown(dropdownToggleEl);
          console.log('Initialized dropdown', index + 1);
          return dropdown;
        } catch (e) {
          console.error('Failed to initialize dropdown', index + 1, ':', e.message);
          return null;
        }
      });
      
      console.log('Successfully initialized', dropdownList.filter(d => d !== null).length, 'out of', dropdownElementList.length, 'dropdowns');
    } else {
      console.error('Bootstrap not found! Dropdown functionality will not work.');
      console.log('Available globals:', Object.keys(window).filter(key => key.toLowerCase().includes('boot')));
    }

    // Setup jQuery event handlers if jQuery is available
    if (typeof $ !== 'undefined') {
      setupJQueryHandlers();
    } else {
      console.warn('jQuery not found, using vanilla JavaScript handlers');
      setupVanillaHandlers();
    }
  }

  function setupJQueryHandlers() {
    console.log('Setting up jQuery dropdown handlers...');
    
    // Fallback: Manual dropdown toggle for profile dropdown
    $('.dropdown-toggle.profile-pic').on('click', function(e) {
      console.log('Profile dropdown clicked (fallback handler)');
      e.preventDefault();
      e.stopPropagation();
      
      const $toggle = $(this);
      const $dropdown = $toggle.next('.dropdown-menu');
      const isShown = $dropdown.hasClass('show');
      
      console.log('Dropdown current state:', isShown ? 'shown' : 'hidden');
      console.log('Dropdown element found:', $dropdown.length > 0);
      
      // Close all other dropdowns first
      $('.dropdown-menu.show').removeClass('show');
      $('.dropdown-toggle[aria-expanded="true"]').attr('aria-expanded', 'false');
      
      // Toggle current dropdown
      if (!isShown) {
        $dropdown.addClass('show');
        $toggle.attr('aria-expanded', 'true');
        console.log('Dropdown opened');
      } else {
        $dropdown.removeClass('show');
        $toggle.attr('aria-expanded', 'false');
        console.log('Dropdown closed');
      }
    });
    
    // Enhanced click outside handler
    $(document).on('click', function(e) {
      const $target = $(e.target);
      if (!$target.closest('.dropdown').length && !$target.hasClass('dropdown-toggle') && !$target.closest('[data-bs-toggle="dropdown"]').length) {
        const openDropdowns = $('.dropdown-menu.show');
        if (openDropdowns.length > 0) {
          console.log('Closing', openDropdowns.length, 'open dropdowns (click outside)');
          openDropdowns.removeClass('show');
          $('.dropdown-toggle[aria-expanded="true"], [data-bs-toggle="dropdown"][aria-expanded="true"]').attr('aria-expanded', 'false');
        }
      }
    });
    
    // Universal dropdown handler for all topbar dropdowns
    $('.topbar-nav .dropdown-toggle, .topbar-nav [data-bs-toggle="dropdown"]').on('click', function(e) {
      console.log('Universal dropdown clicked:', $(this).closest('li').attr('class'));
      e.preventDefault();
      e.stopPropagation();
      
      const $toggle = $(this);
      // Find dropdown menu - can be next sibling or child
      let $dropdown = $toggle.next('.dropdown-menu');
      if ($dropdown.length === 0) {
        $dropdown = $toggle.siblings('.dropdown-menu');
      }
      if ($dropdown.length === 0) {
        $dropdown = $toggle.find('.dropdown-menu');
      }
      
      const isShown = $dropdown.hasClass('show');
      
      console.log('Universal dropdown current state:', isShown ? 'shown' : 'hidden');
      console.log('Universal dropdown element found:', $dropdown.length > 0);
      console.log('Dropdown classes:', $dropdown.attr('class'));
      
      // Close all other dropdowns first
      $('.dropdown-menu.show').removeClass('show');
      $('.dropdown-toggle[aria-expanded="true"], [data-bs-toggle="dropdown"][aria-expanded="true"]').attr('aria-expanded', 'false');
      
      // Toggle current dropdown
      if (!isShown && $dropdown.length > 0) {
        $dropdown.addClass('show');
        $toggle.attr('aria-expanded', 'true');
        console.log('Universal dropdown opened');
      }
    });

    // Debug: Test dropdown visibility on page load
    setTimeout(function() {
      const $profileDropdown = $('.topbar-user .dropdown-menu');
      const $profileToggle = $('.topbar-user .dropdown-toggle');
      
      console.log('=== DROPDOWN VISIBILITY DEBUG ===');
      console.log('Profile dropdown found on page load:', $profileDropdown.length > 0);
      
      if ($profileDropdown.length > 0) {
        console.log('Profile dropdown CSS display:', $profileDropdown.css('display'));
        console.log('Profile dropdown CSS visibility:', $profileDropdown.css('visibility'));
        console.log('Profile dropdown CSS z-index:', $profileDropdown.css('z-index'));
        console.log('Profile dropdown classes:', $profileDropdown.attr('class'));
        
        // Check parent containers
        const $navbar = $profileDropdown.closest('.navbar');
        const $mainHeader = $profileDropdown.closest('.main-header');
        
        console.log('Navbar overflow:', $navbar.css('overflow'));
        console.log('Main header overflow:', $mainHeader.css('overflow'));
      }
      
      // Test remaining dropdowns
      const $remainingDropdowns = $('.topbar-user .dropdown-menu');
      console.log('Remaining dropdowns found:', $remainingDropdowns.length);
      
      if ($remainingDropdowns.length > 0) {
        const $dropdown = $remainingDropdowns.first();
        console.log('Profile dropdown - Display:', $dropdown.css('display'), 'Position:', $dropdown.css('position'));
      }
      
      console.log('=== END DEBUG ===');
    }, 1000);
  }

  function setupVanillaHandlers() {
    console.log('Setting up vanilla JavaScript dropdown handlers...');
    
    // Profile dropdown click handler
    document.addEventListener('click', function(e) {
      const target = e.target.closest('.dropdown-toggle.profile-pic');
      if (target) {
        console.log('Profile dropdown clicked (vanilla handler)');
        e.preventDefault();
        e.stopPropagation();
        
        const dropdown = target.nextElementSibling;
        if (dropdown && dropdown.classList.contains('dropdown-menu')) {
          const isShown = dropdown.classList.contains('show');
          
          console.log('Dropdown current state:', isShown ? 'shown' : 'hidden');
          
          // Close all other dropdowns first
          document.querySelectorAll('.dropdown-menu.show').forEach(menu => {
            menu.classList.remove('show');
          });
          document.querySelectorAll('.dropdown-toggle[aria-expanded="true"]').forEach(toggle => {
            toggle.setAttribute('aria-expanded', 'false');
          });
          
          // Toggle current dropdown
          if (!isShown) {
            dropdown.classList.add('show');
            target.setAttribute('aria-expanded', 'true');
            console.log('Dropdown opened');
          } else {
            dropdown.classList.remove('show');
            target.setAttribute('aria-expanded', 'false');
            console.log('Dropdown closed');
          }
        }
      }
    });
    
    // Click outside handler
    document.addEventListener('click', function(e) {
      if (!e.target.closest('.dropdown') && !e.target.classList.contains('dropdown-toggle')) {
        const openDropdowns = document.querySelectorAll('.dropdown-menu.show');
        if (openDropdowns.length > 0) {
          console.log('Closing', openDropdowns.length, 'open dropdowns (click outside)');
          openDropdowns.forEach(dropdown => {
            dropdown.classList.remove('show');
          });
          document.querySelectorAll('.dropdown-toggle[aria-expanded="true"]').forEach(toggle => {
            toggle.setAttribute('aria-expanded', 'false');
          });
        }
      }
    });
  }

  // Initialize when DOM is ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initializeDropdowns);
  } else {
    initializeDropdowns();
  }

  // Also initialize when jQuery is ready (if jQuery loads after this script)
  if (typeof $ !== 'undefined') {
    $(document).ready(initializeDropdowns);
  }

  // Expose a global function to reinitialize dropdowns if needed
  window.reinitializeDropdowns = initializeDropdowns;

})();