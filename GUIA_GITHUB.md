# 📚 Guía Completa de GitHub para Desarrolladores

Esta guía te enseñará a configurar GitHub completamente para usar en cualquier proyecto.

---

## 🔐 Parte 1: Crear Cuenta en GitHub (si no la tienes)

1. Ve a **https://github.com**
2. Click en **"Sign up"**
3. Ingresa tu email, contraseña y nombre de usuario
4. Verifica tu email

---

## 🎫 Parte 2: Generar Token de Acceso Personal (PAT)

El token es como una contraseña segura que reemplaza tu password normal para Git.

### Paso a paso:

1. Ve a: **https://github.com/settings/tokens**
2. Click en **"Generate new token (classic)"**
3. Configura el token:

| Campo | Valor |
|-------|-------|
| **Note** | Tu nombre o "Desarrollo General" |
| **Expiration** | `90 days` (o 1 año si prefieres) |
| **scopes** | ✅ `repo` (completo) |

4. Click en **"Generate token"**
5. **COPIA Y GUARDA EL TOKEN** 
   - Solo se muestra UNA vez
   - Guárdalo en un lugar seguro
   - Tiene forma: `ghp_xxxxxxxxxxxxxxxxxxxx`

---

## 💻 Parte 3: Configurar Git en tu Computadora

### 3.1 Configuración básica (solo una vez)

```bash
# Configurar tu nombre
git config --global user.name "Tu Nombre Completo"

# Configurar tu email
git config --global user.email "tu@email.com"
```

### 3.2 Configurar credenciales (importante)

Hay 2 formas de configurar las credenciales:

#### Opción A: Usar el token en la URL (recomendado)

```bash
# Para un repositorio existente
git remote set-url origin https://ghp_TU_TOKEN@github.com/usuario/repositorio.git

# Para clonar con token
git clone https://ghp_TU_TOKEN@github.com/usuario/repositorio.git
```

#### Opción B: Usar credential helper (más automático)

```bash
# Mac
git config --global credential.helper osxkeychain

# Windows
git config --global credential.helper manager

# Linux
git config --global credential.helper store
```

---

## 🚀 Parte 4: Comandos Git Esenciales

### Iniciar un nuevo proyecto

```bash
# 1. Crear carpeta
mkdir mi-proyecto
cd mi-proyecto

# 2. Iniciar git
git init

# 3. Crear archivo .gitignore (opcional)
echo "node_modules/" > .gitignore
echo "__pycache__/" >> .gitignore
echo ".env" >> .gitignore

# 4. Añadir archivos
git add .

# 5. Primer commit
git commit -m "Primer commit"

# 6. Crear repositorio en GitHub y conectar
git remote add origin https://github.com/usuario/mi-proyecto.git
git push -u origin main
```

### Comandos diarios

| Comando | Descripción |
|---------|-------------|
| `git status` | Ver estado de archivos |
| `git add .` | Añadir todos los cambios |
| `git commit -m "mensaje"` | Guardar cambios |
| `git push` | Subir a GitHub |
| `git pull` | Descargar cambios |
| `git log` | Ver historial de commits |

### Trabajar con ramas

```bash
# Crear rama
git checkout -b nueva-rama

# Cambiar de rama
git checkout main

# Ver ramas
git branch

# Fusionar rama
git checkout main
git merge mi-rama

# Eliminar rama
git branch -d mi-rama
```

---

## 📦 Parte 5: Buenas Prácticas

### .gitignore básico para Python/Django

```
# Python
__pycache__/
*.py[cod]
*.egg-info/
venv/
env/
.venv/

# Django
*.log
db.sqlite3
.env
media/
staticfiles/

# IDE
.vscode/
.idea/
*.swp

# OS
.DS_Store
Thumbs.db
```

---

## ⚠️ Errores Comunes y Soluciones

### "Authentication failed"

```bash
# Solución: Actualizar el token
git remote set-url origin https://ghp_NUEVO_TOKEN@github.com/usuario/repo.git
```

### "remote origin already exists"

```bash
# Ver el remote actual
git remote -v

# Eliminar y crear nuevo
git remote remove origin
git remote add origin https://github.com/usuario/repo.git
```

### "Could not resolve host"

```bash
# Verificar conexión
ping github.com

# Configurar proxy si es necesario
git config --global http.proxy http://proxy:8080
```

---

## 🔒 Seguridad

### NUNCA hagas esto:

```bash
# ❌ MALO - No subas tokens a Git
git commit -m "Token: ghp_mivototoken123"

# ❌ MALO - No compartas tu token
```

### SIEMPRE haz esto:

- ✅ Guarda el token en un password manager (1Password, Bitwarden)
- ✅ Usa variables de entorno para tokens
- ✅ Renueva el token antes de que expire
- ✅ Revoca tokens que no uses

---

## 📱 GitHub CLI (Opcional)

Puedes usar la terminal de GitHub directamente:

```bash
# Instalar (Mac)
brew install gh

# Login
gh auth login

# Crear repo desde terminal
gh repo create mi-proyecto --public

# Push con authentication automática
gh repo push
```

---

## 📋 Checklist Antes de Cada Proyecto

- [ ] Token de GitHub configurado
- [ ] Git config con nombre y email
- [ ] .gitignore creado
- [ ] Remote configurado
- [ ] Primer push realizado

---

¿Necesitas ayuda con algún paso específico?