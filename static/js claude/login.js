    // Comprobar si ya está logueado
    if (localStorage.getItem('token')) {
        window.location.href = '/'; 
    }

    function switchTab(tab) {
        const isLogin = tab === 'login';
        document.getElementById('formTitle').textContent = isLogin ? 'Iniciar sesión' : 'Crear cuenta';
        document.getElementById('loginForm').classList.toggle('active', isLogin);
        document.getElementById('registerForm').classList.toggle('active', !isLogin);
        document.getElementById('loginError').style.display = 'none';
        document.getElementById('registerError').style.display = 'none';
    }

    
    // --- LÓGICA DE GOOGLE LOGIN ---
    async function handleGoogleCallback(response) {
        // response.credential es el token firmado que nos devuelve Google
        const errorEl = document.getElementById('loginError');
        
        try {
            const res = await fetch('/api/google-login', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ credential: response.credential })
            });
            
            const data = await res.json();
            
            if (data.status === 'ok') {
                localStorage.setItem('token', data.token);
                localStorage.setItem('user', JSON.stringify(data.usuario));
                window.location.href = '/'; // Redirigimos a la home
            } else {
                errorEl.textContent = data.message;
                errorEl.style.display = 'block';
            }
        } catch (err) {
            errorEl.textContent = "Error al conectar con el servidor";
            errorEl.style.display = 'block';
        }
    }


    async function handleLogin(e) {
        e.preventDefault();
        const email = document.getElementById('loginEmail').value;
        const password = document.getElementById('loginPassword').value;
        const errorEl = document.getElementById('loginError');

        // Cambiar botón a cargando
        const btn = e.target.querySelector('button[type="submit"]');
        const oldText = btn.innerHTML;
        btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Cargando...';
        btn.disabled = true;

        try {
            const res = await fetch('/api/login', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ email, password })
            });
            const data = await res.json();

            if (data.status === 'ok') {
                localStorage.setItem('token', data.token);
                localStorage.setItem('user', JSON.stringify(data.usuario));
                window.location.href = '/'; // Éxito, volver a tienda
            } else {
                errorEl.textContent = data.message;
                errorEl.style.display = 'block';
                btn.innerHTML = oldText;
                btn.disabled = false;
            }
        } catch (err) {
            errorEl.textContent = "Error al conectar con el servidor";
            errorEl.style.display = 'block';
            btn.innerHTML = oldText;
            btn.disabled = false;
        }
    }

    async function handleRegister(e) {
        e.preventDefault();
        const nombre = document.getElementById('registerName').value;
        const email = document.getElementById('registerEmail').value;
        const password = document.getElementById('registerPassword').value;
        const errorEl = document.getElementById('registerError');

        // Cambiar botón a cargando
        const btn = e.target.querySelector('button[type="submit"]');
        const oldText = btn.innerHTML;
        btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Creando...';
        btn.disabled = true;

        try {
            const res = await fetch('/api/registro', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ nombre, email, password })
            });
            const data = await res.json();

            if (data.status === 'ok') {
                alert("¡Cuenta creada con éxito! Inicia sesión para continuar.");
                switchTab('login');
                document.getElementById('loginEmail').value = email; 
                btn.innerHTML = oldText;
                btn.disabled = false;
            } else {
                errorEl.textContent = data.message;
                errorEl.style.display = 'block';
                btn.innerHTML = oldText;
                btn.disabled = false;
            }
        } catch (err) {
            errorEl.textContent = "Error de conexión";
            errorEl.style.display = 'block';
            btn.innerHTML = oldText;
            btn.disabled = false;
        }
    }
