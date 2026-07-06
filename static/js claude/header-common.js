// ====================================================================
// HEADER-COMMON.JS
// Lógica de sesión y del header compartida por index.html, ajustes.html
// y cualquier otra página que use templates/_header.html.
//
// IMPORTANTE: este script debe cargarse ANTES que main.js / ajustes.js
// en el <body>, para que currentUser y authToken existan cuando esos
// otros scripts los usen.
// ====================================================================

let currentUser = JSON.parse(localStorage.getItem('user')) || null;
let authToken = localStorage.getItem('token') || null;

// --- Texto y estado del botón de usuario en el header ---
function updateUIForUser() {
    const btnText = document.getElementById('userMenuText');
    if (!btnText) return;
    btnText.textContent = currentUser ? `Hola, ${currentUser.nombre.split(' ')[0]}` : 'Iniciar Sesión';
}

// --- Abrir/cerrar el desplegable del usuario ---
function toggleUserMenu(e) {
    if (e) e.stopPropagation();
    if (!currentUser) {
        window.location.href = '/login';
        return;
    }
    const dropdown = document.getElementById('userDropdown');
    if (!dropdown) return;
    dropdown.style.display = dropdown.style.display === 'flex' ? 'none' : 'flex';
    dropdown.style.flexDirection = 'column';
}

// Cierra el desplegable si se pulsa fuera de él
document.addEventListener('click', (e) => {
    const dropdown = document.getElementById('userDropdown');
    if (dropdown && !e.target.closest('#userMenuBtn') && !e.target.closest('.user-dropdown')) {
        dropdown.style.display = 'none';
    }
});

// --- Cerrar sesión (válido en cualquier página) ---
function handleLogout() {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    currentUser = null;
    authToken = null;
    window.location.href = '/';
}

// --- Buscador del header ---
// Si la página actual define su propia función searchProducts() (como
// index.html), la usamos. Si no (ajustes.html, etc.), redirigimos a la
// home con la búsqueda como parámetro.
function handleHeaderSearch() {
    const input = document.getElementById('searchInput');
    const query = input ? input.value.trim() : '';
    if (typeof searchProducts === 'function' && window.location.pathname === '/') {
        searchProducts();
    } else {
        window.location.href = '/?q=' + encodeURIComponent(query);
    }
}

// --- Botón "Mis Favoritos" del header ---
// Igual que la búsqueda: usa showFavorites() si existe en la página
// actual (index.html), si no redirige a donde corresponda.
function handleHeaderFavorites(e) {
    if (e) e.preventDefault();
    if (typeof showFavorites === 'function' && window.location.pathname === '/') {
        showFavorites(e);
    } else if (!authToken) {
        window.location.href = '/login';
    } else {
        window.location.href = '/';
    }
}

document.addEventListener('DOMContentLoaded', updateUIForUser);
