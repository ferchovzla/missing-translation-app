"""Main CLI application using Typer."""

import json
import sys
from pathlib import Path
from typing import List, Optional

import typer
from rich.console import Console
from rich.table import Table
from typing_extensions import Annotated

from transqa import __version__
from transqa.models.config import TransQAConfig

# Initialize Rich console for beautiful output
console = Console()
app = typer.Typer(
    name="transqa",
    help="🌐 TransQA - Web Translation Quality Assurance Tool",
    add_completion=False,
)


def version_callback(value: bool):
    """Show version and exit."""
    if value:
        console.print(f"TransQA version {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: Annotated[
        Optional[bool], 
        typer.Option("--version", callback=version_callback, help="Show version and exit")
    ] = None,
):
    """TransQA - Web Translation Quality Assurance Tool.
    
    Analyze web pages for translation errors, language leakage,
    and quality issues across Spanish (ES), English (EN), and Dutch (NL).
    """
    pass


@app.command()
def scan(
    url: Annotated[
        Optional[str], 
        typer.Option("--url", "-u", help="URL to analyze")
    ] = None,
    file: Annotated[
        Optional[Path],
        typer.Option("--file", "-f", help="File with URLs to analyze (one per line)", exists=True)
    ] = None,
    lang: Annotated[
        str,
        typer.Option("--lang", "-l", help="Target language (es/en/nl)")
    ] = "en",
    render: Annotated[
        bool,
        typer.Option("--render", help="Enable JavaScript rendering")
    ] = False,
    out: Annotated[
        Optional[Path],
        typer.Option("--out", "-o", help="Output file path")
    ] = None,
    format: Annotated[
        str,
        typer.Option("--format", help="Output format (json/csv/html)")
    ] = "json",
    parallel: Annotated[
        int,
        typer.Option("--parallel", "-p", help="Number of parallel workers for batch processing")
    ] = 1,
    max_errors: Annotated[
        int,
        typer.Option("--max-errors", help="Maximum number of errors before failing")
    ] = -1,
    config: Annotated[
        Optional[Path],
        typer.Option("--config", "-c", help="Configuration file path", exists=True)
    ] = None,
    verbose: Annotated[
        bool,
        typer.Option("--verbose", "-v", help="Verbose output")
    ] = False,
    quiet: Annotated[
        bool,
        typer.Option("--quiet", "-q", help="Quiet mode - minimal output")
    ] = False,
):
    """Scan web pages for translation quality issues.
    
    Examples:
    
      # Scan a single URL
      transqa scan --url "https://example.com" --lang en
      
      # Scan with JavaScript rendering and export to JSON
      transqa scan --url "https://spa-app.com" --lang es --render --out report.json
      
      # Batch process URLs from file
      transqa scan --file urls.txt --lang nl --parallel 4 --format csv
      
      # Use custom configuration
      transqa scan --url "https://example.com" --config my-config.toml
    """
    # Validate inputs
    if not url and not file:
        console.print("❌ Error: Either --url or --file must be specified", style="red")
        raise typer.Exit(1)
    
    if url and file:
        console.print("❌ Error: Cannot specify both --url and --file", style="red")
        raise typer.Exit(1)
    
    if lang not in ["es", "en", "nl"]:
        console.print(f"❌ Error: Unsupported language '{lang}'. Use: es, en, or nl", style="red")
        raise typer.Exit(1)
    
    if format not in ["json", "csv", "html"]:
        console.print(f"❌ Error: Unsupported format '{format}'. Use: json, csv, or html", style="red")
        raise typer.Exit(1)
    
    # Load configuration
    try:
        if config and config.exists():
            app_config = TransQAConfig.from_file(config)
        else:
            # Look for default config files
            default_configs = [
                Path("transqa.toml"),
                Path.home() / ".config" / "transqa" / "config.toml",
            ]
            app_config = None
            for default_config in default_configs:
                if default_config.exists():
                    app_config = TransQAConfig.from_file(default_config)
                    break
            
            if not app_config:
                app_config = TransQAConfig()  # Use defaults
    
    except Exception as e:
        console.print(f"❌ Error loading configuration: {e}", style="red")
        raise typer.Exit(1)
    
    # Override config with CLI arguments
    app_config.target.language = lang
    app_config.target.render_js = render
    
    if not quiet:
        console.print("🔍 Starting TransQA analysis...", style="blue")
        if verbose:
            console.print(f"Target language: {lang}")
            console.print(f"JavaScript rendering: {'enabled' if render else 'disabled'}")
            console.print(f"Output format: {format}")
            if parallel > 1:
                console.print(f"Parallel workers: {parallel}")
    
    # TODO: Implement actual scanning logic here
    # This is a placeholder for the MVP structure
    console.print("⚠️  Scanning logic not yet implemented - this is the MVP structure", style="yellow")
    
    if url:
        console.print(f"Would analyze URL: {url}")
    elif file:
        urls = _load_urls_from_file(file)
        console.print(f"Would analyze {len(urls)} URLs from file: {file}")
    
    console.print("✅ Analysis complete (placeholder)", style="green")
    
    # Placeholder exit code
    raise typer.Exit(0)


@app.command()
def gui(
    config: Annotated[
        Optional[Path],
        typer.Option("--config", "-c", help="Configuration file path", exists=True)
    ] = None,
):
    """Launch the desktop GUI application.
    
    Examples:
    
      # Launch with default settings
      transqa gui
      
      # Launch with custom configuration
      transqa gui --config my-config.toml
    """
    console.print("🖥️  Starting TransQA Desktop GUI...", style="blue")
    
    # TODO: Implement GUI launch logic
    console.print("⚠️  GUI not yet implemented - this is the MVP structure", style="yellow")
    
    try:
        # Placeholder for GUI import and launch
        # from transqa.ui.main import launch_gui
        # launch_gui(config)
        console.print("GUI would launch here")
    except ImportError:
        console.print("❌ GUI dependencies not installed. Install with: pip install transqa[full]", style="red")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"❌ Error launching GUI: {e}", style="red")
        raise typer.Exit(1)


@app.command()
def config(
    init: Annotated[
        bool,
        typer.Option("--init", help="Initialize a new configuration file")
    ] = False,
    path: Annotated[
        Path,
        typer.Option("--path", "-p", help="Configuration file path")
    ] = Path("transqa.toml"),
    show: Annotated[
        bool,
        typer.Option("--show", help="Show current configuration")
    ] = False,
):
    """Manage TransQA configuration.
    
    Examples:
    
      # Create a new configuration file
      transqa config --init
      
      # Create config at custom location
      transqa config --init --path /path/to/config.toml
      
      # Show current configuration
      transqa config --show
    """
    if init:
        if path.exists():
            if not typer.confirm(f"Configuration file {path} already exists. Overwrite?"):
                console.print("❌ Operation cancelled", style="red")
                raise typer.Exit(1)
        
        # Create default configuration
        default_config = TransQAConfig()
        default_config.to_file(path)
        
        console.print(f"✅ Configuration file created at: {path}", style="green")
        console.print("Edit the file to customize settings for your needs.")
    
    elif show:
        # Try to load and display configuration
        config_paths = [
            path if path != Path("transqa.toml") else None,
            Path("transqa.toml"),
            Path.home() / ".config" / "transqa" / "config.toml",
        ]
        
        loaded_config = None
        config_source = None
        
        for config_path in filter(None, config_paths):
            if config_path.exists():
                try:
                    loaded_config = TransQAConfig.from_file(config_path)
                    config_source = config_path
                    break
                except Exception as e:
                    console.print(f"❌ Error loading {config_path}: {e}", style="red")
        
        if loaded_config:
            console.print(f"📋 Configuration loaded from: {config_source}", style="blue")
            
            # Display key settings in a table
            table = Table(title="TransQA Configuration")
            table.add_column("Setting", style="cyan", no_wrap=True)
            table.add_column("Value", style="magenta")
            
            table.add_row("Target Language", loaded_config.target.language)
            table.add_row("Render JavaScript", str(loaded_config.target.render_js))
            table.add_row("Language Leak Threshold", str(loaded_config.rules.leak_threshold))
            table.add_row("LanguageTool Local Server", str(loaded_config.languagetool.local_server))
            table.add_row("Default Export Format", loaded_config.export.default_format)
            table.add_row("UI Theme", loaded_config.ui.theme)
            
            console.print(table)
        else:
            console.print("⚠️  No configuration file found. Use --init to create one.", style="yellow")
    
    else:
        console.print("❌ Please specify an action: --init, --show", style="red")
        raise typer.Exit(1)


@app.command()
def validate(
    config_file: Annotated[
        Path,
        typer.Argument(help="Configuration file to validate")
    ],
):
    """Validate a TransQA configuration file.
    
    Examples:
    
      # Validate default configuration
      transqa validate transqa.toml
      
      # Validate custom configuration
      transqa validate /path/to/my-config.toml
    """
    if not config_file.exists():
        console.print(f"❌ Configuration file not found: {config_file}", style="red")
        raise typer.Exit(1)
    
    try:
        config = TransQAConfig.from_file(config_file)
        console.print(f"✅ Configuration file is valid: {config_file}", style="green")
        
        # Show some key settings
        console.print(f"Target language: {config.target.language}")
        console.print(f"Leak threshold: {config.rules.leak_threshold}")
        console.print(f"LanguageTool server: {config.languagetool.server_url}")
        
    except Exception as e:
        console.print(f"❌ Configuration validation failed: {e}", style="red")
        raise typer.Exit(1)


def _load_urls_from_file(file_path: Path) -> List[str]:
    """Load URLs from a text file, one per line."""
    urls = []
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if line and not line.startswith('#'):  # Skip empty lines and comments
                    urls.append(line)
        return urls
    except Exception as e:
        console.print(f"❌ Error reading URLs from file: {e}", style="red")
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
