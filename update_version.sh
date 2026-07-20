#!/bin/bash
# update_version.sh - Script para actualizar la aplicación

echo "🚀 Actualizando EA-DIXON..."

# Colores
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Directorio del proyecto
PROJECT_DIR="/home/apps/EA-DIXON"

cd $PROJECT_DIR

# ============================================
# 1. GUARDAR BACKUP DE LA BD
# ============================================
echo -e "${YELLOW}📌 1. Creando backup de la base de datos...${NC}"

BACKUP_DIR="/tmp/backups"
mkdir -p $BACKUP_DIR
BACKUP_FILE="$BACKUP_DIR/backup_$(date +%Y%m%d_%H%M%S).sql"

# Si tienes acceso a la BD
# PGPASSWORD=tu_password pg_dump -h localhost -U postgres -d ea_dixon > $BACKUP_FILE

# ============================================
# 2. GUARDAR CAMBIOS LOCALES
# ============================================
echo -e "${YELLOW}📌 2. Guardando cambios locales...${NC}"

git stash save "Backup local antes de actualizar - $(date +%Y%m%d_%H%M%S)"

# ============================================
# 3. ACTUALIZAR CÓDIGO
# ============================================
echo -e "${YELLOW}📌 3. Actualizando código...${NC}"

git pull origin main

if [ $? -ne 0 ]; then
    echo -e "${RED}❌ Error al actualizar código${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Código actualizado${NC}"

# ============================================
# 4. ACTUALIZAR DEPENDENCIAS
# ============================================
echo -e "${YELLOW}📌 4. Actualizando dependencias...${NC}"

# Backend
cd Backend
source venv/bin/activate
pip install -r requirements.txt --upgrade
deactivate
cd ..

echo -e "${GREEN}✅ Dependencias actualizadas${NC}"

# ============================================
# 5. LIMPIAR CACHÉ
# ============================================
echo -e "${YELLOW}📌 5. Limpiando caché...${NC}"

find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null
find . -type f -name "*.pyc" -delete 2>/dev/null

# ============================================
# 6. REINICIAR SERVICIOS
# ============================================
echo -e "${YELLOW}📌 6. Reiniciando servicios...${NC}"

# Systemd
sudo systemctl restart ea-dixon-backend 2>/dev/null
sudo systemctl restart ea-dixon-frontend 2>/dev/null

# Supervisor
# sudo supervisorctl restart ea-dixon-backend 2>/dev/null
# sudo supervisorctl restart ea-dixon-frontend 2>/dev/null

echo -e "${GREEN}✅ Servicios reiniciados${NC}"

# ============================================
# 7. VERIFICAR ESTADO
# ============================================
echo -e "${YELLOW}📌 7. Verificando estado...${NC}"

sleep 3

# Verificar backend
curl -s http://localhost:5000/health > /dev/null
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Backend OK${NC}"
else
    echo -e "${RED}❌ Backend no responde${NC}"
fi

echo -e "${GREEN}✅ Actualización completada exitosamente!${NC}"
echo "📅 $(date)"
