BEGIN READ ONLY;
SET LOCAL statement_timeout = '15s';
SET LOCAL lock_timeout = '2s';
SET LOCAL TIME ZONE 'America/New_York';
WITH reports AS (
    SELECT installation_id, received_at, payload,
           payload->>'miner_version' AS version, payload->'diagnostics' AS diagnostics
    FROM telemetry_reports
    WHERE received_at >= now() - interval '7 days'
      AND NOT (payload->>'debug_build')::boolean
), covered AS (
    SELECT * FROM reports WHERE diagnostics IS NOT NULL AND diagnostics <> 'null'::jsonb
), versions AS (
    SELECT version, count(DISTINCT installation_id) AS installations,
           count(DISTINCT installation_id) FILTER (WHERE diagnostics IS NOT NULL AND diagnostics <> 'null'::jsonb) AS diagnostic_installations
    FROM reports GROUP BY 1
), events AS (
    SELECT installation_id, received_at, version, payload, diagnostics, event
    FROM covered CROSS JOIN LATERAL jsonb_array_elements(diagnostics->'events') event
), clusters AS (
    SELECT version, diagnostics->>'build_commit' AS build_commit,
           diagnostics->>'source_fingerprint' AS source_fingerprint,
           payload #>> '{hardware,cpu_model}' AS cpu,
           payload #>> '{hardware,os}' AS os,
           payload #>> '{hardware,runtime_environment}' AS environment,
           diagnostics->>'mode' AS mode,
           diagnostics->'requested_backends' AS requested_backends,
           event->>'code' AS code, event->>'kind' AS kind,
           event->>'source' AS source, (event->>'line')::int AS line,
           event->>'backend' AS backend,
           event->'detail' AS detail, event->>'phase' AS phase,
           diagnostics->>'cpu_page_mode' AS requested_page_mode,
           (diagnostics->>'requested_cpu_threads')::int AS requested_threads,
           min((payload #>> '{hardware,resources,available_memory_gib}')::int) AS minimum_reported_available_memory_gib,
           count(DISTINCT installation_id) AS affected_installations,
           sum((event->>'count')::bigint) AS occurrences,
           max(received_at) AS last_received
    FROM events GROUP BY 1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17
), unclean_clusters AS (
    SELECT version, diagnostics->>'build_commit' AS build_commit,
           payload #>> '{hardware,cpu_model}' AS cpu,
           payload #>> '{hardware,os}' AS os,
           payload #>> '{hardware,runtime_environment}' AS environment,
           diagnostics #>> '{previous_run,phase}' AS last_observed_phase,
           diagnostics #>> '{previous_run,build_commit}' AS previous_build_commit,
           min((diagnostics #>> '{previous_run,uptime_secs}')::bigint) AS minimum_previous_uptime_secs,
           max((diagnostics #>> '{previous_run,uptime_secs}')::bigint) AS maximum_previous_uptime_secs,
           count(DISTINCT installation_id) AS affected_installations,
           count(DISTINCT installation_id) FILTER (WHERE EXISTS (
               SELECT 1 FROM jsonb_array_elements(payload->'backends') b
               WHERE (b->>'hashes')::bigint > 0
           )) AS installations_hashing_in_restart_report,
           max(received_at) AS last_received
    FROM covered WHERE received_at >= now() - interval '24 hours'
      AND (diagnostics->>'previous_run_unclean')::boolean
    GROUP BY 1,2,3,4,5,6,7
), recent_errors AS (
    SELECT version, count(DISTINCT installation_id) AS affected_installations
    FROM events WHERE received_at >= now() - interval '24 hours'
      AND event->>'code' IN ('error','backend_error','backend_quarantined','run_failed','rust_panic')
    GROUP BY 1
), recent_unclean AS (
    SELECT version, count(DISTINCT installation_id) AS affected_installations
    FROM covered WHERE received_at >= now() - interval '24 hours'
      AND (diagnostics->>'previous_run_unclean')::boolean
    GROUP BY 1
)
SELECT jsonb_build_object(
    'window_days', 7,
    'diagnostic_installations', (SELECT count(DISTINCT installation_id) FROM covered),
    'versions', coalesce((SELECT jsonb_agg(versions ORDER BY version) FROM versions), '[]'::jsonb),
    'issue_clusters', coalesce((SELECT jsonb_agg(c) FROM (SELECT * FROM clusters ORDER BY (code IN ('error','backend_error','backend_quarantined','run_failed','rust_panic')) DESC, (detail IS NOT NULL) DESC, affected_installations DESC, occurrences DESC, version, source, line LIMIT 30) c), '[]'::jsonb),
    'unclean_run_clusters', coalesce((SELECT jsonb_agg(c) FROM (SELECT * FROM unclean_clusters ORDER BY affected_installations DESC, last_received DESC LIMIT 30) c), '[]'::jsonb),
    'unclean_run_installations', (SELECT count(DISTINCT installation_id) FROM covered WHERE (diagnostics->>'previous_run_unclean')::boolean),
    'reports_with_dropped_diagnostics', (SELECT count(*) FROM covered WHERE (diagnostics->>'dropped_events')::bigint > 0 OR (diagnostics->>'dropped_backend_samples')::bigint > 0),
    'recent_error_versions', coalesce((SELECT jsonb_agg(recent_errors ORDER BY version) FROM recent_errors), '[]'::jsonb),
    'recent_unclean_versions', coalesce((SELECT jsonb_agg(recent_unclean ORDER BY version) FROM recent_unclean), '[]'::jsonb),
    'status', CASE WHEN EXISTS (SELECT 1 FROM recent_errors WHERE affected_installations >= 3)
                    OR EXISTS (SELECT 1 FROM recent_unclean WHERE affected_installations >= 3) THEN 'attention'
                   WHEN NOT EXISTS (SELECT 1 FROM covered) THEN 'unavailable' ELSE 'ok' END
);
ROLLBACK;
