// main.js — students will add JavaScript here as features are built

// Video Modal
(function() {
    const modal = document.getElementById('videoModal');
    const openBtn = document.getElementById('openModalBtn');
    const closeBtn = document.getElementById('closeModalBtn');
    const overlay = modal ? modal.querySelector('.video-modal-overlay') : null;
    const videoIframe = document.getElementById('videoIframe');

    // Placeholder YouTube video URL (replace with actual video later)
    const videoURL = 'https://www.youtube.com/embed/dQw4w9WgXcQ?enablejsapi=1';

    function openModal(e) {
        e.preventDefault();
        if (modal && videoIframe) {
            videoIframe.src = videoURL;
            modal.classList.add('active');
            document.body.style.overflow = 'hidden';
        }
    }

    function closeModal() {
        if (modal && videoIframe) {
            modal.classList.remove('active');
            videoIframe.src = ''; // Stop video playback
            document.body.style.overflow = '';
        }
    }

    if (openBtn) {
        openBtn.addEventListener('click', openModal);
    }

    if (closeBtn) {
        closeBtn.addEventListener('click', closeModal);
    }

    if (overlay) {
        overlay.addEventListener('click', closeModal);
    }

    // Close on Escape key
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape' && modal && modal.classList.contains('active')) {
            closeModal();
        }
    });
})();
