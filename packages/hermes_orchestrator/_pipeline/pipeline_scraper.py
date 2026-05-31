from __future__ import annotations

from hermes_orchestrator._pipeline._helpers import *  # noqa: F403
from nimbusware_env.env_flags import hermes_outbound_fetch_enabled


class PipelineScraperMixin:
    def egress_checked_fetch_url(
        self,
        run_id: UUID,
        url: str,
        actor_role_id: UUID,
        *,
        timeout_seconds: float = 30.0,
        client: httpx.Client | None = None,
    ) -> httpx.Response:
        """Opt-in outbound GET using frozen ``run.created`` egress policy.

        Set ``HERMES_OUTBOUND_FETCH_ENABLED=1`` (or ``true``/``yes``) to allow network I/O.
        """
        if not hermes_outbound_fetch_enabled():
            msg = (
                "Set HERMES_OUTBOUND_FETCH_ENABLED=1 to perform outbound GET "
                "from the orchestrator"
            )
            raise RuntimeError(msg)
        return egress_checked_get_for_run(
            self._store,
            run_id,
            url,
            actor_role_id=actor_role_id,
            timeout_seconds=timeout_seconds,
            client=client,
        )

    @staticmethod

    def _parse_content_length_header(resp: httpx.Response) -> int | None:
        raw = resp.headers.get("content-length")
        if raw is None:
            return None
        try:
            return int(raw)
        except ValueError:
            return None

    @staticmethod

    def _scraper_stage_audit_metadata(
        host: str,
        http_status: int,
        nbytes: int,
        attempts_used: int,
        *,
        content_length_header: int | None = None,
    ) -> dict[str, Any]:
        inner: dict[str, Any] = {
            "url_host": host,
            "http_status": http_status,
            "bytes": nbytes,
            "attempts": attempts_used,
        }
        if content_length_header is not None:
            inner["content_length"] = content_length_header
        return {"scraper_fetch": inner}

    @staticmethod

    def _scraper_body_digest_and_snippet(content: bytes, snippet_max_bytes: int) -> dict[str, Any]:
        out: dict[str, Any] = {"body_sha256_hex": hashlib.sha256(content).hexdigest()}
        if snippet_max_bytes > 0:
            raw = content[:snippet_max_bytes]
            out["body_snippet_preview"] = raw.decode("utf-8", errors="replace")
        return out


    def _persist_scraper_response_artifact(
        self,
        run_id: UUID,
        url_index: int,
        content: bytes,
        persist_cap: int,
    ) -> dict[str, Any]:
        """Write truncated response bytes; object-store primary when Enterprise edition."""
        from hermes_orchestrator.scraper_artifacts import persist_scraper_artifact

        return persist_scraper_artifact(
            self._repo_root,
            run_id,
            url_index,
            content,
            persist_cap,
        )


    def _scraper_get_with_retries(
        self,
        run_id: UUID,
        scraper_url: str,
        actor: UUID,
        client: httpx.Client | None,
        cfg: ScraperFetchConfig,
        max_response_bytes: int | None,
    ) -> tuple[httpx.Response, int]:
        last_err: BaseException | None = None
        for attempt in range(1, cfg.max_attempts + 1):
            try:
                fetch_kw: dict[str, Any] = {
                    "timeout_seconds": 30.0,
                    "client": client,
                }
                if max_response_bytes is not None:
                    fetch_kw["max_response_bytes"] = max_response_bytes
                resp = egress_checked_get_for_run(
                    self._store,
                    run_id,
                    scraper_url,
                    actor_role_id=actor,
                    **fetch_kw,
                )
                return resp, attempt
            except PermissionError:
                raise
            except EgressResponseTooLarge:
                raise
            except (OSError, RuntimeError, ValueError, httpx.HTTPError) as exc:
                last_err = exc
                if attempt >= cfg.max_attempts:
                    break
                if cfg.backoff_seconds > 0:
                    time.sleep(cfg.backoff_seconds)
        msg = str(last_err)[:2000] if last_err else "scraper fetch failed"
        raise RuntimeError(msg)


    def _effective_scraper_budget_bytes(
        self,
        run_id: UUID,
        cfg: ScraperFetchConfig,
    ) -> int | None:
        snap = self.policy_snapshot_for_run(run_id)
        ne = snap.get("network_egress") if isinstance(snap, dict) else None
        policy_b: int | None = None
        if isinstance(ne, dict):
            pb = ne.get("budget_bytes_per_run")
            if isinstance(pb, int) and pb >= 0:
                policy_b = pb
        caps: list[int] = []
        if policy_b is not None:
            caps.append(policy_b)
        if cfg.max_bytes is not None:
            caps.append(cfg.max_bytes)
        return min(caps) if caps else None


    def run_optional_scraper_fetch_stage(
        self,
        run_id: UUID,
        *,
        client: httpx.Client | None = None,
    ) -> None:
        """Optional ``scraper:fetch`` stage from workflow YAML (requires env for HTTP)."""
        wf = workflow_profile_from_run_created_rows(self._store.list_run_events(str(run_id)))
        if not wf:
            return
        cfg = load_scraper_fetch_config(
            self._repo_root,
            wf,
            config_materializer=self._config_materializer,
        )
        if not cfg.enabled or not cfg.fetch_urls:
            return
        first_host = urlparse(cfg.fetch_urls[0]).hostname or ""
        self._store.append(
            StageStartedEvent(
                event_type=EventType.STAGE_STARTED,
                event_id=uuid4(),
                run_id=run_id,
                occurred_at=datetime.now(timezone.utc),
                payload=StageStartedPayload(stage_name="scraper:fetch", attempt=1),
            ),
        )
        if not hermes_outbound_fetch_enabled():
            self._store.append(
                StageFailedEvent(
                    event_type=EventType.STAGE_FAILED,
                    event_id=uuid4(),
                    run_id=run_id,
                    occurred_at=datetime.now(timezone.utc),
                    metadata=self._scraper_stage_audit_metadata(first_host, 0, 0, 0),
                    payload=StageFailedPayload(
                        stage_name="scraper:fetch",
                        reason_code="outbound_fetch_disabled",
                        message="HERMES_OUTBOUND_FETCH_ENABLED not set",
                    ),
                ),
            )
            return
        budget = self._effective_scraper_budget_bytes(run_id, cfg)
        remaining: int | None = budget
        actor = self._registry.resolve(cfg.actor_role_key)
        fetches_out: list[dict[str, Any]] = []

        def fail_meta(host: str, partial: list[dict[str, Any]]) -> dict[str, Any]:
            inner: dict[str, Any] = {"fetches": list(partial)}
            if host:
                inner["failed_url_host"] = host
            return {"scraper_fetch": inner}

        for url_index, scraper_url in enumerate(cfg.fetch_urls):
            parsed_host = urlparse(scraper_url).hostname or ""
            per_cap = remaining if remaining is not None else None
            if per_cap is not None and per_cap <= 0:
                self._store.append(
                    StageFailedEvent(
                        event_type=EventType.STAGE_FAILED,
                        event_id=uuid4(),
                        run_id=run_id,
                        occurred_at=datetime.now(timezone.utc),
                        metadata=fail_meta(parsed_host, fetches_out),
                        payload=StageFailedPayload(
                            stage_name="scraper:fetch",
                            reason_code="scraper_budget_exceeded",
                            message="no bytes remaining for next URL",
                        ),
                    ),
                )
                return
            try:
                resp, attempts_used = self._scraper_get_with_retries(
                    run_id,
                    scraper_url,
                    actor,
                    client,
                    cfg,
                    per_cap,
                )
            except PermissionError as exc:
                self._store.append(
                    StageFailedEvent(
                        event_type=EventType.STAGE_FAILED,
                        event_id=uuid4(),
                        run_id=run_id,
                        occurred_at=datetime.now(timezone.utc),
                        metadata=fail_meta(parsed_host, fetches_out),
                        payload=StageFailedPayload(
                            stage_name="scraper:fetch",
                            reason_code="egress_denied",
                            message=str(exc)[:2000],
                        ),
                    ),
                )
                return
            except EgressResponseTooLarge as exc:
                self._store.append(
                    StageFailedEvent(
                        event_type=EventType.STAGE_FAILED,
                        event_id=uuid4(),
                        run_id=run_id,
                        occurred_at=datetime.now(timezone.utc),
                        metadata=fail_meta(parsed_host, fetches_out),
                        payload=StageFailedPayload(
                            stage_name="scraper:fetch",
                            reason_code="scraper_budget_exceeded",
                            message=str(exc)[:2000],
                        ),
                    ),
                )
                return
            except RuntimeError as exc:
                self._store.append(
                    StageFailedEvent(
                        event_type=EventType.STAGE_FAILED,
                        event_id=uuid4(),
                        run_id=run_id,
                        occurred_at=datetime.now(timezone.utc),
                        metadata=fail_meta(parsed_host, fetches_out),
                        payload=StageFailedPayload(
                            stage_name="scraper:fetch",
                            reason_code="scraper_fetch_error",
                            message=str(exc)[:2000],
                        ),
                    ),
                )
                return
            nbytes = len(resp.content)
            status_code = int(resp.status_code)
            cl_hdr = self._parse_content_length_header(resp)
            row: dict[str, Any] = {
                "url_host": parsed_host,
                "http_status": status_code,
                "bytes": nbytes,
                "attempts": attempts_used,
            }
            if cl_hdr is not None:
                row["content_length"] = cl_hdr
            row.update(
                self._scraper_body_digest_and_snippet(resp.content, cfg.body_snippet_max_bytes),
            )
            if cfg.persist_artifacts_max_bytes_per_url is not None:
                try:
                    row.update(
                        self._persist_scraper_response_artifact(
                            run_id,
                            url_index,
                            resp.content,
                            cfg.persist_artifacts_max_bytes_per_url,
                        ),
                    )
                except OSError as exc:
                    self._store.append(
                        StageFailedEvent(
                            event_type=EventType.STAGE_FAILED,
                            event_id=uuid4(),
                            run_id=run_id,
                            occurred_at=datetime.now(timezone.utc),
                            metadata=fail_meta(parsed_host, fetches_out),
                            payload=StageFailedPayload(
                                stage_name="scraper:fetch",
                                reason_code="scraper_fetch_error",
                                message=f"artifact write failed: {exc!s}"[:2000],
                            ),
                        ),
                    )
                    return
            fetches_out.append(row)
            if remaining is not None:
                remaining -= nbytes

        self._store.append(
            StagePassedEvent(
                event_type=EventType.STAGE_PASSED,
                event_id=uuid4(),
                run_id=run_id,
                occurred_at=datetime.now(timezone.utc),
                metadata={"scraper_fetch": {"fetches": fetches_out}},
                payload=StagePassedPayload(stage_name="scraper:fetch", duration_ms=0),
            ),
        )

