"""Worker entrypoint: registers the Allovente VPS gateway workflows and starts the worker."""

import asyncio

import mistralai.workflows as workflows

from cmd_exec import AlloventeSSHWorkflow, AlloventeReadFileWorkflow


async def main() -> None:
    await workflows.run_worker([AlloventeSSHWorkflow, AlloventeReadFileWorkflow])


if __name__ == "__main__":
    asyncio.run(main())
