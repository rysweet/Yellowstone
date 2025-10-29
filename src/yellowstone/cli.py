"""
Yellowstone CLI - Command-line interface for Cypher to KQL translation.

Provides commands for:
  - Translating individual Cypher queries to KQL
  - Batch translating query files
  - Validating schema YAML files
  - Interactive REPL mode for query translation
"""

import sys
import click
import yaml
from pathlib import Path
from typing import Optional, List
from rich.console import Console
from rich.syntax import Syntax
from rich.table import Table
from rich.panel import Panel

from .parser import parse_query
from .translator import translate, CypherToKQLTranslator
from .schema import SchemaValidator, SchemaMapping
from .models import KQLQuery


# Rich console for formatted output
console = Console()
err_console = Console(stderr=True)


@click.group()
@click.version_option(version="0.1.0", prog_name="yellowstone")
def cli():
    """
    Yellowstone: Cypher Query Engine for Microsoft Sentinel Graph

    Translate Cypher queries to KQL for use with Microsoft Sentinel's graph operators.

    Examples:
        yellowstone translate "MATCH (u:User) RETURN u.name"
        yellowstone translate-file queries.cypher --output results.kql
        yellowstone validate-schema schema.yaml
    """
    pass


@cli.command()
@click.argument("query", type=str)
@click.option(
    "--format",
    type=click.Choice(["text", "json", "raw"]),
    default="text",
    help="Output format for the translated query",
)
@click.option(
    "--show-ast",
    is_flag=True,
    help="Display the Cypher AST before translation",
)
@click.option(
    "--confidence",
    type=float,
    default=0.95,
    help="Translation confidence score (0.0-1.0)",
)
def translate_cmd(query: str, format: str, show_ast: bool, confidence: float):
    """
    Translate a single Cypher query to KQL.

    QUERY: The Cypher query string to translate

    Examples:
        yellowstone translate "MATCH (u:User) RETURN u.name"
        yellowstone translate "MATCH (u:User)-[r:LOGGED_IN]->(d:Device) RETURN u, d" --show-ast
    """
    if not 0.0 <= confidence <= 1.0:
        err_console.print("[red]Error:[/red] Confidence must be between 0.0 and 1.0")
        sys.exit(1)

    try:
        # Parse the Cypher query
        ast = parse_query(query)

        if show_ast:
            console.print(Panel(str(ast), title="Cypher AST", expand=False))

        # Translate to KQL
        kql_result = translate(ast, confidence=confidence)

        # Output based on format
        if format == "raw":
            console.print(kql_result.query)
        elif format == "json":
            import json

            output = {
                "cypher": query,
                "kql": kql_result.query,
                "strategy": kql_result.strategy.value,
                "confidence": kql_result.confidence,
                "execution_time_ms": kql_result.estimated_execution_time_ms,
            }
            console.print(json.dumps(output, indent=2))
        else:  # text format (default)
            console.print(
                Panel(
                    Syntax(kql_result.query, "sql", theme="monokai", line_numbers=True),
                    title="KQL Translation",
                    expand=False,
                )
            )
            console.print()
            table = Table(title="Translation Metadata")
            table.add_column("Property", style="cyan")
            table.add_column("Value", style="green")
            table.add_row("Strategy", kql_result.strategy.value)
            table.add_row("Confidence", f"{kql_result.confidence:.2%}")
            if kql_result.estimated_execution_time_ms:
                table.add_row(
                    "Est. Execution Time", f"{kql_result.estimated_execution_time_ms}ms"
                )
            console.print(table)

    except SyntaxError as e:
        err_console.print(f"[red]Syntax Error:[/red] {e}")
        sys.exit(1)
    except ValueError as e:
        err_console.print(f"[red]Translation Error:[/red] {e}")
        sys.exit(1)
    except Exception as e:
        err_console.print(f"[red]Unexpected Error:[/red] {type(e).__name__}: {e}")
        sys.exit(1)


@cli.command()
@click.argument("input_file", type=click.Path(exists=True, readable=True))
@click.option(
    "--output",
    type=click.Path(),
    default=None,
    help="Output file path (defaults to stdout)",
)
@click.option(
    "--format",
    type=click.Choice(["text", "json", "csv"]),
    default="text",
    help="Output format",
)
@click.option(
    "--skip-errors",
    is_flag=True,
    help="Continue processing even if individual queries fail",
)
@click.option(
    "--confidence",
    type=float,
    default=0.95,
    help="Translation confidence score (0.0-1.0)",
)
def translate_file_cmd(
    input_file: str, output: Optional[str], format: str, skip_errors: bool, confidence: float
):
    """
    Translate a file of Cypher queries to KQL.

    INPUT_FILE: Path to file containing Cypher queries (one per line)

    Output formats:
      - text: Readable format with metadata (default)
      - json: JSON array of translation results
      - csv: Comma-separated values for spreadsheet import

    Examples:
        yellowstone translate-file queries.cypher
        yellowstone translate-file queries.cypher --output results.kql --format json
        yellowstone translate-file queries.cypher --skip-errors
    """
    if not 0.0 <= confidence <= 1.0:
        err_console.print("[red]Error:[/red] Confidence must be between 0.0 and 1.0")
        sys.exit(1)

    try:
        input_path = Path(input_file)

        # Read queries from file
        with open(input_path, "r") as f:
            lines = f.readlines()

        # Filter out empty lines and comments
        queries = [
            line.strip()
            for line in lines
            if line.strip() and not line.strip().startswith("#")
        ]

        if not queries:
            err_console.print("[yellow]Warning:[/yellow] No queries found in file")
            return

        err_console.print(f"Processing {len(queries)} queries...")

        results = []
        successful = 0
        failed = 0

        for i, query in enumerate(queries, 1):
            try:
                # Parse and translate
                ast = parse_query(query)
                kql_result = translate(ast, confidence=confidence)
                results.append(
                    {
                        "query_num": i,
                        "cypher": query,
                        "kql": kql_result.query,
                        "strategy": kql_result.strategy.value,
                        "confidence": kql_result.confidence,
                        "status": "success",
                    }
                )
                successful += 1
            except Exception as e:
                failed += 1
                if skip_errors:
                    results.append(
                        {
                            "query_num": i,
                            "cypher": query,
                            "error": str(e),
                            "status": "failed",
                        }
                    )
                else:
                    err_console.print(f"[red]Error on query {i}:[/red] {e}")
                    sys.exit(1)

        # Output results
        output_text = _format_results(results, format)

        if output:
            output_path = Path(output)
            with open(output_path, "w") as f:
                f.write(output_text)
            err_console.print(f"[green]Success:[/green] Results written to {output_path}")
        else:
            console.print(output_text)

        # Print summary
        err_console.print(f"[cyan]Summary:[/cyan] {successful} successful, {failed} failed")

    except FileNotFoundError:
        err_console.print(f"[red]Error:[/red] File not found: {input_file}")
        sys.exit(1)
    except Exception as e:
        err_console.print(f"[red]Error:[/red] {type(e).__name__}: {e}")
        sys.exit(1)


@cli.command()
@click.argument("schema_file", type=click.Path(exists=True, readable=True))
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    help="Show detailed validation information",
)
@click.option(
    "--fix-warnings",
    is_flag=True,
    help="Attempt to auto-fix non-critical issues",
)
def validate_schema_cmd(schema_file: str, verbose: bool, fix_warnings: bool):
    """
    Validate a schema YAML file.

    SCHEMA_FILE: Path to the schema YAML file to validate

    Validates:
      - Required fields present
      - Correct data types
      - Referential integrity
      - Sentinel table consistency

    Examples:
        yellowstone validate-schema schema.yaml
        yellowstone validate-schema schema.yaml --verbose
    """
    try:
        schema_path = Path(schema_file)

        # Load YAML
        with open(schema_path, "r") as f:
            schema_dict = yaml.safe_load(f)

        if not schema_dict:
            err_console.print("[red]Error:[/red] Schema file is empty")
            sys.exit(1)

        # Parse schema with Pydantic
        try:
            schema = SchemaMapping(**schema_dict)
        except Exception as e:
            err_console.print(f"[red]Schema Parse Error:[/red] {e}")
            sys.exit(1)

        # Validate schema
        validator = SchemaValidator()
        result = validator.validate(schema)

        # Display results
        console.print()
        if result.is_valid:
            console.print("[green]✓ Schema is valid[/green]")
        else:
            console.print("[red]✗ Schema validation failed[/red]")

        # Show errors
        if result.errors:
            console.print("\n[red]Errors:[/red]")
            for error in result.errors:
                console.print(f"  • {error}")

        # Show warnings
        if result.warnings:
            console.print("\n[yellow]Warnings:[/yellow]")
            for warning in result.warnings:
                console.print(f"  • {warning}")

        # Show summary
        console.print("\n[cyan]Schema Summary:[/cyan]")
        table = Table(show_header=False)
        table.add_row("Nodes", str(result.node_count))
        table.add_row("Edges", str(result.edge_count))
        table.add_row("Tables", str(result.table_count))
        console.print(table)

        if verbose:
            console.print("\n[cyan]Detailed Information:[/cyan]")

            if schema.nodes:
                console.print("\nNode Mappings:")
                for label, mapping in schema.nodes.items():
                    console.print(f"  {label} → {mapping.sentinel_table}")
                    for prop, prop_map in mapping.properties.items():
                        console.print(
                            f"    • {prop}: {prop_map.sentinel_field} ({prop_map.type})"
                        )

            if schema.edges:
                console.print("\nEdge Mappings:")
                for rel_type, mapping in schema.edges.items():
                    console.print(f"  {rel_type}")
                    console.print(f"    • From: {mapping.from_label}")
                    console.print(f"    • To: {mapping.to_label}")
                    console.print(f"    • Strength: {mapping.strength}")

        sys.exit(0 if result.is_valid else 1)

    except FileNotFoundError:
        err_console.print(f"[red]Error:[/red] File not found: {schema_file}")
        sys.exit(1)
    except yaml.YAMLError as e:
        err_console.print(f"[red]YAML Parse Error:[/red] {e}")
        sys.exit(1)
    except Exception as e:
        err_console.print(f"[red]Error:[/red] {type(e).__name__}: {e}")
        sys.exit(1)


@cli.command()
@click.option(
    "--schema",
    type=click.Path(exists=True, readable=True),
    default=None,
    help="Optional schema file for context-aware translation",
)
def repl_cmd(schema: Optional[str]):
    """
    Start interactive REPL mode for query translation.

    Interactively translate Cypher queries to KQL. Type 'help', 'exit', or 'quit' to exit.

    Commands in REPL:
      - query <cypher>: Translate a Cypher query
      - ast <cypher>: Show AST for a Cypher query
      - help: Show this help message
      - exit/quit: Exit REPL

    Examples:
        yellowstone repl
        yellowstone repl --schema schema.yaml
    """
    console.print(
        Panel(
            "Yellowstone REPL - Cypher to KQL Translator\n"
            "Type 'help' for commands or 'exit' to quit",
            title="Interactive Mode",
            style="cyan",
        )
    )

    # Load schema if provided
    loaded_schema = None
    if schema:
        try:
            with open(schema, "r") as f:
                schema_dict = yaml.safe_load(f)
            loaded_schema = SchemaMapping(**schema_dict)
            err_console.print(f"[green]Loaded schema:[/green] {schema}")
        except Exception as e:
            err_console.print(f"[yellow]Warning:[/yellow] Could not load schema: {e}")

    translator = CypherToKQLTranslator()

    while True:
        try:
            user_input = console.input("[cyan]yellowstone>[/cyan] ").strip()

            if not user_input:
                continue

            # Handle special commands
            if user_input.lower() in ("exit", "quit"):
                console.print("[cyan]Goodbye![/cyan]")
                break

            if user_input.lower() == "help":
                _print_repl_help()
                continue

            # Parse command and argument
            parts = user_input.split(maxsplit=1)
            command = parts[0].lower()
            arg = parts[1] if len(parts) > 1 else None

            if command == "query" and arg:
                _repl_translate_query(arg, translator)

            elif command == "ast" and arg:
                _repl_show_ast(arg)

            else:
                # Treat as direct query string
                _repl_translate_query(user_input, translator)

        except KeyboardInterrupt:
            console.print("\n[cyan]Goodbye![/cyan]")
            break
        except EOFError:
            console.print("\n[cyan]Goodbye![/cyan]")
            break
        except Exception as e:
            err_console.print(f"[red]Error:[/red] {e}")


# ============================================================================
# Helper Functions
# ============================================================================


def _format_results(results: List[dict], format: str) -> str:
    """Format translation results based on requested format."""
    if format == "json":
        import json

        return json.dumps(results, indent=2)

    elif format == "csv":
        import csv
        from io import StringIO

        output = StringIO()
        if results and "status" in results[0]:
            fieldnames = [
                "query_num",
                "cypher",
                "kql",
                "strategy",
                "confidence",
                "status",
                "error",
            ]
        else:
            fieldnames = ["query_num", "cypher", "kql", "strategy", "confidence"]

        writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(results)
        return output.getvalue()

    else:  # text format
        output_lines = []
        for i, result in enumerate(results, 1):
            output_lines.append(f"\n--- Query {result['query_num']} ---")
            output_lines.append(f"Cypher: {result['cypher']}")

            if result.get("status") == "failed":
                output_lines.append(f"Error: {result.get('error', 'Unknown error')}")
            else:
                output_lines.append(f"KQL:\n{result['kql']}")
                output_lines.append(f"Strategy: {result.get('strategy', 'N/A')}")
                output_lines.append(f"Confidence: {result.get('confidence', 'N/A')}")

        return "\n".join(output_lines)


def _print_repl_help():
    """Print help for REPL mode."""
    help_table = Table(title="REPL Commands")
    help_table.add_column("Command", style="cyan")
    help_table.add_column("Description", style="green")

    help_table.add_row("query <cypher>", "Translate a Cypher query")
    help_table.add_row("ast <cypher>", "Show AST for a Cypher query")
    help_table.add_row("<cypher>", "Direct query string (auto-translate)")
    help_table.add_row("help", "Show this help message")
    help_table.add_row("exit/quit", "Exit REPL")

    console.print(help_table)


def _repl_translate_query(query: str, translator: CypherToKQLTranslator):
    """Translate a query in REPL mode."""
    try:
        ast = parse_query(query)
        kql_result = translate(ast)

        console.print("\n[green]Translation successful![/green]")
        console.print(
            Panel(
                Syntax(kql_result.query, "sql", theme="monokai", line_numbers=True),
                title="KQL Result",
                expand=False,
            )
        )
        console.print(f"Strategy: {kql_result.strategy.value}")
        console.print(f"Confidence: {kql_result.confidence:.2%}\n")

    except Exception as e:
        err_console.print(f"\n[red]Error:[/red] {e}\n")


def _repl_show_ast(query: str):
    """Show AST for a query in REPL mode."""
    try:
        ast = parse_query(query)
        console.print("\n[green]AST:[/green]")
        console.print(Panel(str(ast), expand=False))
        console.print()

    except Exception as e:
        err_console.print(f"\n[red]Error:[/red] {e}\n")


if __name__ == "__main__":
    cli()
