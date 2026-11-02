"""SSH gateway workflows for the Allovente VPS.

Credentials never appear in code: the worker reads the SSH private key from the
ALOVENTE_SSH_KEY environment variable, bound to a Mistral workspace secret on
the managed deployment. The VPS host key is pinned below, so a man-in-the-middle
cannot silently intercept the connection.
"""

import asyncio
import base64
import io
import os
from typing import Optional

import paramiko
from pydantic import BaseModel, Field

import mistralai.workflows as workflows

# --- Pinned VPS configuration (host key pinned = MITM-proof) ---
VPS_HOST = os.environ.get("ALLOVENTE_VPS_HOST", "57.129.153.119")
VPS_PORT = int(os.environ.get("ALLOVENTE_VPS_PORT", "22"))
VPS_USER = os.environ.get("ALLOVENTE_VPS_USER", "ubuntu")
VPS_HOST_KEY_TYPE = "ssh-ed25519"
VPS_HOST_KEY_B64 = (
    "AAAAC3NzaC1lZDI1NTE5AAAAIEVFFlzXeXc4yytmp9zLs6OhxES2Avgr3pgBEhgNS0eK"
)
MAX_OUTPUT_CHARS = 200_000


class SshCommandInput(BaseModel):
    command: str = Field(description="Shell command to execute on the Allovente VPS")
    timeout_seconds: int = Field(default=120, ge=1, le=900)


class SshCommandResult(BaseModel):
    exit_code: Optional[int] = None
    stdout: str = ""
    stderr: str = ""
    timed_out: bool = False
    error: Optional[str] = None


class ReadFileInput(BaseModel):
    path: str = Field(description="Absolute path of the file to read on the VPS")
    max_bytes: int = Field(default=500_000, ge=1, le=5_000_000)


def _connect() -> paramiko.SSHClient:
    key_text = os.environ.get("ALOVENTE_SSH_KEY") or os.environ.get("ALLOVENTE_SSH_KEY")
    if not key_text:
        raise RuntimeError(
            "ALOVENTE_SSH_KEY is not set: bind the workspace secret on the deployment."
        )
    key_text = key_text.strip().replace("\\n", "\n")
    if not key_text.endswith("\n"):
        key_text += "\n"
    key: paramiko.pkey.PKey
    try:
        key = paramiko.Ed25519Key.from_private_key(io.StringIO(key_text))
    except Exception:
        try:
            key = paramiko.RSAKey.from_private_key(io.StringIO(key_text))
        except Exception as exc:
            raise RuntimeError(f"Could not parse ALOVENTE_SSH_KEY as Ed25519/RSA key: {exc}")

    client = paramiko.SSHClient()
    client.get_host_keys().add(
        VPS_HOST, VPS_HOST_KEY_TYPE, paramiko.Ed25519Key(data=base64.b64decode(VPS_HOST_KEY_B64))
    )
    client.set_missing_host_key_policy(paramiko.RejectPolicy())
    client.connect(
        hostname=VPS_HOST,
        port=VPS_PORT,
        username=VPS_USER,
        pkey=key,
        timeout=20,
        banner_timeout=20,
        auth_timeout=20,
        allow_agent=False,
        look_for_keys=False,
    )
    return client


def _clip(text: str) -> str:
    if len(text) > MAX_OUTPUT_CHARS:
        return text[:MAX_OUTPUT_CHARS] + f"\n...[truncated, {len(text)} chars total]"
    return text


@workflows.activity()
async def ssh_exec(command: str, timeout_seconds: int) -> SshCommandResult:
    def _run() -> SshCommandResult:
        client = _connect()
        try:
            stdin, stdout, stderr = client.exec_command(
                command, timeout=timeout_seconds
            )
            stdin.channel.shutdown_write()
            out = stdout.read().decode("utf-8", errors="replace")
            err = stderr.read().decode("utf-8", errors="replace")
            rc = stdout.channel.recv_exit_status()
            return SshCommandResult(exit_code=rc, stdout=_clip(out), stderr=_clip(err))
        finally:
            client.close()

    try:
        return await asyncio.wait_for(asyncio.to_thread(_run), timeout=timeout_seconds + 30)
    except asyncio.TimeoutError:
        return SshCommandResult(timed_out=True, error="SSH command timed out")
    except Exception as exc:
        return SshCommandResult(error=f"SSH error: {type(exc).__name__}: {exc}")


@workflows.activity()
async def ssh_read_file(path: str, max_bytes: int) -> SshCommandResult:
    def _run() -> SshCommandResult:
        client = _connect()
        try:
            sftp = client.open_sftp()
            try:
                with sftp.open(path, "r") as f:
                    data = f.read(max_bytes + 1)
                out = data.decode("utf-8", errors="replace")
                if len(data) > max_bytes:
                    out += "\n...[truncated]"
                return SshCommandResult(exit_code=0, stdout=out)
            finally:
                sftp.close()
        finally:
            client.close()

    try:
        return await asyncio.wait_for(asyncio.to_thread(_run), timeout=90)
    except asyncio.TimeoutError:
        return SshCommandResult(timed_out=True, error="SFTP read timed out")
    except Exception as exc:
        return SshCommandResult(error=f"SFTP error: {type(exc).__name__}: {exc}")


@workflows.workflow.define(
    name="allovente-ssh",
    workflow_display_name="Allovente SSH",
    workflow_description=(
        "Exécute une commande shell sur le VPS Allovente (ubuntu@57.129.153.119) "
        "via la clé SSH stockée dans le secret de workspace."
    ),
)
class AlloventeSSHWorkflow:
    @workflows.workflow.entrypoint
    async def run(self, input: SshCommandInput) -> dict:
        result = await ssh_exec(input.command, input.timeout_seconds)
        return result.model_dump()


@workflows.workflow.define(
    name="allovente-read-file",
    workflow_display_name="Allovente Read File",
    workflow_description="Lit un fichier du VPS Allovente via SFTP (sans exécution de commande).",
)
class AlloventeReadFileWorkflow:
    @workflows.workflow.entrypoint
    async def run(self, input: ReadFileInput) -> dict:
        result = await ssh_read_file(input.path, input.max_bytes)
        return result.model_dump()
