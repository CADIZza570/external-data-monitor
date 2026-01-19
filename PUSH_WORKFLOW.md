# 🚀 PROCESO CORRECTO DE PUSH EN WORKTREE

## ⚠️ IMPORTANTE: Estamos en un Worktree

**Worktree actual:** `/Users/constanzaaraya/.claude-worktrees/python-automation/gracious-stonebraker`
**Repo principal:** `/Users/constanzaaraya/Documents/python-automation`
**Branch worktree:** `gracious-stonebraker`
**Branch producción:** `main` (Railway deploy automático)

---

## 📋 PROCESO COMPLETO DE PUSH A MAIN

### 1️⃣ HACER CAMBIOS Y COMMIT EN WORKTREE

```bash
# Desde el worktree (gracious-stonebraker)
git status
git add <archivos>
git commit -m "mensaje"
```

### 2️⃣ PUSH DE LA BRANCH A ORIGIN

```bash
# Push de gracious-stonebraker a GitHub
git push -u origin gracious-stonebraker
```

### 3️⃣ IR AL REPO PRINCIPAL Y ACTUALIZAR MAIN

```bash
# Cambiar al repo principal
cd /Users/constanzaaraya/Documents/python-automation

# Verificar estado
git status

# Actualizar main desde origin (traer cambios remotos)
git pull origin main

# Mergear gracious-stonebraker a main
git merge gracious-stonebraker -m "Merge gracious-stonebraker: <descripción>"

# Push a main (esto activa el deploy de Railway)
git push origin main
```

### 4️⃣ VERIFICAR DEPLOY EN RAILWAY

Railway hace deploy automático cuando detecta push a `main`.

**Dashboard:** https://tranquil-freedom-production.up.railway.app/dashboard

El deploy tarda 1-2 minutos.

---

## ❌ ERRORES COMUNES Y SOLUCIONES

### Error: "fatal: 'main' is already used by worktree"

**Causa:** Intentar hacer `git checkout main` desde el worktree.

**Solución:** NO puedes hacer checkout a main desde el worktree. Debes ir al repo principal.

```bash
# ❌ NO HACER ESTO en worktree
git checkout main

# ✅ HACER ESTO
cd /Users/constanzaaraya/Documents/python-automation
# Aquí sí puedes trabajar con main
```

### Error: "refusing to fetch into branch that is checked out"

**Causa:** Intentar fetch/pull a main desde el worktree.

**Solución:** Ir al repo principal para actualizar main.

---

## 🔄 WORKFLOW RESUMIDO

```bash
# EN WORKTREE (gracious-stonebraker)
git add .
git commit -m "mensaje"
git push -u origin gracious-stonebraker

# EN REPO PRINCIPAL (main)
cd /Users/constanzaaraya/Documents/python-automation
git pull origin main
git merge gracious-stonebraker
git push origin main

# VERIFICAR
# Railway auto-deploy → https://tranquil-freedom-production.up.railway.app/dashboard
```

---

## 📝 NOTAS IMPORTANTES

1. **Railway deploy SOLO desde main**: Los cambios en `gracious-stonebraker` NO se despliegan automáticamente.

2. **Siempre verificar antes de push a main**:
   ```bash
   git log --oneline -5
   git diff main..gracious-stonebraker
   ```

3. **Si hay cambios no commiteados en main**: Stashearlos o commitearlos antes del merge.
   ```bash
   cd /Users/constanzaaraya/Documents/python-automation
   git status
   git stash  # si hay cambios
   ```

4. **Después del push a main**: Esperar 1-2 min para que Railway termine el deploy.

---

## 🎯 CHECKLIST PRE-PUSH

- [ ] Commits hechos en worktree
- [ ] Push de branch a origin: `git push -u origin gracious-stonebraker`
- [ ] Ir a repo principal: `cd /Users/constanzaaraya/Documents/python-automation`
- [ ] Pull de main: `git pull origin main`
- [ ] Merge: `git merge gracious-stonebraker`
- [ ] Push a main: `git push origin main`
- [ ] Verificar Railway dashboard después de 1-2 min

---

**Última actualización:** 2026-01-19
