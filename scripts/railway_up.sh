#!/bin/bash

############################################################################
#
#    Agno Railway Setup (first-time provisioning)
#
#    Usage: ./scripts/railway_up.sh
#    Redeploy: ./scripts/railway_redeploy.sh
#
#    Prerequisites:
#      - Railway CLI installed
#      - Logged in via `railway login`
#      - OPENROUTER_API_KEY set in environment
#
############################################################################

set -e

# Colors
ORANGE='\033[38;5;208m'
DIM='\033[2m'
BOLD='\033[1m'
NC='\033[0m'

echo ""
echo -e "${ORANGE}"
cat << 'BANNER'
     █████╗  ██████╗ ███╗   ██╗ ██████╗
    ██╔══██╗██╔════╝ ████╗  ██║██╔═══██╗
    ███████║██║  ███╗██╔██╗ ██║██║   ██║
    ██╔══██║██║   ██║██║╚██╗██║██║   ██║
    ██║  ██║╚██████╔╝██║ ╚████║╚██████╔╝
    ╚═╝  ╚═╝ ╚═════╝ ╚═╝  ╚═══╝ ╚═════╝
BANNER
echo -e "${NC}"

# Load .env.production if it exists
if [[ -f .env.production ]]; then
    set -a
    source .env.production
    set +a
    echo -e "${DIM}Loaded .env.production${NC}"
fi

# Preflight
if ! command -v railway &> /dev/null; then
    echo "Railway CLI not found. Install: https://docs.railway.app/guides/cli"
    exit 1
fi

if [[ -z "$OPENROUTER_API_KEY" ]]; then
    echo "OPENROUTER_API_KEY not set. Add to .env.production or export it."
    exit 1
fi

echo -e "${BOLD}Initializing project...${NC}"
echo ""
railway init -n "dash"

echo ""
echo -e "${BOLD}Deploying PgVector database...${NC}"
echo ""
railway add -s pgvector -i agnohq/pgvector:18 \
    -v "POSTGRES_USER=${DB_USER:-ai}" \
    -v "POSTGRES_PASSWORD=${DB_PASS:-ai}" \
    -v "POSTGRES_DB=${DB_DATABASE:-ai}" \
    -v "PGDATA=/var/lib/postgresql/data"

echo ""
echo ""
echo -e "${BOLD}Adding database volume...${NC}"
railway service link pgvector
railway volume add -m /var/lib/postgresql/data 2>/dev/null || echo -e "${DIM}Volume already exists or skipped${NC}"

echo ""
echo -e "${DIM}Waiting 15s for database...${NC}"
sleep 15

echo ""
echo -e "${BOLD}Creating application service...${NC}"
echo ""
OPTIONAL_VARS=()
[[ -n "$SLACK_TOKEN" ]]           && OPTIONAL_VARS+=(-v "SLACK_TOKEN=${SLACK_TOKEN}")
[[ -n "$SLACK_SIGNING_SECRET" ]]  && OPTIONAL_VARS+=(-v "SLACK_SIGNING_SECRET=${SLACK_SIGNING_SECRET}")
[[ -n "$JWT_VERIFICATION_KEY" ]]  && OPTIONAL_VARS+=(-v "JWT_VERIFICATION_KEY=${JWT_VERIFICATION_KEY}")
[[ -n "$OPENROUTER_MODEL_ID" ]]   && OPTIONAL_VARS+=(-v "OPENROUTER_MODEL_ID=${OPENROUTER_MODEL_ID}")
[[ -n "$OPENROUTER_EMBEDDING_MODEL_ID" ]] && OPTIONAL_VARS+=(-v "OPENROUTER_EMBEDDING_MODEL_ID=${OPENROUTER_EMBEDDING_MODEL_ID}")
[[ -n "$OPENROUTER_EMBEDDING_DIMENSIONS" ]] && OPTIONAL_VARS+=(-v "OPENROUTER_EMBEDDING_DIMENSIONS=${OPENROUTER_EMBEDDING_DIMENSIONS}")
[[ -n "$OPENROUTER_BASE_URL" ]]   && OPTIONAL_VARS+=(-v "OPENROUTER_BASE_URL=${OPENROUTER_BASE_URL}")
[[ -n "$OPENROUTER_HTTP_REFERER" ]] && OPTIONAL_VARS+=(-v "OPENROUTER_HTTP_REFERER=${OPENROUTER_HTTP_REFERER}")
[[ -n "$OPENROUTER_APP_TITLE" ]]  && OPTIONAL_VARS+=(-v "OPENROUTER_APP_TITLE=${OPENROUTER_APP_TITLE}")
for var_name in \
    OPENROUTER_FALLBACK_MODEL_IDS \
    OPENROUTER_PROVIDER_JSON \
    OPENROUTER_PROVIDER_BY_MODEL_JSON \
    OPENROUTER_PROVIDER_SORT \
    OPENROUTER_PROVIDER_ORDER \
    OPENROUTER_PROVIDER_ONLY \
    OPENROUTER_PROVIDER_IGNORE \
    OPENROUTER_PROVIDER_QUANTIZATIONS \
    OPENROUTER_PROVIDER_ALLOW_FALLBACKS \
    OPENROUTER_PROVIDER_REQUIRE_PARAMETERS \
    OPENROUTER_PROVIDER_DATA_COLLECTION \
    OPENROUTER_PROVIDER_ZDR \
    OPENROUTER_PROVIDER_ENFORCE_DISTILLABLE_TEXT \
    OPENROUTER_PROVIDER_PREFERRED_MIN_THROUGHPUT \
    OPENROUTER_PROVIDER_PREFERRED_MAX_LATENCY \
    OPENROUTER_PROVIDER_MAX_PRICE; do
    [[ -n "${!var_name:-}" ]] && OPTIONAL_VARS+=(-v "${var_name}=${!var_name}")
done

railway add -s dash \
    -v "DB_USER=${DB_USER:-ai}" \
    -v "DB_PASS=${DB_PASS:-ai}" \
    -v "DB_HOST=pgvector.railway.internal" \
    -v "DB_PORT=${DB_PORT:-5432}" \
    -v "DB_DATABASE=${DB_DATABASE:-ai}" \
    -v "DB_DRIVER=postgresql+psycopg" \
    -v "WAIT_FOR_DB=True" \
    -v "OPENROUTER_API_KEY=${OPENROUTER_API_KEY}" \
    -v "PORT=8000" \
    "${OPTIONAL_VARS[@]}"

echo ""
echo -e "${BOLD}Deploying application...${NC}"
echo ""
railway up --service dash -d

echo ""
echo -e "${BOLD}Creating domain...${NC}"
echo ""
railway domain --service dash

echo ""
echo -e "${BOLD}Done.${NC} Domain may take ~5 minutes."
echo -e "${DIM}Logs: railway logs --service dash${NC}"
echo ""
