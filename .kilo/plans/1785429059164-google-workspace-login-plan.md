# Plan: Login con Google Workspace

## Objetivo
Implementar autenticación con Google Workspace (OAuth 2.0) para permitir a usuarios iniciar sesión con su cuenta de Google institucional.

## Estado Actual
- ✅ Sistema de login con email/contraseña funcional
- ❌ No hay integración con Google OAuth
- ❌ No hay sincronización de usuarios de Google Workspace

## Decisiones Confirmadas
1. **Dominio restringido:** Solo usuarios `@losalercespuertomontt.cl` pueden usar Google
2. **Sin auto-registro:** Solo usuarios con cuenta existente pueden usar Google
3. **Sin sincronización de roles:** Los roles no se gestionan desde Google Workspace

## Arquitectura

### Librería: django-allauth (social-auth-app-django como alternativa)

### Flujo de usuarios restringido
```
Google Login → Verificar email termina en @losalercespuertomontt.cl → Verificar usuario existe → Login exitoso
```

## Tareas

### Fase 1: Configuración Base
- [ ] Instalar `django-allauth` y dependencias
- [ ] Configurar dominios autorizados en Google Cloud Console (`/callback` URLs)
- [ ] Generar credenciales OAuth 2.0 (Client ID/Secret)
- [ ] Agregar variables de entorno:
  ```env
  SOCIALACCOUNT_PROVIDERS=google
  GOOGLE_CLIENT_ID=...
  GOOGLE_CLIENT_SECRET=...
  ```

### Fase 2: Configuración Django
- [ ] Agregar apps a `INSTALLED_APPS` en `config/settings.py`:
  ```python
  'allauth',
  'allauth.account',
  'allauth.socialaccount',
  'allauth.socialaccount.providers.google',
  ```
- [ ] Configurar `SITE_ID = 1`
- [ ] Configurar `ACCOUNT_ALLOW_EMAIL_AUTH = True`
- [ ] Configurar providers con restricción de dominio

### Fase 3: Personalización
- [ ] Crear vista personalizada de registro que bloquee auto-registro
- [ ] Override del formulario para restringir dominio `losalercespuertomontt.cl`
- [ ] Configurar `CustomUser` con allauth
- [ ] Manejar caso donde usuario Google no existe en sistema (error amigable)

### Fase 4: Seguridad
- [ ] Restringir login Google solo para usuarios del dominio `losalercespuertomontt.cl`
- [ ] Configurar HTTPS obligatorio para OAuth (en producción)
- [ ] Mantener login tradicional como fallback
- [ ] Agregar `SOCIALACCOUNT_QUERY_EMAIL = True` para evitar duplicados

### Fase 5: Mensajería
- [ ] Mensaje de error cuando usuario no existe: "Su cuenta no está registrada en el sistema. Contacte al administrador."

## Archivos a Modificar
1. `config/settings.py` - Apps, configuración allauth
2. `core/views.py` - Override CustomLoginView o crear SocialLoginView
3. `core/urls.py` - Rutas para OAuth callbacks
4. `.env.example` - Variables de entorno

## Riesgos
1. **Usuario existe en Google pero no en sistema** → Manejar con mensaje de error
2. **Cambio de email en Google** → El email es `USERNAME_FIELD`, cambios requieren admin
3. **Revocación de credenciales Google** → Proceso de regeneración de credenciales

## Validación
- [ ] Usuario con email `@losalercespuertomontt.cl` y cuenta existente puede login
- [ ] Usuario con email fuera del dominio no puede usar Google Login
- [ ] Usuario sin cuenta en sistema recibe mensaje de error amigable
- [ ] Login tradicional sigue funcionando

## Decisiones Marcadas como Out of Scope
- Sincronización automática de roles desde Google Workspace
- Registro masivo de usuarios desde Google Groups