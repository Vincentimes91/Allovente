"""Allovente VPS gateway workflows — self-hosted worker.

The worker runs ON the VPS itself, so commands execute locally (subprocess):
no SSH, no private keys, no credentials in code. The worker authenticates to
Mistral with MISTRAL_API_KEY read from the environment (systemd EnvironmentFile).
"""

import asyncio
import os
from typing import Optional

from pydantic import BaseModel, Field

import mistralai.workflows as workflows

MAX_OUTPUT_CHARS = 200_000
MAX_FILE_BYTES = 500_000


class CommandInput(BaseModel):
    command: str = Field(description="Shell command to execute on the Allovente VPS")
    timeout_seconds: int = Field(default=120, ge=1, le=900)


class ReadFileInput(BaseModel):
    path: str = Field(description="Absolute path of the file to read on the VPS")
    max_bytes: int = Field(default=500_000, ge=1, le=5_000_000)


class CommandResult(BaseModel):
    exit_code: Optional[int] = None
    stdout: str = ""
    stderr: str = ""
    timed_out: bool = False
    error: Optional[str] = None


def _clip(text: str) -> str:
    if len(text) > MAX_OUTPUT_CHARS:
        return text[:MAX_OUTPUT_CHARS] + f"\n...[truncated, {len(text)} chars total]"
    return text


@workflows.activity()
async def exec_command(command: str, timeout_seconds: int) -> CommandResult:
    try:
        proc = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=os.path.expanduser("~ubuntu"),
        )
        try:
            out, err = await asyncio.wait_for(proc.communicate(), timeout=timeout_seconds)
        except asyncio.TimeoutError:
            try:
                proc.kill()
            except ProcessLookupError:
                pass
            return CommandResult(timed_out=True, error="Command timed out")
        return CommandResult(
            exit_code=proc.returncode,
            stdout=_clip(out.decode("utf-8", errors="replace")),
            stderr=_clip(err.decode("utf-8", errors="replace")),
        )
    except Exception as exc:
        return CommandResult(error=f"Exec error: {type(exc).__name__}: {exc}")


@workflows.activity()
async def read_file(path: str, max_bytes: int) -> CommandResult:
    try:
        with open(path, "rb") as f:
            data = f.read(max_bytes + 1)
        out = data.decode("utf-8", errors="replace")
        if len(data) > max_bytes:
            out += "\n...[truncated]"
        return CommandResult(exit_code=0, stdout=out)
    except Exception as exc:
        return CommandResult(error=f"Read error: {type(exc).__name__}: {exc}")


@workflows.workflow.define(
    name="allovente-ssh",
    workflow_display_name="Allovente SSH",
    workflow_description=(
        "Exécute une commande shell sur le VPS Allovente via le worker auto-hébergé."
    ),
)
class AlloventeSSHWorkflow:
    @workflows.workflow.entrypoint
    async def run(self, input: CommandInput) -> dict:
        result = await exec_command(input.command, input.timeout_seconds)
        return result.model_dump()


@workflows.workflow.define(
    name="allovente-read-file",
    workflow_display_name="Allovente Read File",
    workflow_description="Lit un fichier du VPS Allovente via le worker auto-hébergé.",
)
class AlloventeReadFileWorkflow:
    @workflows.workflow.entrypoint
    async def run(self, input: ReadFileInput) -> dict:
        result = await read_file(input.path, input.max_bytes)
        return result.model_dump()
