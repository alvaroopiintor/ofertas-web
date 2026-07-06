        // ==================== GLOBAL VARIABLES ====================
        const API_BASE = '/api/ofertas';
        let currentCategory = 'all';
        let currentSort = 'default';
        let allProducts = [];
        let displayedProducts = [];
        let currentPage = 1;
        const PRODUCTS_PER_PAGE = 20;
        let currentProduct = null;
        let productsLoaded = false;
        let currentCommentPage = 1;
        let totalComments = 0;
        let currentSearch = '';
        
        let relatedProductsList = [];
        let relatedProductsIndex = 0;
        const RELATED_PER_PAGE = 3;



// --- Variables de usuario: currentUser y authToken ahora se declaran
// en header-common.js, que se carga antes que este archivo. ---

        

        function closeAuthModal() {
            document.getElementById('authModal').classList.remove('active');
            document.getElementById('loginError').style.display = 'none';
            document.getElementById('registerError').style.display = 'none';
        }

        function switchAuthTab(tab) {
            const isLogin = tab === 'login';
            document.getElementById('authTitle').textContent = isLogin ? 'Iniciar sesión' : 'Crear cuenta';
            document.getElementById('loginForm').classList.toggle('active', isLogin);
            document.getElementById('registerForm').classList.toggle('active', !isLogin);
            
            // Opcional: limpiar errores al cambiar
            document.getElementById('loginError').style.display = 'none';
            document.getElementById('registerError').style.display = 'none';
        }


        // --- LÓGICA DE REGISTRO ---
        async function handleRegister(e) {
            e.preventDefault();
            const nombre = document.getElementById('registerName').value;
            const email = document.getElementById('registerEmail').value;
            const password = document.getElementById('registerPassword').value;
            const errorEl = document.getElementById('registerError');

            try {
                const res = await fetch('/api/registro', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ nombre, email, password })
                });
                const data = await res.json();

                if (data.status === 'ok') {
                    alert("¡Cuenta creada! Ahora puedes iniciar sesión.");
                    switchAuthTab('login');
                } else {
                    errorEl.textContent = data.message;
                    errorEl.style.display = 'block';
                }
            } catch (err) {
                errorEl.textContent = "Error de conexión con el servidor";
                errorEl.style.display = 'block';
            }
        }

        // --- LÓGICA DE LOGIN ---
        async function handleLogin(e) {
            e.preventDefault();
            const email = document.getElementById('loginEmail').value;
            const password = document.getElementById('loginPassword').value;
            const errorEl = document.getElementById('loginError');

            try {
                const res = await fetch('/api/login', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ email, password })
                });
                const data = await res.json();

                if (data.status === 'ok') {
                    // Guardamos la sesión
                    localStorage.setItem('token', data.token);
                    localStorage.setItem('user', JSON.stringify(data.usuario));
                    authToken = data.token;
                    currentUser = data.usuario;
                    
                    updateUIForUser();
                    closeAuthModal();
                    logDebug(`✅ Sesión iniciada: ${currentUser.nombre}`);
                } else {
                    errorEl.textContent = data.message;
                    errorEl.style.display = 'block';
                }
            } catch (err) {
                errorEl.textContent = "Error al conectar con el servidor";
                errorEl.style.display = 'block';
            }
        }

        function handleLogout() {
            localStorage.removeItem('token');
            localStorage.removeItem('user');
            authToken = null;
            currentUser = null;
            updateUIForUser();
            logDebug("🚪 Sesión cerrada");
            window.location.reload(); // Recargamos para limpiar estados
        }

        


        let userFavorites = new Set(); // Guardaremos aquí los IDs de los favoritos del usuario

        async function fetchUserFavorites() {
            if (!authToken) return;
            try {
                const res = await fetch('/api/favoritos', {
                    headers: { 'Authorization': `Bearer ${authToken}` }
                });
                const data = await res.json();
                if (data.favoritos) {
                    userFavorites = new Set(data.favoritos.map(f => f.id));
                    renderProducts(); // Refrescamos la cuadrícula para pintar los corazones
                }
            } catch (e) { console.error("Error cargando favoritos:", e); }
        }

        async function toggleFavorite(e, productId) {
            e.stopPropagation();
            if (!authToken) {
                openAuthModal();
                return;
            }

            try {
                const res = await fetch(`/api/ofertas/${productId}/favorito`, {
                    method: 'POST',
                    headers: { 'Authorization': `Bearer ${authToken}` }
                });
                const data = await res.json();
                if (data.status === 'ok') {
                    if (data.accion === 'añadido') userFavorites.add(productId);
                    else userFavorites.delete(productId);
                    renderProducts(); // Actualizamos visualmente
                    if (currentProduct && currentProduct.id === productId) renderDetailFavoriteBtn();
                }
            } catch (e) { alert("Error al conectar con el servidor"); }
        }


        // --- FUNCIÓN PARA MOSTRAR LA LISTA DE FAVORITOS ---
        async function showFavorites(e) {
            if (e) e.preventDefault();
            
            if (!authToken) {
                window.location.href = '/login'; // Te lleva directo sin alert
                return;
            }
            
            showLoading(); 
            try {
                const res = await fetch('/api/favoritos', {
                    headers: { 'Authorization': `Bearer ${authToken}` }
                });
                const data = await res.json();
                
                displayedProducts = data.favoritos.map(p => ({
                    ...p,
                    precioAntes: p.precio_antes,
                    votosHot: p.votos_calientes || 0,
                    votosCold: p.votos_frios || 0,
                    timestamp: p.fecha_creacion || new Date()
                }));
                
                // ESCONDEMOS EL RESTO DE SECCIONES PARA QUE SE VEA EL GRID
                document.getElementById('productDetailSection').classList.remove('active');
                document.getElementById('blogSection').style.display = 'none';
                document.getElementById('hotSection').style.display = 'none';
                document.getElementById('storesSection').style.display = 'none';
                document.getElementById('homeSection').style.display = 'block';
                
                renderProducts(); // Dibuja los productos con el mismo diseño exacto
                
                document.getElementById('loadMoreBtn').style.display = 'none';
                document.querySelectorAll('.sidebar-btn').forEach(btn => btn.classList.remove('active'));
            } catch (err) {
                showError();
            }
        }


function renderDetailFavoriteBtn() {
            const container = document.querySelector('.product-detail-info-container');
            if (!container || !currentProduct) return;

            // Borramos el botón viejo si ya existe
            const oldBtn = document.getElementById('detailFavBtn');
            if (oldBtn) oldBtn.remove();

            const isFav = userFavorites.has(currentProduct.id);
            const favBtn = document.createElement('button');
            favBtn.id = 'detailFavBtn';
            favBtn.style.cssText = 'background: none; border: 2px solid var(--border-color); border-radius: 12px; padding: 15px; cursor: pointer; font-size: 20px; transition: all 0.2s; margin-bottom: 25px; width: 60px; margin-left: 10px; vertical-align: top;';
            favBtn.innerHTML = `<i class="${isFav ? 'fas' : 'far'} fa-heart" style="color: ${isFav ? 'var(--danger-color)' : 'var(--text-muted)'}"></i>`;
            favBtn.onclick = (e) => toggleFavorite(e, currentProduct.id);
            
            // Insertamos el corazón justo después del botón de Amazon
            const amazonBtn = document.getElementById('detailAmazonLink');
            amazonBtn.style.display = 'inline-block';
            amazonBtn.style.width = 'calc(100% - 80px)';
            amazonBtn.parentNode.insertBefore(favBtn, amazonBtn.nextSibling);
        }


        // ==================== INITIALIZATION ====================
        document.addEventListener('DOMContentLoaded', () => {
            console.log('🟢 DOMContentLoaded - Iniciando aplicación');
            updateUIForUser(); // <--- AÑADIR ESTA LÍNEA
            fetchUserFavorites(); // <--- AÑADE ESTA LÍNEA
            loadProducts();
            updateStats();
            setupEventListeners();
            updateLastUpdateTime();
            updateThemeIcon();
        });

        // ==================== SIDEBAR TOGGLE ====================
        function toggleSidebar() {
            const sidebar = document.getElementById('sidebar');
            const overlay = document.getElementById('sidebarOverlay');
            sidebar.classList.toggle('active');
            overlay.classList.toggle('active');
        }

        // ==================== FUNCION MENU DESPLEGABLE DE CATEGORIAS ====================
        function toggleCategoriesSubmenu(event) {
            if (event) event.preventDefault();
            const menu = document.getElementById('sidebarCategoriesMenu');
            const icon = document.getElementById('catSubmenuIcon');
            
            if (menu.style.display === 'none') {
                menu.style.display = 'flex';
                icon.classList.add('rotate-180');
            } else {
                menu.style.display = 'none';
                icon.classList.remove('rotate-180');
            }
        }

        // ==================== EVENT LISTENERS ====================
        function setupEventListeners() {
            document.querySelectorAll('.category-btn').forEach(btn => {
                btn.addEventListener('click', (e) => {
                    document.querySelectorAll('.category-btn').forEach(b => b.classList.remove('active'));
                    e.target.closest('.category-btn').classList.add('active');
                    setCategory(e.target.closest('.category-btn').dataset.category);
                });
            });

            document.querySelectorAll('.sort-btn').forEach(btn => {
                btn.addEventListener('click', (e) => {
                    document.querySelectorAll('.sort-btn').forEach(b => b.classList.remove('active'));
                    e.target.closest('.sort-btn').classList.add('active');
                    setSort(e.target.closest('.sort-btn').dataset.sort);
                });
            });

            document.getElementById('searchInput').addEventListener('keypress', (e) => {
                if (e.key === 'Enter') searchProducts();
            });

            document.getElementById('loadMoreBtn').addEventListener('click', loadMoreProducts);

            window.addEventListener('popstate', () => checkRoute());

            document.addEventListener('keydown', (e) => {
                if (e.key === 'Escape') {
                    const sidebar = document.getElementById('sidebar');
                    if (sidebar.classList.contains('active')) {
                        toggleSidebar();
                    }
                    if (document.getElementById('productDetailSection').classList.contains('active')) {
                        showHome();
                    }
                }
            });
        }

        // ==================== CHECK URL HASH ====================
        // ==================== CHECK URL ROUTE ====================
        function checkRoute() {
            if (!productsLoaded || allProducts.length === 0) {
                setTimeout(checkRoute, 100);
                return;
            }
            
            const path = window.location.pathname; // Leemos la ruta real, ej: /producto/123
            
            if (path.startsWith('/producto/')) {
                const productId = path.split('/').pop();
                const producto = allProducts.find(p => p.id == productId);
                if (producto) {
                    showProductDetailPage(producto, false); // false = no empujar al historial otra vez
                } else {
                    showHome(null, false);
                }
            } else {
                // Si estamos en la raíz o cualquier otra ruta
                const detailSection = document.getElementById('productDetailSection');
                if (detailSection && detailSection.classList.contains('active')) {
                     showHome(null, false);
                }
            }
        }

        // ==================== SHOW PRODUCT DETAIL PAGE ====================
        function showProductDetailPage(producto, updateURL = true) {
            console.log('🟢 showProductDetailPage llamado - ID:', producto ? producto.id : 'NULL');
            
            if (!producto) {
                console.error('❌ No hay producto para mostrar');
                showHome();
                return;
            }
            
            currentProduct = producto;
            if (updateURL) {
                window.history.pushState({ id: producto.id }, "", `/producto/${producto.id}`);
            }
            
            const precioAntiguo = producto.precioAntes || producto.precio_antes;
            const descuento = calculateDiscount(producto.precio, precioAntiguo);
            const userVote = getUserVote(producto.id);
            const votosNetos = (producto.votosHot || 0) - (producto.votosCold || 0);
            
            // Rellenar datos de la página
            const detailImage = document.getElementById('detailImage');
            const imageContainer = document.querySelector('.product-detail-image-container'); // Buscamos el contenedor
            const detailTitle = document.getElementById('detailTitle');
            const detailPrice = document.getElementById('detailPrice');
            const detailAmazonLink = document.getElementById('detailAmazonLink');
            
            if (detailImage) detailImage.src = sanitizeURL(producto.imagen) || 'https://via.placeholder.com/600x600?text=Producto';
            if (detailCategory) detailCategory.textContent = producto.categoria || 'General';
            if (detailTitle) detailTitle.textContent = producto.nombre || 'Producto';
            if (detailPrice) detailPrice.textContent = producto.precio || '';
            if (detailAmazonLink) detailAmazonLink.href = sanitizeURL(producto.link) || '#';
            

            // --- AÑADIR LOGO A LA IMAGEN GRANDE ---
            if (imageContainer) {
                imageContainer.style.position = 'relative'; // Aseguramos que el contenedor permita posicionar el logo
                
                // Limpiamos logos anteriores para que no se amontonen si cambias de producto
                const oldLogo = imageContainer.querySelector('.detail-logo-badge');
                if (oldLogo) oldLogo.remove();

                const detailLogo = document.createElement('div');
                detailLogo.className = 'detail-logo-badge';
                // Lo ponemos a 15px de la esquina en la imagen grande porque el contenedor es más amplio
                detailLogo.style.cssText = 'position: absolute; bottom: 15px; left: 15px; z-index: 10;';
                detailLogo.innerHTML = '<img src="/static/logoamazon.png" style="height: 80px; width: auto; filter: drop-shadow(0px 4px 6px rgba(0,0,0,0.3));">';
                imageContainer.appendChild(detailLogo);
            }          

            // Breadcrumb
            document.getElementById('breadcrumbProduct').textContent = producto.nombre || 'Producto';
            document.getElementById('breadcrumbCategory').textContent = producto.categoria || 'General';
            
            // Precio anterior y descuento
            const detailOldPrice = document.getElementById('detailOldPrice');
            const detailDiscount = document.getElementById('detailDiscount');

            if (detailOldPrice) {
                if (precioAntiguo && precioAntiguo !== "N/A") {
                    detailOldPrice.textContent = precioAntiguo;
                    detailOldPrice.style.display = 'inline';
                } else {
                    detailOldPrice.style.display = 'none';
                }
            }
            if (detailDiscount) {
                detailDiscount.textContent = descuento > 0 ? `-${descuento}%` : '';
                // Podemos usar los mismos colores verdes para el detalle:
                detailDiscount.style.backgroundColor = '#e6f4ea';
                detailDiscount.style.color = '#137333';
                detailDiscount.style.display = descuento > 0 ? 'inline' : 'none';
            }
            
            // ✅ VOTOS - ACTUALIZAR BOTONES CON ESTADO DEL USUARIO
            const detailVoteHot = document.getElementById('detailVoteHot');
            const detailVoteCold = document.getElementById('detailVoteCold');
            const detailVoteHotCount = document.getElementById('detailVoteHotCount');
            const detailVoteColdCount = document.getElementById('detailVoteColdCount');
            const detailVoteTotal = document.getElementById('detailVoteTotal');
            
            if (detailVoteHotCount) detailVoteHotCount.textContent = producto.votosHot || 0;
            if (detailVoteColdCount) detailVoteColdCount.textContent = producto.votosCold || 0;
            if (detailVoteTotal) {
                detailVoteTotal.textContent = `${votosNetos >= 0 ? '+' : ''}${votosNetos}°`;
                detailVoteTotal.className = `product-detail-vote-total ${votosNetos >= 0 ? 'positive' : 'negative'}`;
            }
            
            // ✅ APLICAR CLASES DE VOTO DEL USUARIO
            if (detailVoteHot) {
                detailVoteHot.classList.remove('voted-hot', 'voted-cold');
                if (userVote === 'hot') {
                    detailVoteHot.classList.add('voted-hot');
                }
            }
            if (detailVoteCold) {
                detailVoteCold.classList.remove('voted-hot', 'voted-cold');
                if (userVote === 'cold') {
                    detailVoteCold.classList.add('voted-cold');
                }
            }
            
            // Timestamp
            const detailTimestamp = document.getElementById('detailTimestamp');
            if (detailTimestamp) detailTimestamp.textContent = tiempoRelativo(producto.timestamp);
            
            // Descripción
            renderDetailDescription(producto);
            
            // Comentarios (carga inicial)
            currentCommentPage = 1;
            renderDetailComments(producto.id, true); // true indica que es una carga desde cero
            
            // Productos relacionados (Nuevo Carrusel)
            renderDetailRelated(producto);
            
            // Mostrar página completa
            document.getElementById('homeSection').style.display = 'none';
            document.getElementById('blogSection').style.display = 'none';
            document.getElementById('hotSection').style.display = 'none';
            document.getElementById('storesSection').style.display = 'none';
            document.getElementById('productDetailSection').classList.add('active');
            
            // Actualizar nav active
            document.querySelectorAll('.sidebar-btn').forEach(btn => btn.classList.remove('active'));
            
            // ✅ CARGAR PRODUCTOS DESTACADOS EN SIDEBAR (con el nuevo filtro para excluir al producto actual)
            renderFeaturedProducts();
            
            window.scrollTo(0, 0);
            
            logDebug(`📄 Página de detalle abierta: ${producto.id}`);
            



            // ... (todo el código anterior de la función)
            
            // ✅ CARGAR PRODUCTOS DESTACADOS EN SIDEBAR
            renderFeaturedProducts();
            
            window.scrollTo(0, 0);
            
            // 1. Añadimos la llamada aquí para que dibuje el corazón
            renderDetailFavoriteBtn(); 
            
            logDebug(`📄 Página de detalle abierta: ${producto.id}`);
        } // <--- Esta es la llave que cierra la función            




        // ==================== HANDLE VOTE ON DETAIL PAGE ====================
        async function handleDetailVote(voteType) {
            if (!currentProduct) {
                console.error('❌ No hay producto seleccionado');
                return;
            }
    
            // Desactivar botones temporalmente para evitar doble clic
            const detailVoteHot = document.getElementById('detailVoteHot');
            const detailVoteCold = document.getElementById('detailVoteCold');
            if (detailVoteHot) detailVoteHot.style.pointerEvents = 'none';
            if (detailVoteCold) detailVoteCold.style.pointerEvents = 'none';
     
            const currentVote = getUserVote(currentProduct.id);
            const newVote = await setUserVote(currentProduct.id, voteType); // Esperamos al servidor
    
            // Actualizar contadores locales
            if (newVote === 'hot') {
                currentProduct.votosHot = (currentProduct.votosHot || 0) + 1;
                if (currentVote === 'cold') {
                    currentProduct.votosCold = Math.max(0, (currentProduct.votosCold || 0) - 1);
                }
            } else if (newVote === 'cold') {
                currentProduct.votosCold = (currentProduct.votosCold || 0) + 1;
                if (currentVote === 'hot') {
                    currentProduct.votosHot = Math.max(0, (currentProduct.votosHot || 0) - 1);
                }
            } else {
                // Quitar voto
                if (currentVote === 'hot') {
                    currentProduct.votosHot = Math.max(0, (currentProduct.votosHot || 0) - 1);
                }
                if (currentVote === 'cold') {
                    currentProduct.votosCold = Math.max(0, (currentProduct.votosCold || 0) - 1);
                }
            }
    
            // Actualizar números en la pantalla
            const detailVoteHotCount = document.getElementById('detailVoteHotCount');
            const detailVoteColdCount = document.getElementById('detailVoteColdCount');
            const detailVoteTotal = document.getElementById('detailVoteTotal');
    
            const votosNetos = (currentProduct.votosHot || 0) - (currentProduct.votosCold || 0);
    
            if (detailVoteHotCount) detailVoteHotCount.textContent = currentProduct.votosHot || 0;
            if (detailVoteColdCount) detailVoteColdCount.textContent = currentProduct.votosCold || 0;
            if (detailVoteTotal) {
                detailVoteTotal.textContent = `${votosNetos >= 0 ? '+' : ''}${votosNetos}°`;
                detailVoteTotal.className = `product-detail-vote-total ${votosNetos >= 0 ? 'positive' : 'negative'}`;
            }
    
            // Actualizar colores
            if (detailVoteHot) {
                detailVoteHot.classList.remove('voted-hot', 'voted-cold');
                if (newVote === 'hot') detailVoteHot.classList.add('voted-hot');
                detailVoteHot.style.pointerEvents = 'auto'; // Reactivar botón
            }
            if (detailVoteCold) {
                detailVoteCold.classList.remove('voted-hot', 'voted-cold');
                if (newVote === 'cold') detailVoteCold.classList.add('voted-cold');
                detailVoteCold.style.pointerEvents = 'auto'; // Reactivar botón
            }
    
            updateProductVoteInGrid(currentProduct.id);
        }

        // ==================== RENDER FEATURED PRODUCTS (SIDEBAR) ====================
        async function renderFeaturedProducts() {
            const list = document.getElementById('featuredProductsList');
            const listDetail = document.getElementById('topDealsListDetail');
            
            if (!list && !listDetail) return;
            
            try {
                const response = await fetch(`${API_BASE}?sort=discount-desc&limit=10&activos=true`);
                if (!response.ok) throw new Error('Error al cargar destacados');
                const data = await response.json();
                
                let featured = data.ofertas;
                
                if (currentProduct) {
                    featured = featured.filter(p => p.id !== currentProduct.id);
                }
                
                featured = featured.slice(0, 3);

                if (featured.length === 0) return;

                const html = featured.map((p, index) => {
                    // Detectamos el precio antiguo (formato API o formato local)
                    const precioAntiguo = p.precio_antes || p.precioAntes;
                    const descuento = calculateDiscount(p.precio, precioAntiguo); 
                    
                    return `
                        <li class="featured-product-item" onclick="showProductDetailPage(${JSON.stringify(p).replace(/"/g, '&quot;')})">
                            <div style="position: relative;">
                                <img src="${sanitizeURL(p.imagen) || 'https://via.placeholder.com/70'}" alt="${p.nombre || 'Producto'}">
                                <span style="position: absolute; top: -5px; left: -5px; background: var(--danger-color); color: #fff; width: 24px; height: 24px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 12px; font-weight: bold;">${index + 1}</span>
                            </div>
                            <div class="featured-product-info">
                                <div class="featured-product-title">${sanitizeHTML(p.nombre || 'Producto')}</div>
                                
                                <div style="display: flex; align-items: baseline; gap: 6px; flex-wrap: wrap; margin-bottom: 4px;">
                                    <div class="featured-product-price" style="font-size: 15px;">${p.precio || 'N/A'}</div>
                                    ${precioAntiguo && precioAntiguo !== "N/A" ? 
                                        `<span style="text-decoration: line-through; color: var(--text-muted); font-size: 11px;">${precioAntiguo}</span>` : ''}
                                </div>
                                
                                ${descuento > 0 ? `<span class="featured-product-discount">-${descuento}%</span>` : ''}
                            </div>
                        </li>
                    `;
                }).join('');
                
                if (list) list.innerHTML = html;
                if (listDetail) listDetail.innerHTML = html;
                
            } catch (e) {
                console.error("❌ Error cargando destacados:", e);
            }
        }

        // ==================== RENDER DESCRIPTION ====================
        function renderDetailDescription(producto) {
            const contentDiv = document.getElementById('detailDescriptionContent');
            if (!contentDiv) return;
            
            let desc = producto.descripcion;
            
            if (!desc || typeof desc !== 'string') {
                desc = '• Producto disponible en Amazon\n• Consulta todos los detalles y características en la página oficial\n• Envío rápido y seguro';
            }
            
            try {
                contentDiv.innerHTML = `<p>${desc.split('\n').map(l => l.trim()).filter(l => l).join('<br>')}</p>`;
            } catch (e) {
                console.error('❌ Error procesando descripción:', e);
                contentDiv.innerHTML = '<p class="no-description">Consulta todos los detalles en la página oficial de Amazon.</p>';
            }
        }

        // ==================== RENDER COMMENTS ====================
        async function renderDetailComments(productId, reset = false) {
    const list = document.getElementById('detailCommentsList');
    
    // Si reseteamos, limpiamos la lista y mostramos un loader
    if (reset) {
        currentCommentPage = 1;
        if (list) list.innerHTML = '<div style="text-align:center; padding: 20px;"><i class="fas fa-spinner fa-spin"></i> Cargando comentarios...</div>';
    }

    const comments = await getProductComments(productId, currentCommentPage);
    const countBadge = document.getElementById('detailCommentsCount');
    
    if (countBadge) countBadge.textContent = totalComments; // Usamos el total real de la BD

    if (reset && comments.length === 0) {
        if (list) {
            list.innerHTML = '<div class="no-comments"><i class="fas fa-comment-slash"></i><p>Sé el primero en comentar sobre este producto</p></div>';
        }
        return;
    }

    const html = comments.map(c => {
        const initial = c.username.charAt(0).toUpperCase();
        const fecha = new Date(c.date).toLocaleDateString('es-ES', { day: 'numeric', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' });
        return `
            <div class="comment-item">
                <div class="comment-header">
                    <div class="comment-author">
                        <div class="comment-avatar">${initial}</div>
                        <div>
                            <div class="comment-username">${sanitizeHTML(c.username)}</div>
                            <div class="comment-date">${fecha}</div>
                        </div>
                    </div>
                </div>
                <div class="comment-text">${sanitizeHTML(c.text)}</div>
            </div>
        `;
    }).join('');

    // Si es reset, sustituimos. Si no, adjuntamos al final.
    if (list) {
        if (reset) {
            list.innerHTML = html;
        } else {
            // Quitamos el botón de "Cargar más" anterior si existía
            const oldBtn = document.getElementById('loadMoreCommentsBtn');
            if (oldBtn) oldBtn.remove();
            list.insertAdjacentHTML('beforeend', html);
        }

        // Si aún hay más comentarios por cargar, dibujamos el botón al final
        const currentDisplayedCount = list.querySelectorAll('.comment-item').length;
        if (currentDisplayedCount < totalComments) {
            list.insertAdjacentHTML('beforeend', `
                <button id="loadMoreCommentsBtn" class="load-more" onclick="loadMoreComments()" style="display: block; margin: 20px auto; width: 100%;">
                    Ver más comentarios
                </button>
            `);
        }
    }
}

// Nueva función para el botón
function loadMoreComments() {
    if (!currentProduct) return;
    currentCommentPage++;
    
    const btn = document.getElementById('loadMoreCommentsBtn');
    if (btn) btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Cargando...';
    
    renderDetailComments(currentProduct.id, false);
}

        // ==================== RENDER RELATED PRODUCTS (CARRUSEL) ====================

        
        // ✅ AÑADIR ESTA FUNCIÓN NUEVA (junto a tus otras funciones de render):
        function renderDetailCommentsFromAPI(productId, comments) {
            const list = document.getElementById('detailCommentsList');
            const count = document.getElementById('detailCommentsCount');
    
            if (count) count.textContent = comments.length;
    
            if (comments.length === 0) {
                if (list) {
                    list.innerHTML = '<div class="no-comments"><i class="fas fa-comment-slash"></i><p>Sé el primero en comentar sobre este producto</p></div>';
                }
                return;
            }
    
            if (list) {
                list.innerHTML = comments.map(c => {
                    const initial = c.username.charAt(0).toUpperCase();
                    const fecha = new Date(c.date).toLocaleDateString('es-ES', { day: 'numeric', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' });
                    return `
                        <div class="comment-item">
                            <div class="comment-header">
                                <div class="comment-author">
                                    <div class="comment-avatar">${initial}</div>
                                    <div>
                                        <div class="comment-username">${sanitizeHTML(c.username)}</div>
                                        <div class="comment-date">${fecha}</div>
                                    </div>
                                </div>
                            </div>
                            <div class="comment-text">${sanitizeHTML(c.text)}</div>
                        </div>
                    `;
                }).join('');
            }
        }


        
// ==================== RELATED PRODUCTS (CARRUSEL) ====================

async function renderDetailRelated(producto) {
    const relatedGrid = document.getElementById('detailRelatedGrid');
    if (relatedGrid) {
        relatedGrid.innerHTML = '<div style="grid-column: 1/-1; text-align: center; padding: 30px;"><i class="fas fa-spinner fa-spin"></i> Buscando chollos similares...</div>';
    }

    try {
        // Le pedimos al servidor 12 productos de esta misma categoría
        const response = await fetch(`${API_BASE}?categoria=${encodeURIComponent(producto.categoria)}&limit=12&activos=true`);
        if (!response.ok) throw new Error('Error al cargar relacionadas');
        const data = await response.json();

        // Filtramos para NO incluir el producto que el usuario ya está viendo
        relatedProductsList = data.ofertas
            .filter(p => p.id !== producto.id)
            .map(p => ({
                ...p,
                votosHot: p.votos_calientes || 0,
                votosCold: p.votos_frios || 0
            }));

        // Reiniciamos el índice del carrusel al principio
        relatedProductsIndex = 0;
        
        // Dibujamos las tarjetas
        updateRelatedGrid();
        
    } catch (error) {
        console.error("❌ Error cargando relacionadas:", error);
        if (relatedGrid) {
            relatedGrid.innerHTML = '<p style="color: var(--text-muted); grid-column: 1/-1; text-align: center;">No hay más ofertas en esta categoría ahora mismo.</p>';
        }
    }
}

function updateRelatedGrid() {
    const relatedGrid = document.getElementById('detailRelatedGrid');
    const nextBtn = document.getElementById('nextRelatedBtn');
    const prevBtn = document.getElementById('prevRelatedBtn'); 
    
    if (!relatedGrid) return;
    
    if (relatedProductsList.length === 0) {
        relatedGrid.innerHTML = '<p style="color: var(--text-muted); grid-column: 1/-1; text-align: center;">No hay ofertas relacionadas en esta categoría</p>';
        if (nextBtn) nextBtn.style.display = 'none';
        if (prevBtn) prevBtn.style.display = 'none';
        return;
    }
    
    relatedGrid.classList.remove('carousel-animate');
    void relatedGrid.offsetWidth;
    relatedGrid.classList.add('carousel-animate');
    
    const visibleProducts = relatedProductsList.slice(relatedProductsIndex, relatedProductsIndex + RELATED_PER_PAGE);
    
    relatedGrid.innerHTML = visibleProducts.map(p => {
        // Buscamos el precio antiguo en ambos formatos posibles
        const precioAntiguo = p.precio_antes || p.precioAntes;
        const descuento = calculateDiscount(p.precio, precioAntiguo);
        
        return `
            <div class="product-card" onclick="showProductDetailPage(${JSON.stringify(p).replace(/"/g, '&quot;')})">
                <div class="product-card-image">
                    <div style="position: absolute; bottom: 5px; left: 5px; z-index: 10; display: flex; align-items: center; justify-content: center;">
                        <img src="/static/logoamazon.png" style="height: 65px; width: auto; object-fit: contain; filter: drop-shadow(0px 2px 4px rgba(0,0,0,0.4));">
                    </div>
                    <img src="${sanitizeURL(p.imagen) || 'https://via.placeholder.com/300x200?text=Producto'}" alt="${p.nombre}" loading="lazy">
                </div>
                <div class="product-card-content">
                    <span class="store-badge">${p.categoria || 'General'}</span>
                    <h3>${sanitizeHTML(p.nombre || 'Producto')}</h3>
                    <div class="price-container">
                        <span class="price">${p.precio || ''}</span>
                        ${precioAntiguo && precioAntiguo !== "N/A" ? `<span class="old-price">${precioAntiguo}</span>` : ''}
                        ${descuento > 0 ? `<span class="inline-discount">-${descuento}%</span>` : ''}
                    </div>
                    <a href="${sanitizeURL(p.link) || '#'}" target="_blank" class="amazon-btn" onclick="event.stopPropagation()">Ver Oferta en Amazon →</a>
                </div>
            </div>
        `;
    }).join('');

    if (nextBtn) {
        nextBtn.style.display = (relatedProductsIndex + RELATED_PER_PAGE < relatedProductsList.length) ? 'flex' : 'none';
    }
    if (prevBtn) {
        prevBtn.style.display = (relatedProductsIndex > 0) ? 'flex' : 'none';
    }
}
function nextRelatedProducts() {
    if (relatedProductsIndex + RELATED_PER_PAGE < relatedProductsList.length) {
        relatedProductsIndex += RELATED_PER_PAGE;
        updateRelatedGrid();
    }
}

function prevRelatedProducts() {
    if (relatedProductsIndex - RELATED_PER_PAGE >= 0) {
        relatedProductsIndex -= RELATED_PER_PAGE;
        updateRelatedGrid();
    }
}

        // ==================== SHOW HOME ====================
        function showHome(event) {
            if (event) event.preventDefault();
            
            if (event !== false) window.history.pushState(null, "", "/");
            currentProduct = null;
            
            document.getElementById('productDetailSection').classList.remove('active');
            document.getElementById('homeSection').style.display = 'block';
            document.getElementById('blogSection').style.display = 'none';
            document.getElementById('hotSection').style.display = 'none';
            document.getElementById('storesSection').style.display = 'none';
            
            document.querySelectorAll('.sidebar-btn').forEach(btn => btn.classList.remove('active'));
            document.querySelector('.sidebar-btn:first-child').classList.add('active');
            
            window.scrollTo(0, 0);

            // Al volver al inicio, recargamos los destacados para que vuelva a salir el producto en la lista si lo merece
            renderFeaturedProducts();
        }

        // ==================== SHOW SECTION ====================
        function showSection(event, section) {
            if (event) event.preventDefault();
            
            window.history.pushState(null, "", "/");
            currentProduct = null;
            
            document.getElementById('productDetailSection').classList.remove('active');
            document.getElementById('homeSection').style.display = 'none';
            document.getElementById('blogSection').style.display = section === 'blog' ? 'block' : 'none';
            document.getElementById('hotSection').style.display = section === 'hot' ? 'block' : 'none';
            document.getElementById('storesSection').style.display = section === 'stores' ? 'block' : 'none';
            
            document.querySelectorAll('.sidebar-btn').forEach(btn => btn.classList.remove('active'));
            event.target.closest('.sidebar-btn').classList.add('active');
            
            if (section === 'hot') renderHotProducts();
            
            window.scrollTo(0, 0);

            // Recargamos los destacados también al entrar en otras secciones
            renderFeaturedProducts();
        }

        // ==================== OTHER FUNCTIONS ====================
        function updateLastUpdateTime() {
            const now = new Date();
            const timeString = now.toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit' });
            
            const statLastUpdate = document.getElementById('statLastUpdate');
            const statLastUpdateSidebar = document.getElementById('statLastUpdateSidebar');
            const statLastUpdateDetail = document.getElementById('statLastUpdateDetail');
            
            if (statLastUpdate) statLastUpdate.textContent = timeString;
            if (statLastUpdateSidebar) statLastUpdateSidebar.textContent = timeString;
            if (statLastUpdateDetail) statLastUpdateDetail.textContent = timeString;
        }

        function tiempoRelativo(fecha) {
            if (!fecha) return 'Reciente';
            const ahora = new Date();
            const diff = ahora - new Date(fecha);
            const minutos = Math.floor(diff / 60000);
            const horas = Math.floor(minutos / 60);
            const dias = Math.floor(horas / 24);
            if (minutos < 1) return 'Ahora mismo';
            if (minutos < 60) return `Hace ${minutos} min`;
            if (horas < 24) return `Hace ${horas} h`;
            return `Hace ${dias} días`;
        }

        function getTemperatureClass(descuento) {
            if (descuento >= 50) return 'temperature-hot';
            if (descuento >= 30) return 'temperature-warm';
            return 'temperature-cool';
        }

        function getFireEmojis(descuento) {
            if (descuento >= 50) return '🔥🔥🔥';
            if (descuento >= 30) return '🔥🔥';
            if (descuento >= 15) return '🔥';
            return '';
        }

        function sanitizeHTML(str) {
            if (!str) return '';
            const div = document.createElement('div');
            div.textContent = str;
            return div.innerHTML;
        }

        function sanitizeURL(str) {
            if (!str) return '';
            const trimmed = String(str).trim();
            if (/^(javascript|data|vbscript):/i.test(trimmed)) return '';
            return trimmed;
        }

        function extractPrice(priceStr) {
            if (!priceStr) return 0;
            return parseFloat(String(priceStr).replace(/[^0-9.,]/g, '').replace(',', '.')) || 0;
        }

        function calculateDiscount(price, oldPrice) {
            if (!price || !oldPrice) return 0;
            const priceNum = extractPrice(price);
            const oldPriceNum = extractPrice(oldPrice);
            if (oldPriceNum > 0) return Math.round(((oldPriceNum - priceNum) / oldPriceNum) * 100);
            return 0;
        }

        function updateThemeIcon() {
            const themeIcon = document.getElementById('themeIcon');
            const isDark = document.documentElement.classList.contains('dark-mode');
            themeIcon.className = isDark ? 'fas fa-sun' : 'fas fa-moon';
        }

        function toggleTheme() {
            const isDark = document.documentElement.classList.toggle('dark-mode');
            localStorage.setItem('theme', isDark ? 'dark' : 'light');
            updateThemeIcon();
        }

        function getUserVote(productId) {
            const votes = JSON.parse(localStorage.getItem('userVotes') || '{}');
            return votes[productId] || null;
        }

        async function setUserVote(productId, voteType) {
            // 1. COMPROBAR SI ESTÁ LOGUEADO
            if (!authToken) {
                openAuthModal();
                return null;
            }

            try {
                // 2. ENVIAR EL VOTO CON EL TOKEN DE SEGURIDAD
                const res = await fetch(`${API_BASE.replace('/api/ofertas', '')}/api/ofertas/${productId}/voto`, {
                    method: "POST",
                    headers: { 
                        "Content-Type": "application/json",
                        "Authorization": `Bearer ${authToken}` // <-- ¡LA LLAVE MAESTRA!
                    },
                    body: JSON.stringify({ tipo: voteType === 'hot' ? 'caliente' : 'frio' })
                });
                
                const data = await res.json();
                
                if (res.status === 401) {
                    // Si el token ha caducado
                    handleLogout();
                    alert("Tu sesión ha caducado. Por favor, inicia sesión de nuevo.");
                    openAuthModal();
                    return null;
                }

                if (data.status === "ok") {
                    // Actualizar localStorage visual (para que los botones sigan marcados al recargar)
                    const votes = JSON.parse(localStorage.getItem('userVotes') || '{}');
                    if (data.voto_actual) {
                        votes[productId] = data.voto_actual === 'caliente' ? 'hot' : 'cold';
                    } else {
                        delete votes[productId];
                    }
                    localStorage.setItem('userVotes', JSON.stringify(votes));

                    // Actualizar UI si estamos en la página de detalle
                    if (currentProduct && currentProduct.id == productId) {
                        document.getElementById('detailVoteHotCount').textContent = data.calientes || 0;
                        document.getElementById('detailVoteColdCount').textContent = data.frios || 0;
                        
                        const netos = (data.calientes || 0) - (data.frios || 0);
                        const totalEl = document.getElementById('detailVoteTotal');
                        if (totalEl) {
                            totalEl.textContent = `${netos >= 0 ? '+' : ''}${netos}°`;
                            totalEl.className = `product-detail-vote-total ${netos >= 0 ? 'positive' : 'negative'}`;
                        }
                    }
                    
                    return votes[productId];
                } else {
                    console.error("Error del servidor:", data.message);
                    return null;
                }
            } catch (e) {
                console.error("❌ Error enviando voto:", e);
                return null;
            }
        }

        async function getProductComments(productId, page = 1) {
          try {
              const res = await fetch(`${API_BASE.replace('/api/ofertas', '')}/api/ofertas/${productId}/comentarios?page=${page}&limit=10`);
              if (!res.ok) throw new Error('Error cargando comentarios');
              const data = await res.json();

              // Actualizamos la variable global con el total
              totalComments = data.total;

              return data.comentarios.map(c => ({
                  id: c.id,
                  username: c.usuario || 'Anónimo',
                  text: c.texto,
                  date: c.fecha,
                  votes: 0
               }));
           } catch (e) {
              console.error("❌ Error cargando comentarios:", e);
              return [];
           }
      }
      

        async function addProductComment(productId, username, text) {
            try {
                const res = await fetch(`${API_BASE.replace('/api/ofertas', '')}/api/ofertas/${productId}/comentarios`, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ usuario: username, texto: text })
                });
        
                if (res.ok) {
                    logDebug('✅ Comentario publicado en servidor');
                    return true;
                } else {
                    console.error('❌ Error publicando comentario:', await res.text());
                    return false;
                }
            } catch (e) {
                console.error("❌ Error de red publicando comentario:", e);
                return false;
            }
        }


// ==================== SUBMIT COMMENT ====================
        
        function getUserName() {
            return localStorage.getItem('userName') || 'Usuario' + Math.floor(Math.random() * 10000);
        }

       function setCategory(category) {
            currentCategory = category;
            currentSearch = ''; 
            document.getElementById('searchInput').value = ''; 
            
            // Iluminamos el botón de arriba correspondiente
            document.querySelectorAll('.category-btn').forEach(b => b.classList.remove('active'));
            const btnArriba = document.querySelector(`.category-btn[data-category="${category}"]`);
            if (btnArriba) btnArriba.classList.add('active');

            showHome(null, false); // Forzamos ir a la vista principal (inicio)
            loadProducts(true);    // Cargamos los productos de esa categoría
            window.history.pushState(null, "", "/");
        }

        function setSort(sort) {
            currentSort = sort;
            loadProducts(true); // Recargar desde página 1
        }


async function submitDetailComment() {
            // 1. Verificar si hay sesión
            if (!authToken) {
                // Como ya no hay modal, los mandamos a la página de login
                window.location.href = '/login';
                return;
            }

            const textInput = document.getElementById('detailCommentText');
            const text = textInput.value.trim();

            if (!text) {
                alert("Por favor, escribe algo antes de publicar.");
                return;
            }

            try {
                // Bloquear botón para evitar doble envío
                const btn = document.querySelector('.comment-form button');
                const oldText = btn.innerHTML;
                btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Publicando...';
                btn.disabled = true;

                const res = await fetch(`${API_BASE.replace('/api/ofertas', '')}/api/ofertas/${currentProduct.id}/comentarios`, {
                    method: 'POST',
                    headers: { 
                        'Content-Type': 'application/json',
                        'Authorization': `Bearer ${authToken}` // Enviamos la llave maestra
                    },
                    body: JSON.stringify({ texto: text })
                });

                const data = await res.json();

                // Restaurar botón
                btn.innerHTML = oldText;
                btn.disabled = false;

                if (data.status === 'ok') {
                    textInput.value = ''; // Limpiamos el cuadro de texto
                    renderDetailComments(currentProduct.id, true); // Recargamos la lista de comentarios
                    logDebug("💬 Comentario verificado publicado");
                } else {
                    alert("Error: " + data.message);
                }
            } catch (err) {
                console.error("❌ Error enviando comentario:", err);
                alert("No se pudo conectar con el servidor.");
                const btn = document.querySelector('.comment-form button');
                btn.innerHTML = '<i class="fas fa-paper-plane"></i> Publicar Comentario';
                btn.disabled = false;
            }
        }

       
        async function loadProducts(reset = true) {
    if (reset) {
        currentPage = 1;
        displayedProducts = [];
        showLoading();
    }

    try {
        // Construimos la URL con todos los parámetros para el Backend
        let url = `${API_BASE}?activos=true&page=${currentPage}&limit=${PRODUCTS_PER_PAGE}`;
        if (currentCategory !== 'all') url += `&categoria=${currentCategory}`;
        if (currentSort !== 'default') url += `&sort=${currentSort}`;
        if (currentSearch) url += `&search=${encodeURIComponent(currentSearch)}`;

        const response = await fetch(url);
        if (!response.ok) throw new Error('Error en la API');
        const data = await response.json();

        const nuevosProductos = data.ofertas.map(p => ({
            ...p,
            precioAntes: p.precio_antes,
            votosHot: p.votos_calientes || 0,
            votosCold: p.votos_frios || 0,
            timestamp: p.fecha_creacion,
            descripcion: p.descripcion || 'Consulta todos los detalles en Amazon.'
        }));

        // Si es página 1 (reset), sobreescribimos. Si es Cargar Más, añadimos al final.
        if (reset) {
            displayedProducts = nuevosProductos;
        } else {
            displayedProducts = [...displayedProducts, ...nuevosProductos];
        }

        renderProducts();

        // Mostrar u ocultar el botón "Cargar Más" según el TOTAL que indica la Base de Datos
        const loadMoreBtn = document.getElementById('loadMoreBtn');
        if (loadMoreBtn) {
            loadMoreBtn.style.display = displayedProducts.length < data.total ? 'block' : 'none';
        }

        productsLoaded = true;
        updateLastUpdateTime();

    } catch (error) {
        console.error('Error cargando productos:', error);
        showError();
    }
}


        // Reemplazar loadMoreProducts
function loadMoreProducts() {
    currentPage++;
    loadProducts(false); // false indica que NO queremos resetear la lista
}

        function searchProducts() {
    const query = document.getElementById('searchInput').value.trim();
    currentSearch = query;
    
    // Opcional: Reiniciar la categoría al buscar en toda la tienda
    document.querySelectorAll('.category-btn').forEach(b => b.classList.remove('active'));
    document.querySelector('.category-btn[data-category="all"]').classList.add('active');
    currentCategory = 'all';

    loadProducts(true); // Pide la búsqueda al servidor desde la página 1
}



// ==================== UPDATE STATS ====================
async function updateStats() {
    try {
        const res = await fetch(`${API_BASE.replace('/api/ofertas', '')}/api/stats`);
        if (!res.ok) throw new Error('Error al conectar con stats');
        const data = await res.json();

        if (data.activos !== undefined) {
            
            // 1. Ofertas Activas
            const elActive1 = document.getElementById('statActiveSidebar');
            const elActive2 = document.getElementById('statActiveDetail');
            if (elActive1) elActive1.textContent = data.activos;
            if (elActive2) elActive2.textContent = data.activos;
            
            // 2. Chollos de Hoy
            const elToday1 = document.getElementById('statTodaySidebar');
            const elToday2 = document.getElementById('statTodayDetail');
            if (elToday1) elToday1.textContent = data.chollos_hoy;
            if (elToday2) elToday2.textContent = data.chollos_hoy;

            // 3. Mayor Descuento 
            const descText = `-${data.mayor_descuento}%`;
            const elDesc1 = document.getElementById('statMaxDiscountSidebar');
            const elDesc2 = document.getElementById('statMaxDiscountDetail');
            if (elDesc1) elDesc1.textContent = descText;
            if (elDesc2) elDesc2.textContent = descText;
            
            // 4. Votos de la comunidad (con separador de miles)
            const votosStr = new Intl.NumberFormat('es-ES').format(data.votos_totales);
            const elVotos1 = document.getElementById('statVotesSidebar');
            const elVotos2 = document.getElementById('statVotesDetail');
            if (elVotos1) elVotos1.textContent = votosStr;
            if (elVotos2) elVotos2.textContent = votosStr;

            // 5. Categorías
            const categories = [
                'electronica', 'videojuegos', 'hogar', 'ropa_complementos', 'salud_belleza', 
                'bebes_ninos', 'comida_bebida', 'deportes', 'viajes', 'ocio', 'mascotas', 
                'gratis', 'varios'
            ];
            categories.forEach(cat => {
                const count = data.categorias[cat] || 0; 
                const elSidebar = document.getElementById(`count-${cat}-sidebar`);
                if (elSidebar) elSidebar.textContent = count;
            });
        }
    } catch (e) {
        console.error("❌ Error cargando estadísticas:", e);
    }
}


function compartirProducto(idProducto, nombreProducto) {
    const urlCompartir = `${window.location.origin}/producto/${idProducto}`;

    if (navigator.share) {
        navigator.share({
            title: nombreProducto, // El móvil lee esto para crear la tarjeta interna
            url: urlCompartir      // Esto es lo único que se pega en WhatsApp
        }).catch((error) => console.log('Error compartiendo:', error));
    } else {
        navigator.clipboard.writeText(urlCompartir).then(() => {
            alert("¡Enlace copiado! Ya puedes pegarlo.");
        });
    }
}
        

        function renderProducts() {
            const grid = document.getElementById('productsGrid');
            const emptyState = document.getElementById('emptyState');
            const errorState = document.getElementById('errorState');
            
            if (!grid) return;
            
            grid.innerHTML = '';
            if (emptyState) emptyState.style.display = 'none';
            if (errorState) errorState.style.display = 'none';
            
            if (displayedProducts.length === 0) {
                if (emptyState) emptyState.style.display = 'block';
                return;
            }
            
            displayedProducts.forEach(producto => {
                const descuento = calculateDiscount(producto.precio, producto.precioAntes);
                const fireEmojis = getFireEmojis(descuento);
                const tempClass = getTemperatureClass(descuento);
                const votosNetos = (producto.votosHot || 0) - (producto.votosCold || 0);
                
                const card = document.createElement('div');
                card.className = 'product-card';
                
                const imageDiv = document.createElement('div');
                imageDiv.className = 'product-card-image';
                imageDiv.onclick = (e) => {
                    e.stopPropagation();
                    showProductDetailPage(producto);
                };
                
                const img = document.createElement('img');
                img.src = sanitizeURL(producto.imagen) || 'https://via.placeholder.com/300x200?text=Sin+imagen';
                img.alt = producto.nombre || 'Producto';
                img.onerror = function() { this.src = 'https://via.placeholder.com/300x200?text=Sin+imagen'; };
                img.loading = 'lazy';
                
                // --- LOGO DE AMAZON ---
                const logoBadge = document.createElement('div');
                logoBadge.style.cssText = 'position: absolute; bottom: 5px; left: 5px; z-index: 10; display: flex; align-items: center; justify-content: center;';
                logoBadge.innerHTML = '<img src="/static/logoamazon.png" style="height: 65px; width: auto; object-fit: contain; filter: drop-shadow(0px 2px 4px rgba(0,0,0,0.4));">';
                
                // --- NUEVO: BOTÓN DE FAVORITO (Arriba a la derecha) ---
                const favBtn = document.createElement('div');
                // Si el ID del producto está en nuestro Set de favoritos, le ponemos la clase 'is-favorite'
                const isFav = userFavorites.has(producto.id);
                favBtn.className = `favorite-btn ${isFav ? 'is-favorite' : ''}`;
                favBtn.innerHTML = `<i class="${isFav ? 'fas' : 'far'} fa-heart"></i>`;
                favBtn.title = isFav ? "Quitar de favoritos" : "Guardar en favoritos";
                favBtn.onclick = (e) => toggleFavorite(e, producto.id);
                
                // Añadimos todo al contenedor de la imagen
                imageDiv.appendChild(logoBadge);
                imageDiv.appendChild(favBtn); // <--- Corazón añadido
                imageDiv.appendChild(img);
                card.appendChild(imageDiv);
                
                const contentDiv = document.createElement('div');
                contentDiv.className = 'product-card-content';
                
                const storeBadge = document.createElement('span');
                storeBadge.className = 'store-badge';
                storeBadge.textContent = 'Amazon';
                contentDiv.appendChild(storeBadge);
                
                const title = document.createElement('h3');
                title.textContent = producto.nombre || '';
                title.title = producto.nombre || '';
                title.onclick = (e) => {
                    e.stopPropagation();
                    console.log('🔵 Click en título - Producto ID:', producto.id);
                    showProductDetailPage(producto);
                };
                contentDiv.appendChild(title);
                
                const priceContainer = document.createElement('div');
                priceContainer.className = 'price-container';

                const price = document.createElement('span');
                price.className = 'price';
                price.textContent = producto.precio || '';
                priceContainer.appendChild(price);

                // AÑADIMOS LÓGICA DEL PRECIO ANTERIOR Y PORCENTAJE
                if (producto.precio_antes && producto.precio_antes !== "N/A") {
                    const oldPrice = document.createElement('span');
                    oldPrice.className = 'old-price';
                    oldPrice.textContent = producto.precio_antes;
                    priceContainer.appendChild(oldPrice);
    
                    // Si hay descuento, añadimos la etiqueta verde
                    if (descuento > 0) {
                        const inlineDiscount = document.createElement('span');
                        inlineDiscount.className = 'inline-discount';
                        inlineDiscount.textContent = `-${descuento}%`;
                        priceContainer.appendChild(inlineDiscount);
                   }
                }

                contentDiv.appendChild(priceContainer);
                
                const voteSection = document.createElement('div');
                voteSection.className = 'vote-section';
                
                const userVote = getUserVote(producto.id);
                
                const voteBtnHot = document.createElement('button');
                voteBtnHot.className = `vote-btn hot ${userVote === 'hot' ? 'voted-hot' : ''}`;
                voteBtnHot.innerHTML = `<i class="fas fa-arrow-up"></i> <span class="vote-count">${producto.votosHot || 0}</span>`;
                voteBtnHot.onclick = (e) => {
                    e.stopPropagation();
                    handleVote(producto, 'hot', voteBtnHot, voteBtnCold);
                };
                
                const voteBtnCold = document.createElement('button');
                voteBtnCold.className = `vote-btn cold ${userVote === 'cold' ? 'voted-cold' : ''}`;
                voteBtnCold.innerHTML = '<i class="fas fa-arrow-down"></i>';
                voteBtnCold.onclick = (e) => {
                    e.stopPropagation();
                    handleVote(producto, 'cold', voteBtnHot, voteBtnCold);
                };
                
                voteSection.appendChild(voteBtnHot);
                voteSection.appendChild(voteBtnCold);
                voteSection.appendChild(voteBtnHot);
                voteSection.appendChild(voteBtnCold);
                
                // --- NUEVO: BOTÓN DE COMPARTIR ---
                const shareBtn = document.createElement('button');
                shareBtn.className = 'share-btn';
                shareBtn.title = 'Compartir chollo';
                shareBtn.style.marginLeft = 'auto'; // Para empujarlo a la derecha del todo
                shareBtn.innerHTML = `
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <circle cx="18" cy="5" r="3"></circle>
                        <circle cx="6" cy="12" r="3"></circle>
                        <circle cx="18" cy="19" r="3"></circle>
                        <line x1="8.59" y1="13.51" x2="15.42" y2="17.49"></line>
                        <line x1="15.41" y1="6.51" x2="8.59" y2="10.49"></line>
                    </svg>`;
                shareBtn.onclick = (e) => {
                    e.stopPropagation(); 
                    compartirProducto(producto.id, producto.nombre); 
                };
                voteSection.appendChild(shareBtn);
                // ---------------------------------

                contentDiv.appendChild(voteSection);
                
                const timestamp = document.createElement('div');
                timestamp.className = 'timestamp';
                timestamp.innerHTML = `<i class="fas fa-clock"></i> ${tiempoRelativo(producto.timestamp)}`;
                contentDiv.appendChild(timestamp);
                
                const link = document.createElement('a');
                link.href = sanitizeURL(producto.link) || '#';
                link.target = '_blank';
                link.rel = 'noopener noreferrer';
                link.className = 'amazon-btn';
                link.textContent = 'Ver Oferta en Amazon →';
                link.onclick = (e) => e.stopPropagation();
                contentDiv.appendChild(link);
                
                card.appendChild(contentDiv);
                grid.appendChild(card);
            });
        }

        async function handleVote(producto, voteType, hotBtn, coldBtn) {
            // Evitar doble clic
            hotBtn.style.pointerEvents = 'none';
            coldBtn.style.pointerEvents = 'none';

            const currentVote = getUserVote(producto.id);
            const newVote = await setUserVote(producto.id, voteType);
    
            // Actualizar memoria local (Aquí estaba el error de currentProduct)
            if (newVote === 'hot') {
                producto.votosHot = (producto.votosHot || 0) + 1;
                if (currentVote === 'cold') producto.votosCold = Math.max(0, (producto.votosCold || 0) - 1);
            } else if (newVote === 'cold') {
                producto.votosCold = (producto.votosCold || 0) + 1;
                if (currentVote === 'hot') producto.votosHot = Math.max(0, (producto.votosHot || 0) - 1);
    } else {
                if (currentVote === 'hot') producto.votosHot = Math.max(0, (producto.votosHot || 0) - 1);
                if (currentVote === 'cold') producto.votosCold = Math.max(0, (producto.votosCold || 0) - 1); // ¡CORREGIDO!
            }
    
            // Actualizar número en el botón
            const voteCountEl = hotBtn.querySelector('.vote-count');
            if (voteCountEl) voteCountEl.textContent = producto.votosHot || 0;
    
            // Actualizar colores
            if (newVote === 'hot') {
                hotBtn.classList.add('voted-hot');
                coldBtn.classList.remove('voted-cold');
            } else if (newVote === 'cold') {
                coldBtn.classList.add('voted-cold');
                hotBtn.classList.remove('voted-hot');
            } else {
                hotBtn.classList.remove('voted-hot');
                coldBtn.classList.remove('voted-cold');
            }

            // Reactivar clics
            hotBtn.style.pointerEvents = 'auto';
            coldBtn.style.pointerEvents = 'auto';
        }

        // --- MÁS VOTADAS (30 productos, de mejor a peor, mismo diseño) ---
        async function renderHotProducts() {
            showLoading();
            try {
                // Pedimos 30 productos ordenados por votos
                const res = await fetch(`${API_BASE}?sort=votes&limit=30&activos=true`);
                const data = await res.json();
                
                const hotProducts = data.ofertas.map(p => ({
                    ...p,
                    precioAntes: p.precio_antes,
                    votosHot: p.votos_calientes || 0,
                    votosCold: p.votos_frios || 0,
                    timestamp: p.fecha_creacion
                }));
                
                const hotGrid = document.getElementById('hotProductsGrid');
                hotGrid.innerHTML = ''; 
                
                // Truco para que use el CSS principal y mantenga las proporciones
                const mainGrid = document.getElementById('productsGrid');
                const tempDisplayed = displayedProducts; 
                
                displayedProducts = hotProducts; 
                mainGrid.id = 'tempMainGrid';    
                hotGrid.id = 'productsGrid';     
                
                renderProducts(); // Pinta usando toda la lógica (precios, tachados, enlaces)
                
                // Restauramos los IDs
                hotGrid.id = 'hotProductsGrid';
                mainGrid.id = 'productsGrid';
                displayedProducts = tempDisplayed;
                
            } catch (err) {
                console.error("Error cargando Más Votadas:", err);
            }
        }

        function setCategoryFromDetail(event) {
            if (event) event.preventDefault();
            if (currentProduct && currentProduct.categoria) {
                setCategory(currentProduct.categoria);
            }
        }

        function updateTopDeals() {
            const topDealsList = document.getElementById('topDealsList');
            if (!topDealsList) return;
            
            const sorted = [...allProducts].sort((a, b) => calculateDiscount(b.precio, b.precioAntes) - calculateDiscount(a.precio, a.precioAntes)).slice(0, 3);
            
            topDealsList.innerHTML = sorted.map(deal => `
                <li>
                    <img src="${sanitizeURL(deal.imagen) || 'https://via.placeholder.com/60'}" alt="${deal.nombre || 'Deal'}" loading="lazy">
                    <div class="deal-info">
                        <div class="deal-title">${sanitizeHTML(deal.nombre || 'Producto')}</div>
                        <div class="deal-price">${deal.precio || ''}</div>
                    </div>
                </li>
            `).join('');
        }

        
        function refreshData() {
            logDebug('🔄 Actualizando datos...');
            loadProducts();
        }

        function toggleDebug() {
            const debugConsole = document.getElementById('debugConsole');
            if (debugConsole) debugConsole.classList.toggle('show');
        }

        function logDebug(message) {
            const consoleEl = document.getElementById('debugConsole');
            if (!consoleEl) return;
            const time = new Date().toLocaleTimeString();
            consoleEl.innerHTML += `[${time}] ${message}<br>`;
            consoleEl.scrollTop = consoleEl.scrollHeight;
        }

        function showLoading() {
            const grid = document.getElementById('productsGrid');
            if (grid) grid.innerHTML = '<div class="empty-state"><i class="fas fa-spinner fa-spin"></i><h3>Cargando ofertas...</h3></div>';
        }

        function showError() {
            const grid = document.getElementById('productsGrid');
            const emptyState = document.getElementById('emptyState');
            const errorState = document.getElementById('errorState');
            if (grid) grid.innerHTML = '';
            if (emptyState) emptyState.style.display = 'none';
            if (errorState) errorState.style.display = 'block';
        }

        function scrollToCategories() {
            const catSection = document.getElementById('categoriesSection');
            if (catSection) {
                catSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
            }
        }


        // ==================== DROPDOWN DE ORDENACIÓN (VERSIÓN A PRUEBA DE FALLOS) ====================
        // FUNCIONES DE ORDENACIÓN GLOBALES
        window.toggleSortMenu = function(event) {
            if (event) event.stopPropagation();
            const menu = document.getElementById('sortDropdownMenu');
            const arrow = document.getElementById('sortArrow');
            if (menu) {
                menu.classList.toggle('active');
                if (arrow) arrow.style.transform = menu.classList.contains('active') ? 'rotate(180deg)' : 'rotate(0deg)';
            }
        };

        window.applySort = function(sortValue, label) {
            const menu = document.getElementById('sortDropdownMenu');
            if (menu) menu.classList.remove('active');
            document.getElementById('currentSortLabel').textContent = label;
            
            // Llamamos a tu función original de carga
            if (typeof setSort === 'function') {
                setSort(sortValue);
            }
        };

        // Cerrar al pulsar fuera
        window.addEventListener('click', (e) => {
            const container = document.querySelector('.sort-dropdown-container');
            if (container && !container.contains(e.target)) {
                const menu = document.getElementById('sortDropdownMenu');
                if (menu) menu.classList.remove('active');
            }
        });


// =================================================================
        // --- 1. MENÚ DE USUARIO Y SESIÓN ---
        // toggleUserMenu, updateUIForUser y handleLogout ahora viven en
        // header-common.js (compartido con ajustes.html). No se
        // redefinen aquí para evitar duplicidad.
        // =================================================================


        // =================================================================
        // --- 2. BUSCADOR EN TIEMPO REAL CON LA API ---
        // =================================================================
        let searchTimeout;
        async function liveSearch(query) {
            const suggestions = document.getElementById('searchSuggestions');
            if (query.length < 2) {
                suggestions.style.display = 'none';
                return;
            }
            
            clearTimeout(searchTimeout);
            searchTimeout = setTimeout(async () => {
                try {
                    // Pide a la base de datos las 5 coincidencias exactas
                    const res = await fetch(`${API_BASE}?search=${encodeURIComponent(query)}&limit=5&activos=true`);
                    const data = await res.json();
                    
                    if (data.ofertas && data.ofertas.length > 0) {
                        suggestions.innerHTML = data.ofertas.map(p => `
                            <div class="suggestion-card" onclick="showProductDetailPage(${JSON.stringify(p).replace(/"/g, '&quot;')}); hideSuggestions()">
                                <img src="${p.imagen}">
                                <div class="info">
                                    <div class="title">${p.nombre}</div>
                                    <div class="price">${p.precio}</div>
                                </div>
                            </div>
                        `).join('');
                        suggestions.style.display = 'flex';
                    } else {
                        suggestions.style.display = 'none';
                    }
                } catch (e) { console.error(e); }
            }, 300); // 300ms de retraso para no saturar el servidor mientras escribe
        }

        function hideSuggestions() {
            const suggestions = document.getElementById('searchSuggestions');
            if(suggestions) suggestions.style.display = 'none';
        }


        // =================================================================
        // --- 3. MÁS VOTADAS (30 productos con mismo diseño) ---
        // =================================================================
        async function renderHotProducts() {
            showLoading();
            try {
                // Pedimos 30 productos ordenados por votos
                const res = await fetch(`${API_BASE}?sort=votes&limit=30&activos=true`);
                const data = await res.json();
                
                const hotProducts = data.ofertas.map(p => ({
                    ...p,
                    precioAntes: p.precio_antes,
                    votosHot: p.votos_calientes || 0,
                    votosCold: p.votos_frios || 0,
                    timestamp: p.fecha_creacion
                }));
                
                const hotGrid = document.getElementById('hotProductsGrid');
                hotGrid.innerHTML = ''; 
                
                // Truco maestro: Engañamos a renderProducts() para que pinte en hotProductsGrid con el mismo diseño exacto
                const mainGrid = document.getElementById('productsGrid');
                const tempDisplayed = displayedProducts; 
                
                displayedProducts = hotProducts; // Le damos los 30 productos
                mainGrid.id = 'tempMainGrid';    // Escondemos el ID del original temporálmente
                hotGrid.id = 'productsGrid';     // Le ponemos el ID al grid de los hot para que coja los estilos
                
                renderProducts();                // Pintamos (Usa todo el CSS y botones de la home)
                
                // Restauramos los IDs y los datos a la normalidad
                hotGrid.id = 'hotProductsGrid';
                mainGrid.id = 'productsGrid';
                displayedProducts = tempDisplayed;
                
            } catch (err) {
                console.error("Error cargando Más Votadas:", err);
            }
        }

        // =================================================================
        // --- 4. LÓGICA DE LAS BARRAS LATERALES MÓVILES ---
        // =================================================================
        function toggleRightSidebar() {
            const sidebar = document.getElementById('rightSidebar');
            const content = document.getElementById('profile-content');
            sidebar.classList.toggle('active');

            // Usamos tu variable global currentUser
            if (!currentUser) {
                content.innerHTML = `
                    <div style="margin-top:40px;">
                        <i class="fas fa-user-circle" style="font-size: 60px; color: #ccc;"></i>
                        <h3 style="margin: 15px 0;">Iniciar Sesión</h3>
                        <p style="color: var(--text-muted); font-size: 14px; margin-bottom: 20px;">Únete para guardar favoritos y votar.</p>
                        <button onclick="window.location.href='/login'" style="background: var(--primary-color); color: white; border: none; padding: 12px 30px; border-radius: 25px; font-weight: bold; cursor: pointer;">Entrar</button>
                    </div>
                `;
            } else {
                content.innerHTML = `
                    <div style="margin-top:40px;">
                        <div style="width: 60px; height: 60px; background: var(--primary-color); color: white; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 24px; margin: 0 auto 15px auto; font-weight: bold;">
                            ${currentUser.nombre.charAt(0).toUpperCase()}
                        </div>
                        <h3 style="margin-top: 10px;">Hola, ${currentUser.nombre.split(' ')[0]}</h3>
                        <hr style="margin: 20px 0; border: 0; border-top: 1px solid var(--border-color);">
                        <a href="/ajustes" style="display: flex; align-items: center; gap: 10px; color: var(--text-color); text-decoration: none; padding: 15px; border-radius: 8px; transition: background 0.2s; font-size: 16px;"><i class="fas fa-cog"></i> Ajustes</a>
                        <div onclick="handleLogout()" style="display: flex; align-items: center; gap: 10px; color: var(--danger-color); padding: 15px; cursor: pointer; border-radius: 8px; transition: background 0.2s; font-size: 16px;">
                            <i class="fas fa-sign-out-alt"></i> Cerrar Sesión
                        </div>
                    </div>
                `;
            }
        }

        // Cerramos la sidebar si se pulsa fuera
        document.addEventListener('click', (e) => {
            const sidebar = document.getElementById('rightSidebar');
            if (sidebar && !sidebar.contains(e.target) && !e.target.closest('.mobile-nav-item')) {
                sidebar.classList.remove('active');
            }
        });

        
