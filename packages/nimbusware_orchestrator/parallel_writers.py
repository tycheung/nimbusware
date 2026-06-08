"""Concurrent writer-group dispatch via ``asyncio.gather``."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from dataclasses import dataclass


@dataclass(frozen=True)
class WriterStageResult:
    stage_name: str
    verifier_exit_code: int = 0
    verifier_log: str = ""


async def run_parallel_writer_group(
    stage_runners: list[tuple[str, Callable[[], WriterStageResult]]],
) -> list[WriterStageResult]:
    """Run each writer stage callable concurrently (sync work in ``asyncio.to_thread``)."""

    async def _run_one(
        stage_name: str,
        runner: Callable[[], WriterStageResult],
    ) -> WriterStageResult:
        result = await asyncio.to_thread(runner)
        if result.stage_name != stage_name:
            return WriterStageResult(
                stage_name=stage_name,
                verifier_exit_code=result.verifier_exit_code,
                verifier_log=result.verifier_log,
            )
        return result

    tasks = [_run_one(name, fn) for name, fn in stage_runners]
    return list(await asyncio.gather(*tasks))
