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
PURPLE='\033[0;35m'
NC='\033[0m'

echo -e "${CYAN}"
echo "=================================================="
echo "     Darknet Omniscient Crawler v6.4"
echo "     Installation pour Ubuntu Server"
echo "=================================================="
echo -e "${NC}"

# Verifier si on est root
if [ "$EUID" -eq 0 ]; then
    echo -e "${YELLOW}Ne pas executer en tant que root. Utilisez un utilisateur normal.${NC}"
    exit 1
fi

# Repertoire d'installation
INSTALL_DIR="$HOME/crawler-onion"
SERVICE_NAME="crawler-onion"

# Options
INSTALL_DAEMON=false
WEB_PORT=4587
WORKERS=15

# Parser les arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --daemon)
            INSTALL_DAEMON=true
            shift
            ;;
        --port)
            WEB_PORT="$2"
            shift 2
            ;;
        --workers)
            WORKERS="$2"
            shift 2
            ;;
        --help)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --daemon     Installer comme service systemd"
            echo "  --port NUM   Port du serveur web (defaut: 4587)"
            echo "  --workers N  Nombre de workers (defaut: 15)"
            echo "  --help       Afficher cette aide"
            exit 0
            ;;
        *)
            shift
            ;;
    esac
done

echo -e "${GREEN}[1/6]${NC} Mise a jour du systeme..."
sudo apt update -qq

echo -e "${GREEN}[2/6]${NC} Installation des dependances systeme..."
sudo apt install -y -qq python3 python3-pip python3-venv tor git

echo -e "${GREEN}[3/6]${NC} Configuration et demarrage de Tor..."
sudo systemctl enable tor
sudo systemctl start tor

# Verifier que Tor fonctionne
sleep 2
if systemctl is-active --quiet tor; then
    echo -e "${GREEN}OK${NC} Tor est actif"
else
    echo -e "${RED}ERREUR${NC} Tor n'a pas demarre"
    exit 1
fi

echo -e "${GREEN}[4/6]${NC} Clonage du repository..."
if [ -d "$INSTALL_DIR" ]; then
    echo -e "${YELLOW}Le repertoire existe deja. Mise a jour...${NC}"
    cd "$INSTALL_DIR"
    git pull origin master
else
    git clone https://github.com/ahottois/crawler-onion.git "$INSTALL_DIR"
    cd "$INSTALL_DIR"
fi

echo -e "${GREEN}[5/6]${NC} Creation de l'environnement virtuel Python..."
python3 -m venv venv
source venv/bin/activate

echo -e "${GREEN}[6/6]${NC} Installation des dependances Python..."
pip install --upgrade pip -q
pip install -r requirements.txt -q

# Creer un script de lancement
cat > "$INSTALL_DIR/start.sh" << 'EOF'
#!/bin/bash
cd "$(dirname "$0")"
source venv/bin/activate
python run.py "$@"
EOF
chmod +x "$INSTALL_DIR/start.sh"

# Creer un alias
ALIAS_LINE="alias crawler='$INSTALL_DIR/start.sh'"
if ! grep -q "alias crawler=" "$HOME/.bashrc" 2>/dev/null; then
    echo "$ALIAS_LINE" >> "$HOME/.bashrc"
fi

# Installation du daemon si demande
if [ "$INSTALL_DAEMON" = true ]; then
    echo ""
    echo -e "${PURPLE}[DAEMON]${NC} Installation du service systemd..."
    
    # Creer le fichier service
    SERVICE_FILE="/tmp/${SERVICE_NAME}.service"
    cat > "$SERVICE_FILE" << EOF
[Unit]
Description=Darknet Omniscient Crawler - Tor .onion Crawler
Documentation=https://github.com/ahottois/crawler-onion
After=network.target tor.service
Wants=tor.service

[Service]
Type=simple
User=$USER
Group=$USER
WorkingDirectory=$INSTALL_DIR
Environment="PATH=$INSTALL_DIR/venv/bin:/usr/local/bin:/usr/bin:/bin"
ExecStart=$INSTALL_DIR/venv/bin/python $INSTALL_DIR/run.py --workers $WORKERS --web-port $WEB_PORT
ExecReload=/bin/kill -HUP \$MAINPID
Restart=on-failure
RestartSec=10
StandardOutput=journal
StandardError=journal
SyslogIdentifier=$SERVICE_NAME

# Securite
NoNewPrivileges=true
PrivateTmp=true

[Install]
WantedBy=multi-user.target
EOF

    # Installer le service
    sudo cp "$SERVICE_FILE" "/etc/systemd/system/${SERVICE_NAME}.service"
    rm "$SERVICE_FILE"
    
    # Activer et demarrer
    sudo systemctl daemon-reload
    sudo systemctl enable "$SERVICE_NAME"
    sudo systemctl start "$SERVICE_NAME"
    
    sleep 2
    if systemctl is-active --quiet "$SERVICE_NAME"; then
        echo -e "${GREEN}OK${NC} Service $SERVICE_NAME demarre"
    else
        echo -e "${YELLOW}ATTENTION${NC} Le service n'a pas demarre correctement"
        echo "Verifiez avec: sudo journalctl -u $SERVICE_NAME -f"
    fi
fi

echo ""
echo -e "${GREEN}=================================================="
echo -e "         Installation terminee !"
echo -e "==================================================${NC}"
echo ""
echo -e "Installe dans: ${CYAN}$INSTALL_DIR${NC}"
echo ""

if [ "$INSTALL_DAEMON" = true ]; then
    echo -e "${PURPLE}Mode Daemon active${NC}"
    echo ""
    echo -e "${YELLOW}Commandes de controle:${NC}"
    echo -e "  ${CYAN}sudo systemctl status $SERVICE_NAME${NC}   Statut"
    echo -e "  ${CYAN}sudo systemctl restart $SERVICE_NAME${NC}  Redemarrer"
    echo -e "  ${CYAN}sudo systemctl stop $SERVICE_NAME${NC}     Arreter"
    echo -e "  ${CYAN}sudo journalctl -u $SERVICE_NAME -f${NC}   Logs"
else
    echo -e "${YELLOW}Pour lancer le crawler:${NC}"
    echo -e "  ${CYAN}cd $INSTALL_DIR && ./start.sh${NC}"
    echo ""
    echo -e "${YELLOW}Ou apres avoir recharge le terminal:${NC}"
    echo -e "  ${CYAN}source ~/.bashrc${NC}"
    echo -e "  ${CYAN}crawler${NC}"
    echo ""
    echo -e "${YELLOW}Pour installer comme daemon:${NC}"
    echo -e "  ${CYAN}curl -sSL https://raw.githubusercontent.com/ahottois/crawler-onion/master/install.sh | bash -s -- --daemon${NC}"
fi

echo ""
echo -e "${YELLOW}Options disponibles:${NC}"
echo -e "  ${CYAN}crawler --help${NC}           Afficher l'aide"
echo -e "  ${CYAN}crawler --workers 20${NC}     20 workers paralleles"
echo -e "  ${CYAN}crawler --no-web${NC}         Sans interface web"
echo ""
echo -e "${YELLOW}Interface web:${NC}"
echo -e "  ${CYAN}http://VOTRE_IP:$WEB_PORT${NC}"
echo ""
