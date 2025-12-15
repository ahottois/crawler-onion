#!/bin/bash
# ============================================
# Darknet Omniscient Crawler v6.4
# Script d'installation pour Ubuntu Server
# ============================================

set -e

# Couleurs
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${CYAN}"
echo "?????????????????????????????????????????????????????"
echo "?     ???  Darknet Omniscient Crawler v6.4          ?"
echo "?         Installation pour Ubuntu Server           ?"
echo "?????????????????????????????????????????????????????"
echo -e "${NC}"

# Vérifier si on est root
if [ "$EUID" -eq 0 ]; then
    echo -e "${YELLOW}??  Ne pas exécuter en tant que root. Utilisez un utilisateur normal.${NC}"
    exit 1
fi

# Répertoire d'installation
INSTALL_DIR="$HOME/crawler-onion"

echo -e "${GREEN}[1/6]${NC} Mise à jour du système..."
sudo apt update -qq

echo -e "${GREEN}[2/6]${NC} Installation des dépendances système..."
sudo apt install -y -qq python3 python3-pip python3-venv tor git

echo -e "${GREEN}[3/6]${NC} Configuration et démarrage de Tor..."
sudo systemctl enable tor
sudo systemctl start tor

# Vérifier que Tor fonctionne
sleep 2
if systemctl is-active --quiet tor; then
    echo -e "${GREEN}?${NC} Tor est actif"
else
    echo -e "${RED}?${NC} Erreur: Tor n'a pas démarré"
    exit 1
fi

echo -e "${GREEN}[4/6]${NC} Clonage du repository..."
if [ -d "$INSTALL_DIR" ]; then
    echo -e "${YELLOW}Le répertoire existe déjà. Mise à jour...${NC}"
    cd "$INSTALL_DIR"
    git pull origin master
else
    git clone https://github.com/ahottois/crawler-onion.git "$INSTALL_DIR"
    cd "$INSTALL_DIR"
fi

echo -e "${GREEN}[5/6]${NC} Création de l'environnement virtuel Python..."
python3 -m venv venv
source venv/bin/activate

echo -e "${GREEN}[6/6]${NC} Installation des dépendances Python..."
pip install --upgrade pip -q
pip install -r requirements.txt -q

# Créer un script de lancement
cat > "$INSTALL_DIR/start.sh" << 'EOF'
#!/bin/bash
cd "$(dirname "$0")"
source venv/bin/activate
python run.py "$@"
EOF
chmod +x "$INSTALL_DIR/start.sh"

# Créer un alias
ALIAS_LINE="alias crawler='$INSTALL_DIR/start.sh'"
if ! grep -q "alias crawler=" "$HOME/.bashrc" 2>/dev/null; then
    echo "$ALIAS_LINE" >> "$HOME/.bashrc"
fi

echo ""
echo -e "${GREEN}?????????????????????????????????????????????????????${NC}"
echo -e "${GREEN}?         ? Installation terminée !                ?${NC}"
echo -e "${GREEN}?????????????????????????????????????????????????????${NC}"
echo ""
echo -e "?? Installé dans: ${CYAN}$INSTALL_DIR${NC}"
echo ""
echo -e "${YELLOW}Pour lancer le crawler:${NC}"
echo -e "  ${CYAN}cd $INSTALL_DIR && ./start.sh${NC}"
echo ""
echo -e "${YELLOW}Ou après avoir rechargé le terminal:${NC}"
echo -e "  ${CYAN}source ~/.bashrc${NC}"
echo -e "  ${CYAN}crawler${NC}"
echo ""
echo -e "${YELLOW}Options disponibles:${NC}"
echo -e "  ${CYAN}crawler --help${NC}           Afficher l'aide"
echo -e "  ${CYAN}crawler --workers 20${NC}     20 workers parallèles"
echo -e "  ${CYAN}crawler --no-web${NC}         Sans interface web"
echo ""
echo -e "${YELLOW}Interface web:${NC}"
echo -e "  ${CYAN}http://VOTRE_IP:4587${NC}"
echo ""
