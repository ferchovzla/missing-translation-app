#!/bin/bash
# TransQA Docker Runner Script
# Makes it easy to run TransQA commands in Docker

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Create necessary directories
mkdir -p reports models cache

# Function to build the Docker image
build() {
    print_info "Building TransQA Docker image..."
    docker build -t transqa:latest .
    print_success "TransQA image built successfully!"
}

# Function to run a single URL analysis
analyze_url() {
    local url="$1"
    local lang="${2:-en}"
    local output="${3:-reports/analysis-$(date +%Y%m%d-%H%M%S)}"
    
    print_info "Analyzing $url (language: $lang)"
    
    docker run --rm \
        -v "$(pwd)/reports:/app/reports" \
        -v "$(pwd)/models:/app/models" \
        -v "$(pwd)/cache:/app/cache" \
        -v "$(pwd)/transqa.toml:/app/transqa.toml:ro" \
        -v "$(pwd)/whitelist.txt:/app/whitelist.txt:ro" \
        transqa:latest \
        scan --url "$url" --lang "$lang" --out "/app/$output.json" --format json --verbose
    
    print_success "Analysis complete! Results saved to $output.json"
}

# Function to run batch analysis from file
analyze_batch() {
    local urls_file="$1"
    local lang="${2:-en}"
    local output="${3:-reports/batch-$(date +%Y%m%d-%H%M%S)}"
    
    if [[ ! -f "$urls_file" ]]; then
        print_error "URLs file not found: $urls_file"
        exit 1
    fi
    
    print_info "Running batch analysis from $urls_file (language: $lang)"
    
    docker run --rm \
        -v "$(pwd)/reports:/app/reports" \
        -v "$(pwd)/models:/app/models" \
        -v "$(pwd)/cache:/app/cache" \
        -v "$(pwd)/$urls_file:/app/urls.txt:ro" \
        -v "$(pwd)/transqa.toml:/app/transqa.toml:ro" \
        -v "$(pwd)/whitelist.txt:/app/whitelist.txt:ro" \
        transqa:latest \
        scan --file "/app/urls.txt" --lang "$lang" --out "/app/$output.csv" --format csv --verbose
    
    print_success "Batch analysis complete! Results saved to $output.csv"
}

# Function to run interactive shell
shell() {
    print_info "Starting interactive TransQA shell..."
    docker run --rm -it \
        -v "$(pwd)/reports:/app/reports" \
        -v "$(pwd)/models:/app/models" \
        -v "$(pwd)/cache:/app/cache" \
        -v "$(pwd)/transqa.toml:/app/transqa.toml:ro" \
        -v "$(pwd)/whitelist.txt:/app/whitelist.txt:ro" \
        --entrypoint /bin/bash \
        transqa:latest
}

# Function to show configuration
show_config() {
    print_info "Showing TransQA configuration..."
    docker run --rm \
        -v "$(pwd)/transqa.toml:/app/transqa.toml:ro" \
        transqa:latest \
        config --show
}

# Function to validate configuration
validate_config() {
    print_info "Validating TransQA configuration..."
    docker run --rm \
        -v "$(pwd)/transqa.toml:/app/transqa.toml:ro" \
        transqa:latest \
        validate /app/transqa.toml
}

# Function to run examples
run_examples() {
    print_info "Running example analyses..."
    
    # Example 1: Simple English website
    print_info "Example 1: Analyzing example.com (English)"
    analyze_url "https://example.com" "en" "reports/example-com"
    
    # Example 2: Using the example URLs file
    if [[ -f "examples/urls.txt" ]]; then
        print_info "Example 2: Batch analysis of example URLs"
        analyze_batch "examples/urls.txt" "en" "reports/example-batch"
    fi
    
    print_success "Examples completed! Check the reports/ directory for results"
}

# Help function
show_help() {
    echo "TransQA Docker Runner"
    echo ""
    echo "Usage: $0 <command> [options]"
    echo ""
    echo "Commands:"
    echo "  build                          Build the TransQA Docker image"
    echo "  url <url> [lang] [output]      Analyze a single URL"
    echo "  batch <file> [lang] [output]   Analyze URLs from file"
    echo "  shell                          Start interactive shell"
    echo "  config                         Show configuration"
    echo "  validate                       Validate configuration"
    echo "  examples                       Run example analyses"
    echo "  help                           Show this help"
    echo ""
    echo "Examples:"
    echo "  $0 build"
    echo "  $0 url https://example.com en"
    echo "  $0 batch examples/urls.txt es reports/spanish-sites"
    echo "  $0 shell"
    echo ""
}

# Main script logic
case "${1:-help}" in
    build)
        build
        ;;
    url)
        if [[ -z "$2" ]]; then
            print_error "URL is required"
            echo "Usage: $0 url <url> [lang] [output]"
            exit 1
        fi
        analyze_url "$2" "$3" "$4"
        ;;
    batch)
        if [[ -z "$2" ]]; then
            print_error "URLs file is required"
            echo "Usage: $0 batch <file> [lang] [output]"
            exit 1
        fi
        analyze_batch "$2" "$3" "$4"
        ;;
    shell)
        shell
        ;;
    config)
        show_config
        ;;
    validate)
        validate_config
        ;;
    examples)
        run_examples
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        print_error "Unknown command: $1"
        show_help
        exit 1
        ;;
esac
