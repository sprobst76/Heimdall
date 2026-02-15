#!/bin/bash
# Heimdall Deployment Script
# Usage: ./deploy.sh [install|update|logs|status|backup|restart|stop|migrate]

set -e

# Configuration
REPO_URL="git@github.com:sprobst76/Heimdall.git"
INSTALL_DIR="/srv/heimdall"
BACKEND_DIR="$INSTALL_DIR/backend"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Check if running as correct user
check_user() {
    if [[ $EUID -eq 0 ]]; then
        log_error "Don't run as root. Use your regular user."
        exit 1
    fi
}

# Initial installation
install() {
    log_info "Installing Heimdall..."

    if [[ -d "$INSTALL_DIR" ]]; then
        log_error "$INSTALL_DIR already exists. Use 'update' instead."
        exit 1
    fi

    # Clone repository
    log_info "Cloning repository..."
    cd /srv
    git clone "$REPO_URL" heimdall

    # Setup environment
    cd "$BACKEND_DIR"
    if [[ ! -f .env ]]; then
        log_info "Creating .env file..."
        cp .env.example .env

        # Generate secure passwords
        POSTGRES_PW=$(openssl rand -base64 24)
        SECRET=$(openssl rand -base64 32)
        sed -i "s/CHANGE_ME_TO_SECURE_PASSWORD/$POSTGRES_PW/" .env
        sed -i "s/CHANGE_ME_TO_SECURE_SECRET/$SECRET/" .env

        log_warn "Edit .env to set your domain and optional API keys:"
        log_warn "  nano $BACKEND_DIR/.env"
        echo ""
        read -p "Enter your domain (e.g., example.com): " DOMAIN
        sed -i "s/example.com/$DOMAIN/g" .env
    fi

    # Build and start
    log_info "Building and starting containers..."
    docker compose up -d --build

    # Wait for health
    log_info "Waiting for services to be healthy..."
    sleep 15

    # Run migrations
    migrate

    # Check status
    status

    log_info "Installation complete!"
    log_info "API available at: https://heimdall.lab.$(grep DOMAIN .env | cut -d= -f2)"
}

# Update existing installation
update() {
    log_info "Updating Heimdall..."

    if [[ ! -d "$INSTALL_DIR" ]]; then
        log_error "$INSTALL_DIR does not exist. Use 'install' first."
        exit 1
    fi

    cd "$INSTALL_DIR"

    # Pull latest changes
    log_info "Pulling latest changes..."
    git pull

    # Rebuild and restart API + Web
    cd "$BACKEND_DIR"
    log_info "Rebuilding containers..."
    docker compose build --no-cache api web
    docker compose up -d api web

    # Run migrations
    log_info "Running database migrations..."
    sleep 5
    migrate

    # Cleanup old images
    log_info "Cleaning up old images..."
    docker image prune -f

    # Check status
    status

    log_info "Update complete!"
}

# Run Alembic migrations
migrate() {
    log_info "Running Alembic migrations..."
    cd "$BACKEND_DIR"
    docker compose exec -T api uv run alembic upgrade head
    log_info "Migrations complete!"
}

# Show logs
logs() {
    cd "$BACKEND_DIR"
    docker compose logs -f --tail=100 "${1:-api}"
}

# Show status
status() {
    log_info "Service Status:"
    cd "$BACKEND_DIR"
    docker compose ps

    echo ""
    log_info "Health Checks:"

    if docker compose exec -T api curl -sf http://localhost:8000/health > /dev/null 2>&1; then
        echo -e "  API:        ${GREEN}healthy${NC}"
    else
        echo -e "  API:        ${RED}unhealthy${NC}"
    fi

    if docker compose exec -T postgres pg_isready -U heimdall > /dev/null 2>&1; then
        echo -e "  PostgreSQL: ${GREEN}healthy${NC}"
    else
        echo -e "  PostgreSQL: ${RED}unhealthy${NC}"
    fi

    if docker compose exec -T redis redis-cli ping > /dev/null 2>&1; then
        echo -e "  Redis:      ${GREEN}healthy${NC}"
    else
        echo -e "  Redis:      ${RED}unhealthy${NC}"
    fi
}

# Backup database
backup() {
    log_info "Creating database backup..."
    cd "$BACKEND_DIR"

    mkdir -p data/backups
    BACKUP_FILE="data/backups/heimdall_$(date +%Y%m%d_%H%M%S).sql"
    docker compose exec -T postgres pg_dump -U heimdall heimdall > "$BACKUP_FILE"

    log_info "Backup saved to: $BACKEND_DIR/$BACKUP_FILE"
    ls -lh "$BACKUP_FILE"
}

# Restart services
restart() {
    log_info "Restarting services..."
    cd "$BACKEND_DIR"
    docker compose restart
    sleep 5
    status
}

# Stop services
stop() {
    log_info "Stopping services..."
    cd "$BACKEND_DIR"
    docker compose down
}

# Show help
help() {
    echo "Heimdall Deployment Script"
    echo ""
    echo "Usage: $0 <command>"
    echo ""
    echo "Commands:"
    echo "  install   - Initial installation (clone, configure, start)"
    echo "  update    - Pull latest changes, rebuild, migrate"
    echo "  logs      - Show logs (default: api, or specify service)"
    echo "  status    - Show service status and health"
    echo "  backup    - Create database backup"
    echo "  migrate   - Run Alembic database migrations"
    echo "  restart   - Restart all services"
    echo "  stop      - Stop all services"
    echo "  help      - Show this help"
    echo ""
    echo "Examples:"
    echo "  $0 install          # First-time setup"
    echo "  $0 update           # Deploy latest version"
    echo "  $0 logs             # View API logs"
    echo "  $0 logs postgres    # View database logs"
    echo "  $0 backup           # Create DB backup"
}

# Main
check_user

case "${1:-help}" in
    install) install ;;
    update)  update ;;
    logs)    logs "$2" ;;
    status)  status ;;
    backup)  backup ;;
    migrate) migrate ;;
    restart) restart ;;
    stop)    stop ;;
    help)    help ;;
    *)       log_error "Unknown command: $1"; help; exit 1 ;;
esac
