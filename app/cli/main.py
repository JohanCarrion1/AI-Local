#!/usr/bin/env python3
"""
AI-Local-Hub - CLI Interface
=============================
Main command-line interface for managing AI models locally.
"""

import sys
import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich import box

from app.core.model_manager import ModelManager
from app.core.executor import ModelExecutor, InferenceResult
from app.core.github_connector import GitHubConnector
from app.core.resource_detector import ResourceDetector, DeviceSpecs
from app.utils.config import Config
from app.db.database import Database, ModelRecord


# Initialize components
model_manager = ModelManager()
executor = ModelExecutor()
db = Database()
console = Console()


@click.group()
@click.version_option(version="0.1.0", message="AI-Local-Hub v%(version)")
def cli():
    """AI-Local-Hub: Gestor local de modelos de IA."""
    pass


# ==================== DETECCIÓN DE RECURSOS ====================

@cli.command(name="detect", help="Detectar recursos del dispositivo")
@click.option("--json", is_flag=True, help="Mostrar salida en formato JSON")
def detect_resources(json: bool):
    """Detecta RAM, VRAM, GPU y recomienda modelos compatibles."""
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task("Detectando recursos...", total=None)
        specs = ResourceDetector.detect()
        progress.update(task, completed=True)
    
    if json:
        import json as json_module
        click.echo(json_module.dumps({
            "os": specs.os,
            "os_version": specs.os_version,
            "ram_total_gb": specs.ram_total_gb,
            "ram_available_gb": specs.ram_available_gb,
            "cpu_cores": specs.cpu_cores,
            "cpu_model": specs.cpu_model,
            "gpu": specs.gpu,
            "gpu_vram_gb": specs.gpu_vram_gb,
            "is_mobile": specs.is_mobile,
            "is_termux": specs.is_termux,
            "architecture": specs.architecture,
            "recommended_models": [
                {"name": m["name"], "size": m["size"], "vram": m["vram"]}
                for m in Config.get_recommendations(Config.detect_tier())
            ]
        }, indent=2))
        return
    
    # Mostrar información del dispositivo
    console.print(Panel(
        "[bold blue]📱 Información del Dispositivo[/bold blue]",
        style="blue",
        box=box.DOUBLE
    ))
    
    table = Table(box=box.ROUNDED, show_header=True, header_style="bold cyan")
    table.add_column("Propiedad", style="white")
    table.add_column("Valor", style="green")
    
    table.add_row("Sistema Operativo", specs.os)
    table.add_row("Arquitectura", specs.architecture)
    table.add_row("RAM Total", f"{specs.ram_total_gb:.1f} GB")
    table.add_row("RAM Disponible", f"{specs.ram_available_gb:.1f} GB")
    table.add_row("Núcleos CPU", str(specs.cpu_cores))
    table.add_row("Modelo CPU", specs.cpu_model)
    
    if specs.gpu:
        table.add_row("GPU", specs.gpu)
    if specs.gpu_vram_gb:
        table.add_row("VRAM GPU", f"{specs.gpu_vram_gb:.1f} GB")
    
    if specs.is_mobile:
        table.add_row("Tipo", "[yellow]Móvil[/yellow]")
    else:
        table.add_row("Tipo", "[cyan]Escritorio[/cyan]")
    
    if specs.is_termux:
        table.add_row("Entorno", "[magenta]Termux[/magenta]")
    
    console.print(table)
    
    # Mostrar modelos recomendados
    tier = Config.detect_tier()
    recommendations = Config.get_recommendations(tier)
    
    console.print(Panel(
        f"[bold blue]🎯 Modelos Recomendados para {Config.MODEL_RECOMMENDATIONS[tier]['name']}[/bold blue]",
        style="blue",
        box=box.DOUBLE
    ))
    
    model_table = Table(box=box.ROUNDED, show_header=True, header_style="bold cyan")
    model_table.add_column("Modelo", style="white")
    model_table.add_column("Tamaño", style="green")
    model_table.add_column("VRAM Requerida", style="yellow")
    model_table.add_column("Tipo", style="magenta")
    model_table.add_column("Fuente", style="cyan")
    
    for model in recommendations:
        model_type = model.get("type", "text")
        type_str = "🖼️ Multimodal" if model_type == "multimodal" else "📝 Texto"
        model_table.add_row(
            model["name"],
            model["size"],
            f"{model.get('vram', 0)} GB",
            type_str,
            model["source"]
        )
    
    console.print(model_table)


# ==================== GESTIÓN DE MODELOS ====================

@cli.group(name="models", help="Gestionar modelos de IA")
def models_group():
    """Comandos para gestionar modelos."""
    pass


@models_group.command(name="list", help="Listar modelos disponibles o locales")
@click.option("--local", is_flag=True, help="Listar solo modelos descargados")
@click.option("--source", type=str, help="Filtrar por fuente (ollama, huggingface, github)")
@click.option("--type", type=str, help="Filtrar por tipo (text, multimodal)")
def list_models(local: bool, source: str, type: str):
    """Lista modelos disponibles o descargados."""
    if local:
        # Listar modelos locales
        local_models = model_manager.list_local_models()
        
        if not local_models:
            console.print("[yellow]No hay modelos descargados localmente.[/yellow]")
            return
        
        table = Table(box=box.ROUNDED, show_header=True, header_style="bold cyan")
        table.add_column("ID", style="white")
        table.add_column("Nombre", style="green")
        table.add_column("Fuente", style="yellow")
        table.add_column("Ruta", style="white")
        table.add_column("Descargado", style="green")
        
        for model in local_models:
            table.add_row(
                str(model.id) if model.id else "-",
                model.name,
                model.source,
                str(model.path),
                "✅" if model.downloaded else "❌"
            )
        
        console.print(Panel(
            "[bold blue]📦 Modelos Locales[/bold blue]",
            style="blue",
            box=box.DOUBLE
        ))
        console.print(table)
    else:
        # Listar modelos disponibles
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("Obteniendo modelos disponibles...", total=None)
            available_models = model_manager.list_available_models(source)
            progress.update(task, completed=True)
        
        if not available_models:
            console.print("[yellow]No se encontraron modelos disponibles.[/yellow]")
            return
        
        # Filtrar por tipo si se especifica
        if type:
            available_models = [m for m in available_models if m.get("type") == type]
        
        table = Table(box=box.ROUNDED, show_header=True, header_style="bold cyan")
        table.add_column("Nombre", style="green")
        table.add_column("Tamaño", style="white")
        table.add_column("VRAM", style="yellow")
        table.add_column("Tipo", style="magenta")
        table.add_column("Fuente", style="cyan")
        table.add_column("ID", style="white")
        
        for model in available_models:
            model_type = model.get("type", "text")
            type_str = "🖼️ Multimodal" if model_type == "multimodal" else "📝 Texto"
            table.add_row(
                model["name"],
                model["size"],
                f"{model.get('vram', 0)} GB",
                type_str,
                model["source"],
                model["id"]
            )
        
        console.print(Panel(
            f"[bold blue]🌐 Modelos Disponibles{' (Filtrado: ' + source + ')' if source else ''}[/bold blue]",
            style="blue",
            box=box.DOUBLE
        ))
        console.print(table)


@models_group.command(name="search", help="Buscar modelos por nombre")
@click.argument("query", type=str)
@click.option("--source", type=str, help="Buscar en fuente específica")
def search_models(query: str, source: str):
    """Busca modelos por nombre."""
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task("Buscando modelos...", total=None)
        results = model_manager.search_models(query, source)
        progress.update(task, completed=True)
    
    if not results:
        console.print(f"[yellow]No se encontraron modelos para: {query}[/yellow]")
        return
    
    table = Table(box=box.ROUNDED, show_header=True, header_style="bold cyan")
    table.add_column("Nombre", style="green")
    table.add_column("Tamaño", style="white")
    table.add_column("VRAM", style="yellow")
    table.add_column("Tipo", style="magenta")
    table.add_column("Fuente", style="cyan")
    
    for model in results:
        model_type = model.get("type", "text")
        type_str = "🖼️ Multimodal" if model_type == "multimodal" else "📝 Texto"
        table.add_row(
            model["name"],
            model["size"],
            f"{model.get('vram', 0)} GB",
            type_str,
            model["source"]
        )
    
    console.print(Panel(
        f"[bold blue]🔍 Resultados para: {query}[/bold blue]",
        style="blue",
        box=box.DOUBLE
    ))
    console.print(table)


@cli.command(name="download", help="Descargar un modelo")
@click.argument("model_id", type=str)
@click.option("--source", type=click.Choice(Config.SUPPORTED_SOURCES), default="ollama",
              help="Fuente del modelo")
@click.option("--output", "-o", type=str, help="Directorio de salida")
def download_model(model_id: str, source: str, output: str):
    """Descarga un modelo desde la fuente especificada."""
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task(f"Descargando {model_id} desde {source}...", total=None)
        
        try:
            output_dir = Path(output) if output else None
            model_info = model_manager.download_model(model_id, source, output_dir)
            
            # Guardar en la base de datos
            record = ModelRecord(
                name=model_info.name,
                model_id=model_info.model_id,
                source=model_info.source,
                path=str(model_info.path),
                type=model_info.type,
                vram_required=model_info.vram_required
            )
            db.add_model(record)
            
            progress.update(task, completed=True)
            console.print(f"[green]✅ Modelo descargado: {model_info.name}[/green]")
            console.print(f"   [white]Ruta: {model_info.path}[/white]")
            console.print(f"   [white]Fuente: {model_info.source}[/white]")
            
        except Exception as e:
            progress.update(task, completed=True)
            console.print(f"[red]❌ Error al descargar: {e}[/red]")
            sys.exit(1)


@cli.command(name="delete", help="Eliminar un modelo descargado")
@click.argument("model_id", type=str)
@click.option("--source", type=str, help="Fuente del modelo")
def delete_model(model_id: str, source: str):
    """Elimina un modelo descargado."""
    try:
        success = model_manager.delete_model(model_id, source)
        if success:
            # Eliminar de la base de datos
            db.delete_model(model_id)
            console.print(f"[green]✅ Modelo eliminado: {model_id}[/green]")
        else:
            console.print(f"[yellow]⚠️ Modelo no encontrado: {model_id}[/yellow]")
    except Exception as e:
        console.print(f"[red]❌ Error al eliminar: {e}[/red]")
        sys.exit(1)


# ==================== EJECUCIÓN DE MODELOS ====================

@cli.command(name="run", help="Ejecutar inferencia con un modelo")
@click.argument("model_id", type=str)
@click.option("--prompt", "-p", type=str, required=True, help="Prompt de entrada")
@click.option("--model-type", type=click.Choice(["text", "multimodal"]), default="text",
              help="Tipo de modelo")
@click.option("--temperature", type=float, default=0.7, help="Temperatura para generación")
@click.option("--max-tokens", type=int, default=512, help="Máximo de tokens a generar")
def run_inference(model_id: str, prompt: str, model_type: str, temperature: float, max_tokens: int):
    """Ejecuta inferencia con un modelo."""
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task(f"Ejecutando {model_id}...", total=None)
        
        try:
            # Buscar el modelo localmente
            model_path = None
            local_models = model_manager.list_local_models()
            
            for model in local_models:
                if model.model_id == model_id or model.name == model_id:
                    model_path = model.path
                    model_type = model.type
                    break
            
            if not model_path:
                progress.update(task, completed=True)
                console.print(f"[red]❌ Modelo no encontrado: {model_id}[/red]")
                console.print("[white]Usa [bold]ailocal models --local[/bold] para ver modelos descargados.[/white]")
                sys.exit(1)
            
            # Ejecutar inferencia
            result: InferenceResult = executor.run_inference(
                model_path=model_path,
                prompt=prompt,
                model_type=model_type,
                temperature=temperature,
                max_new_tokens=max_tokens
            )
            
            progress.update(task, completed=True)
            
            # Guardar en historial
            db.add_inference(
                model_id=model_id,
                prompt=prompt,
                response=result.text,
                time_taken=result.time_taken,
                tokens=result.tokens_generated
            )
            
            if result.success:
                console.print(Panel(
                    f"[bold green]✅ Resultado de {model_id}[/bold green]",
                    style="green",
                    box=box.DOUBLE
                ))
                console.print(f"[white]Prompt: {prompt}[/white]")
                console.print(f"[white]---[/white]")
                console.print(f"[cyan]{result.text}[/cyan]")
                console.print(f"[white]---[/white]")
                console.print(f"[yellow]Tiempo: {result.time_taken:.2f}s | Tokens: {result.tokens_generated}[/yellow]")
            else:
                console.print(f"[red]❌ Error: {result.error}[/red]")
                sys.exit(1)
                
        except Exception as e:
            progress.update(task, completed=True)
            console.print(f"[red]❌ Error al ejecutar: {e}[/red]")
            sys.exit(1)


# ==================== INTEGRACIÓN CON GITHUB ====================

@cli.group(name="github", help="Gestionar conexión con GitHub")
def github_group():
    """Comandos para GitHub."""
    pass


@github_group.command(name="connect", help="Conectar con GitHub usando un token")
@click.argument("token", type=str)
def github_connect(token: str):
    """Guarda un token de GitHub para autenticación."""
    try:
        success = GitHubConnector.set_token(token)
        if success:
            # Validar el token
            if GitHubConnector.validate_token():
                console.print("[green]✅ Token guardado y validado correctamente![/green]")
                
                # Obtener info del usuario
                user_info = GitHubConnector.get_user_info()
                if user_info:
                    console.print(f"[white]Usuario: {user_info['login']}[/white]")
                    console.print(f"[white]Nombre: {user_info.get('name', 'N/A')}[/white]")
            else:
                console.print("[yellow]⚠️ Token guardado pero no es válido. Verifica que tenga los scopes correctos.[/yellow]")
        else:
            console.print("[red]❌ Error al guardar el token.[/red]")
            sys.exit(1)
    except Exception as e:
        console.print(f"[red]❌ Error: {e}[/red]")
        sys.exit(1)


@github_group.command(name="disconnect", help="Desconectar de GitHub")
def github_disconnect():
    """Elimina el token de GitHub guardado."""
    try:
        success = GitHubConnector.remove_token()
        if success:
            console.print("[green]✅ Token eliminado correctamente.[/green]")
        else:
            console.print("[yellow]⚠️ No había ningún token guardado.[/yellow]")
    except Exception as e:
        console.print(f"[red]❌ Error: {e}[/red]")
        sys.exit(1)


@github_group.command(name="repos", help="Listar repositorios de GitHub")
@click.option("--user", type=str, help="Usuario de GitHub (por defecto: el autenticado)")
@click.option("--org", type=str, help="Organización de GitHub")
@click.option("--starred", is_flag=True, help="Listar repositorios con estrella")
def github_repos(user: str, org: str, starred: bool):
    """Lista repositorios de GitHub."""
    if starred:
        repos = GitHubConnector.list_starred_repos()
        title = "Repositorios con Estrella"
    elif org:
        repos = GitHubConnector.get_org_repos(org)
        title = f"Repositorios de {org}"
    elif user:
        repos = GitHubConnector.get_user_repos(user)
        title = f"Repositorios de {user}"
    else:
        repos = GitHubConnector.get_user_repos()
        title = "Tus Repositorios"
    
    if not repos:
        console.print("[yellow]No se encontraron repositorios.[/yellow]")
        return
    
    table = Table(box=box.ROUNDED, show_header=True, header_style="bold cyan")
    table.add_column("Nombre", style="green")
    table.add_column("Privado", style="yellow")
    table.add_column("Estrellas", style="white")
    table.add_column("Forks", style="white")
    table.add_column("Descripción", style="white")
    
    for repo in repos:
        private_str = "✅" if repo.private else "❌"
        table.add_row(
            repo.full_name,
            private_str,
            str(repo.stars),
            str(repo.forks),
            repo.description[:50] + "..." if len(repo.description) > 50 else repo.description
        )
    
    console.print(Panel(
        f"[bold blue]📦 {title}[/bold blue]",
        style="blue",
        box=box.DOUBLE
    ))
    console.print(table)


@github_group.command(name="clone", help="Clonar un repositorio de GitHub")
@click.argument("repo", type=str)
@click.option("--branch", type=str, default="main", help="Rama a clonar")
@click.option("--output", "-o", type=str, help="Directorio de salida")
def github_clone(repo: str, branch: str, output: str):
    """Clona un repositorio de GitHub."""
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task(f"Clonando {repo} (rama: {branch})...", total=None)
        
        try:
            output_dir = Path(output) if output else Config.MODELS_DIR / "github" / repo.split("/")[-1]
            model_info = model_manager.download_model(repo, "github", output_dir)
            
            # Guardar en la base de datos
            record = ModelRecord(
                name=model_info.name,
                model_id=model_info.model_id,
                source="github",
                path=str(model_info.path),
                type="text"  # Default, can be detected later
            )
            db.add_model(record)
            
            progress.update(task, completed=True)
            console.print(f"[green]✅ Repositorio clonado: {repo}[/green]")
            console.print(f"   [white]Ruta: {model_info.path}[/white]")
            
        except Exception as e:
            progress.update(task, completed=True)
            console.print(f"[red]❌ Error al clonar: {e}[/red]")
            sys.exit(1)


# ==================== ESTADÍSTICAS ====================

@cli.command(name="stats", help="Mostrar estadísticas de uso")
def show_stats():
    """Muestra estadísticas de la base de datos."""
    stats = db.get_stats()
    
    console.print(Panel(
        "[bold blue]📊 Estadísticas de Uso[/bold blue]",
        style="blue",
        box=box.DOUBLE
    ))
    
    table = Table(box=box.ROUNDED, show_header=True, header_style="bold cyan")
    table.add_column("Categoría", style="white")
    table.add_column("Cantidad", style="green")
    
    table.add_row("Modelos descargados", str(stats["models"]))
    table.add_row("Repositorios de GitHub", str(stats["repositories"]))
    table.add_row("Historial de inferencias", str(stats["inference_history"]))
    
    console.print(table)
    
    if stats["sources"]:
        console.print("\n[bold]Por Fuente:[/bold]")
        for source, count in stats["sources"].items():
            console.print(f"  {source}: {count}")
    
    if stats["types"]:
        console.print("\n[bold]Por Tipo:[/bold]")
        for model_type, count in stats["types"].items():
            console.print(f"  {model_type}: {count}")


# ==================== INFORMACIÓN ====================

@cli.command(name="info", help="Mostrar información sobre un modelo")
@click.argument("model_id", type=str)
def show_info(model_id: str):
    """Muestra información detallada sobre un modelo."""
    # Buscar en modelos locales
    model_info = model_manager.get_model_info(model_id)
    
    if model_info:
        table = Table(box=box.ROUNDED, show_header=True, header_style="bold cyan")
        table.add_column("Propiedad", style="white")
        table.add_column("Valor", style="green")
        
        table.add_row("Nombre", model_info.name)
        table.add_row("ID", model_info.model_id)
        table.add_row("Fuente", model_info.source)
        table.add_row("Ruta", str(model_info.path))
        table.add_row("Tamaño", f"{model_info.size_bytes / (1024**2):.2f} MB" if model_info.size_bytes else "Desconocido")
        table.add_row("Tipo", model_info.type)
        table.add_row("VRAM Requerida", f"{model_info.vram_required} GB")
        table.add_row("Descargado", "✅" if model_info.downloaded else "❌")
        
        console.print(Panel(
            f"[bold blue]ℹ️ Información de {model_id}[/bold blue]",
            style="blue",
            box=box.DOUBLE
        ))
        console.print(table)
        return
    
    # Buscar en modelos disponibles
    available_models = model_manager.list_available_models()
    for model in available_models:
        if model.get("id") == model_id or model.get("name") == model_id:
            table = Table(box=box.ROUNDED, show_header=True, header_style="bold cyan")
            table.add_column("Propiedad", style="white")
            table.add_column("Valor", style="green")
            
            table.add_row("Nombre", model.get("name", "N/A"))
            table.add_row("ID", model.get("id", "N/A"))
            table.add_row("Fuente", model.get("source", "N/A"))
            table.add_row("Tamaño", model.get("size", "N/A"))
            table.add_row("VRAM Requerida", f"{model.get('vram', 0)} GB")
            table.add_row("Tipo", model.get("type", "text"))
            
            console.print(Panel(
                f"[bold blue]ℹ️ Información de {model_id}[/bold blue]",
                style="blue",
                box=box.DOUBLE
            ))
            console.print(table)
            return
    
    console.print(f"[yellow]⚠️ Modelo no encontrado: {model_id}[/yellow]")


# ==================== HISTORIAL ====================

@cli.command(name="history", help="Mostrar historial de inferencias")
@click.option("--model", type=str, help="Filtrar por modelo")
@click.option("--limit", type=int, default=10, help="Número de registros a mostrar")
def show_history(model: str, limit: int):
    """Muestra el historial de inferencias."""
    history = db.get_inference_history(model, limit)
    
    if not history:
        console.print("[yellow]No hay historial de inferencias.[/yellow]")
        return
    
    table = Table(box=box.ROUNDED, show_header=True, header_style="bold cyan")
    table.add_column("Modelo", style="green")
    table.add_column("Prompt", style="white")
    table.add_column("Tiempo", style="yellow")
    table.add_column("Tokens", style="cyan")
    table.add_column("Fecha", style="white")
    
    for record in history:
        table.add_row(
            record["model_id"][:20] + "..." if len(record["model_id"]) > 20 else record["model_id"],
            record["prompt"][:30] + "..." if len(record["prompt"]) > 30 else record["prompt"],
            f"{record['time_taken']:.2f}s",
            str(record["tokens_generated"]),
            record["created_at"][:19]  # Format: YYYY-MM-DD HH:MM:SS
        )
    
    console.print(Panel(
        "[bold blue]📜 Historial de Inferencias[/bold blue]",
        style="blue",
        box=box.DOUBLE
    ))
    console.print(table)


# ==================== LIMPIEZA ====================

@cli.command(name="clean", help="Limpiar caché y temporal")
@click.option("--all", is_flag=True, help="Eliminar todos los modelos")
@click.option("--history", is_flag=True, help="Eliminar historial de inferencias")
def clean(all: bool, history: bool):
    """Limpia archivos temporales y caché."""
    if all:
        # Eliminar todos los modelos
        local_models = model_manager.list_local_models()
        for model in local_models:
            model_manager.delete_model(model.model_id, model.source)
            db.delete_model(model.model_id)
        console.print("[green]✅ Todos los modelos eliminados.[/green]")
    
    if history:
        db.clear_inference_history()
        console.print("[green]✅ Historial de inferencias eliminado.[/green]")
    
    if not all and not history:
        console.print("[yellow]⚠️ Especifica --all o --history para limpiar algo.[/yellow]")
        console.print("[white]Ejemplo: ailocal clean --all[/white]")


# ==================== INICIO ====================

@cli.command(name="start", help="Iniciar la interfaz gráfica (GUI)")
def start_gui():
    """Inicia la interfaz gráfica con Streamlit."""
    try:
        import subprocess
        import sys
        
        # Check if streamlit is installed
        try:
            import streamlit
        except ImportError:
            console.print("[red]❌ Streamlit no está instalado.[/red]")
            console.print("[white]Instálalo con: pip install streamlit[/white]")
            sys.exit(1)
        
        # Start streamlit
        console.print("[green]🚀 Iniciando interfaz gráfica...[/green]")
        console.print("[white]Abre tu navegador en: http://localhost:8501[/white]")
        
        subprocess.Popen(
            [sys.executable, "-m", "streamlit", "run", "app/gui/app.py"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
    except Exception as e:
        console.print(f"[red]❌ Error al iniciar GUI: {e}[/red]")
        sys.exit(1)


# Entry point
if __name__ == "__main__":
    cli()
