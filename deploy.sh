#!/bin/bash

echo "🚀 FB Automation - Deployment Script"
echo "====================================="

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Verificar se docker compose está instalado
if ! command -v docker compose &> /dev/null; then
    echo -e "${RED}❌ docker compose não está instalado${NC}"
    exit 1
fi

# Parar serviços existentes
echo -e "${YELLOW}⏹️  Parando serviços existentes...${NC}"
docker compose down

# Build das imagens
echo -e "${YELLOW}🔨 Construindo imagens Docker...${NC}"
docker compose build

# Subir banco de dados e redis primeiro
echo -e "${YELLOW}🗄️  Iniciando banco de dados e Redis...${NC}"
docker compose up -d db redis

# Aguardar serviços ficarem prontos
echo -e "${YELLOW}⏳ Aguardando serviços ficarem prontos...${NC}"
sleep 10

# Subir todos os serviços
echo -e "${YELLOW}🚀 Iniciando todos os serviços...${NC}"
docker compose up -d

# Aguardar web service iniciar
echo -e "${YELLOW}⏳ Aguardando servidor web iniciar...${NC}"
sleep 15

# Verificar status
echo -e "${GREEN}✅ Verificando status dos serviços...${NC}"
docker compose ps

# Mostrar logs
echo ""
echo -e "${GREEN}📋 Últimas linhas dos logs:${NC}"
docker compose logs --tail=20

echo ""
echo -e "${GREEN}✨ Deployment concluído!${NC}"
echo ""
echo "🌐 Acesse a aplicação em: http://localhost"
echo "👤 Admin: http://localhost/admin (admin/admin123)"
echo "🌸 Flower: http://localhost:5555"
echo ""
echo "📊 Para ver logs em tempo real:"
echo "   docker compose logs -f"
echo ""
echo "🛑 Para parar os serviços:"
echo "   docker compose down"
