        // authToken y currentUser ya se declaran en header-common.js,
        // que se carga antes que este archivo.

        if (!authToken || !currentUser) {
            window.location.href = '/login';
        } else {
            // Cargar datos
            document.getElementById('perfilNombre').value = currentUser.nombre;
            document.getElementById('perfilEmail').value = currentUser.email || '';
            
            // Cargar foto
            if (currentUser.avatar) {
                document.getElementById('userAvatarImg').src = currentUser.avatar;
                document.getElementById('userAvatarImg').style.display = 'flex';
                document.getElementById('userAvatarText').style.display = 'none';
            } else {
                document.getElementById('userAvatarText').textContent = currentUser.nombre.charAt(0).toUpperCase();
            }
        }

        function switchTab(tabId) {
            document.querySelectorAll('.settings-tab').forEach(t => t.classList.remove('active'));
            document.querySelectorAll('.settings-section').forEach(s => s.classList.remove('active'));
            event.target.classList.add('active');
            document.getElementById(`sec-${tabId}`).classList.add('active');
        }

        function showMessage(elementId, msg, type) {
            const el = document.getElementById(elementId);
            el.textContent = msg;
            el.className = `msg-box msg-${type}`;
            setTimeout(() => el.className = 'msg-box', 4000);
        }

        // --- MANEJO DE LA FOTO ---
        function previewPhoto(event) {
            const file = event.target.files[0];
            if (file) {
                const reader = new FileReader();
                reader.onload = function(e) {
                    document.getElementById('userAvatarImg').src = e.target.result;
                    document.getElementById('userAvatarImg').style.display = 'flex';
                    document.getElementById('userAvatarText').style.display = 'none';
                    
                    // Guardar en local storage visualmente (para el momento)
                    currentUser.avatar = e.target.result;
                    localStorage.setItem('user', JSON.stringify(currentUser));
                    showMessage('msgPerfil', 'Foto actualizada temporalmente. Pulsa Guardar.', 'success');
                }
                reader.readAsDataURL(file);
            }
        }

        function removePhoto() {
            document.getElementById('userAvatarImg').src = '';
            document.getElementById('userAvatarImg').style.display = 'none';
            document.getElementById('userAvatarText').style.display = 'flex';
            document.getElementById('photoInput').value = '';
            
            delete currentUser.avatar;
            localStorage.setItem('user', JSON.stringify(currentUser));
            showMessage('msgPerfil', 'Foto eliminada. Pulsa Guardar para confirmar.', 'success');
        }

        // --- ACTUALIZACIONES API ---
        async function actualizarPerfil(e) {
            e.preventDefault();
            const btn = document.getElementById('btnPerfil');
            btn.innerHTML = 'Guardando...';
            btn.disabled = true;

            const nombre = document.getElementById('perfilNombre').value;
            const email = document.getElementById('perfilEmail').value;

            try {
                const res = await fetch('/api/usuarios/perfil', {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${authToken}` },
                    body: JSON.stringify({ nombre, email })
                });
                const data = await res.json();
                
                if (data.status === 'ok') {
                    currentUser.nombre = nombre;
                    currentUser.email = email;
                    localStorage.setItem('user', JSON.stringify(currentUser));
                    showMessage('msgPerfil', 'Perfil guardado correctamente', 'success');
                } else {
                    showMessage('msgPerfil', data.message, 'error');
                }
            } catch (err) { showMessage('msgPerfil', 'Error de conexión', 'error'); }
            
            btn.innerHTML = 'Guardar';
            btn.disabled = false;
        }

        async function actualizarPassword(e) {
            e.preventDefault();
            const pwd1 = document.getElementById('newPassword').value;
            const pwd2 = document.getElementById('confirmPassword').value;

            if (pwd1 !== pwd2) {
                showMessage('msgPassword', 'Las contraseñas no coinciden', 'error');
                return;
            }

            try {
                const res = await fetch('/api/usuarios/password', {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${authToken}` },
                    body: JSON.stringify({ password: pwd1 })
                });
                const data = await res.json();
                
                if (data.status === 'ok') {
                    document.getElementById('newPassword').value = '';
                    document.getElementById('confirmPassword').value = '';
                    showMessage('msgPassword', 'Contraseña actualizada con éxito', 'success');
                } else {
                    showMessage('msgPassword', data.message, 'error');
                }
            } catch (err) { showMessage('msgPassword', 'Error de conexión', 'error'); }
        }

        // --- BORRAR CUENTA ---
        async function borrarCuenta(e) {
            e.preventDefault();
            const password = document.getElementById('deletePassword').value;
            const btn = document.getElementById('btnDelete');
            
            btn.innerHTML = 'Borrando...';
            btn.disabled = true;

            try {
                const res = await fetch('/api/usuarios', {
                    method: 'DELETE',
                    headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${authToken}` },
                    body: JSON.stringify({ password })
                });
                const data = await res.json();
                
                if (data.status === 'ok') {
                    localStorage.removeItem('token');
                    localStorage.removeItem('user');
                    window.location.href = '/login';
                } else {
                    showMessage('msgDelete', data.message, 'error');
                    btn.innerHTML = 'Borrar cuenta';
                    btn.disabled = false;
                }
            } catch (err) { 
                showMessage('msgDelete', 'Error de conexión al servidor', 'error'); 
                btn.innerHTML = 'Borrar cuenta';
                btn.disabled = false;
            }
        }
