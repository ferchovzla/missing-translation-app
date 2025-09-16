"""Main CLI application using Typer."""

import csv
import json
import logging
import sys
from pathlib import Path
from typing import List, Optional

import typer
from rich.console import Console
from rich.progress import track
from rich.table import Table
from typing_extensions import Annotated

from transqa import __version__
from transqa.core.analyzer import TransQAAnalyzer
from transqa.models.config import TransQAConfig
from transqa.models.result import PageResult, BatchResult

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
    
    # Setup logging
    log_level = logging.DEBUG if verbose else logging.INFO if not quiet else logging.WARNING
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler() if verbose else logging.NullHandler()
        ]
    )
    
    # Initialize analyzer
    try:
        analyzer = TransQAAnalyzer(app_config)
        
        if not quiet:
            console.print("🔧 Initializing TransQA analyzer...", style="blue")
        
        analyzer.initialize()
        
        if not quiet:
            console.print("✅ Analyzer initialized successfully", style="green")
        
    except Exception as e:
        console.print(f"❌ Failed to initialize analyzer: {e}", style="red")
        raise typer.Exit(1)
    
    try:
        # Perform analysis
        results: List[PageResult] = []
        urls_to_process = []
        
        if url:
            urls_to_process = [url]
        elif file:
            urls_to_process = _load_urls_from_file(file)
        
        if not urls_to_process:
            console.print("❌ No URLs to process", style="red")
            raise typer.Exit(1)
        
        # Process URLs
        for current_url in track(urls_to_process, description="Analyzing URLs...") if not quiet else urls_to_process:
            try:
                if not quiet and len(urls_to_process) > 1:
                    console.print(f"🔍 Analyzing: {current_url}")
                
                result = analyzer.analyze_url(current_url, lang, render)
                results.append(result)
                
                if not quiet:
                    # Show quick summary
                    issues_count = len(result.issues)
                    if issues_count == 0:
                        console.print(f"   ✅ No issues found", style="green")
                    else:
                        critical = len(result.get_critical_issues())
                        errors = len(result.get_error_issues()) 
                        warnings = len(result.get_warning_issues())
                        
                        summary_parts = []
                        if critical > 0:
                            summary_parts.append(f"{critical} critical")
                        if errors > 0:
                            summary_parts.append(f"{errors} errors")
                        if warnings > 0:
                            summary_parts.append(f"{warnings} warnings")
                        
                        status_color = "red" if critical > 0 or errors > 0 else "yellow"
                        console.print(f"   ⚠️  {issues_count} issues: {', '.join(summary_parts)}", style=status_color)
            
            except Exception as e:
                console.print(f"   ❌ Failed to analyze {current_url}: {e}", style="red")
                # Create error result
                error_result = PageResult(
                    url=current_url,
                    target_lang=lang,
                    issues=[],
                )
                results.append(error_result)
        
        # Create batch result
        batch_result = BatchResult(results=results)
        
        # Export results if requested
        if out:
            _export_results(batch_result, out, format)
            if not quiet:
                console.print(f"📄 Results exported to: {out}", style="green")
        
        # Display summary
        if not quiet:
            _display_summary(batch_result, console)
        
        # Determine exit code
        exit_code = batch_result.get_exit_code()
        
        if max_errors > 0:
            total_errors = sum(len(r.get_error_issues()) + len(r.get_critical_issues()) for r in results)
            if total_errors > max_errors:
                console.print(f"❌ Error count ({total_errors}) exceeds maximum ({max_errors})", style="red")
                exit_code = 2
        
        raise typer.Exit(exit_code)
    
    finally:
        # Cleanup analyzer
        try:
            analyzer.cleanup()
        except:
            pass


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


def _export_results(batch_result: BatchResult, output_path: Path, format: str) -> None:
    """Export results to file in specified format."""
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        if format == "json":
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(batch_result.dict(), f, indent=2, ensure_ascii=False)
        
        elif format == "csv":
            with open(output_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                
                # Write header
                writer.writerow([
                    'url', 'target_lang', 'issue_type', 'severity', 'message', 
                    'suggestion', 'snippet', 'xpath', 'confidence'
                ])
                
                # Write issues
                for result in batch_result.results:
                    for issue in result.issues:
                        writer.writerow([
                            str(result.url),
                            result.target_lang,
                            str(issue.type),
                            str(issue.severity),
                            issue.message,
                            issue.suggestion or '',
                            issue.snippet,
                            issue.xpath,
                            issue.confidence
                        ])
        
        elif format == "html":
            _export_html_report(batch_result, output_path)
        
        else:
            raise ValueError(f"Unsupported format: {format}")
            
    except Exception as e:
        console.print(f"❌ Export failed: {e}", style="red")
        raise typer.Exit(1)


def _export_html_report(batch_result: BatchResult, output_path: Path) -> None:
    """Export results as HTML report."""
    html_content = """
<!DOCTYPE html>
<html>
<head>
    <title>TransQA Analysis Report</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        .header { background: #f5f5f5; padding: 20px; border-radius: 5px; margin-bottom: 20px; }
        .url-section { margin-bottom: 30px; border: 1px solid #ddd; padding: 15px; border-radius: 5px; }
        .issue { margin: 10px 0; padding: 10px; border-left: 4px solid #ccc; }
        .critical { border-left-color: #d32f2f; background: #ffebee; }
        .error { border-left-color: #f57c00; background: #fff3e0; }
        .warning { border-left-color: #fbc02d; background: #fffde7; }
        .info { border-left-color: #1976d2; background: #e3f2fd; }
        .stats { background: #f9f9f9; padding: 10px; border-radius: 3px; margin-top: 10px; }
    </style>
</head>
<body>
    <div class="header">
        <h1>TransQA Analysis Report</h1>
        <p>Generated: {timestamp}</p>
        <p>Total URLs: {total_urls}</p>
        <p>Total Issues: {total_issues}</p>
    </div>
""".format(
        timestamp=batch_result.generated_at.strftime("%Y-%m-%d %H:%M:%S"),
        total_urls=len(batch_result.results),
        total_issues=sum(len(r.issues) for r in batch_result.results)
    )
    
    for result in batch_result.results:
        html_content += f"""
        <div class="url-section">
            <h2>{result.url}</h2>
            <div class="stats">
                <strong>Language:</strong> {result.target_lang} | 
                <strong>Issues:</strong> {len(result.issues)} | 
                <strong>Score:</strong> {result.stats.overall_score:.2f}
            </div>
        """
        
        if result.issues:
            for issue in result.issues:
                severity_class = str(issue.severity).lower()
                html_content += f"""
                <div class="issue {severity_class}">
                    <strong>{issue.type}</strong> ({issue.severity})<br>
                    {issue.message}<br>
                    <code>{issue.snippet}</code>
                    {f'<br><em>Suggestion: {issue.suggestion}</em>' if issue.suggestion else ''}
                </div>
                """
        else:
            html_content += "<p>✅ No issues found</p>"
        
        html_content += "</div>"
    
    html_content += "</body></html>"
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html_content)


def _display_summary(batch_result: BatchResult, console: Console) -> None:
    """Display analysis summary."""
    summary = batch_result.get_summary()
    
    console.print("\n📊 Analysis Summary", style="bold blue")
    
    # Summary table
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Metric", style="cyan", no_wrap=True)
    table.add_column("Value", style="white")
    
    table.add_row("URLs Analyzed", str(summary['total_pages']))
    table.add_row("Total Issues", str(summary['total_issues']))
    table.add_row("Critical", str(summary['total_critical']))
    table.add_row("Errors", str(summary['total_errors']))
    table.add_row("Warnings", str(summary['total_warnings']))
    table.add_row("Average Score", f"{summary['average_score']:.2f}")
    table.add_row("Analysis Time", f"{summary['analysis_time']:.2f}s")
    
    console.print(table)
    
    # Show worst pages if any
    worst_pages = batch_result.get_worst_pages(3)
    if worst_pages and len(batch_result.results) > 1:
        console.print("\n🔴 Pages with Most Issues", style="bold red")
        for i, result in enumerate(worst_pages, 1):
            issues_count = len(result.issues)
            score = result.stats.overall_score
            console.print(f"{i}. {result.url} - {issues_count} issues (score: {score:.2f})")
    
    console.print("")


if __name__ == "__main__":
    app()
